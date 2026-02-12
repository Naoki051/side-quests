from models.pessoa import Pessoa
from database.persistence import carregar_dados, salvar_dados

# ==========================================================
# CREATE
# ==========================================================

def salvar(pessoa_obj, path):
    db = carregar_dados(path)
    db.append(pessoa_obj.to_dict())
    salvar_dados(db, path)
    return pessoa_obj

# ==========================================================
# READ
# ==========================================================

def buscar_por_id(id_pessoa, path):
    db = carregar_dados(path)
    dados = next((p for p in db if p["id"] == id_pessoa), None)
    return Pessoa.from_dict(dados) if dados else None

def buscar_todos(path):
    db = carregar_dados(path)
    return [Pessoa.from_dict(p) for p in db]

def buscar_dependentes(id_responsavel, path):
    """Retorna a lista de objetos Pessoa que possuem este id_responsavel."""
    db = carregar_dados(path)
    return [
        Pessoa.from_dict(p) 
        for p in db 
        if p.get("id_responsavel") == id_responsavel
    ]

def buscar_responsavel(id_pessoa, path):
    """Retorna o objeto Pessoa que é responsável pela pessoa informada."""
    pessoa = buscar_por_id(id_pessoa, path)
    
    if pessoa and pessoa.id_responsavel:
        return buscar_por_id(pessoa.id_responsavel, path)
    
    return None

# ==========================================================
# UPDATE
# ==========================================================

def atualizar(id_pessoa, novos_dados, path):
    """
    Atualiza os dados de uma pessoa no arquivo JSON.
    """
    db = carregar_dados(path)
    encontrado = False

    for i, p in enumerate(db):
        if p["id"] == id_pessoa:
            db[i].update(novos_dados)
            db[i]["id"] = id_pessoa  # Proteção de ID
            encontrado = True
            break

    if encontrado:
        salvar_dados(db, path)
        return Pessoa.from_dict(db[i])

    return None

# ==========================================================
# DELETE
# ==========================================================

def deletar(id_pessoa, path):
    """
    Remove a pessoa se ela não for responsável por ninguém (Integridade).
    """
    db = carregar_dados(path)

    # Verifica se a pessoa tem dependentes antes de deletar
    if any(p.get("id_responsavel") == id_pessoa for p in db):
        return False 

    nova_lista = [p for p in db if p["id"] != id_pessoa]

    if len(nova_lista) == len(db):
        return False

    salvar_dados(nova_lista, path)
    return True