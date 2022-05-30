from fastapi import HTTPException, APIRouter, status, Body, Depends, Response
from pydantic.main import BaseModel
from auth import permissions_user_role, RoleName
from crud_pedidos import getPedidos
from generate_pdf_and_sheet import stage_pdf_faturamento, get_pdf_link_for_download
from database import db

COLLECTION = "faturas"
collection = db[COLLECTION]

# Define nosso router
router = APIRouter(prefix="/faturamentos", tags=["Obter faturamento da empresa em determinado período"])

MONTH_DICT = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro"
}

class FaturamentoModel(BaseModel):
    empresa: str
    mes: int
    ano: int

def is_same_month_year(string1: str, month: int, year: int):
    if len(string1.split('/')) != 3:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="A data não está no formato correto.")
    mes = int(string1.split('/')[1])
    ano = int(string1.split('/')[2])
    return mes == month and ano == year

def format_pedidos(pedidos, empresa):
    if not isinstance(pedidos, list):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Pedidos não constitui um dicionário.")
    pedidos_array = []
    for pedido in pedidos:
        if pedido['active']:
            rowspan = 0
            item_array = []
            for item in pedido['items']:
                if not item['almoxarifadoPossui'] and item['direcionamentoDeCompra'] == empresa and item['recebido']: # Sob demandas recebidos pela empresa
                    rowspan += 1
                    item_array += [item]
            if len(item_array) > 0:
                pedidos_array.append({"rowspan": rowspan, "os": pedido['os'], "dataPedido": pedido['dataPedido'], "items": item_array})
    return pedidos_array
        
def check_if_fatura_exists(empresa, mes, ano):
    res = collection.find_one({'empresa': empresa})
    if res:
        pdf_id = res.get(f'{mes}-{ano}')
        if not pdf_id:
            return False
        else:
            return pdf_id
    return False

def update_create_faturas(fatura_id, empresa, mes, ano) -> bool:
    res = collection.find_one_and_update({'empresa': empresa}, {'$set': {f'{mes}-{ano}': fatura_id}})
    if not res:
        res = collection.insert_one({'empresa': empresa, f'{mes}-{ano}': fatura_id})
    if not res:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ocorreu um erro ao criar a empresa com o id da fatura do mês.")
    return

@router.post("/", summary="Post para obter faturamento", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente, RoleName.almoxarife, RoleName.regular
        ]))])
def get_faturamento(faturamento_info: FaturamentoModel = Body(...)):
    empresa = faturamento_info.empresa
    if not empresa:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empresa não foi fornecida no JSON.")
    mes = faturamento_info.mes
    if mes < 1 or mes > 12:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O mês informado não é valido.")
    ano = faturamento_info.ano
    pdf_id = check_if_fatura_exists(empresa, mes, ano)
    if pdf_id:
        pdf_link = get_pdf_link_for_download(pdf_id)
        return Response(pdf_link, status_code=302)

    pedidos = getPedidos(faturamento_info.empresa)
    if len(pedidos) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhum pedido encontrado para a empresa em questão.")

    pedidos = list(filter(lambda pedido: is_same_month_year(pedido['dataPedido'], mes, ano), pedidos))
    if len(pedidos) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhum pedido encontrado para a data fornecida.")
    pedidos = format_pedidos(pedidos, empresa)
    if len(pedidos) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhum pedido encontrado para a data fornecida.")
        
    request = {
                "document": {
                    "document_template_id": None,
                    "meta": {
                        "_filename": f"faturamento_{mes}-{ano}.pdf"
                    },
                    "payload": dict(),
                    "status": "pending"
                }
            }

    request['document']['payload']['infoMes'] = f"{MONTH_DICT.get(mes)}/{ano}"
    request['document']['payload']['pedidos'] = pedidos
    request['document']['payload']['valorTotal'] = sum(map(lambda pedido: sum(map(lambda item: item['valorTotal'], pedido['items'])), pedidos))

    response = stage_pdf_faturamento(request)
    update_create_faturas(response["document"]["id"], empresa, mes, ano)
    pdf_link = get_pdf_link_for_download(response["document"]["id"])
    return pdf_link
