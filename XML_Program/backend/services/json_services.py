import json
import os

# Define o caminho para o arquivo JSON
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(BASE_DIR, "data", "json", "temas.json")

def get_all_temas():
    """Retorna a árvore completa de temas, assuntos e motivos."""
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": "Arquivo temas.json não encontrado."}
    except json.JSONDecodeError:
        return {"error": "Erro ao processar o formato do arquivo JSON."}

def get_motivo_details(categoria, assunto, motivo):
    """
    Retorna os detalhes (Itens, Recomendações, Flags) de um motivo específico.
    """
    data = get_all_temas()
    
    try:
        # Navega na estrutura: Categoria -> Assunto -> Motivos -> Motivo Específico
        detalhes = data[categoria][assunto]["Motivos"][motivo]
        return detalhes
    except KeyError:
        return None

def get_recomendacoes_gerais(categoria, assunto):
    """Retorna a lista de recomendações gerais de um assunto específico."""
    data = get_all_temas()
    try:
        return data[categoria][assunto].get("Recomendacoes_Gerais", [])
    except KeyError:
        return []