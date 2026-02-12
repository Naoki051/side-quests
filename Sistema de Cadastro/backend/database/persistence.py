import json
import os

def carregar_dados(data_base_path):
    """
    Lê o arquivo JSON e retorna uma lista. 
    Se o arquivo não existir ou estiver corrompido, retorna uma lista vazia.
    """
    if not os.path.exists(data_base_path):
        return []

    try:
        with open(data_base_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        # Caso o arquivo esteja vazio ou não seja um JSON válido
        return []

def salvar_dados(dados, data_base_path):
    """
    Grava a lista de dicionários no arquivo JSON com formatação legível.
    """
    # Garante que a pasta existe antes de tentar salvar
    os.makedirs(os.path.dirname(data_base_path), exist_ok=True)
    
    with open(data_base_path, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)