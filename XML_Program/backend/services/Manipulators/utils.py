# utils.py
from typing import Dict, List
import lxml.etree as ET
import logging

logger = logging.getLogger(__name__)

NS = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
        'rel': 'http://schemas.openxmlformats.org/package/2006/relationships',
        'ct': 'http://schemas.openxmlformats.org/package/2006/content-types'
    }

def create_table_element(data: List[List[str]], config: dict = None) -> ET._Element:
    """
    Constrói o XML de uma tabela com largura fixa e espaçamentos de parágrafo
    diferenciados para o cabeçalho e corpo.
    """
    config = config or {}
    w_tag = f"{{{NS['w']}}}"
    
    total_width = config.get("total_width", 9000) 
    num_cols = len(data[0]) if data else 1
    cell_width = total_width // num_cols

    tbl = ET.Element(f"{w_tag}tbl")
    
    # --- 1. Propriedades da Tabela ---
    tbl_pr = ET.SubElement(tbl, f"{w_tag}tblPr")
    ET.SubElement(tbl_pr, f"{w_tag}tblStyle", {f"{w_tag}val": config.get("style", "TableGrid")})
    ET.SubElement(tbl_pr, f"{w_tag}tblW", {f"{w_tag}w": str(total_width), f"{w_tag}type": "dxa"})
    ET.SubElement(tbl_pr, f"{w_tag}jc", {f"{w_tag}val": "center"})

    # Bordas
    tbl_borders = ET.SubElement(tbl_pr, f"{w_tag}tblBorders")
    for border_name in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        ET.SubElement(tbl_borders, f"{w_tag}{border_name}", {
            f"{w_tag}val": "single", f"{w_tag}sz": "4", f"{w_tag}space": "0", f"{w_tag}color": "auto"
        })

    # --- 2. Grid da Tabela ---
    tbl_grid = ET.SubElement(tbl, f"{w_tag}tblGrid")
    for _ in range(num_cols):
        ET.SubElement(tbl_grid, f"{w_tag}gridCol", {f"{w_tag}w": str(cell_width)})

    # --- 3. Geração de Linhas e Células ---
    for row_idx, row_data in enumerate(data):
        tr = ET.SubElement(tbl, f"{w_tag}tr")
        
        for cell_text in row_data:
            tc = ET.SubElement(tr, f"{w_tag}tc")
            
            # Propriedades da Célula
            tc_pr = ET.SubElement(tc, f"{w_tag}tcPr")
            ET.SubElement(tc_pr, f"{w_tag}tcW", {f"{w_tag}w": str(cell_width), f"{w_tag}type": "dxa"})
            ET.SubElement(tc_pr, f"{w_tag}vAlign", {f"{w_tag}val": "center"})
            
            # Conteúdo (Parágrafo)
            p = ET.SubElement(tc, f"{w_tag}p")
            p_pr = ET.SubElement(p, f"{w_tag}pPr")
            ET.SubElement(p_pr, f"{w_tag}jc", {f"{w_tag}val": "center"})

            # --- LÓGICA DE ESPAÇAMENTO (w:spacing) ---
            if row_idx == 0:
                # Primeira linha: Adiciona 120 twips (6pt) antes e depois
                ET.SubElement(p_pr, f"{w_tag}spacing", {
                    f"{w_tag}before": "120", 
                    f"{w_tag}after": "120",
                    f"{w_tag}line": "240", 
                    f"{w_tag}lineRule": "auto"
                })
            else:
                # Outras linhas: Remove espaçamento antes e depois
                ET.SubElement(p_pr, f"{w_tag}spacing", {
                    f"{w_tag}before": "60", 
                    f"{w_tag}after": "60",
                    f"{w_tag}line": "240", 
                    f"{w_tag}lineRule": "auto"
                })
            
            # Run e Formatação (Times New Roman, 12pt)
            r = ET.SubElement(p, f"{w_tag}r")
            r_pr = ET.SubElement(r, f"{w_tag}rPr")
            ET.SubElement(r_pr, f"{w_tag}rFonts", {f"{w_tag}ascii": "Times New Roman", f"{w_tag}hAnsi": "Times New Roman"})
            
            # Negrito apenas para a primeira linha (opcional, mas recomendado para tabelas jurídicas)
            if row_idx == 0:
                ET.SubElement(r_pr, f"{w_tag}b")

            ET.SubElement(r_pr, f"{w_tag}sz", {f"{w_tag}val": "24"})
            ET.SubElement(r_pr, f"{w_tag}szCs", {f"{w_tag}val": "24"})
            
            t = ET.SubElement(r, f"{w_tag}t")
            t.text = str(cell_text)
            
    return tbl

