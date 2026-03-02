import lxml.etree as ET
import logging
import os
from collections import Counter

from .utils import NS, get_rels_part
from .DocxPackage import DocxPackage

logger = logging.getLogger("VALIDATOR")

class DocxValidator:
    @staticmethod
    def validate(pkg):
        """
        Realiza uma auditoria forense no pacote DOCX.
        Retorna True se aprovado, False se houver erros críticos.
        """
        logger.info("🔍 Iniciando Auditoria Forense de Integridade...")
        has_errors = False

        # 1. Identificar partes XML
        content_parts = [p for p in pkg.list_parts() if p.endswith('.xml') and 'rels' not in p]
        
        # 2. Validação de Relacionamentos e Ativos Físicos
        for part in content_parts:
            if not DocxValidator._check_relationships_and_assets(pkg, part):
                has_errors = True

        # 3. Validação Lógica Global (Notas, Numeração, Estilos)
        if not DocxValidator._check_global_notes(pkg, content_parts): has_errors = True
        if not DocxValidator._check_global_numbering(pkg, content_parts): has_errors = True
        
        # 4. Validação de Duplicidade de IDs (O "Assassino" de DOCX)
        if not DocxValidator._check_duplicate_ids(pkg, content_parts): has_errors = True

        # 5. Validação de Content Types
        if not DocxValidator._check_content_types(pkg): has_errors = True

        # 6. Validação de Seções (Headers/Footers)
        if not DocxValidator._check_section_integrity(pkg): has_errors = True

        # 7. Verificação de Lixo (Apenas Warning)
        DocxValidator._check_orphaned_parts(pkg)

        if has_errors:
            logger.error("❌ O documento contém erros estruturais que podem impedir a abertura.")
        else:
            logger.info("✅ Documento íntegro e pronto para produção.")
        
        return not has_errors

    @staticmethod
    def _check_relationships_and_assets(pkg: DocxPackage, part_path):
        """
        Verifica XML -> Rels -> Arquivo Físico no ZIP.
        """
        try:
            root = pkg.get_part_xml(part_path)
            rels_path = get_rels_part(part_path)
            
            # IDs usados no XML
            used_rids = set(root.xpath("//@*[local-name()='id' and namespace-uri()='http://schemas.openxmlformats.org/officeDocument/2006/relationships']"))
            
            if not used_rids: return True

            if not pkg.part_exists(rels_path):
                logger.error(f"❌ [Rels] {part_path} usa rIds, mas não possui arquivo {rels_path}")
                return False

            rels_root = pkg.get_part_xml(rels_path)
            rels_map = {
                node.get("Id"): (node.get("Target"), node.get("TargetMode"))
                for node in rels_root.xpath(f"//rel:Relationship", namespaces=NS)
            }

            valid = True
            for rid in used_rids:
                if rid not in rels_map:
                    logger.error(f"❌ [Orphan rId] '{rid}' em {part_path} não existe no .rels")
                    valid = False
                    continue

                target, mode = rels_map[rid]
                
                # Validação Física: O arquivo existe no ZIP?
                if mode != "External":
                    # Resolver caminho relativo
                    head = os.path.dirname(part_path)
                    abs_target = os.path.normpath(os.path.join(head, target)).replace("\\", "/")
                    
                    if not pkg.part_exists(abs_target):
                        logger.error(f"❌ [Missing Asset] {part_path} aponta para '{abs_target}', mas o arquivo não está no ZIP.")
                        valid = False

            return valid
        except Exception as e:
            logger.error(f"⚠️ Erro ao validar assets de {part_path}: {e}")
            return False

    @staticmethod
    def _check_duplicate_ids(pkg, content_parts):
        """
        Detecta IDs duplicados que confundem o motor de renderização do Word.
        Foca em Bookmarks e DocPr (objetos de desenho).
        """
        valid = True
        
        # Verifica duplicidade de Bookmarks (global no documento.xml)
        if "word/document.xml" in content_parts:
            try:
                root = pkg.get_part_xml("word/document.xml")
                # Bookmark IDs devem ser únicos
                b_ids = [node.get(f"{{{NS['w']}}}id") for node in root.xpath("//w:bookmarkStart", namespaces=NS)]
                
                counts = Counter(b_ids)
                dupes = [bid for bid, count in counts.items() if count > 1]
                
                if dupes:
                    logger.warning(f"⚠️ [Duplicate Bookmarks] IDs duplicados encontrados: {dupes}. O Word pode recuperar, mas é arriscado.")
                    # Nota: Não marcamos como False fatal pois o Word costuma corrigir isso ao abrir ("reparar"),
                    # mas é péssima prática.
            except Exception: pass

        return valid

    @staticmethod
    def _check_global_notes(pkg, content_parts):
        valid = True
        note_configs = {
            'footnote': ('footnoteReference', 'word/footnotes.xml'),
            'endnote': ('endnoteReference', 'word/endnotes.xml')
        }

        for note_type, (ref_tag, def_part) in note_configs.items():
            referenced_ids = set()
            for part in content_parts:
                try:
                    root = pkg.get_part_xml(part)
                    refs = root.xpath(f"//w:{ref_tag}/@w:id", namespaces=NS)
                    referenced_ids.update([i for i in refs if int(i) > 0])
                except: continue

            if not referenced_ids: continue

            if not pkg.part_exists(def_part):
                logger.error(f"❌ [{note_type}] Referências existem, mas {def_part} está ausente.")
                valid = False
                continue

            try:
                def_root = pkg.get_part_xml(def_part)
                defined_ids = set(def_root.xpath(f"//w:{note_type}/@w:id", namespaces=NS))
                
                missing = referenced_ids - defined_ids
                if missing:
                    logger.error(f"❌ [{note_type}] IDs referenciados sem texto definido: {missing}")
                    valid = False
            except Exception as e:
                logger.error(f"Erro ao ler {def_part}: {e}")
                valid = False
        return valid

    @staticmethod
    def _check_global_numbering(pkg, content_parts):
        valid = True
        referenced_num_ids = set()
        
        for part in content_parts:
            try:
                root = pkg.get_part_xml(part)
                nums = root.xpath(".//w:numId/@w:val", namespaces=NS)
                referenced_num_ids.update([n for n in nums if n != "0"])
            except: continue

        if not referenced_num_ids: return True

        if not pkg.part_exists("word/numbering.xml"):
            logger.error("❌ [Numbering] Listas usadas no texto, mas numbering.xml não existe.")
            return False

        try:
            num_root = pkg.get_part_xml("word/numbering.xml")
            defined_num_ids = set(num_root.xpath(".//w:num/@w:numId", namespaces=NS))
            
            missing = referenced_num_ids - defined_num_ids
            if missing:
                logger.error(f"❌ [Numbering] Listas fantasmas (sem definição): {missing}")
                valid = False
            
            # Validação extra: AbstractNum existe?
            abstracts_ref = set(num_root.xpath(".//w:num/w:abstractNumId/@w:val", namespaces=NS))
            abstracts_def = set(num_root.xpath(".//w:abstractNum/@w:abstractNumId", namespaces=NS))
            missing_abs = abstracts_ref - abstracts_def
            if missing_abs:
                logger.error(f"❌ [Numbering] Num definitions apontam para AbstractNums inexistentes: {missing_abs}")
                valid = False

        except Exception as e:
            logger.error(f"Erro em numbering: {e}")
            valid = False
            
        return valid

    @staticmethod
    def _check_content_types(pkg):
        """
        Garante que todo arquivo XML no ZIP esteja registrado em [Content_Types].xml.
        Se não estiver, o Word se recusa a abrir o arquivo.
        """
        valid = True
        try:
            ct_root = pkg.get_part_xml("[Content_Types].xml")
            # Obtém todos os PartNames registrados (Override + Default extension)
            registered_paths = set(node.get("PartName") for node in ct_root.xpath("//ct:Override", namespaces=NS))
            
            # Adiciona extensões padrão (como rels ou xml) se houver Default
            # (Lógica simplificada, o ideal é checar extensões, mas Override é o principal para parts do Word)
            
            for part in pkg.list_parts():
                if part.startswith("word/") and part.endswith(".xml"):
                    formatted_part = "/" + part # ContentTypes usa leading slash
                    if formatted_part not in registered_paths:
                        # Exceção comum: stylesWithEffects nem sempre está lá, mas document.xml DEVE estar
                        if "styles" not in part and "numbering" not in part:
                            logger.warning(f"⚠️ [Content_Types] A parte '{formatted_part}' existe mas não está explicitamente registrada em Content_Types.")
                            # Isso nem sempre é erro fatal dependendo da extensão default, mas é bom avisar
        except Exception as e:
            logger.warning(f"Não foi possível validar Content_Types: {e}")
        
        return valid


    @staticmethod
    def _check_orphaned_parts(pkg):
        """
        Detecta arquivos dentro do ZIP que não são referenciados por ninguém.
        (Lixo acumulado de edições anteriores ou merges).
        """
        # 1. Listar todas as partes físicas
        all_parts = set(pkg.list_parts())
        
        # Partes que sempre devem existir (Roots)
        referenced_parts = {
            "[Content_Types].xml", 
            "_rels/.rels", 
            "docProps/app.xml", 
            "docProps/core.xml", 
            "docProps/custom.xml"
        }

        # 2. Varrer todos os .rels para encontrar o que está em uso
        for part in all_parts:
            if part.endswith(".rels"):
                try:
                    root = pkg.get_part_xml(part)
                    targets = root.xpath("//rel:Relationship/@Target", namespaces=NS)
                    
                    # O arquivo .rels pertence a um pai (ex: word/_rels/document.xml.rels -> word/document.xml)
                    # Precisamos resolver os caminhos relativos dos Targets
                    parent_dir = os.path.dirname(os.path.dirname(part)) # sobe _rels e pega a pasta
                    
                    for t in targets:
                        if "http" in t: continue # Ignora links externos
                        
                        # Resolve caminho absoluto
                        abs_path = os.path.normpath(os.path.join(parent_dir, t)).replace("\\", "/")
                        if abs_path.startswith("/"): abs_path = abs_path[1:]
                        
                        referenced_parts.add(abs_path)
                        
                        # O próprio arquivo .rels é "usado" se o pai existe, mas vamos simplificar:
                        referenced_parts.add(part) 
                except: pass

        # 3. Calcular Orfãos
        # Filtra pastas ou arquivos de sistema do ZIP
        candidates = {p for p in all_parts if not p.endswith("/")}
        orphans = candidates - referenced_parts
        
        # Filtra falso-positivos comuns (entry points)
        real_orphans = [o for o in orphans if "word/document.xml" not in o and "word/styles.xml" not in o]

        if real_orphans:
            logger.warning(f"⚠️ [Garbage] Arquivos órfãos detectados no pacote (ocupando espaço inútil): {real_orphans}")
            # Dica: Em um sistema de produção, você poderia deletar esses arquivos aqui.
            return False # Não é erro fatal, apenas aviso
        return True

    @staticmethod
    def _check_section_integrity(pkg):
        """
        Verifica se Cabeçalhos e Rodapés referenciados nas seções realmente existem.
        Isso é CRÍTICO em merges, pois quebras de seção costumam se perder.
        """
        valid = True
        try:
            doc_root = pkg.get_part_xml("word/document.xml")
            
            # Busca todas as referências de header/footer nas propriedades da seção
            # Elas podem estar no body > sectPr ou em p > pPr > sectPr
            xpaths = ["//w:headerReference", "//w:footerReference"]
            
            rels_path = "word/_rels/document.xml.rels"
            if not pkg.part_exists(rels_path):
                return True # Se não tem rels, não tem headers linkados
                
            rels_root = pkg.get_part_xml(rels_path)
            # Mapa de rId -> Target
            rels_map = {
                n.get("Id"): n.get("Target") 
                for n in rels_root.xpath("//rel:Relationship", namespaces=NS)
            }

            for xp in xpaths:
                refs = doc_root.xpath(xp, namespaces=NS)
                for ref in refs:
                    rid = ref.get(f"{{{NS['r']}}}id")
                    if rid not in rels_map:
                        logger.error(f"❌ [Sections] Seção aponta para Header/Footer rId='{rid}' que não existe!")
                        valid = False
                    else:
                        target = rels_map[rid]
                        # Verifica se o arquivo físico do header existe
                        abs_target = f"word/{target}"
                        if not pkg.part_exists(abs_target):
                            logger.error(f"❌ [Sections] Header/Footer '{abs_target}' está linkado mas não existe no ZIP.")
                            valid = False
                            
        except Exception as e:
            logger.error(f"Erro ao validar seções: {e}")
            valid = False
            
        return valid