from models.pessoa import Pessoa
from models.residencia import Residencia
from models.documento import Documento
from repositories import pessoa_repo, residencia_repo, documento_repo

def realizar_cadastro_completo(payload, path_p, path_r, path_d):
    # Extraímos as "gavetas" do payload
    dados_pessoa = payload.get("pessoa", {})
    dados_residencia = payload.get("residencia", {})
    list_documentos = payload.get("documentos", [])

    # ==========================================================
    # 1. VALIDAR DOCUMENTOS ANTES (Fail Fast)
    # ==========================================================
    for doc_item in list_documentos:
        existente = documento_repo.buscar_por_chave(
            doc_item.get("tipo"),
            doc_item.get("valor"),
            path_d
        )
        if existente:
            raise ValueError(f"Documento {doc_item.get('tipo')} já cadastrado.")

    # ==========================================================
    # 2. RESOLVER RESIDÊNCIA (Get or Create)
    # ==========================================================
    id_residencia_final = None

    # Verificamos se há dados mínimos de residência no payload
    if (dados_residencia.get("cep") or dados_residencia.get("logradouro")) and dados_residencia.get("numero"):
        res_info = Residencia(
            cep=dados_residencia.get("cep"),
            logradouro=dados_residencia.get("logradouro"),
            numero=dados_residencia.get("numero"),
            bairro=dados_residencia.get("bairro"),
            cidade=dados_residencia.get("cidade"),
            estado=dados_residencia.get("estado")
        )

        trinca = res_info.get_chave_identificadora()
        existente = residencia_repo.buscar_por_trinca(trinca, path_r)

        if existente:
            id_residencia_final = existente.id
        else:
            id_residencia_final = residencia_repo.salvar(res_info, path_r).id

    # ==========================================================
    # 3. LÓGICA DE HERANÇA
    # ==========================================================
    id_resp = dados_pessoa.get("id_responsavel")

    if id_resp and not id_residencia_final:
        responsavel = pessoa_repo.buscar_por_id(id_resp, path_p)
        if not responsavel:
            raise ValueError("Responsável não encontrado.")
        id_residencia_final = responsavel.id_residencia

    # ==========================================================
    # 4. CRIAR PESSOA
    # ==========================================================
    nova_pessoa = Pessoa(
        nome=dados_pessoa.get("nome"),
        celular=dados_pessoa.get("celular"),
        data_nascimento=dados_pessoa.get("data_nascimento"),
        id_responsavel=id_resp,
        parentesco=dados_pessoa.get("parentesco"),
        id_residencia=id_residencia_final
    )

    pessoa_salva = pessoa_repo.salvar(nova_pessoa, path_p)

    # ==========================================================
    # 5. SALVAR DOCUMENTOS
    # ==========================================================
    documentos_salvos = []

    for doc_item in list_documentos:
        novo_doc = Documento(
            tipo=doc_item.get("tipo"),
            valor=doc_item.get("valor"),
            id_pessoa=pessoa_salva.id
        )

        doc_final = documento_repo.salvar(novo_doc, path_d)
        documentos_salvos.append(doc_final)

    # ==========================================================
    # 6. RETORNO ESTRUTURADO
    # ==========================================================
    return {
        "status": "sucesso",
        "data": {
            "pessoa": pessoa_salva.to_dict(),
            "residencia_id": id_residencia_final,
            "documentos_total": len(documentos_salvos)
        }
    }