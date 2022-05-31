from typing import Optional
from fastapi import HTTPException, APIRouter, status, Body, Depends
from database import db
from bson import ObjectId

from auth import permissions_user_role, get_dests
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

# Define nosso router
router = APIRouter(prefix="/crud/pedidos", tags=["Pedidos de Compra"])

def list_from_query_param(empresa: str = None, sep=","):
    if empresa:
        if not isinstance(empresa, str):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parâmetros de Query deveriam ser uma string.")
        return empresa.split(sep)
    return 

def filterPedidos(pedidos):
    if isinstance(pedidos, list):
        for pedido in pedidos:
            pedido["_id"] = str(pedido["_id"])
    else:
        pedidos["_id"] = str(pedidos["_id"])
    return pedidos

def getPedidos(empresa=None):
    if empresa:
        if isinstance(empresa, list):
            all_pedidos = list(collection.find({"$or": [{"empresa": emp} for emp in empresa]}))
        else:
            all_pedidos = list(collection.find({"empresa": empresa}))
    else:
        all_pedidos = list(collection.find())
    return all_pedidos

def getQuantidadePedidos():
    try:
        coll_find = collection.find({}, ["number"])
        if coll_find.count() == 0:
            return 0
        max_number = max(
            map(
                lambda doc: doc['number'], coll_find
            )
        )
        return max_number
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Não há o campo \'number\' nos documentos .")

def getPedidoNumber(pedido_id):
    pedido_id = ObjectId(pedido_id)
    pedido_number = collection.count_documents({"_id": {"$lte": pedido_id}})
    return pedido_number

def getPedido(pedido_id):
    pedido_id = ObjectId(pedido_id)
    pedido = collection.find_one({'_id': ObjectId(pedido_id)})
    return pedido

def postPedido(pedido):
    quantidade = getQuantidadePedidos()
    pedido['number'] = quantidade + 1
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

def generate_padronized_data_for_pdfmonkey(payload, filename):
    return {
                "document": {
                    "document_template_id": None,
                    "meta": {
                        "_filename": f"{filename}.pdf"
                    },
                    "payload": payload,
                    "status": "pending"
                }
            }

def get_name_padrao_para_pedido(suffix):
    return f"pedido_de_compra_{suffix}"

def filter_valid_items_from_pedido(pedido):
    # Itens de fixos não devem ser agregados na cobrança e itens aprovados pelo fiscal estão aprovados para compra
    itens_do_pedido = pedido['items'].copy() # Lista
    pedido['items'] = [item for item in itens_do_pedido if item['aprovadoFiscal'] and item['categoria'] != "Fixo"]

    items_demap = list(filter(lambda item: item['direcionamentoDeCompra'].lower() == "demap" and not item['almoxarifadoPossui'], pedido['items']))
    items_empresa = list(filter(lambda item: item['direcionamentoDeCompra'].lower() == pedido['empresa'].lower() and not item['almoxarifadoPossui'], pedido['items']))
    items_almoxarifado = list(filter(lambda item: item['almoxarifadoPossui'], pedido['items']))

    # Checa alguns erros possíveis
    if (len(items_demap) == 0 and len(items_empresa) == 0 and len(items_almoxarifado) == 0) or any(map(lambda item: item['direcionamentoDeCompra'] is None, pedido['items'])):
        if any(map(lambda item: item['categoria'] != 'Fixo', pedido['items'])):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="\033[93m"+"PDF:" + "\033[0m" + f"\t  Almoxarifado não possui o item e/ou o direcionamento de compra não consta como \'Demap\' ou \'{pedido['empresa']}\'.")
    
    return items_demap, items_empresa, items_almoxarifado

