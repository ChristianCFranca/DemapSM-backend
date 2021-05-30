from fastapi import HTTPException, APIRouter, status, Body, Depends
from database import db
from bson import ObjectId

from auth import permissions_user_role, get_all_users_by_role
from cargos import RoleName, Departamentos
from send_email import SEND_EMAIL, send_email_to_role

from generate_pdf_and_sheet import stage_pdf

COLLECTION = "pedidosdecompra"
collection = db[COLLECTION]

STEPS_TO_ROLES = {
    2: RoleName.assistente,
    3: RoleName.fiscal,
    4: RoleName.almoxarife,
    5: RoleName.fiscal
}

TEMPLATES_FOR_DEPARTAMENTO = {
    Departamentos.demap: "BFDE2B7D-4255-4ACA-9525-0209F55C0CFC",
    Departamentos.engemil: "BFDE2B7D-4255-4ACA-9525-0209F55C0CFC",
    Departamentos.almoxarife: "BFDE2B7D-4255-4ACA-9525-0209F55C0CFC"
}

# Define nosso router
router = APIRouter(prefix="/crud/pedidos", tags=["Pedidos de Compra"])

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

def send_email_acompanhamento(_pedido, pedido_id=None):
    pedido = _pedido.copy()
    if pedido_id:
        pedido['_id'] = pedido_id
    status_step = pedido['statusStep']
    if status_step != 6 and pedido['active']:  # Emails acontecem para todas as etapas exceto para a etapa 6. Também ocorrem apenas para pedidos ativos (que não foram cancelados)
        role_name = STEPS_TO_ROLES.get(pedido['statusStep']) # Obtem o role responsável por aquele pedido
        if role_name is None:
            print("\033[93m"+"EMAIL:" + "\033[0m" + "\t  Não foi possível obter o role responsável pela etapa em questão.")
            return
        users_with_specific_role = get_all_users_by_role(role_name)
        if users_with_specific_role is None: # Se não houverem usuários, ocorre um warning e não envia emails
            print("\033[93m"+"EMAIL:" + "\033[0m" + "\t  Não existem usuários com o role especificado. Nenhum email será enviado.")
            return
        dests = list(map(lambda user: user['username'], users_with_specific_role))  # Obtem todos os emails dos usuarios com o role especificado

        if status_step <= 4: # Emails apenas para notificação
            send_email_to_role(dests)

        else: # Etapa 5 é email de attachment
            json_data = {
                "document": {
                    "document_template_id": None,
                    "meta": {
                        "_filename": f"pedido_de_compra_{pedido['_id']}.pdf"
                    },
                    "payload": {key: value for key, value in pedido.items() if key != "items"},
                    "status": "pending"
                }
            }
            for item in pedido['items']:
                departamento = None
                if item['almoxarifadoPossui']: # Se o almoxarifado não possuir, a engemil ou o demap devem realizar a compra
                    departamento = Departamentos.almoxarife
                elif item['direcionamentoDeCompra'].lower() == "demap":
                    departamento = Departamentos.demap
                elif item['direcionamentoDeCompra'].lower() == "engemil":
                    departamento = Departamentos.engemil
                else:
                    print("\033[93m"+"PDF:" + "\033[0m" + "\t  Almoxarifado não possui porém o direcionamento de compra não consta como \'Demap\' ou \'Engemil\'. Nenhum email será enviado.")
                    return

                for key in item: # item é um dict
                    json_data['document']['payload'][key] = item[key]

                json_data['document']["document_template_id"] = TEMPLATES_FOR_DEPARTAMENTO[departamento]
                stage_pdf(json_data, departamento, dests)

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
    if pedido['statusStep'] == 2 and SEND_EMAIL: # Envia um email de acompanhamento
        send_email_acompanhamento(pedido)
    pedido_id = postPedido(pedido)
    return {"_id": pedido_id}


@router.put("/{pedido_id}", summary="Update pedido", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente, RoleName.almoxarife
        ]))])
def put_pedido(pedido_id: str, pedido = Body(...)):
    if getPedido(pedido_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado.")

    if pedido['statusStep'] != 6 and SEND_EMAIL: # Envia um email de acompanhamento (se não for a última etapa)
        send_email_acompanhamento(pedido, pedido_id)

    res = putPedido(pedido_id, pedido) # pedido é um dict
    return {"alterado": res}


@router.delete("/{pedido_id}", summary="Delete pedido", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal
        ]))])
def delete_pedido(pedido_id: str):
    if getPedido(pedido_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado.")
    res = deletePedido(pedido_id)
    return {"alterado": res}
