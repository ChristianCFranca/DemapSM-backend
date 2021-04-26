# Utilizado para debugging facilitar o deploy
import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

if os.path.exists("./.env"): # Carrega as variaveis de ambiente de desenvolvimento
    from dotenv import load_dotenv
    load_dotenv()

import crud_pedidos
import crud_materiais
import cargos
import collect_data
import auth

app = FastAPI(title="Pedidos de Compra", description="REST API para realizar pedidos de compra no Banco Central do Brasil.", version="0.0.1")
app.include_router(crud_pedidos.router)
app.include_router(crud_materiais.router)
app.include_router(cargos.router)
app.include_router(collect_data.router)
app.include_router(auth.router)

origins = [
    "//localhost:8080",
    "https://demapsm.herokuapp.com"
    "//demapsm.herokuapp.com"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Home"])
async def get_home():
    return {"message": "Hello DemapSM!"}