def send_email_acompanhamento(_pedido, pedido_id):
    if not 'empresa' in _pedido:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="A chave \'empresa\' não existe no pedido.")

    pedido = _pedido.copy()
    pedido['_id'] = pedido_id
    status_step = pedido['statusStep']
    correct_empresa = pedido['empresa']

    if status_step != 6 and pedido['active']:  # Emails acontecem para todas as etapas exceto para a etapa 6. Também ocorrem apenas para pedidos ativos (que não foram cancelados)
        role_name = STEPS_TO_ROLES.get(pedido['statusStep']) # Obtem o role responsável por aquele pedido
        if role_name is None:
            print("\033[93m"+"EMAIL:" + "\033[0m" + "\t  Não foi possível obter o role responsável pela etapa em questão.")
            return
        dests = get_dests(role_name, correct_empresa, verbose=False)  # Obtem todos os emails dos usuarios com o role especificado e que acessam a empresa em questão
        
        if 'number' not in pedido:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="O pedido não apresente o identificador de número.")

        if status_step <= 4: # Emails apenas para notificação
            send_email_to_role(dests, correct_empresa, pedido['number'], status_step)

        else: # Etapa 5 é email de attachment

            items_demap, items_empresa, items_almoxarifado = filter_valid_items_from_pedido(pedido)

            filename = get_name_padrao_para_pedido(pedido['number'])
            json_data = generate_padronized_data_for_pdfmonkey(pedido, filename)

            pdfs_ids = dict()
            # As funções abaixo alteram o dicionario original
            stage_new_pdf_for_group(items_empresa, Departamentos.empresa, json_data, pdfs_ids)
            stage_new_pdf_for_group(items_demap, Departamentos.demap, json_data, pdfs_ids)
            stage_new_pdf_for_group(items_almoxarifado, Departamentos.almoxarife, json_data, pdfs_ids)

            if pdfs_ids: # Verifica se pelo menos um pdf foi setado para ir pro banco de dados
                _pedido["pdfs_ids"] = pdfs_ids # Esta alteração altera o dicionário ORIGINAL, e não a CÓPIA. Isso fará com que, ao atualizar o pedido saindo desta função, o pedido tenha as informações de id's dos documentos correlacionados

def stage_new_pdf_for_group(items, dept, json_data, pdfs_ids):
    if len(items) > 0:
        json_data['document']['payload']['items'] = items
        res = stage_pdf(json_data, dept)
        pdfs_ids[dept] = res["document"]["id"]

def map_pedidos_for_compra_demap():
    pedidos = getPedidos()
    if not pedidos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Não há pedidos no momento.")
    pedidos = filterPedidos(pedidos) # Lista de jsons
    if not isinstance(pedidos, list):
        pedidos = [pedidos]
    pedidos_staged_compra = list(filter(lambda pedido: pedido['statusStep'] == 5 and pedido['active'], pedidos)) # Apenas os que estão na etapa 5 e estão ativos

    items = []
    for pedido in pedidos_staged_compra:
        if 'items' not in pedido:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Pedido não apresenta campo \'items\'.")
        if not isinstance(pedido['items'], list):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="\'items\' do pedido não constitui uma lista.")

        for item in pedido['items']:
            recebido = item.get('recebido')
            if recebido is None:
                recebido = False
            if item['direcionamentoDeCompra'] == "Demap" and not item['almoxarifadoPossui'] and not recebido:
                items.append(item)

    return items

# -----------------------------------------------------------------------------

@router.get("/", summary="Get pedidos", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente, RoleName.almoxarife, RoleName.regular
        ]))])
def get_pedidos(empresa: Optional[str] = Depends(list_from_query_param)):
    pedidos = getPedidos(empresa)
    if not pedidos:
        raise HTTPException(status_code=status.HTTP_200_OK, detail="Não há pedidos no momento.")
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


@router.get("/compra/demap", summary="Get itens que precisam de compra pelo DEMAP", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal
        ]))])
def get_pedidos_for_compra():
    pedidos_para_comprar = map_pedidos_for_compra_demap()
    return pedidos_para_comprar


@router.post("/", summary="Post pedido", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente, RoleName.almoxarife, RoleName.regular
        ]))])
def post_pedido(pedido = Body(...)):
    pedido_id = postPedido(pedido)
    if (pedido['statusStep'] == 2 or pedido['statusStep'] == 3) and SEND_EMAIL: # Envia um email de acompanhamento
        send_email_acompanhamento(pedido, pedido_id)
    return {"_id": pedido_id}


@router.put("/{pedido_id}", summary="Update pedido", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente, RoleName.almoxarife, RoleName.regular
        ]))])
def put_pedido(pedido_id: str, email: bool = True, pedido = Body(...)):
    pedido_in_db = getPedido(pedido_id)
    if pedido_in_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado.")
    if pedido_in_db['statusStep'] > pedido['statusStep']:
        raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED, detail="Pedido já foi aprovado por outro usuário. Favor atualizar a página.")

    if pedido['statusStep'] != 6 and SEND_EMAIL and email: # Envia um email de acompanhamento (se não for a última etapa)
        send_email_acompanhamento(pedido, pedido_id)

    res = putPedido(pedido_id, pedido) # pedido é um dict
    return {"alterado": res}

@router.put("/direct/{pedido_id}", summary="Update pedido diretamente no DB", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin
        ]))])
def put_pedido_direto(pedido_id: str, pedido = Body(...)):
    pedido_in_db = getPedido(pedido_id)
    if pedido_in_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado.")
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
