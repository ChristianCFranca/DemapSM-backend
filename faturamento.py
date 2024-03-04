from fastapi import HTTPException, APIRouter, status, Body, Depends
from pydantic import BaseModel, Field
from auth import permissions_user_role, RoleName
from crud_pedidos import getPedidos, generate_padronized_data_for_pdfmonkey
from generate_pdf_and_sheet import stage_pdf_faturamento, get_pdf_link_for_download, delete_pdf_by_id, check_if_pdf_exists_by_id
from empresas import getEmpresas
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
    mes: int = Field(gt=0, lt=13, description="O numero relativo ao mes em questao")
    ano: int = Field(gt=2020, description="O numero relativo ao ano em questao")

def is_same_month_year(pedido, month: int, year: int):
    if pedido['statusStep'] != 6:
        return False
    try:
        data_finalizacao_formatada = pedido['dataFinalizacao'].replace(',','')
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ocorreu um erro ao processar a data de finalização do pedido {pedido['number']}. Data do pedido: {pedido['dataPedido']}.Data finalização: {pedido['dataFinalizacao']}")
    if len(data_finalizacao_formatada.split('/')) != 3:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="A data não está no formato correto.")
    mes = int(data_finalizacao_formatada.split('/')[1])
    ano = int(data_finalizacao_formatada.split('/')[2])
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

def update_link_fatura_pdf(fatura_id, empresa, mes, ano) -> bool:
    res = collection.find_one_and_update({'empresa': empresa}, {'$set': {f'{mes}-{ano}': fatura_id}})
    if not res:
        res = collection.insert_one({'empresa': empresa, f'{mes}-{ano}': fatura_id})
    if not res:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ocorreu um erro ao criar a empresa com o id da fatura do mês.")
    return

def get_info_faturamento_empresa(empresa):

    custos_indiretos = empresa.get('custosIndiretos')
    if not custos_indiretos:
        custos_indiretos = 0
    elif not isinstance(custos_indiretos, float):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Custos indiretos não é um float.")

    lucro = empresa.get('lucro')
    if not lucro:
        lucro = 0
    elif not isinstance(lucro, float):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Lucro não é um float.")

    tributos = empresa.get('tributos')
    if not tributos:
        tributos = 0
    elif not isinstance(tributos, float):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Tributos não é um float.")

    bdi = empresa.get('bdi')
    if bdi:
        if not isinstance(bdi, float):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="BDI não é um float.")
        
    return custos_indiretos, lucro, tributos, bdi

# Rotas ---------------------------------------------------------------------------------------------------------------------

@router.post("/", summary="Post para obter faturamento", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente
        ]))])
def get_faturamento(faturamento_info: FaturamentoModel = Body(...)):
    empresa = faturamento_info.empresa
    mes = faturamento_info.mes
    ano = faturamento_info.ano
    
    empresas_existentes = getEmpresas() # Lista de objetos
    empresa_existe = next(filter(lambda emp: emp['nome'] == empresa, empresas_existentes), None)
    if not empresa_existe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empresa fornecida não existe.")

    custos_indiretos, lucro, tributos, bdi = get_info_faturamento_empresa(empresa_existe)

    pedidos = getPedidos(faturamento_info.empresa)
    if len(pedidos) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="A empresa não possui nenhum pedido cadastrado.")
    pedidos_filtered_mes_ano = list(filter(lambda pedido: is_same_month_year(pedido, mes, ano), pedidos))
    if len(pedidos_filtered_mes_ano) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhum pedido encontrado para o período fornecido.")
    pedidos_fmt = format_pedidos(pedidos_filtered_mes_ano, empresa)
    if len(pedidos_fmt) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Existem pedidos para o período mas nenhum foi recebido.")

    # Calcula os valores corretos de cada termo para cada empresa
    valor_total = sum(map(lambda pedido: sum(map(lambda item: item['valorTotal'], pedido['items'])), pedidos_fmt))
    filename = f"faturamento_{mes}-{ano}"
    if bdi:
        valor_BDI = bdi*valor_total # Calcula mas não será usado se não houver o BDI
        valor_final = valor_total + valor_BDI
        payload = {
            'infoMes': f"{MONTH_DICT.get(mes)}/{ano}",
            'pedidos': pedidos_fmt,
            'valorTotal': valor_total,
            'empresa': empresa_existe['nome'],
            'bdi': bdi,
            'valorBDI': valor_BDI,
            'valorFinal': valor_final
        }
    else:
        valor_ci = valor_total*custos_indiretos
        valor_lucro = valor_total*lucro*(1 + custos_indiretos)
        valor_s1 = valor_total + valor_ci + valor_lucro
        valor_final = valor_s1 / (1 - tributos)
        valor_trib = valor_final - valor_s1
        payload = {
            'infoMes': f"{MONTH_DICT.get(mes)}/{ano}",
            'pedidos': pedidos_fmt,
            'valorTotal': valor_total,
            'empresa': empresa_existe['nome'],
            'valorCI': valor_ci,
            'valorLucro': valor_lucro,
            'valorTrib': valor_trib,
            'custosIndiretos': custos_indiretos,
            'lucro': lucro,
            'tributos': tributos,
            'valorFinal': valor_final
        }


    pdf_id = check_if_fatura_exists(empresa, mes, ano)
    # Se já existir uma fatura para a empresa, deleta e cria uma nova
    if pdf_id:
        pdf_exists = check_if_pdf_exists_by_id(pdf_id)
        if pdf_exists:
            pdf_link = delete_pdf_by_id(pdf_id)

    request = generate_padronized_data_for_pdfmonkey(payload, filename)
    response = stage_pdf_faturamento(request)
    id_pdf_fatura = response["document"]["id"]

    update_link_fatura_pdf(id_pdf_fatura, empresa, mes, ano)

    pdf_link = get_pdf_link_for_download(id_pdf_fatura)
    return pdf_link
