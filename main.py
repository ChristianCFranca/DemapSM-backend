# Utilizado para debugging facilitar o deploy
import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import crud_pedidos
import crud_materiais
import cargos

app = FastAPI(title="Pedidos de Compra", description="REST API para realizar pedidos de compra no Banco Central do Brasil.", version="0.0.1")
app.include_router(crud_pedidos.router)
app.include_router(crud_materiais.router)
app.include_router(cargos.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Home"])
async def get_home():
    return {"message": "Hello Database!"}