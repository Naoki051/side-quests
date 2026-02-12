from models.residencia import Residencia
from database.persistence import carregar_dados, salvar_dados
# ==========================================================
# CREATE
# ==========================================================

def salvar(residencia_obj, path):
    db = carregar_dados(path)
    db.append(residencia_obj.to_dict())
    salvar_dados(db, path)
    return residencia_obj
# ==========================================================
# READ
# ==========================================================

def buscar_por_trinca(trinca, path):
    db = carregar_dados(path)

    trinca = trinca.upper()

    for r in db:
        obj = Residencia.from_dict(r)
        if obj.get_chave_identificadora() == trinca:
            return obj

    return None
def buscar_por_id(id_res, path):
    db = carregar_dados(path)
    dados = next((r for r in db if r["id"] == id_res), None)
    return Residencia.from_dict(dados) if dados else None
def buscar_todos(path):
    db = carregar_dados(path)
    return [Residencia.from_dict(r) for r in db]
def buscar_por_cep(cep, path):
    db = carregar_dados(path)
    return [
        Residencia.from_dict(r)
        for r in db
        if r.get("cep") == cep
    ]
# ==========================================================
# UPDATE
# ==========================================================

def atualizar(id_res, novos_dados, path):
    db = carregar_dados(path)

    for i, r in enumerate(db):
        if r["id"] == id_res:
            db[i].update(novos_dados)
            db[i]["id"] = id_res  # proteção contra overwrite
            salvar_dados(db, path)
            return Residencia.from_dict(db[i])

    return None
# ==========================================================
# DELETE
# ==========================================================

def deletar(id_res, path_res, path_pessoas):
    """
    Remove uma residência apenas se não houver nenhuma pessoa vinculada a ela.
    Exige o path de pessoas para verificação de integridade.
    """
    db_res = carregar_dados(path_res)
    db_pessoas = carregar_dados(path_pessoas)

    # 1. Verificação de Integridade (Restrição)
    # Se existir QUALQUER pessoa com este id_residencia, impedimos a deleção.
    if any(p.get("id_residencia") == id_res for p in db_pessoas):
        return False

    # 2. Filtragem
    nova_lista = [r for r in db_res if r["id"] != id_res]

    # Se a lista não diminuiu, a residência não existia
    if len(nova_lista) == len(db_res):
        return False

    salvar_dados(nova_lista, path_res)
    return True