from typing import Optional
from fastapi import HTTPException, APIRouter, status
from database import db

COLLECTION = "empresas"
collection = db[COLLECTION]

# Define nosso router
router = APIRouter(prefix="/empresas", tags=["Empresas"])

def mapObjectIdsToStrings(objects):
    if isinstance(objects, list):
        for obj in objects:
            obj["_id"] = str(obj["_id"])
    else:
        objects["_id"] = str(objects["_id"])
    return objects

def getEmpresas():
    all_empresas = list(collection.find())
    return all_empresas

# -----------------------------------------------------------------------------
@router.get("/", summary="Get empresas")
def get_empresas(key: Optional[str] = None):
    empresas = getEmpresas()
    empresas = mapObjectIdsToStrings(empresas)
    if not empresas:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Não há empresas cadastradas na coleção selecionada.")
    if key:
        try:
            empresas = list(map(lambda empresa: empresa[key], empresas))
        except KeyError:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"A chave de nome \'{key}\' não foi encontrada em um elemento.")
    return empresas