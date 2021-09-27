from fastapi import HTTPException, APIRouter, status, Body, Depends
from pydantic.main import BaseModel
from auth import permissions_user_role, RoleName
from crud_pedidos import getPedidos
from generate_pdf_and_sheet import stage_pdf_faturamento

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

def format_pedidos(pedidos):
    if not isinstance(pedidos, list):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Pedidos não constitui um dicionário.")
    item_array = []
    for pedido in pedidos:
        item_array = [item for items in pedido['items']]
    return item_array
        
@router.post("/", summary="Post para obter faturamento", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente, RoleName.almoxarife, RoleName.regular
        ]))])
def get_faturamento(faturamento_info: FaturamentoModel = Body(...)):
    empresa = faturamento_info.empresa
    if not empresa:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empresa não foi fornecida no JSON.")
    mes = faturamento_info.mes
    if not mes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O mês de faturamento não foi encontrado no JSON.")
    if not isinstance(mes, int) or mes < 1 or mes > 12:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O mês informado não é valido.")
    ano = faturamento_info.ano
    if not ano:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O ano de faturamento não foi encontrado no JSON.")
    if not isinstance(ano, int):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O ano informado não é valido.")
    pedidos = getPedidos(faturamento_info.empresa)
    if len(pedidos) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhum pedido encontrado para a empresa em questão.")

    pedidos = list(filter(lambda pedido: is_same_month_year(pedido['dataPedido'], mes, ano), pedidos))
    if len(pedidos) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhum pedido encontrado para a data fornecida.")
    pedidos = format_pedidos(pedidos)
        
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
    request['document']['payload']['valorTotal'] = sum(map(lambda pedido: pedido['valorTotal'], pedidos))
            
    response = stage_pdf_faturamento(request)
    return {"download_url": response['document']['download_url']}
