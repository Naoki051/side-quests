import os
import shutil
import re
from datetime import datetime
from PIL import Image, ExifTags
from pathlib import Path

# --- CONFIGURAÇÕES ---
DIR_ORIGEM = "./"
DIR_DESTINO = "./Fotos_Organizadas" 
DRY_RUN = False  # <--- LEMBRE-SE DE MUDAR PARA FALSE PARA EXECUTAR
# ---------------------

REGEX_PATTERNS = [
    r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})[-_]?(\d{2})[-_]?(\d{2})[-_]?(\d{2})',
    r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})'
]

def obter_data_exif(caminho_arquivo):
    try:
        img = Image.open(caminho_arquivo)
        exif = img._getexif()
        if not exif: return None
        for tag, value in exif.items():
            decoded = ExifTags.TAGS.get(tag, tag)
            if decoded == 'DateTimeOriginal':
                return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
    except:
        return None
    return None

def obter_data_nome(nome_arquivo):
    for pattern in REGEX_PATTERNS:
        match = re.search(pattern, nome_arquivo)
        if match:
            g = match.groups()
            if len(g) >= 6:
                return datetime(int(g[0]), int(g[1]), int(g[2]), int(g[3]), int(g[4]), int(g[5]))
            elif len(g) >= 3:
                return datetime(int(g[0]), int(g[1]), int(g[2]), 0, 0, 0)
    return None

def obter_data_arquivo(caminho_arquivo):
    return datetime.fromtimestamp(os.path.getmtime(caminho_arquivo))

def gerar_nome_unico(pasta, nome_base, ext):
    contador = 1
    novo_nome = f"{nome_base}{ext}"
    while os.path.exists(os.path.join(pasta, novo_nome)):
        novo_nome = f"{nome_base}_{contador}{ext}"
        contador += 1
    return novo_nome

def processar():
    extensions = {'.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi', '.heic'}
    ignorados = {'organizar_fotos.py', 'print_dir.py', '.ds_store'}
    
    print(f"--- INICIANDO ORGANIZAÇÃO (DRY_RUN={DRY_RUN}) ---")
    arquivos_proc = 0
    
    for root, dirs, files in os.walk(DIR_ORIGEM):
        if os.path.abspath(DIR_DESTINO) in os.path.abspath(root): continue
            
        for file in files:
            if file.lower() in ignorados: continue
            
            path_full = Path(root) / file
            ext = path_full.suffix.lower()
            
            if ext not in extensions: continue
            
            arquivos_proc += 1
            
            data = obter_data_exif(path_full)
            metodo = "EXIF"
            
            if not data:
                data = obter_data_nome(file)
                metodo = "Nome"
            
            if not data:
                data = obter_data_arquivo(path_full)
                metodo = "Sistema"
            
            ano = str(data.year)
            novo_nome = data.strftime('%Y-%m-%d_%H-%M-%S')
            pasta_final = Path(DIR_DESTINO) / ano
            
            if DRY_RUN:
                print(f"[{metodo}] {file} -> {pasta_final}/{novo_nome}{ext}")
            else:
                # --- ALTERAÇÃO AQUI: Verifica se existe antes de criar ---
                if not os.path.exists(pasta_final):
                    os.makedirs(pasta_final, exist_ok=True)
                    print(f"📂 [NOVO DIRETÓRIO] Criando pasta: {pasta_final}")
                # ---------------------------------------------------------
                
                nome_final = gerar_nome_unico(pasta_final, novo_nome, ext)
                shutil.copy2(path_full, pasta_final / nome_final)
                print(f"Copiado: {file} -> {pasta_final}/{nome_final}")

    print(f"--- FIM. {arquivos_proc} arquivos processados. ---")

if __name__ == "__main__":
    processar()