def get_next_rid(rels_root: ET._Element) -> str:
    """
    Extrai todos os Ids de Relationship ignorando namespaces para evitar falhas de busca.
    """
    # Usar local-name() é a "blindagem" contra namespaces fantasmas em arquivos .rels
    ids = rels_root.xpath("//*[local-name()='Relationship']/@Id")
    
    numeric_ids = []
    for rid in ids:
        try:
            # Filtra apenas o que começa com rId e extrai o numeral
            if rid.startswith("rId"):
                numeric_ids.append(int(rid[3:]))
        except (ValueError, TypeError):
            continue
            
    # Garante que nunca sobrescrevemos um ID existente
    next_id = max(numeric_ids) + 1 if numeric_ids else 1
    return f"rId{next_id}"

def get_rels_part(target_part: str):
        """
        Retorna o XML da parte .rels associada ao target_part.
        Ex: word/document.xml -> word/_rels/document.xml.rels
        """
        if "/" in target_part:
            base_path, filename = target_part.rsplit("/", 1)
            return f"{base_path}/_rels/{filename}.rels"
        return f"_rels/{target_part}.rels"

def apply_node_surgery(node_map: List[dict], m_start: int, m_end: int, new_text: str):
        """Executa a troca do texto sem corromper a estrutura das runs."""
        inserted = False
        for item in node_map:
            node = item['node']
            n_start, n_end = item['start'], item['end']
            
            # O nó intercepta o marcador?
            if n_end > m_start and n_start < m_end:
                # Extraímos o que não deve ser apagado
                prefix = node.text[0 : max(0, m_start - n_start)] if n_start <= m_start else ""
                suffix = node.text[max(0, m_end - n_start) : ] if n_end >= m_end else ""
                
                if not inserted:
                    # Injetamos o novo texto no primeiro nó encontrado
                    node.text = prefix + str(new_text) + suffix
                    inserted = True
                else:
                    # Limpamos os nós subsequentes que faziam parte do marcador
                    node.text = suffix

def build_node_map(t_nodes: List[ET._Element]) -> tuple[str, List[Dict]]:
        """Mapeia o texto linear para os nós XML correspondentes."""
        full_text = ""
        node_map = []
        for node in t_nodes:
            start = len(full_text)
            full_text += node.text if node.text else ""
            node_map.append({'node': node, 'start': start, 'end': len(full_text)})
        return full_text, node_map

def get_next_note_id(note_root: ET._Element) -> str:
    existing_ids = []
    # Usando local-name para garantir a captura das notas
    query = "//*[local-name()='footnote' or local-name()='endnote']"
    for note in note_root.xpath(query):
        nid = note.get(f"{{{NS['w']}}}id")
        try:
            val = int(nid)
            if val >= 0:
                existing_ids.append(val)
        except (ValueError, TypeError):
            continue
            
    return str(max(existing_ids) + 1 if existing_ids else 1)

def get_next_numbering_ids(num_root: ET._Element) -> tuple[str, str]:
    """
    Retorna o próximo (abstractNumId, numId) disponível.
    """
    abstract_ids = [int(n.get(f"{{{NS['w']}}}abstractNumId")) for n in num_root.xpath(".//w:abstractNum", namespaces=NS)]
    num_ids = [int(n.get(f"{{{NS['w']}}}numId")) for n in num_root.xpath(".//w:num", namespaces=NS)]
    
    next_abs = str(max(abstract_ids) + 1 if abstract_ids else 0)
    next_num = str(max(num_ids) + 1 if num_ids else 1)
    
    return next_abs, next_num