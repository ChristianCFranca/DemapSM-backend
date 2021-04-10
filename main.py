# Utilizado para debugging facilitar o deploy
import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import crud_pedidos
import crud_materiais

app = FastAPI(title="Pedidos de Compra", description="REST API para realizar pedidos de compra no Banco Central do Brasil.", version="0.0.1")
app.include_router(crud_pedidos.router)
app.include_router(crud_materiais.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    port = os.environ.get('PORT') if os.environ.get('PORT') else 8000 # Para deploy no Heroku
    uvicorn.run(app, host="0.0.0.0", port=port)