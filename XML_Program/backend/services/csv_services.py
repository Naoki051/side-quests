#backend\services\csv_services.py
import pandas as pd
import os

# Caminhos base (ajustados para a estrutura informada)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_DIR = os.path.join(BASE_DIR, "data", "csv")

def get_prefeitos_by_exercicio_and_cod_munic(exercicio, cod_munic):
    """
    Retorna a lista de nomes de prefeitos para um exercício e município específicos.
    """
    file_path = os.path.join(CSV_DIR, "prefeito_consolidado.csv")
    df = pd.read_csv(file_path, sep=';', encoding='utf-8')
    
    # Filtro: Exercício e COD. MUNIC
    # Convertendo para int para garantir a comparação se vierem como string
    filtro = (df['Exercício'].astype(int) == int(exercicio)) & \
             (df['COD. MUNIC'].astype(int) == int(cod_munic))
    
    prefeitos = df[filtro]['nome'].tolist()
    return prefeitos

def get_procuradoria_by_cod_munic(cod_munic):
    """
    Retorna os detalhes da procuradoria vinculada ao código do município.
    """
    file_path = os.path.join(CSV_DIR, "procuradoria_consolidada.csv")
    df = pd.read_csv(file_path, sep=';', encoding='utf-8')
    
    filtro = df['COD. MUNIC'].astype(int) == int(cod_munic)
    resultado = df[filtro]
    
    if not resultado.empty:
        # Retorna o primeiro registro encontrado como dicionário
        cols = ['Porte', 'Procuradoria', 'Procurador', 'Gênero', 
                'Iniciais Procurador', 'Assessor', 'Cod do Assessor']
        return resultado[cols].iloc[0].to_dict()
    return None

def get_all_recomendacoes():
    """
    Retorna uma lista com todas as recomendações adicionais.
    """
    file_path = os.path.join(CSV_DIR, "recomendacoes_adicionais.csv")
    df = pd.read_csv(file_path, sep=';', encoding='utf-8')
    
    return df['Recomendações'].tolist()

def get_lista_municipios():
    """
    Retorna a lista de municípios e seus códigos para o select do frontend.
    Baseado no arquivo de procuradoria.
    """
    file_path = os.path.join(CSV_DIR, "procuradoria_consolidada.csv")
    df = pd.read_csv(file_path, sep=';', encoding='utf-8')
    
    # Seleciona apenas as colunas necessárias e remove duplicatas (se houver)
    municipios = df[['COD. MUNIC', 'Município']].drop_duplicates()
    
    # Ordena alfabeticamente para facilitar a escolha do usuário
    municipios = municipios.sort_values(by='Município')
    
    return municipios.to_dict(orient='records')

def get_all_relatorio_data():
    """
    Retorna todos os dados do relatório municipal (sem filtro).
    Usado para carregar o AppState no frontend e alimentar o modal de tabelas.
    """
    file_path = os.path.join(CSV_DIR, "relatorio_municipal.csv")
    df = pd.read_csv(file_path, sep=';', encoding='utf-8')
    
    # Preenche valores nulos para evitar erros no JSON (convertendo para string vazia ou 0)
    df = df.fillna("")
    
    return df.to_dict(orient='records')

def get_relatorio_by_cod_munic(cod_munic):
    """
    Retorna o histórico de indicadores do município (vários exercícios).
    """
    file_path = os.path.join(CSV_DIR, "relatorio_municipal.csv")
    df = pd.read_csv(file_path, sep=';', encoding='utf-8')
    
    filtro = df['COD. MUNIC'].astype(int) == int(cod_munic)
    cols = [
        'EXERCÍCIO', 'iegm', 'iplanejamento', 'ifiscal', 'ieduc', 
        'isaude', 'iamb', 'icidade', 'igov', 'Resultado Financeiro', 
        'Déficit/Superávit de vagas em creches'
    ]
    
    resultado = df[filtro][cols]
    return resultado.to_dict(orient='records')

def get_dados_economicos_by_exercicio_and_cod_munic(exercicio, cod_munic):
    """
    Retorna População e Receita Líquida para um exercício específico.
    """
    file_path = os.path.join(CSV_DIR, "relatorio_municipal.csv")
    df = pd.read_csv(file_path, sep=';', encoding='utf-8')
    
    filtro = (df['EXERCÍCIO'].astype(int) == int(exercicio)) & \
             (df['COD. MUNIC'].astype(int) == int(cod_munic))
    
    resultado = df[filtro]
    
    if not resultado.empty:
        return {
            'POPULAÇÃO ESTIMADA': resultado.iloc[0]['POPULAÇÃO ESTIMADA'],
            'Receita Líquida Municipal': resultado.iloc[0]['Receita Líquida Municipal']
        }
    return None