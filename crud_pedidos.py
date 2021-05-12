from fastapi import HTTPException, APIRouter, status, Body, Depends
from database import db
from bson import ObjectId

from auth import permissions_user_role, RoleName
from send_email import send_email_to_role

import os

COLLECTION = "pedidosdecompra"
collection = db[COLLECTION]

SEND_EMAIL = os.environ.get("SEND_EMAIL")
if not SEND_EMAIL:
    raise Exception("No SEND EMAIL env available...")
else:
    try:
        if SEND_EMAIL.lower() == "true":
            SEND_EMAIL = True
        else:
            SEND_EMAIL = False
        print("\033[94m"+"INFO:" + "\033[0m" + f"\t  SEND EMAIL environment data available: \033[1m{SEND_EMAIL}\033[0m - Loaded.")
    except:
        raise Exception("SEND EMAIL env is available but cannot be casted to boolean...")

# Define nosso router
router = APIRouter(prefix="/crud/pedidos", tags=["Pedidos de Compra"])

from cargos import checkKey

def filterPedidos(pedidos):
    if isinstance(pedidos, list):
        for pedido in pedidos:
            pedido["_id"] = str(pedido["_id"])
    else:
        pedidos["_id"] = str(pedidos["_id"])
    return pedidos

def getPedidos():
    all_pedidos = list(collection.find())
    return all_pedidos

def getPedido(pedido_id):
    pedido_id = ObjectId(pedido_id)
    pedido = collection.find_one({'_id': ObjectId(pedido_id)})
    return pedido

def postPedido(pedido):
    res = collection.insert_one(pedido)
    return str(res.inserted_id)

def putPedido(pedido_id, update_pedido):
    pedido_id = {"_id": ObjectId(pedido_id)}
    update_pedido = {"$set": update_pedido}
    res = collection.update_one(pedido_id, update_pedido)
    return res.modified_count

def deletePedido(pedido_id):
    pedido_id = {"_id": ObjectId(pedido_id)}
    res = collection.delete_one(pedido_id)
    return res.deleted_count

# -----------------------------------------------------------------------------

@router.get("/", summary="Get pedidos", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente, RoleName.almoxarife, RoleName.regular
        ]))])
def get_pedidos():
    pedidos = getPedidos()
    return filterPedidos(pedidos)


@router.get("/{pedido_id}", summary="Get pedido by id", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente, RoleName.almoxarife, RoleName.regular
        ]))])
def get_pedido(pedido_id: str):
    pedido = getPedido(pedido_id)
    if pedido is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado.")
    return filterPedidos(pedido)


@router.post("/", summary="Post pedido", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente, RoleName.almoxarife, RoleName.regular
        ]))])
def post_pedido(pedido = Body(...)):
    if pedido['statusStep'] == 2 and SEND_EMAIL: # Envia um email
        send_email_to_role(pedido['statusStep']) # pedido['statusStep'] é um inteiro

    pedido_id = postPedido(pedido)
    return {"_id": pedido_id}


@router.put("/{pedido_id}", summary="Update pedido", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente, RoleName.almoxarife
        ]))])
def put_pedido(pedido_id: str, pedido = Body(...)):
    if getPedido(pedido_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado.")

    if pedido['statusStep'] != 6 and SEND_EMAIL: # Envia um email se não for a ultima etapa
        send_email_to_role(pedido['statusStep']) # pedido['statusStep'] é um inteiro

    res = putPedido(pedido_id, pedido) # pedido é um dict
    return {"alterado": res}


@router.delete("/{pedido_id}", summary="Delete pedido", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal
        ]))])
def delete_pedido(pedido_id: str, key: str, cargo: int):
    if checkKey(key, cargo):
        if getPedido(pedido_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado.")
        res = deletePedido(pedido_id)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chave inválida.")
    return {"alterado": res}
