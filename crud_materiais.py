from fastapi import Depends, FastAPI, HTTPException, APIRouter, status, Body
from typing import List
from database import db
from bson import ObjectId

COLLECTION = "itensdisponiveis"
collection = db[COLLECTION]

# Define nosso router
router = APIRouter(prefix="/crud/materiais", tags=["Materiais"])

def filterMateriais(materiais):
    if isinstance(materiais, list):
        for material in materiais:
            material["_id"] = str(material["_id"])
    else:
        materiais["_id"] = str(materiais["_id"])
    return materiais

def getMateriais():
    all_materiais = list(collection.find())
    return all_materiais

def getMaterial(material_id):
    material_id = ObjectId(material_id)
    material = collection.find_one({'_id': ObjectId(material_id)})
    return material

def postMaterial(material):
    res = collection.insert_one(material)
    return str(res.inserted_id)

def putMaterial(material_id, update_material):
    material_id = {"_id": ObjectId(material_id)}
    update_material = {"$set": update_material}
    res = collection.update_one(material_id, update_material)
    return res.modified_count

def deleteMaterial(material_id):
    material_id = {"_id": ObjectId(material_id)}
    res = collection.delete_one(material_id)
    return res.deleted_count


@router.get("/", summary="Get materiais")
def get_materiais():
    materiais = getMateriais()
    return filterMateriais(materiais)

@router.get("/{material_id}", summary="Get material by id")
def get_material(material_id: str):
    material = getMaterial(material_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material não encontrado.")
    return filterMateriais(material)

@router.post("/", summary="Post material")
def post_material(material = Body(...)):
    material_id = postMaterial(material)
    return {"_id": material_id}

@router.put("/{material_id}", summary="Update material")
def put_material(material_id: str, material = Body(...)):
    if getMaterial(material_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material não encontrado.")
    res = putmaterial(material_id, material)
    return {"alterado": res}

@router.delete("/{material_id}", summary="Delete material")
def delete_material(material_id: str):
    if getMaterial(material_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material não encontrado.")
    res = deleteMaterial(material_id)
    return {"alterado": res}
