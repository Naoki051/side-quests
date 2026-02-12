from models.documento import Documento
from database.persistence import carregar_dados, salvar_dados

# ==========================================================
# CREATE
# ==========================================================

def salvar(documento_obj, path):
    """Persiste um novo objeto Documento no JSON."""
    db = carregar_dados(path)
    db.append(documento_obj.to_dict())
    salvar_dados(db, path)
    return documento_obj

# ==========================================================
# READ
# ==========================================================

def buscar_por_id(id_doc, path):
    db = carregar_dados(path)
    dados = next((d for d in db if d["id"] == id_doc), None)
    return Documento.from_dict(dados) if dados else None

def buscar_por_pessoa(id_pessoa, path):
    """Retorna todos os documentos vinculados a uma pessoa específica."""
    db = carregar_dados(path)
    return [
        Documento.from_dict(d) 
        for d in db 
        if d.get("id_pessoa") == id_pessoa
    ]

def buscar_por_chave(tipo, valor, path):
    """
    Busca um documento específico pela trinca (Tipo e Valor).
    Útil para verificar se um CPF já existe no sistema.
    """
    db = carregar_dados(path)
    tipo_busca = str(tipo).strip().upper()
    valor_busca = str(valor).strip()
    
    for d_dict in db:
        if d_dict.get("tipo") == tipo_busca and d_dict.get("valor") == valor_busca:
            return Documento.from_dict(d_dict)
    return None

def buscar_todos(path):
    db = carregar_dados(path)
    return [Documento.from_dict(d) for d in db]

# ==========================================================
# UPDATE
# ==========================================================

def atualizar(id_doc, novos_dados, path):
    """
    Atualiza dados do documento (ex: mudar o número se foi digitado errado).
    """
    db = carregar_dados(path)
    encontrado = False

    for i, d in enumerate(db):
        if d["id"] == id_doc:
            db[i].update(novos_dados)
            db[i]["id"] = id_doc  # Proteção de ID
            encontrado = True
            break

    if encontrado:
        salvar_dados(db, path)
        return Documento.from_dict(db[i])
    return None

# ==========================================================
# DELETE
# ==========================================================

def deletar(id_doc, path):
    db = carregar_dados(path)
    nova_lista = [d for d in db if d["id"] != id_doc]

    if len(nova_lista) == len(db):
        return False

    salvar_dados(nova_lista, path)
    return True

def deletar_por_pessoa(id_pessoa, path):
    """Remove todos os documentos de uma pessoa (usado ao excluir a pessoa)."""
    db = carregar_dados(path)
    nova_lista = [d for d in db if d.get("id_pessoa") != id_pessoa]
    
    if len(nova_lista) < len(db):
        salvar_dados(nova_lista, path)
        return True
    return False