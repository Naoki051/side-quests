# backend\services\docx_services.py
import os
import logging
from typing import Dict, List

# Importando as classes do nosso framework
from .Manipulators.DocxPackage import DocxPackage
from .Manipulators.DocxMerger import DocxMerger
from .Manipulators.DocxEditor import DocxEditor
from .Manipulators.DocxValidator import DocxValidator

logger = logging.getLogger("ORCHESTRATOR")

def gerar_minuta(
    modelo_path: str, 
    output_path: str, 
    list_docx: Dict[str, str],                  # {placeholder: caminho_arquivo}
    list_multiple_docx: Dict[str, List[str]],   # {placeholder: [caminho1, caminho2]}
    list_multiple_ranges: Dict[str, List[Dict]],# {placeholder: [{path, start, stop}, ...]}
    list_tables: Dict[str, List[Dict]],         # {placeholder: [{"data": List[List], "config": dict}, ...]}
    list_text: Dict[str, str],                  # {placeholder: texto_substituto}
    list_hyperlinks: Dict[str, str],            # {placeholder: url}
    list_num_list: Dict[str, List[str]]         # {placeholder: [item1, item2]}
) -> bool:
    """
    Orquestra a geração de documentos com separação estrita de tipos de substituição.
    """
    try:
        logger.info(f"🚀 Iniciando orquestração da minuta: {os.path.basename(output_path)}")

        # 1. Carregar o Pacote
        if not os.path.exists(modelo_path):
            logger.error(f"❌ Modelo não encontrado: {modelo_path}")
            return False
            
        pkg = DocxPackage(modelo_path)
        merger = DocxMerger()
        editor = DocxEditor(pkg)

        # ==============================================================================
        # FASE 1: FUSÃO ESTRUTURAL (Merger)
        # ==============================================================================
        
        # 1.1 DOCX Simples (1 placeholder -> 1 arquivo)
        for placeholder, fpath in list_docx.items():
            if os.path.exists(fpath):
                logger.info(f"📄 Mesclando DOCX único em '{placeholder}'")
                merger.replace_docx(placeholder, DocxPackage(fpath), pkg)
            else:
                logger.warning(f"⚠️ Arquivo não encontrado para '{placeholder}': {fpath}")

        # 1.2 Múltiplos DOCX (1 placeholder -> Lista de arquivos)
        for placeholder, path_list in list_multiple_docx.items():
            valid_paths = [p for p in path_list if os.path.exists(p)]
            if valid_paths:
                logger.info(f"📚 Mesclando {len(valid_paths)} arquivos em '{placeholder}'")
                merger.replace_multiple_docx(placeholder, valid_paths, pkg)
            else:
                logger.warning(f"⚠️ Nenhum arquivo válido encontrado para '{placeholder}'")

        # 1.3 Tabelas (Implementação Solicitada)
        # Processa a lista de tabelas para cada placeholder
        for placeholder, configs in list_tables.items():
            for cfg in configs:
                data = cfg.get("data")
                table_config = cfg.get("config") # Opcional
                if data:
                    logger.info(f"📊 Gerando tabela dinâmica em '{placeholder}'")
                    # Chamamos o método do Editor pois ele manipula o XML diretamente
                    editor.replace_table(placeholder, data, table_config=table_config)

        # 1.4 Intervalos de Texto (Ranges)
        for placeholder, configs in list_multiple_ranges.items():
            # Filtra configurações onde o arquivo de origem existe
            valid_configs = [cfg for cfg in configs if os.path.exists(cfg.get("path", ""))]
            if valid_configs:
                logger.info(f"✂️ Mesclando intervalos complexos em '{placeholder}'")
                merger.replace_multiple_ranges(placeholder, valid_configs, pkg)
            else:
                logger.warning(f"⚠️ Configuração de range inválida ou arquivo ausente para '{placeholder}'")

        # ==============================================================================
        # FASE 2: EDIÇÃO DE CONTEÚDO (Editor)
        # ==============================================================================

        # 2.1 Substituição de Texto Simples (Metadados)
        logger.info(f"📝 Processando {len(list_text)} substituições de texto...")
        for placeholder, valor in list_text.items():
            texto = str(valor)
            # Aplica no corpo principal
            editor.replace_text(placeholder, texto, target_part="word/document.xml")
            
            # Aplica também em Cabeçalhos e Rodapés (importante para numeração de processos/páginas)
            # O método replace_text já suporta wildcards (*) se implementado conforme passo anterior
            editor.replace_text(placeholder, texto, target_part="word/header1.xml")
            editor.replace_text(placeholder, texto, target_part="word/footer1.xml")

        # 2.2 Listas Numeradas (Estilo Forçado)
        for placeholder, itens in list_num_list.items():
            if itens:
                logger.info(f"🔢 Gerando lista numerada em '{placeholder}'")
                # Força o estilo "MotivoseRecDet" conforme regra de negócio definida
                editor.replace_num_list(
                    placeholder, 
                    itens, 
                    style_name="MotivoseRec-Det"
                )

        # 2.3 Hyperlinks
        for placeholder, link_info in list_hyperlinks.items():
            if link_info.get("url"):
                logger.info(f"🔗 Inserindo hyperlink em nota de rodapé: '{placeholder}'")
                
                editor.replace_hyperlink(
                    placeholder, 
                    link_info.get("display", "clique aqui"), 
                    link_info["url"], 
                    target_part="word/footnotes.xml" # Direcionado para Notas de Rodapé
                )

        # ==============================================================================
        # FASE 3: VALIDAÇÃO E SALVAMENTO
        # ==============================================================================
        
        logger.info("🔍 Executando validação de integridade...")
        if DocxValidator.validate(pkg):
            logger.info("✅ Documento validado com sucesso.")
        else:
            logger.warning("⚠️ O documento gerado contém inconsistências estruturais.")

        pkg.save_to_path(output_path)
        logger.info(f"💾 Minuta salva em: {output_path}")
        return True

    except Exception as e:
        logger.error(f"❌ Erro crítico na geração da minuta: {e}", exc_info=True)
        return False

