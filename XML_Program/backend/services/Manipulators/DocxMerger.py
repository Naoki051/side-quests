import lxml.etree as ET
import copy
import logging
import os
from typing import Dict, Set

from .DocxPackage import DocxPackage
from .utils import NS, get_rels_part, get_next_rid, get_next_note_id, get_next_numbering_ids

logger = logging.getLogger(__name__)

class DocxMerger:
    """
    Motor de fusão industrial. 
    Resolve conflitos de ID, evita duplicação de mídia e limpa rastros de revisão.
    """
    def __init__(self):
        # Contexto persistente para evitar duplicatas
        self.rel_map: Dict[tuple, str] = {}
        self.style_map: Set[str] = set()
        self.num_map: Dict[tuple, str] = {}
        self.abstract_map: Dict[tuple, str] = {}
        self.note_map: Dict[tuple, str] = {} 
        self.media_path_map: Dict[tuple, str] = {} # (id(src_pkg), old_path) -> new_path_in_target
        self.rel_signature_map: Dict[tuple, str] = {}
    def _transfer_element(self, src_pkg: DocxPackage, target_pkg: DocxPackage, element: ET._Element, src_part: str, target_part: str) -> ET._Element:
        new_element = copy.deepcopy(element)
        # 1. Sanitização Pesada
        self._resolver_sanitization(new_element)
        # 2. Notas (Recursivas com Numbering/Rels interno)
        self._resolver_notes(src_pkg, target_pkg, new_element)
        # 3. Listas (Agora com contexto e IDs otimizados)
        self._resolver_numbering(src_pkg, target_pkg, new_element)
        # 4. Estilos (Focado apenas em tags de Estilo reais)
        self._resolver_styles(src_pkg, target_pkg, new_element)
        
        # 5. Relacionamentos (Idempotente e seguro contra colisão de arquivos)
        self._resolver_relationships(src_pkg, target_pkg, new_element, src_part, target_part)
        
        return new_element
    def _resolver_relationships(self, src_pkg: DocxPackage, target_pkg: DocxPackage,
                                element: ET._Element, src_part: str, target_part: str):
        nodes_with_rid = element.xpath(".//*[@r:id]", namespaces=NS)
        if not nodes_with_rid:
            return
        src_rels_xml = src_pkg.get_part_xml(get_rels_part(src_part))
        target_rels_path = get_rels_part(target_part)
        target_rels_xml = target_pkg.get_part_xml(target_rels_path)
        # 🛠️ FIX 1: Identificador estável para o pacote (não usar id() de memória)
        # Usa o filename se disponível, senão fallback para id (apenas se for in-memory)
        src_pkg_key = getattr(src_pkg, 'filename', str(id(src_pkg)))
        for node in nodes_with_rid:
            old_rid = node.get(f"{{{NS['r']}}}id")
            # 🛠️ FIX 1: Uso da chave estável no mapa
            state_key = (src_pkg_key, src_part, old_rid)
            if state_key in self.rel_map:
                node.set(f"{{{NS['r']}}}id", self.rel_map[state_key])
                continue
            rel_entry = src_rels_xml.find(
                f".//rel:Relationship[@Id='{old_rid}']",
                namespaces=NS
            )
            if rel_entry is None:
                continue
            rel_type = rel_entry.get("Type")
            target_mode = rel_entry.get("TargetMode", "Internal")
            target_url = rel_entry.get("Target")
            final_target_path = target_url
            # 🔹 Resolver binários internos
            if target_mode != "External":
                # 🛠️ FIX 1: Uso da chave estável
                media_key = (src_pkg_key, target_url)
                if media_key in self.media_path_map:
                    final_target_path = self.media_path_map[media_key]
                else:
                    # 🛠️ FIX 2: Normalização de Caminhos para Padrão ZIP (Forward Slash)
                    # O Windows usa '\', mas o XML do Word EXIGE '/'
                    # 1. Calcular caminho absoluto dentro do ZIP de origem
                    src_dir = os.path.dirname(src_part)
                    src_res_path = os.path.normpath(os.path.join(src_dir, target_url))
                    src_res_path = src_res_path.replace(os.sep, "/") # Força '/'
                    # 2. Gerar nome único para o destino
                    # Nota: Mantemos a pasta 'media/' se ela existir no original ou forçamos
                    target_folder = os.path.dirname(target_url) 
                    filename_only = os.path.basename(target_url)
                    unique_name = self._ensure_unique_media_path(
                        target_pkg, filename_only
                    )
                    # Reconstrói o caminho relativo (ex: "media/imagem_1.png")
                    if target_folder:
                        final_target_path = f"{target_folder}/{unique_name}".replace("\\", "/")
                    else:
                        final_target_path = unique_name
                    try:
                        data = src_pkg.get_part_bytes(src_res_path)
                        # 3. Calcular caminho absoluto onde o byte será salvo no ZIP de destino
                        target_dir = os.path.dirname(target_part)
                        dest_abs_path = os.path.normpath(os.path.join(target_dir, final_target_path))
                        dest_abs_path = dest_abs_path.replace(os.sep, "/") # Força '/'
                        target_pkg.set_part_bytes(dest_abs_path, data)
                        
                        self.media_path_map[media_key] = final_target_path
                    except KeyError:
                        logger.error(f"Binário não encontrado no pacote origem: {src_res_path}")
                        # Se falhar, mantém o target original para não quebrar o XML, embora a imagem não vá aparecer
                        final_target_path = target_url
            # 🔹 Assinatura global por part destino
            rel_signature = (target_part, rel_type, final_target_path, target_mode)
            if rel_signature in self.rel_signature_map:
                new_rid = self.rel_signature_map[rel_signature]
            else:
                # Verificar se já existe no XML antes de criar
                existing = target_rels_xml.find(
                    f".//rel:Relationship[@Type='{rel_type}'][@Target='{final_target_path}']",
                    namespaces=NS
                )
                if existing is not None:
                    new_rid = existing.get("Id")
                else:
                    new_rid = get_next_rid(target_rels_xml)
                    ET.SubElement(
                        target_rels_xml,
                        f"{{{NS['rel']}}}Relationship",
                        Id=new_rid,
                        Type=rel_type,
                        Target=final_target_path,
                        TargetMode=target_mode
                    )
                self.rel_signature_map[rel_signature] = new_rid
            self.rel_map[state_key] = new_rid
            node.set(f"{{{NS['r']}}}id", new_rid)
    def _ensure_unique_media_path(self, target_pkg: DocxPackage, original_path: str) -> str:
        """Evita que imagens de pacotes diferentes com o mesmo nome se sobrescrevam."""
        existing = target_pkg.list_parts()
        if f"word/{original_path}" not in existing:
            return original_path
        
        base, ext = os.path.splitext(original_path)
        counter = 1
        while f"word/{base}_{counter}{ext}" in existing:
            counter += 1
        return f"{base}_{counter}{ext}"
    def _resolver_styles(self, src_pkg: DocxPackage, target_pkg: DocxPackage, element: ET._Element):
        """Identifica e importa estilos de parágrafo, caractere e tabela."""
        style_xpath = ".//w:pStyle | .//w:rStyle | .//w:tblStyle | .//w:pPrChange/w:pPr/w:pStyle"
        style_nodes = element.xpath(style_xpath, namespaces=NS)
        
        for node in style_nodes:
            sid = node.get(f"{{{NS['w']}}}val")
            if sid:
                # O cache style_map impede que processemos o mesmo estilo 1000 vezes
                self._import_style_recursive(src_pkg, target_pkg, sid)
    def _import_style_recursive(self, src_pkg: DocxPackage, target_pkg: DocxPackage, style_id: str):
        # 1. Verificar se já processamos este estilo nesta sessão de merge
        if not style_id or style_id in self.style_map: 
            return
        target_styles_xml = target_pkg.get_part_xml("word/styles.xml")
        
        # 2. Verificar se o estilo já existe fisicamente no documento de destino
        # (Isso evita duplicar estilos nativos como 'Normal' ou 'DefaultParagraphFont')
        if target_styles_xml.find(f".//w:style[@w:styleId='{style_id}']", namespaces=NS) is not None:
            self.style_map.add(style_id)
            return
        src_styles_xml = src_pkg.get_part_xml("word/styles.xml")
        style_def = src_styles_xml.find(f".//w:style[@w:styleId='{style_id}']", namespaces=NS)
        
        if style_def is None: 
            return
        # 🔄 3. RECURSÃO: Importar dependências (baseado em, linkado a, próximo estilo)
        # Isso é fundamental para manter a hierarquia visual do Word
        dependencies = style_def.xpath(".//w:basedOn/@w:val | .//w:link/@w:val | .//w:next/@w:val", namespaces=NS)
        for dep_sid in dependencies:
            self._import_style_recursive(src_pkg, target_pkg, dep_sid)
        # 4. Inserir a definição do estilo no destino
        target_styles_xml.append(copy.deepcopy(style_def))
        self.style_map.add(style_id)
    def _resolver_numbering(self, src_pkg: DocxPackage, target_pkg: DocxPackage, element: ET._Element):
        num_pr_nodes = element.xpath(".//w:numPr", namespaces=NS)
        if not num_pr_nodes: return
        src_num_xml = src_pkg.get_part_xml("word/numbering.xml")
        target_num_xml = target_pkg.get_part_xml("word/numbering.xml")
        # 🛠️ FIX 1: Identificador estável para o pacote (evita colisão de memória)
        src_pkg_key = getattr(src_pkg, 'filename', str(id(src_pkg)))
        for num_pr in num_pr_nodes:
            num_id_node = num_pr.find(f"{{{NS['w']}}}numId", namespaces=NS)
            if num_id_node is None: continue
            old_num_id = num_id_node.get(f"{{{NS['w']}}}val")
            if old_num_id == "0": continue
            # 🛠️ FIX 1: Uso da chave estável no mapa
            state_key = (src_pkg_key, "num", old_num_id)
            if state_key in self.num_map:
                num_id_node.set(f"{{{NS['w']}}}val", self.num_map[state_key])
                continue
            src_num_instance = src_num_xml.find(f".//w:num[@w:numId='{old_num_id}']", namespaces=NS)
            if src_num_instance is None: continue
            abs_node = src_num_instance.find(f"{{{NS['w']}}}abstractNumId", namespaces=NS)
            if abs_node is None: continue
            abs_num_id = abs_node.get(f"{{{NS['w']}}}val")
            # 🛠️ FIX 1: Uso da chave estável no mapa de abstracts
            abs_key = (src_pkg_key, "abs", abs_num_id)
            # 1. Resolver o AbstractNum (o molde da lista)
            if abs_key not in self.abstract_map:
                new_abs_id, _ = get_next_numbering_ids(target_num_xml)
                src_abs_num = src_num_xml.find(f".//w:abstractNum[@w:abstractNumId='{abs_num_id}']", namespaces=NS)
                if src_abs_num is not None:
                    new_abs_node = copy.deepcopy(src_abs_num)
                    new_abs_node.set(f"{{{NS['w']}}}abstractNumId", new_abs_id)
                    # 🛠️ FIX 2: Lógica de Inserção Inteligente (Insertion Logic)
                    # Não inserir cegamente no [0]. Encontrar o último abstractNum e inserir APÓS ele.
                    # Isso mantém a estrutura do XML válida e organizada.
                    last_abstracts = target_num_xml.findall(f".//w:abstractNum", namespaces=NS)
                    if last_abstracts:
                        # Pega o índice do último elemento encontrado e soma 1
                        last_node = last_abstracts[-1]
                        # Nota: .index() busca no children direto. Ensure last_node is direct child.
                        try:
                            insert_idx = list(target_num_xml).index(last_node) + 1
                            target_num_xml.insert(insert_idx, new_abs_node)
                        except ValueError:
                            # Fallback caso o xpath pegue algo aninhado (raro em numbering)
                            target_num_xml.insert(0, new_abs_node)
                    else:
                        # Se não houver nenhum, insere no início
                        target_num_xml.insert(0, new_abs_node)
                    self.abstract_map[abs_key] = new_abs_id
            # 2. Resolver o Num (a instância/contador da lista)
            _, new_num_id = get_next_numbering_ids(target_num_xml)
            new_num_node = copy.deepcopy(src_num_instance)
            new_num_node.set(f"{{{NS['w']}}}numId", new_num_id)
            # Atualiza a referência para apontar para o NOVO abstract importado
            # (Se o abs não foi encontrado no passo 1, o código quebraria, 
            #  mas assumimos integridade do doc origem)
            if abs_key in self.abstract_map:
                new_num_node.find(f"{{{NS['w']}}}abstractNumId", namespaces=NS).set(
                    f"{{{NS['w']}}}val", self.abstract_map[abs_key]
                )
            # <w:num> sempre vai no final do arquivo numbering.xml
            target_num_xml.append(new_num_node)
            self.num_map[state_key] = new_num_id
            num_id_node.set(f"{{{NS['w']}}}val", new_num_id)
    def _resolver_notes(self, src_pkg: DocxPackage, target_pkg: DocxPackage, element: ET._Element):
        note_types = {
            "w:footnoteReference": ("word/footnotes.xml", "footnote"),
            "w:endnoteReference": ("word/endnotes.xml", "endnote")
        }
        for ref_tag, (part_name, base_tag) in note_types.items():
            refs = element.xpath(f".//{ref_tag}", namespaces=NS)
            if not refs: continue
            for ref in refs:
                old_id = ref.get(f"{{{NS['w']}}}id")
                if not old_id or int(old_id) <= 0: continue
                # 🔥 MUDANÇA CRÍTICA: Use o objeto src_pkg na chave, não o id()
                # Isso impede a reciclagem do ID e garante unicidade real.
                state_key = (src_pkg, base_tag, old_id) 
                
                if state_key in self.note_map:
                    new_id = self.note_map[state_key]
                    ref.set(f"{{{NS['w']}}}id", new_id)
                    logger.debug(f"   ♻️ Cache Hit Real: {old_id} -> {new_id}")
                    continue
                # 2. Localizar conteúdo no arquivo de origem
                try:
                    src_note_xml = src_pkg.get_part_xml(part_name)
                    src_note_content = src_note_xml.find(f".//w:{base_tag}[@w:id='{old_id}']", namespaces=NS)
                except KeyError:
                    logger.error(f"   ❌ Arquivo de parte '{part_name}' não existe no pacote de origem.")
                    continue
                if src_note_content is not None:
                    # 3. Preparar destino
                    target_note_xml = target_pkg.get_part_xml(part_name)
                    new_id = get_next_note_id(target_note_xml)
                    logger.debug(f"   ✨ Transplantando {base_tag}: {old_id} -> {new_id}")
                    # 4. Criar cópia e atualizar ID físico
                    new_note_node = copy.deepcopy(src_note_content)
                    new_note_node.set(f"{{{NS['w']}}}id", new_id)
                    target_note_xml.append(new_note_node)
                    # 5. RESOLUÇÃO RECURSIVA (Onde o problema geralmente se esconde)
                    logger.debug(f"      🔄 Iniciando recursão para conteúdo da nota {new_id}...")
                    self._resolver_numbering(src_pkg, target_pkg, new_note_node)
                    self._resolver_styles(src_pkg, target_pkg, new_note_node)
                    self._resolver_relationships(src_pkg, target_pkg, new_note_node, part_name, part_name)
                    # 6. Registrar e atualizar referência
                    self.note_map[state_key] = new_id
                    ref.set(f"{{{NS['w']}}}id", new_id)
                else:
                    logger.warning(f"   ⚠️ Conteúdo da nota {old_id} não encontrado em {part_name}!")
    @staticmethod
    def _resolver_sanitization(element: ET._Element):
        """O 'Esquadrão de Limpeza': remove lixo de revisão e marcas de controle."""
        
        # 1. Atributos de RSID (Aqui o iter() funciona bem com Clark Notation ou busca genérica)
        for elem in element.iter():
            # Buscamos qualquer atributo que contenha 'rsid' no nome
            attribs_to_del = [a for a in elem.attrib if 'rsid' in a.lower()]
            for attr in attribs_to_del:
                del elem.attrib[attr]
        # 2. Tags de Revisão, Marcadores e Permissões
        # Mudamos para usar o prefixo 'w:' pois o .xpath() exige mapeamento por prefixo
        targets = [
            "w:proofErr", 
            "w:lastRenderedPageBreak",
            "w:bookmarkStart", "w:bookmarkEnd",
            "w:commentRangeStart", "w:commentRangeEnd",
            "w:permStart", "w:permEnd"
        ]
        
        for target in targets:
            # Agora o XPath ficará formatado como ".//w:proofErr", etc.
            for node in element.xpath(f".//{target}", namespaces=NS):
                p = node.getparent()
                if p is not None:
                    p.remove(node)
    def replace_docx(self, placeholder: str, src_pkg: DocxPackage, target_pkg: DocxPackage):
        """
        Substitui um placeholder por todo o conteúdo de outro documento.
        """
        target_part = "word/document.xml"
        target_root = target_pkg.get_part_xml(target_part)
        target_body = target_root.find(f"{{{NS['w']}}}body")
        # 1. Localização robusta do parágrafo alvo
        # Usamos itertext para garantir que pegamos texto fragmentado
        target_paragraph = None
        for p in target_body.xpath(".//w:p", namespaces=NS):
            if placeholder in "".join(p.itertext()):
                target_paragraph = p
                break
        if target_paragraph is None:
            logger.error(f"Placeholder '{placeholder}' não encontrado no documento.")
            return
        insert_index = target_body.index(target_paragraph)
        # 2. Extração do conteúdo de origem
        src_part = "word/document.xml"
        src_root = src_pkg.get_part_xml(src_part)
        src_body = src_root.find(f"{{{NS['w']}}}body")
        # Coletar elementos, mas cuidado com sectPr internos
        src_blocks = []
        for el in src_body:
            if el.tag == f"{{{NS['w']}}}sectPr":
                continue
            # Limpeza preventiva: Se for um parágrafo com quebra de seção interna, 
            # removemos a quebra para o conteúdo fluir no layout do destino.
            # (A menos que você QUEIRA manter a quebra, aí a lógica muda)
            sect_pr_internal = el.xpath(".//w:pPr/w:sectPr", namespaces=NS)
            if sect_pr_internal:
                for s in sect_pr_internal:
                    s.getparent().remove(s)
            src_blocks.append(el)
        # 3. Transferência e Inserção
        # Inserimos em ordem reversa ou usamos um offset para manter a sequência
        for offset, block in enumerate(src_blocks):
            new_block = self._transfer_element(
                src_pkg, target_pkg, block, src_part, target_part
            )
            target_body.insert(insert_index + offset, new_block)
        # 4. Cleanup e Persistência
        target_body.remove(target_paragraph)
        
        # Sincroniza o XML de volta ao pacote
        target_pkg.set_part_xml(target_part, target_root)
        
        logger.info(f"Conteúdo de {id(src_pkg)} inserido no lugar de '{placeholder}'.")
    def replace_with_range(self, placeholder: str, src_pkg: DocxPackage, target_pkg: DocxPackage, 
                         start_markers: list, stop_markers: list):
        """
        Localiza um placeholder no destino e o substitui por um intervalo de blocos
        extraídos da origem, delimitado por listas de marcadores de início e fim.
        """
        target_part = "word/document.xml"
        target_root = target_pkg.get_part_xml(target_part)
        target_body = target_root.find(f"{{{NS['w']}}}body")
        # 1. Localizar ponto de inserção no destino
        target_paragraph = None
        for p in target_body.xpath(".//w:p", namespaces=NS):
            if placeholder in "".join(p.itertext()):
                target_paragraph = p
                break
        if target_paragraph is None:
            logger.error(f"Placeholder '{placeholder}' não encontrado no documento.")
            return
        insert_index = target_body.index(target_paragraph)
        # 2. Extração Seletiva na Origem
        src_part = "word/document.xml"
        src_root = src_pkg.get_part_xml(src_part)
        src_body = src_root.find(f"{{{NS['w']}}}body")
        capturing = False
        blocks_to_transfer = []
        for block in src_body:
            if block.tag == f"{{{NS['w']}}}sectPr":
                continue
            # Extraímos o texto do bloco para busca (funciona para w:p e w:tbl)
            block_text = "".join(block.itertext())
            # Verificamos gatilho de parada (Stop)
            if capturing and any(stop in block_text for stop in stop_markers):
                logger.debug(f"Stop marker encontrado: {block_text[:30]}...")
                break # Encerra a captura
            # Se estiver capturando, guarda o bloco
            if capturing:
                blocks_to_transfer.append(block)
            # Verificamos gatilho de início (Start)
            if not capturing and any(start in block_text for start in start_markers):
                logger.debug(f"Start marker encontrado: {block_text[:30]}...")
                capturing = True
                # Opcional: Se quiser incluir o parágrafo do marcador de início, 
                # descomente a linha abaixo:
                # blocks_to_transfer.append(block)
        # 3. Transferência e Injeção
        if not blocks_to_transfer:
            logger.warning("Nenhum conteúdo encontrado entre os marcadores fornecidos.")
            return
        for offset, block in enumerate(blocks_to_transfer):
            new_block = self._transfer_element(
                src_pkg, target_pkg, block, src_part, target_part
            )
            target_body.insert(insert_index + offset, new_block)
        # 4. Cleanup
        target_body.remove(target_paragraph)
        target_pkg.set_part_xml(target_part, target_root)
        
        logger.info(f"Extraídos {len(blocks_to_transfer)} blocos entre os marcadores.")
    def replace_multiple_docx(self, placeholder: str, src_paths: list, target_pkg: DocxPackage):
        """
        Recebe uma lista de strings (caminhos de arquivo) e insere o conteúdo
        integral de cada um no lugar do placeholder.
        """
        target_part = "word/document.xml"
        target_root = target_pkg.get_part_xml(target_part)
        target_body = target_root.find(f"{{{NS['w']}}}body")
        # 1. Localizar ponto de inserção
        target_paragraph = next(
            (p for p in target_body.xpath(".//w:p", namespaces=NS) 
             if placeholder in "".join(p.itertext())), 
            None
        )
        if target_paragraph is None:
            logger.error(f"Placeholder '{placeholder}' não encontrado.")
            return
        insert_index = target_body.index(target_paragraph)
        current_offset = 0
        # 2. Iterar pelos caminhos
        for path in src_paths:
            logger.debug(f"Processando integração de: {path}")
            # Instancia o pacote internamente
            src_pkg = DocxPackage(path) 
            src_root = src_pkg.get_part_xml("word/document.xml")
            src_body = src_root.find(f"{{{NS['w']}}}body")
            for el in src_body:
                if el.tag == f"{{{NS['w']}}}sectPr":
                    continue
                
                # O motor 'self' mantém o contexto de IDs entre arquivos diferentes!
                new_block = self._transfer_element(
                    src_pkg, target_pkg, el, "word/document.xml", target_part
                )
                
                target_body.insert(insert_index + current_offset, new_block)
                current_offset += 1
        # 3. Cleanup
        target_body.remove(target_paragraph)
        target_pkg.set_part_xml(target_part, target_root)
    def replace_multiple_ranges(self, placeholder: str, configs: list, target_pkg: DocxPackage):
        """
        Substitui por intervalos, mas agora as configs aceitam o path:
        configs = [{"path": "caminho/doc.docx", "start": [...], "stop": [...]}, ...]
        """
        target_part = "word/document.xml"
        target_root = target_pkg.get_part_xml(target_part)
        target_body = target_root.find(f"{{{NS['w']}}}body")
        target_paragraph = next(
            (p for p in target_body.xpath(".//w:p", namespaces=NS) 
             if placeholder in "".join(p.itertext())), 
            None
        )
        if target_paragraph is None: return
        insert_index = target_body.index(target_paragraph)
        current_offset = 0
        for cfg in configs:
            # Instancia o pacote a partir do path fornecido na config
            src_pkg = DocxPackage(cfg["path"]) 
            start_markers = cfg["start"]
            stop_markers = cfg["stop"]
            src_root = src_pkg.get_part_xml("word/document.xml")
            src_body = src_root.find(f"{{{NS['w']}}}body")
            capturing = False
            blocks_to_transfer = []
            for block in src_body:
                if block.tag == f"{{{NS['w']}}}sectPr": continue
                
                text = "".join(block.itertext())
                if capturing and any(stop in text for stop in stop_markers):
                    break
                if capturing:
                    blocks_to_transfer.append(block)
                if not capturing and any(start in text for start in start_markers):
                    capturing = True
            for block in blocks_to_transfer:
                new_block = self._transfer_element(
                    src_pkg, target_pkg, block, "word/document.xml", target_part
                )
                target_body.insert(insert_index + current_offset, new_block)
                current_offset += 1
        target_body.remove(target_paragraph)
        target_pkg.set_part_xml(target_part, target_root)
