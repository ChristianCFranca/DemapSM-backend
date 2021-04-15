from fastapi import FastAPI, HTTPException, APIRouter, status, Body
from typing import List
from database import db
from bson import ObjectId

COLLECTION = "pedidosdecompra"
collection = db[COLLECTION]

# Define nosso router
router = APIRouter(prefix="/crud/pedidos", tags=["Pedidos de Compra"])

from cargos import cargo_key, checkKey

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


@router.get("/", summary="Get pedidos")
def get_pedidos():
    pedidos = getPedidos()
    return filterPedidos(pedidos)

@router.get("/{pedido_id}", summary="Get pedido by id")
def get_pedido(pedido_id: str):
    pedido = getPedido(pedido_id)
    if pedido is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado.")
    return filterPedidos(pedido)

@router.post("/", summary="Post pedido")
def post_pedido(pedido = Body(...)):
    pedido_id = postPedido(pedido)
    return {"_id": pedido_id}

@router.put("/{pedido_id}", summary="Update pedido")
def put_pedido(pedido_id: str, pedido = Body(...)):
    if getPedido(pedido_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado.")
    res = putPedido(pedido_id, pedido)
    return {"alterado": res}

@router.delete("/{pedido_id}", summary="Delete pedido")
def delete_pedido(pedido_id: str, key: str, cargo: int):
    if checkKey(key, cargo):
        if getPedido(pedido_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado.")
        res = deletePedido(pedido_id)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chave inválida.")
    return {"alterado": res}
