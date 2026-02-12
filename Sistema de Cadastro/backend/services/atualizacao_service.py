from datetime import datetime, timezone
from repositories import pessoa_repo, residencia_repo, documento_repo
from models.residencia import Residencia
from models.documento import Documento

def realizar_atualizacao_completa(id_pessoa, payload, path_p, path_r, path_d):
    """
    Atualiza os dados de uma pessoa e seus vínculos de forma granular.
    Auditado apenas para Pessoa e Residência.
    """
    resumo_alteracoes = []
    agora = datetime.now(timezone.utc).isoformat()

    # 1. BUSCAR REGISTRO ATUAL
    pessoa_atual = pessoa_repo.buscar_por_id(id_pessoa, path_p)
    if not pessoa_atual:
        raise ValueError("Pessoa não encontrada para atualização.")

    # ==========================================================
    # 2. ATUALIZAR DADOS DA PESSOA
    # ==========================================================
    dados_pessoa = payload.get("pessoa")
    if dados_pessoa:
        dados_pessoa["data_atualizacao"] = agora # Mantém auditoria
        pessoa_repo.atualizar(id_pessoa, dados_pessoa, path_p)
        resumo_alteracoes.append("pessoa")

    # ==========================================================
    # 3. ATUALIZAR RESIDÊNCIA
    # ==========================================================
    dados_res = payload.get("residencia")
    if dados_res:
        res_temp = Residencia(
            cep=dados_res.get("cep"),
            logradouro=dados_res.get("logradouro"),
            numero=dados_res.get("numero"),
            bairro=dados_res.get("bairro"),
            cidade=dados_res.get("cidade"),
            estado=dados_res.get("estado")
        )
        
        trinca = res_temp.get_chave_identificadora()
        res_existente = residencia_repo.buscar_por_trinca(trinca, path_r)
        
        id_nova_residencia = None
        if res_existente:
            id_nova_residencia = res_existente.id
            # Atualiza apenas o timestamp da casa existente
            residencia_repo.atualizar(id_nova_residencia, {"data_atualizacao": agora}, path_r)
        else:
            nova_res = residencia_repo.salvar(res_temp, path_r)
            id_nova_residencia = nova_res.id

        if id_nova_residencia != pessoa_atual.id_residencia:
            pessoa_repo.atualizar(id_pessoa, {"id_residencia": id_nova_residencia}, path_p)
            resumo_alteracoes.append("residencia (vinculo alterado)")
        else:
            resumo_alteracoes.append("residencia (dados corrigidos)")

    # ==========================================================
    # 4. ATUALIZAR DOCUMENTOS (Upsert sem data de atualização)
    # ==========================================================
    list_docs = payload.get("documentos")
    if list_docs is not None:
        for doc_item in list_docs:
            id_doc = doc_item.get("id")
            
            if id_doc:
                # Se tem ID, atualizamos o valor/tipo diretamente
                # Linha de data_atualizacao REMOVIDA
                documento_repo.atualizar(id_doc, doc_item, path_d)
            else:
                novo_doc = Documento(
                    tipo=doc_item.get("tipo"),
                    valor=doc_item.get("valor"),
                    id_pessoa=id_pessoa
                )
                if not documento_repo.buscar_por_chave(novo_doc.tipo, novo_doc.valor, path_d):
                    documento_repo.salvar(novo_doc, path_d)
        
        resumo_alteracoes.append("documentos")

    return {
        "status": "sucesso",
        "id_pessoa": id_pessoa,
        "alteracoes": resumo_alteracoes,
        "data_finalizacao": agora
    }