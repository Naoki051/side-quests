from repositories import pessoa_repo, residencia_repo, documento_repo

def buscar_perfil_completo(id_pessoa, path_p, path_r, path_d):
    """
    Consolida todos os dados de uma pessoa: 
    Residência, Documentos, Dependentes e Responsável.
    """
    # 1. Buscar a Entidade Principal
    pessoa = pessoa_repo.buscar_por_id(id_pessoa, path_p)
    if not pessoa:
        return None

    # 2. Buscar Entidades Relacionadas (Residência e Documentos)
    residencia = None
    if pessoa.id_residencia:
        residencia = residencia_repo.buscar_por_id(pessoa.id_residencia, path_r)

    documentos = documento_repo.buscar_por_pessoa(id_pessoa, path_d)
    
    # 3. Buscar Dependentes (Descendo na árvore)
    dependentes = pessoa_repo.buscar_dependentes(id_pessoa, path_p)

    # 4. Buscar Responsável (Subindo na árvore)
    responsavel = pessoa_repo.buscar_responsavel(id_pessoa, path_p)

    # 5. Montar o Objeto Consolidado para o Front
    return {
        "pessoa": pessoa.to_dict(),
        "residencia": residencia.to_dict() if residencia else None,
        "documentos": [d.to_dict() for d in documentos],
        "responsavel": {
            "id": responsavel.id, 
            "nome": responsavel.nome
        } if responsavel else None,
        "dependentes": [
            {"id": dep.id, "nome": dep.nome, "parentesco": dep.parentesco} 
            for dep in dependentes
        ]
    }

def buscar_pessoa_por_documento(tipo, valor, path_p, path_r, path_d):
    """
    Busca por documento e retorna o perfil completo.
    """
    doc = documento_repo.buscar_por_chave(tipo, valor, path_d)
    if not doc:
        return None
    
    return buscar_perfil_completo(doc.id_pessoa, path_p, path_r, path_d)