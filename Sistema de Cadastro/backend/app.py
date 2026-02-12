from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from services import cadastro_service, busca_service, atualizacao_service

# Inicialização do App
app = FastAPI(
    title="Sistema de Cadastro Residencial",
    description="API para gestão de pessoas, documentos e residências.",
    version="1.0.0"
)

# Configuração de CORS (Permite que o Front-end acesse o Back-end)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, substitua pelo endereço do seu front
    allow_methods=["*"],
    allow_headers=["*"],
)

# Definição dos caminhos dos bancos de dados JSON
P_PATH = "database/pessoas.json"
R_PATH = "database/residencias.json"
D_PATH = "database/documentos.json"

# ==========================================================
# ROTAS DE CADASTRO
# ==========================================================

@app.post("/cadastro", status_code=201)
def cadastrar_pessoa(payload: dict):
    """
    Realiza o cadastro completo: Pessoa, Residência (se informada) e Documentos.
    """
    try:
        resultado = cadastro_service.realizar_cadastro_completo(
            payload, P_PATH, R_PATH, D_PATH
        )
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro interno ao processar cadastro.")

# ==========================================================
# ROTAS DE BUSCA
# ==========================================================

@app.get("/perfil/{id_pessoa}")
def obter_perfil_completo(id_pessoa: str):
    """
    Retorna o perfil consolidado: Dados, Residência, Documentos e Família.
    """
    perfil = busca_service.buscar_perfil_completo(id_pessoa, P_PATH, R_PATH, D_PATH)
    if not perfil:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada.")
    return perfil

@app.get("/busca/documento")
def buscar_por_documento(
    tipo: str = Query(..., description="Tipo do documento (Ex: CPF)"),
    valor: str = Query(..., description="Número do documento")
):
    """
    Localiza uma pessoa através de um documento específico.
    """
    perfil = busca_service.buscar_pessoa_por_documento(tipo, valor, P_PATH, R_PATH, D_PATH)
    if not perfil:
        raise HTTPException(status_code=404, detail="Nenhum registro encontrado para este documento.")
    return perfil

# ==========================================================
# ROTAS DE ATUALIZAÇÃO
# ==========================================================

@app.put("/perfil/{id_pessoa}")
def atualizar_perfil(id_pessoa: str, payload: dict):
    """
    Atualiza dados da pessoa, documentos ou residência de forma granular.
    """
    try:
        resultado = atualizacao_service.realizar_atualizacao_completa(
            id_pessoa, payload, P_PATH, R_PATH, D_PATH
        )
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro interno ao atualizar perfil.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)