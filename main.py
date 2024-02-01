import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

if os.path.exists("./.env"): # Carrega as variaveis de ambiente de desenvolvimento
    from dotenv import load_dotenv
    load_dotenv()

import crud_pedidos
import crud_materiais
import collect_data
import empresas
import auth
import generate_pdf_and_sheet
import faturamento

app = FastAPI(title="Pedidos de Compra", description="REST API para realizar pedidos de compra no Banco Central do Brasil.", version="0.0.1")
app.include_router(crud_pedidos.router)
app.include_router(crud_materiais.router)
app.include_router(collect_data.router)
app.include_router(auth.router)
app.include_router(generate_pdf_and_sheet.router)
app.include_router(empresas.router)
app.include_router(faturamento.router)

origins = [
    "http://localhost:8080",
    "https://bug-free-train-95vppvwqx4jfxg45-8080.app.github.dev",
    os.environ.get("CORS_ORIGIN") if os.environ.get("CORS_ORIGIN") else "https://demapsm.herokuapp.com"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.get("/", tags=["Home"])
async def get_home():
    return {"message": "Hello DemapSM!"}