# if __name__ == "__main__":
#     # --- Configuração de Caminhos ---
#     BASE = "test"
    
#     # 1. list_docx: DOCX Simples
#     list_docx = {
#         "[PARECER]": os.path.join(BASE, "sim_dipe.docx")
#     }

#     # 2. list_multiple_docx: Lista de DOCX
#     list_multiple_docx = {
#         "[OFICIOS]": [
#             os.path.join(BASE, "Auto_de_Vistoria_do_Corpo_de_Bombeiros.docx"),
#             os.path.join(BASE, "Comunicacao_MP_Educacao.docx")
#         ]
#     }

#     # 3. list_multiple_ranges: Intervalos Complexos
#     src_motivos = os.path.join(BASE, "Violação das diretrizes do TCESP.docx")
#     list_multiple_ranges = {
#         "[MOTIVOS_TEXTOS]": [
#             {"path": src_motivos, "start": ["Motivos: Baixo desempenho Global;"], "stop": ["Item X"]},
#             {"path": src_motivos, "start": ["Motivos: Baixo desempenho i-Amb;"], "stop": ["Item X"]}
#         ]
#     }

#     # 4. list_text: Variáveis de Texto
#     list_text = {
#         "[PROCESSO]": "TC-123456.789.12-3",
#         "[MUNICIPIO]": "São Paulo",
#         "[PREFEITOS]": "Bruno Covas / Ricardo Nunes",
#         "[POPULACAO]": "11.451.245",
#         "[EXERCICIO]": "2024",
#         "[AVALIACAO]": "Irregularidade nas contas.",
#         "[PROCURADOR]": "Dr. João da Silva",
#         "[DIA]": "12", "[MES]": "Fevereiro", "[ANO]": "2026"
#     }

#     # 5. list_hyperlinks: Links
#     list_hyperlinks = {
#         "[PDF_LINK]": "http://tce.sp.gov.br/processo/123"
#     }

#     # 6. list_num_list: Listas Numeradas
#     list_num_list = {
#         "[MOTIVOS_ITENS]": [
#             "Baixa efetividade da gestão (IEG-M).",
#             "Déficit de vagas em creches."
#         ],
#         "[RECOMENDACAO_ITENS]": [
#             "Elaborar plano de ação.",
#             "Regularizar AVCBs."
#         ]
#     }

#     # --- Execução ---
#     sucesso = gerar_minuta(
#         modelo_path=os.path.join(BASE, "modelo.docx"),
#         output_path=os.path.join(BASE, "Minuta_Final_Refatorada.docx"),
#         list_docx=list_docx,
#         list_multiple_docx=list_multiple_docx,
#         list_multiple_ranges=list_multiple_ranges,
#         list_text=list_text,
#         list_hyperlinks=list_hyperlinks,
#         list_num_list=list_num_list
#     )

#     if sucesso:
#         print("🎉 Sucesso total na nova assinatura!")