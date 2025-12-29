# 📸 Organizador de Fotos e Vídeos em Python

Script em Python para organizar fotos e vídeos automaticamente por **ano**, usando a melhor data disponível (EXIF, nome do arquivo ou sistema).

---

## 🚀 Funcionalidades

* 📅 Detecta a data do arquivo por prioridade:

  1. Metadados **EXIF**
  2. **Nome do arquivo** (ex: `2023-08-15_14-30-00.jpg`)
  3. **Data de modificação** do sistema
* 📂 Organiza arquivos em pastas por **ano**
* 🏷️ Renomeia arquivos no formato `YYYY-MM-DD_HH-MM-SS.ext`
* 🔁 Evita sobrescrita (adiciona sufixos `_1`, `_2`, …)
* 🧪 Modo **DRY_RUN** para simulação segura

---

## 📁 Estrutura Gerada

```text
Fotos_Organizadas/
 └── 2023/
     ├── 2023-08-15_14-30-00.jpg
     └── 2023-08-15_14-30-00_1.jpg
```

---

## 🗂️ Tipos de Arquivos Suportados

* Imagens: `.jpg`, `.jpeg`, `.png`, `.heic`
* Vídeos: `.mp4`, `.mov`, `.avi`

---

## ⚙️ Configuração

Edite no início do script:

```python
DIR_ORIGEM = "./"
DIR_DESTINO = "./Fotos_Organizadas"
DRY_RUN = True  # True = simulação | False = executa
```

---

## ▶️ Como Usar

### 1️⃣ Instalar dependências

```bash
pip install pillow
```

### 2️⃣ Executar em modo de teste

```bash
python organizar_fotos.py
```

### 3️⃣ Executar de verdade

Altere:

```python
DRY_RUN = False
```

E execute novamente.

---

## 📄 Licença

Uso livre para projetos pessoais ou educacionais.

