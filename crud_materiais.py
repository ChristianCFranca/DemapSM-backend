from fastapi import HTTPException, APIRouter, status, Body, Depends
from database import db
from bson import ObjectId

from auth import permissions_user_role, RoleName

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

def getMateriais(empresa: str = None):
    if empresa:
        all_materiais = list(collection.find({"empresa": empresa}))
    else:
        all_materiais = list(collection.find())
    return all_materiais

def getMateriaisDiversosByName(search_string):
    collection = db['itens-diversos']
    materiais = list(collection.find({'descricao': {'$regex': search_string, '$options': 'i'}}))
    collection = db[COLLECTION]
    return materiais

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


@router.get("/", summary="Get materiais", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente, RoleName.almoxarife, RoleName.regular
        ]))])
def get_materiais(empresa: str):
    materiais = getMateriais(empresa)
    return filterMateriais(materiais)

@router.get("/{material_id}", summary="Get material by id", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente, RoleName.almoxarife, RoleName.regular
        ]))])
def get_material(material_id: str):
    material = getMaterial(material_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material não encontrado.")
    return filterMateriais(material)

@router.get("/diversos/", summary="Get non registered material by name", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente, RoleName.almoxarife, RoleName.regular
        ]))])
def get_materiais_by_name(search_string: str):
    materiais = getMateriaisDiversosByName(search_string)
    if not isinstance(materiais, list):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Os materiais deveriam ser do tipo 'list', mas são do tipo {type(materiais)}.")
    return filterMateriais(materiais)

@router.post("/", summary="Post material", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente
        ]))])
def post_material(material = Body(...)):
    material_id = postMaterial(material)
    return {"_id": material_id}

@router.put("/{material_id}", summary="Update material", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente
        ]))])
def put_material(material_id: str, material = Body(...)):
    if getMaterial(material_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material não encontrado.")
    res = putMaterial(material_id, material)
    return {"alterado": res}

@router.delete("/{material_id}", summary="Delete material", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente
        ]))])
def delete_material(material_id: str):
    if getMaterial(material_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material não encontrado.")
    res = deleteMaterial(material_id)
    return {"alterado": res}
