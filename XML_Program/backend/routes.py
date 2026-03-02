# backend/routes.py
from flask import jsonify, Blueprint, render_template, request, send_file
from backend.services import csv_services, json_services, docx_services
from datetime import datetime
import os, tempfile, logging, json
# Criamos o Blueprint apenas UMA vez
main = Blueprint('main', __name__)
logger = logging.getLogger(__name__)
# Configuração de caminhos para os fragmentos DOCX
DOCX_BASE_PATH = os.path.abspath("backend/data/Docx")

@main.route('/api/gerar-minuta', methods=['POST'])
def handle_gerar_minuta():
    try:
        data = request.json
        if not data:
            logger.warning("🚫 Solicitação recebida com payload vazio.")
            return jsonify({"error": "Payload vazio"}), 400
        
        logger.info(f"📥 Payload recebido do Frontend:\n{json.dumps(data, indent=4, ensure_ascii=False)}")

        # 1. Dados Básicos e IDs
        municipio = data.get('dados_basicos', {}).get('municipio', 'Desconhecido')
        exercicio = str(data.get('dados_basicos', {}).get('exercicio', '????'))
        cod_munic = data.get('dados_basicos', {}).get('cod_munic')
        
        logger.info(f"🚀 Iniciando geração: {municipio} ({exercicio})")

        # ------------------------------------------------------------------------------
        # 2. COLETA E FORMATAÇÃO DE DADOS (CSV SERVICES)
        # ------------------------------------------------------------------------------
        lista_prefeitos = csv_services.get_prefeitos_by_exercicio_and_cod_munic(exercicio, cod_munic)
        prefeitos_str = " / ".join(lista_prefeitos) if lista_prefeitos else "NOME DO(S) PREFEITO(S)"
        dados_econ = csv_services.get_dados_economicos_by_exercicio_and_cod_munic(exercicio, cod_munic) or {}
        proc_info = data.get('procuradoria') or {}
        genero = proc_info.get('Gênero', 'M')
        titulo_procurador = "Procurador" if genero == 'M' else "Procuradora"

        def fmt_moeda(v):
            try: return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except: return "R$ 0,00"

        def fmt_num(v):
            try: return f"{int(float(v)):,}".replace(",", ".")
            except: return "0"

        # ------------------------------------------------------------------------------
        # 3. PREPARAÇÃO DOS DICIONÁRIOS PARA O ORQUESTRADOR
        # ------------------------------------------------------------------------------

        # 3.1 list_text: Variáveis de texto simples
        hoje = datetime.now()
        meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
                 "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

        list_text = {
            "[PROCESSO]": data['dados_basicos'].get('processo', "TC-XXXXXX.000.XX-X"),
            "[MUNICIPIO]": municipio,
            "[EXERCICIO]": exercicio,
            "[DIA]": str(hoje.day),
            "[MES]": meses[hoje.month - 1],
            "[ANO]": str(hoje.year),
            "[PROCURADORIA]": proc_info.get('Procuradoria', 'Procuradoria'),
            "[PREFEITOS]": prefeitos_str,
            "[POPULACAO]": fmt_num(dados_econ.get('POPULAÇÃO ESTIMADA', 0)),
            "[PORTE]": proc_info.get('Porte', 'Pequeno/Médio/Grande'),
            "[RECEITA_LIQUIDA]": fmt_moeda(dados_econ.get('Receita Líquida Municipal', 0)),
            "[PROCURADOR(A)]": titulo_procurador,
            "[PROCURADOR]": proc_info.get('Procurador', 'NOME DO PROCURADOR'),
            "[COD_ASSESSOR]": proc_info.get('Cod do Assessor', ''),
        }

        # 3.2 list_hyperlinks: Links Dinâmicos do IBGE
        URL_IBGE = {
            "2022": "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Previa_da_Populacao/POP2022_Municipios_20230622.pdf",
            "2023": "https://ftp.ibge.gov.br/Informacoes_Gerais_e_Referencia/Relacao_da_Populacao_dos_Municipios_para_publicacao_no_DOU_em_2023/POP_TCU_2023_Municipios_POP2022_Malha2023.pdf",
            "2024": "https://ftp.ibge.gov.br/Estimativas_de_Populacao/Estimativas_2024/POP2024_20241230.pdf"
        }
        url_selecionada = URL_IBGE.get(exercicio, "https://www.ibge.gov.br")
        
        list_hyperlinks = {
            "[PDF_LINK]": {
                "url": url_selecionada,
                "display": url_selecionada
            }
        }

        # 3.3 list_docx: Fragmentos Únicos
        list_docx = {}
        pos = data.get('posicionamento', 'favoravel').capitalize()
        dipe = data.get('segue_dipe', 'sim')
        path_parecer = os.path.join(DOCX_BASE_PATH, "Posicionamento", pos, f"{dipe}_dipe.docx")
        if os.path.exists(path_parecer): list_docx["[PARECER]"] = path_parecer

        acomp = data.get('acompanhamento', 'nao_houve')
        path_acomp = os.path.join(DOCX_BASE_PATH, "Acompanhamentos", f"{acomp}.docx")
        if os.path.exists(path_acomp): list_docx["[AVALIACAO]"] = path_acomp

        # 3.4 list_tables: Tabelas Transpostas com Regras de Negócio
        list_tables = {}
        LABEL_MAP = {
            'EXERCÍCIO': 'Exercício', 'iegm': 'IEG-M', 'iplanejamento': 'i-Plan',
            'ifiscal': 'i-Fiscal', 'ieduc': 'i-Educ', 'isaude': 'i-Saúde',
            'iamb': 'i-Amb', 'icidade': 'i-Cidade', 'igov': 'i-Gov',
            'Resultado Financeiro': 'Resultado Financeiro',
            'Déficit/Superávit de vagas em creches': 'Déficit de Vagas (Creches)'
        }
        MAP_COLUNAS = {
            'iegm': ['EXERCÍCIO', 'iegm', 'iplanejamento', 'ifiscal', 'ieduc', 'isaude', 'iamb', 'icidade', 'igov'],
            'financeiro': ['EXERCÍCIO', 'Resultado Financeiro'],
            'creches': ['EXERCÍCIO', 'Déficit/Superávit de vagas em creches']
        }

        for tipo in ['iegm', 'financeiro', 'creches']:
            placeholder_layout = f"[{tipo.upper()}]"
            info_tabela = data.get('tabelas', {}).get(tipo)
            dados_brutos = info_tabela.get('dados', []) if info_tabela else []
            
            if dados_brutos:
                path_fragment = os.path.join(DOCX_BASE_PATH, "Tabelas", f"tabela_{tipo}.docx")
                if os.path.exists(path_fragment):
                    list_docx[placeholder_layout] = path_fragment
                    cols_raw = MAP_COLUNAS[tipo]
                    dados_ordenados = sorted(dados_brutos, key=lambda x: int(x.get('EXERCÍCIO', 0)))
                    
                    corpo = []
                    header_anos = [LABEL_MAP['EXERCÍCIO']] + [str(d.get('EXERCÍCIO')) for d in dados_ordenados]
                    corpo.append(header_anos)
                    
                    for c_raw in cols_raw:
                        if c_raw == 'EXERCÍCIO': continue
                        linha = [LABEL_MAP.get(c_raw, c_raw)]
                        for d in dados_ordenados:
                            val = d.get(c_raw, 0)
                            if tipo == 'creches':
                                try: val = str(int(abs(float(val)))) if float(val) < 0 else "Não houve"
                                except: val = "Não houve"
                                list_text["[DEFICIT_VAGAS]"] =  val
                            elif tipo == 'financeiro': val = fmt_moeda(val)
                            else: val = str(val) if val != "" else "-"
                            linha.append(val)
                        corpo.append(linha)
                    
                    list_tables[f"[TABELA_{tipo.upper()}]"] = [{"data": corpo, "config": {"total_width": 9000}}]
            else:
                list_text[placeholder_layout] = ""

        # 3.5 list_num_list & Ranges (Motivos)
        arvore_temas = json_services.get_all_temas()
        motivos_itens = []
        recomendacoes_itens = data.get('recomendacoes_adicionais', [])
        ranges = []

        for cat_nome, assuntos in data.get('motivos', {}).items():
            src_origem_textos = os.path.join(DOCX_BASE_PATH, "Temas", f"{cat_nome}.docx")
            for ass_nome, motivos_selecionados in assuntos.items():
                dados_ass_json = arvore_temas.get(cat_nome, {}).get(ass_nome, {})
                for r in dados_ass_json.get('Recomendacoes_Gerais', []):
                    if r not in recomendacoes_itens: recomendacoes_itens.append(r)

                for mot_nome, mot_info in motivos_selecionados.items():
                    dados_mot_json = dados_ass_json.get('Motivos', {}).get(mot_nome, {})
                    flags = mot_info.get('flags', [])
                    flags_str = f" ({', '.join(flags)})" if flags else ""
                    for t in dados_mot_json.get('Itens', []): motivos_itens.append(f"{t}{flags_str}")
                    rec_esp = dados_mot_json.get('Recomendacao_Especifica')
                    if rec_esp and rec_esp not in recomendacoes_itens: recomendacoes_itens.append(rec_esp)
                    ranges.append({
                        "path": src_origem_textos,
                        "start": [f"Motivos: {mot_nome}"],
                        "stop": ["Item X", "Itens X", "Recomendação"]
                    })

        list_num_list = {"[MOTIVOS_ITENS]": motivos_itens, "[RECOMENDACAO_ITENS]": recomendacoes_itens}
        list_multiple_ranges = {"[MOTIVOS_TEXTOS]": ranges}
        list_multiple_docx = {"[OFICIOS]": [os.path.join(DOCX_BASE_PATH, "Oficios", f"{of}.docx") for of in data.get('oficios', [])]}

        # ------------------------------------------------------------------------------
        # 4. EXECUÇÃO
        # ------------------------------------------------------------------------------
        # 4.1 Extração das iniciais e preparação dos componentes do nome
        iniciais = proc_info.get('Iniciais Procurador', 'XXX')
        posicionamento_str = data.get('posicionamento', 'Favoravel').capitalize()
        # Limpamos o processo para o nome do arquivo (ex: TC-123.456 -> TC123456)
        processo_slug = data['dados_basicos'].get('processo', '000000').replace('.', '').replace('-', '')

        # 4.2 Construção do nome conforme solicitado: 
        # "{exercicio} {municipio} PM {processo} {posicionamento} [{iniciais}].docx"
        output_filename = f"{exercicio} {municipio} PM {processo_slug} {posicionamento_str} [{iniciais}].docx"
        
        # Caminho temporário no servidor
        output_path = os.path.join(tempfile.gettempdir(), output_filename)
        
        logger.info(f"📡 Invocando orquestrador para gerar: {output_filename}")
        
        sucesso = docx_services.gerar_minuta(
            modelo_path=os.path.join(DOCX_BASE_PATH, "modelo_geral.docx"),
            output_path=output_path,
            list_docx=list_docx,
            list_multiple_docx=list_multiple_docx,
            list_multiple_ranges=list_multiple_ranges,
            list_tables=list_tables,
            list_text=list_text,
            list_hyperlinks=list_hyperlinks,
            list_num_list=list_num_list
        )

        if sucesso:
            return send_file(output_path, as_attachment=True, download_name=output_filename,mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        else:
            raise Exception("Falha na consolidação do orquestrador.")

    except Exception as e:
        import traceback
        logger.error(f"💥 ERRO: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@main.route('/')
def index():
    """Serve a página principal do frontend"""
    return render_template('gerador-minutas.html')

@main.route('/api/municipios')
def get_municipios():
    """Retorna a lista para o select de municípios"""
    data = csv_services.get_lista_municipios()
    return jsonify(data)

@main.route('/api/relatorio-consolidado')
def get_relatorio_total():
    """Retorna todos os dados para o AppState (modal)"""
    data = csv_services.get_all_relatorio_data()
    return jsonify(data)

@main.route('/api/procuradoria/<cod_munic>')
def get_procuradoria(cod_munic):
    """Retorna dados da procuradoria por código"""
    data = csv_services.get_procuradoria_by_cod_munic(cod_munic)
    return jsonify(data)

@main.route('/api/recomendacoes')
def get_recomendas():
    """Retorna recomendações gerais do CSV"""
    data = csv_services.get_all_recomendacoes()
    return jsonify(data)

@main.route('/api/relatorio/<cod_munic>')
def get_relatorio(cod_munic):
    """Retorna indicadores de um município específico"""
    data = csv_services.get_relatorio_by_cod_munic(cod_munic)
    return jsonify(data)

@main.route('/api/economico/<exercicio>/<cod_munic>')
def get_dados_economicos(exercicio, cod_munic):
    """Retorna população e receita de um ano específico"""
    data = csv_services.get_dados_economicos_by_exercicio_and_cod_munic(exercicio, cod_munic)
    return jsonify(data)

@main.route('/api/temas')
def get_temas_tree():
    """Retorna a árvore de temas do JSON"""
    data = json_services.get_all_temas()
    return jsonify(data)