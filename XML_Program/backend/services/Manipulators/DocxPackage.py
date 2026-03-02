import zipfile
import logging
from io import BytesIO
from pathlib import Path
from typing import Dict, Union, List
import lxml.etree as ET

SourceType = Union[str, Path, bytes, BytesIO]
logger = logging.getLogger(__name__)

from .utils import NS

class DocxPackage:
    """
    CONTÊINER PURO: Gerencia apenas a integridade do ZIP e o tráfego de dados.
    Responsabilidades: Load, Save, Get, Set.
    """
    def __init__(self, source: Union[str, Path, bytes, BytesIO]):
        self._files: Dict[str, bytes] = {}
        self._xml_cache: Dict[str, ET._Element] = {}
        self._load(source)

    # -------------------------
    # Persistência (Load)
    # -------------------------
    def _load(self, source: SourceType):
        """
        Lê a fonte (Caminho, Bytes ou BytesIO) e descompacta o 
        conteúdo para o dicionário interno.
        """
        try:
            if isinstance(source, (str, Path)):
                if not Path(source).exists():
                    raise FileNotFoundError(f"Arquivo não encontrado: {source}")
                zip_source = zipfile.ZipFile(source, "r")
            elif isinstance(source, (bytes, bytearray)):
                zip_source = zipfile.ZipFile(BytesIO(source), "r")
            elif isinstance(source, BytesIO):
                zip_source = zipfile.ZipFile(source, "r")
            else:
                raise TypeError(f"Fonte inválida: {type(source)}. Esperado Path, bytes ou BytesIO.")

            with zip_source as z:
                # Validação de integridade do ZIP
                bad_file = z.testzip()
                if bad_file:
                    raise zipfile.BadZipFile(f"Arquivo ZIP corrompido detectado: {bad_file}")

                # Extração total para memória
                for name in z.namelist():
                    self._files[name] = z.read(name)
            
            self._loaded = True
            logger.debug(f"Pacote carregado. {len(self._files)} partes em memória.")

        except zipfile.BadZipFile as e:
            logger.error(f"Erro: O arquivo não é um DOCX/ZIP válido. {e}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao carregar pacote: {e}")
            raise

    # -------------------------
    # Persistência (Save)
    # -------------------------
    def save_to_path(self, path: Union[str, Path]):
        """
        Sincroniza alterações do cache XML e grava o pacote ZIP no disco.
        """
        # 1. COMMIT: Sincroniza o cache de XML para o dicionário de bytes
        for internal_path, xml_root in self._xml_cache.items():
            try:
                self._files[internal_path] = ET.tostring(
                    xml_root, 
                    encoding='utf-8', 
                    xml_declaration=True, 
                    standalone="yes"
                )
                logger.debug(f"Sincronizado: {internal_path}")
            except Exception as e:
                logger.error(f"Falha ao serializar XML de '{internal_path}': {e}")
                raise

        # 2. GRAVAÇÃO: Escreve o ZIP físico no destino
        try:
            output_path = Path(path)
            
            # Garante que a pasta de destino existe
            if not output_path.parent.exists():
                output_path.parent.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
                for name, content in self._files.items():
                    z.writestr(name, content)
            
            logger.info(f"Sucesso: Documento salvo em '{output_path}'")

        except PermissionError:
            logger.error(f"Erro de Permissão: O arquivo '{path}' pode estar aberto em outro programa.")
            raise
        except Exception as e:
            logger.error(f"Falha ao gravar arquivo no disco: {e}")
            raise

    def _create_default_part(self, internal_path: str) -> ET._Element:
        """
        Cria estrutura mínima válida para parts conhecidas.
        """
        W_NS = NS['w']
        REL_NS = NS['rel']
        # --- Relationships (.rels) ---
        if internal_path.endswith(".rels"):
            return ET.Element(
                f"{{{REL_NS}}}Relationships",
                nsmap={None: REL_NS}
            )
        # --- Numbering ---
        if internal_path.endswith("numbering.xml"):
            return ET.Element(
                f"{{{W_NS}}}numbering",
                nsmap={None: W_NS}
            )
        # --- Footnotes ---
        if internal_path.endswith("footnotes.xml"):
            root = ET.Element(
                f"{{{W_NS}}}footnotes",
                nsmap={None: W_NS}
            )
            self._append_special_note(root, note_type="separator", note_id="-1")
            self._append_special_note(root, note_type="continuationSeparator", note_id="0")
            return root
        # --- Endnotes ---
        if internal_path.endswith("endnotes.xml"):
            root = ET.Element(
                f"{{{W_NS}}}endnotes",
                nsmap={None: W_NS}
            )
            self._append_special_note(root, note_type="separator", note_id="-1")
            self._append_special_note(root, note_type="continuationSeparator", note_id="0")
            return root

        raise KeyError(f"Part '{internal_path}' not found and no fallback defined.")

    def _append_special_note(self, root, note_type: str, note_id: str):
        """
        Cria nota especial exigida pelo Word:
        separator ou continuationSeparator
        """

        W_NS = NS['w']

        note_tag = root.tag.split("}")[-1][:-1]  # footnotes -> footnote
        note = ET.SubElement(
            root,
            f"{{{W_NS}}}{note_tag}",
            {f"{{{W_NS}}}id": note_id}
        )

        ET.SubElement(
            note,
            f"{{{W_NS}}}{note_type}"
        )

    # --- Acesso e Mutação (Get/Set) ---
    def get_part_bytes(self, internal_path: str) -> bytes:
        """Retorna os bytes brutos de qualquer parte."""
        if internal_path not in self._files:
            raise KeyError(f"Parte {internal_path} não existe no pacote.")
        return self._files[internal_path]

    def set_part_bytes(self, internal_path: str, data: bytes):
        """Sobrescreve os bytes de uma parte e limpa o cache de XML."""
        self._files[internal_path] = data
        self._xml_cache.pop(internal_path, None)

    def get_part_xml(self, internal_path: str) -> ET._Element:
        """
        Retorna o XML da part.
        Se a part não existir, cria estrutura mínima válida
        para tipos conhecidos (.rels, numbering.xml).
        """

        if internal_path in self._xml_cache:
            return self._xml_cache[internal_path]

        try:
            data = self.get_part_bytes(internal_path)
            root = ET.fromstring(data)
        except KeyError:
            # Part não existe → fallback estruturado
            root = self._create_default_part(internal_path)
            self.set_part_xml(internal_path, root)

        self._xml_cache[internal_path] = root
        return root

    def set_part_xml(self, internal_path: str, root: ET._Element):
        """Atualiza o cache de XML para uma parte específica."""
        self._xml_cache[internal_path] = root

    def list_parts(self) -> List[str]:
        return list(self._files.keys())

    def part_exists(self, internal_path: str) -> bool:
        """
        Verifica se uma determinada parte existe no pacote (nos arquivos carregados ou no cache XML).
        
        Args:
            internal_path (str): O caminho interno do arquivo no ZIP (ex: 'word/document.xml').
            
        Returns:
            bool: True se a parte existir, False caso contrário.
        """
        # Verifica se está nos arquivos físicos carregados
        if internal_path in self._files:
            return True
            
        # Verifica se está no cache de XML (pode ter sido criada mas ainda não serializada)
        if internal_path in self._xml_cache:
            return True
            
        return False