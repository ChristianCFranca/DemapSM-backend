from fastapi import FastAPI, HTTPException, APIRouter, status, Body
from typing import List
# from database import db
# from bson import ObjectId
import os

# Define nosso router
router = APIRouter(prefix="/cargos", tags=["Aprovações"])

KEY_ASSISTENTE = os.environ.get("KEY_ASSISTENTE") if os.environ.get("KEY_ASSISTENTE") is not None else "1234"
KEY_FISCAL = os.environ.get("KEY_FISCAL") if os.environ.get("KEY_FISCAL") is not None else "5678"
KEY_ALMOXARIFE = os.environ.get("KEY_ALMOXARIFE") if os.environ.get("KEY_ALMOXARIFE") is not None else "9999"

cargo_key = {0: KEY_ASSISTENTE, 1: KEY_FISCAL, 2: KEY_ALMOXARIFE}

def checkKey(key, cargo):
    return key == cargo_key[cargo]

def checkKeyBoth(key):
    return key == cargo_key[0] or key == cargo_key[1]

@router.get("/keycheck", summary="Validar chave")
def post_key_cargo(key: str, cargo: int):
    return {"valid": checkKey(key, cargo)}

@router.get("/keycheck_both", summary="Validar chave")
def post_key_cargo_both(key: str):
    return {"valid": checkKeyBoth(key)}
    