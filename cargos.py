from fastapi import Depends, FastAPI, HTTPException, APIRouter, status, Body
from typing import List
# from database import db
# from bson import ObjectId
import os

# COLLECTION = "cargos"
# collection = db[COLLECTION]

# Define nosso router
router = APIRouter(prefix="/cargos", tags=["Aprovações"])

KEY_GERENTE = os.environ.get("KEY_GERENTE") if os.environ.get("KEY_GERENTE") is not None else "1234"
KEY_SERVIDOR = os.environ.get("KEY_SERVIDOR") if os.environ.get("KEY_SERVIDOR") is not None else "5678"
KEY_ALMOXARIFE = os.environ.get("KEY_ALMOXARIFE") if os.environ.get("KEY_ALMOXARIFE") is not None else "9999"

cargo_key = {0: KEY_GERENTE, 1: KEY_SERVIDOR, 2: KEY_ALMOXARIFE}

def checkKey(key, cargo):
    return key == cargo_key[cargo]

@router.get("/keycheck", summary="Validar chave")
def post_material(key: str, cargo: int):
    return {"valid": checkKey(key, cargo)}