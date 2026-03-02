# DocxEditor.py
import logging
import lxml.etree as ET
from typing import List

from .DocxPackage import DocxPackage
from .utils import (NS, build_node_map, apply_node_surgery, create_table_element, get_rels_part, get_next_rid, get_next_numbering_ids)

logger = logging.getLogger(__name__)
class DocxEditor:
    """
    Classe de alto nível para editar qualquer parte XML de um DocxPackage.
    """

    def __init__(self, package: DocxPackage):
        self.package = package

    # --- Funções Auxiliares (Privadas) ---

    def _process_paragraph_substitution(self, p: ET._Element, old_text: str, new_text: str) -> int:
        """Gerencia a substituição dentro de um único parágrafo."""
        sub_count = 0
        while True:
            t_nodes = p.xpath(".//w:t", namespaces=NS)
            full_text, node_map = build_node_map(t_nodes)
            
            if old_text not in full_text:
                break
            
            match_start = full_text.find(old_text)
            match_end = match_start + len(old_text)
            
            apply_node_surgery(node_map, match_start, match_end, new_text)
            sub_count += 1
        return sub_count
    
    def _process_hyperlink_substitution(self, p: ET._Element, old_text: str, new_text: str, new_url: str, target_part: str) -> int:

        sub_count = 0
        hyperlink_type = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"

        while True:
            t_nodes = p.xpath(".//w:t", namespaces=NS)
            full_text, node_map = build_node_map(t_nodes)

            if old_text not in full_text:
                break

            # 🔎 DEBUG — ANTES
            logger.debug("----- HYPERLINK SUBSTITUTION START -----")
            logger.debug(f"Texto completo ANTES: '{full_text}'")

            match_start = full_text.find(old_text)
            match_end = match_start + len(old_text)

            logger.debug(f"Match encontrado: '{old_text}'")
            logger.debug(f"Posição: {match_start} → {match_end}")

            # 1️⃣ RELATIONSHIP
            rels_path = get_rels_part(target_part)
            rels_root = self.package.get_part_xml(rels_path)

            new_rid = get_next_rid(rels_root)

            logger.debug(f"Novo rId gerado: {new_rid}")
            logger.debug(f"URL registrada: {new_url}")

            ET.SubElement(
                rels_root,
                f"{{{NS['rel']}}}Relationship",
                Id=new_rid,
                Type=hyperlink_type,
                Target=new_url,
                TargetMode="External"
            )

            # 2️⃣ Localização da run
            first_item_affected = next(
                item for item in node_map if item['end'] > match_start
            )

            first_node = first_item_affected['node']
            first_run = first_node.getparent()

            # 3️⃣ Criar hyperlink
            hyperlink_el = ET.Element(
                f"{{{NS['w']}}}hyperlink",
                {f"{{{NS['r']}}}id": new_rid}
            )

            new_r = ET.SubElement(hyperlink_el, f"{{{NS['w']}}}r")
            rPr = ET.SubElement(new_r, f"{{{NS['w']}}}rPr")
            ET.SubElement(
                rPr,
                f"{{{NS['w']}}}rStyle",
                {f"{{{NS['w']}}}val": "Hyperlink"}
            )

            new_t = ET.SubElement(new_r, f"{{{NS['w']}}}t")
            new_t.text = str(new_text)

            # 1️⃣ Remover marcador primeiro
            apply_node_surgery(node_map, match_start, match_end, "")

            # 2️⃣ Recalcular runs após cirurgia
            t_nodes = p.xpath(".//w:t", namespaces=NS)
            full_text, node_map = build_node_map(t_nodes)

            # 3️⃣ Encontrar ponto de inserção atualizado
            first_item = next(item for item in node_map if item['start'] >= match_start)
            first_node = first_item['node']
            first_run = first_node.getparent()

            # 4️⃣ Inserir hyperlink no ponto correto
            p.insert(p.index(first_run), hyperlink_el)


            # 🔎 DEBUG — DEPOIS
            t_nodes_after = p.xpath(".//w:t", namespaces=NS)
            full_text_after, _ = build_node_map(t_nodes_after)

            logger.debug(f"Texto completo DEPOIS: '{full_text_after}'")
            logger.debug("----- HYPERLINK SUBSTITUTION END -----")

            sub_count += 1

        return sub_count

    # --- Lógica de Edição de Texto ---

    def replace_text(self, old_text: str, new_text: str, target_part: str = "word/document.xml") -> int:
        """
        Substitui old_text por new_text cirurgicamente, preservando a 
        formatação e as runs vizinhas.
        """
        # Passo 1: Verificação rápida de existência (Fail-fast)
        root = self.package.get_part_xml(target_part)
        # Reconstruímos o texto de toda a parte para validar a existência
        full_part_text = "".join(root.xpath(".//w:t/text()", namespaces=NS))
        
        if old_text not in full_part_text:
            logger.warning(f"Termo '{old_text}' não encontrado em '{target_part}'.")
            return 0

        count = 0
        # Passo 2: Iterar apenas pelos parágrafos que contêm o termo
        # Isso é mais preciso do que usar get_run_nodes globalmente para substituição
        for p in root.xpath(".//w:p", namespaces=NS):
            p_text = "".join(p.xpath(".//w:t/text()", namespaces=NS))
            
            if old_text in p_text:
                count += self._process_paragraph_substitution(p, old_text, new_text)

        # Passo 3: Sincronizar se houver mudanças
        if count > 0:
            self.package.set_part_xml(target_part, root)
            logger.info(f"Substituídas {count} ocorrências de '{old_text}' em '{target_part}'.")
        
        return count

    def replace_hyperlink(self, old_text: str, new_text: str, new_url: str, target_part: str = "word/document.xml") -> int:
        """Substitui texto old_text por new_text e gera um hyperlink."""

        root = self.package.get_part_xml(target_part)
        
        full_part_text = "".join(root.xpath(".//w:t/text()", namespaces=NS))
        
        if old_text not in full_part_text:
            logger.warning(f"Termo '{old_text}' não encontrado em '{target_part}'.")
            return 0
        
        target_rels_part = get_rels_part(target_part)
        rels_root = self.package.get_part_xml(target_rels_part)
        count = 0
        for p in root.xpath(".//w:p", namespaces=NS):
            p_text = "".join(p.xpath(".//w:t/text()", namespaces=NS))
            
            if old_text in p_text:
                count += self._process_hyperlink_substitution(p, old_text, new_text, new_url, target_part)
        if count > 0:
            self.package.set_part_xml(target_part, root)
            self.package.set_part_xml(target_rels_part, rels_root)
        
        return count
    
    def replace_table(self, old_text: str, data: List[List[str]], table_config: dict = None, target_part: str = "word/document.xml") -> int:
        """
        Localiza um marcador em um parágrafo e substitui o parágrafo inteiro 
        por uma tabela gerada dinamicamente.
        """
        root = self.package.get_part_xml(target_part)
        
        # 1️⃣ Passo 1: Fail-fast
        full_part_text = "".join(root.xpath(".//w:t/text()", namespaces=NS))
        if old_text not in full_part_text:
            logger.warning(f"Marcador de tabela '{old_text}' não encontrado em '{target_part}'.")
            return 0

        count = 0
        # 2️⃣ Passo 2: Localizar os parágrafos que contêm o marcador
        # Iteramos de forma reversa ou coletamos para evitar erro de índice ao remover elementos
        paragraphs_to_replace = []
        for p in root.xpath(".//w:p", namespaces=NS):
            p_text = "".join(p.xpath(".//w:t/text()", namespaces=NS))
            if old_text in p_text:
                paragraphs_to_replace.append(p)

        for p in paragraphs_to_replace:
            parent = p.getparent()
            if parent is None:
                continue

            # 3️⃣ Passo 3: Criar a estrutura da tabela (w:tbl)
            new_table_el = create_table_element(data, table_config)

            # Inserir a tabela no lugar do parágrafo
            index = parent.index(p)
            parent.insert(index, new_table_el)
            parent.remove(p)
            count += 1

        if count > 0:
            self.package.set_part_xml(target_part, root)
            logger.info(f"Tabela inserida com sucesso no lugar de '{old_text}'.")
        
        return count
    
    def replace_num_list(self, old_text: str, new_list: List[str], 
                         style_name: str = "MotivoseRec-Det", # Padrão forçado
                         target_part: str = "word/document.xml") -> int:
        """
        Substitui um marcador de texto por uma lista numerada real.
        
        Args:
            old_text: O texto placeholder a ser substituído (ex: "[LISTA]").
            new_list: Lista de strings com os itens.
            style_name: Nome do estilo do Word a ser aplicado (ex: "MotivoseRecDet").
            target_part: Caminho do XML alvo (geralmente document.xml).
            
        Returns:
            int: Número de substituições realizadas.
        """
        root = self.package.get_part_xml(target_part)
        
        # 1️⃣ Passo 1: Fail-fast (Verificação rápida)
        # Usamos any() com generator para eficiência de memória e velocidade
        if not any(old_text in (t.text or "") for t in root.xpath(".//w:t", namespaces=NS)):
            logger.warning(f"Marcador de lista '{old_text}' não encontrado em '{target_part}'.")
            return 0

        # 2️⃣ Passo 2: Preparar a infraestrutura de numeração
        
        num_xml_path = "word/numbering.xml"
        num_root = self.package.get_part_xml(num_xml_path)
        
        # Gera novos IDs únicos para garantir que esta lista comece do 1 e seja independente
        abs_id, num_id = get_next_numbering_ids(num_root)
        
        # Cria a definição do estilo da lista (1., 2., 3...)
        self._add_decimal_numbering_definition(num_root, abs_id)
        
        # Cria a instância que liga o documento à definição
        self._add_num_instance(num_root, num_id, abs_id)
        
        # Salva o XML de numeração atualizado no pacote
        self.package.set_part_xml(num_xml_path, num_root)

        # 3️⃣ Passo 3: Localizar e substituir no texto
        # Encontra todos os parágrafos que contêm o placeholder
        paragraphs_to_replace = []
        for p in root.xpath(".//w:p", namespaces=NS):
            if old_text in "".join(p.xpath(".//w:t/text()", namespaces=NS)):
                paragraphs_to_replace.append(p)

        count = 0
        for original_p in paragraphs_to_replace:
            parent = original_p.getparent()
            if parent is None: continue
            
            insert_index = parent.index(original_p)
            
            # Gera os novos parágrafos numerados
            for i, item_text in enumerate(new_list):
                if not (item_text.startswith("Item X") or item_text.startswith("Itens X")):
                    item_text = "Item X – "+item_text
                new_p = self._create_numbered_paragraph(
                    text=item_text, 
                    num_id=num_id, 
                    style_id=style_name # Aplica o estilo aqui
                )
                parent.insert(insert_index + i, new_p)
            
            # Remove o parágrafo antigo (o placeholder)
            parent.remove(original_p)
            count += 1

        if count > 0:
            self.package.set_part_xml(target_part, root)
            logger.info(f"Lista de {len(new_list)} itens inserida no lugar de '{old_text}' com estilo '{style_name}'.")
        
        return count

    # --- Funções Internas de Suporte ---

    def _create_numbered_paragraph(self, text: str, num_id: str, style_id: str = None) -> ET._Element:
        """
        Cria um elemento <w:p> completo configurado como item de lista.
        """
        W = f"{{{NS['w']}}}"
        p = ET.Element(f"{W}p")
        
        # --- Propriedades do Parágrafo (<w:pPr>) ---
        pPr = ET.SubElement(p, f"{W}pPr")
        
        # 1. Aplica o Estilo Visual (Fonte, cor, espaçamento definidos no styles.xml)
        if style_id:
            ET.SubElement(pPr, f"{W}pStyle", {f"{W}val": style_id})
        
        # 2. Configura a Numeração (Vínculo com numbering.xml)
        numPr = ET.SubElement(pPr, f"{W}numPr")
        ET.SubElement(numPr, f"{W}ilvl", {f"{W}val": "0"})   # Nível 0 (Indentação principal)
        ET.SubElement(numPr, f"{W}numId", {f"{W}val": str(num_id)}) # ID da lista gerada
        
        # --- Conteúdo do Texto (<w:r> -> <w:t>) ---
        r = ET.SubElement(p, f"{W}r")
        t = ET.SubElement(r, f"{W}t")
        t.text = text
        
        return p

    def _add_decimal_numbering_definition(self, num_root: ET._Element, abstract_id: str):
        """
        Adiciona a definição abstrata de uma lista decimal (1., 2., 3.) ao numbering.xml.
        """
        W = f"{{{NS['w']}}}"

        # Cria o elemento <w:abstractNum>
        abstract_num = ET.Element(f"{W}abstractNum", {f"{W}abstractNumId": str(abstract_id)})
        
        # Insere no INÍCIO do root para manter a ordem correta (abstracts antes de nums)
        num_root.insert(0, abstract_num)

        # Propriedades padrão
        ET.SubElement(abstract_num, f"{W}multiLevelType", {f"{W}val": "hybridMultilevel"})
        ET.SubElement(abstract_num, f"{W}tmpl", {f"{W}val": "0409000F"})

        # Definição do Nível 0
        lvl = ET.SubElement(abstract_num, f"{W}lvl", {f"{W}ilvl": "0"})
        ET.SubElement(lvl, f"{W}start", {f"{W}val": "1"})       # Começa em 1
        ET.SubElement(lvl, f"{W}numFmt", {f"{W}val": "decimal"}) # Formato 1, 2, 3
        ET.SubElement(lvl, f"{W}lvlText", {f"{W}val": "%1."})    # Texto "1."
        ET.SubElement(lvl, f"{W}lvlJc", {f"{W}val": "left"})     # Alinhamento

        # Recuos (Indentation) - Ajuste conforme necessário (Twips)
        p_pr = ET.SubElement(lvl, f"{W}pPr")
        ET.SubElement(p_pr, f"{W}ind", {f"{W}left": "720", f"{W}hanging": "360"})

    def _add_num_instance(self, num_root: ET._Element, num_id: str, abs_id: str):
        """
        Adiciona a instância <w:num> que conecta o documento à definição abstrata.
        """
        W = f"{{{NS['w']}}}"
        
        # <w:num> sempre vai no final do arquivo numbering.xml
        num = ET.SubElement(num_root, f"{W}num", {f"{W}numId": str(num_id)})
        ET.SubElement(num, f"{W}abstractNumId", {f"{W}val": str(abs_id)})