from fastapi import APIRouter, HTTPException, status, Depends, Body, Query

from auth import permissions_user_role
from cargos import RoleName, Departamentos

from generate_pdf_and_sheet import get_pdf_link_for_download, delete_pdf_by_id

from crud_pedidos import getPedido, getPedidos, putPedido, generate_padronized_data_for_pdfmonkey, stage_new_pdf_for_group, filter_valid_items_from_pedido, get_name_padrao_para_pedido

from crud_materiais import getMateriais

# Define nosso router
router = APIRouter(prefix="/collect-data", tags=["Pedidos de Compra"])

def filter_pedidos_por_mes_ano(pedidos, mes_de_inicio: int, ano: int):
    filtrados_ano_1 = list(filter(lambda pedido: int(pedido['dataPedido'].split('/')[-1]) == ano and int(pedido['dataPedido'].split('/')[-2]) >= mes_de_inicio, pedidos))
    if mes_de_inicio > 1:
        return filtrados_ano_1
    else:
        # Pega os meses que faltaram no ano seguinte
        return filtrados_ano_1 + list(filter(lambda pedido: int(pedido['dataPedido'].split('/')[-1]) == ano + 1 and int(pedido['dataPedido'].split('/')[-2]) < mes_de_inicio, pedidos))

def filter_materiais_ja_recebidos(materiais):
    return list(filter(lambda material: material['recebido'], materiais))

def filter_pedidos_validos(pedidos, empresa):
    pedidos_validos = list(map(lambda pedido: pedido['items'], list(filter(lambda pedido: pedido['active'] and pedido['empresa'] == empresa, pedidos))))
    return [item for sublist in pedidos_validos for item in sublist]

def filter_materiais_contratuais(materiais):
    return list(filter(lambda material: material['categoria'] == "Fixo" or material['categoria'] == "Sob Demanda", materiais))

def agrupa_materiais(materiais):
    materiais_agrupados = dict()
    for material in materiais:
        if materiais_agrupados.get(material['nome']) is None:
            materiais_agrupados[material['nome']] = {'utilizado': float(material['quantidade']), 'categoria': material['categoria']}
        else:
            materiais_agrupados[material['nome']]['utilizado'] += float(material['quantidade'])
    return materiais_agrupados

def insere_quantidade_anual(materiais_dos_pedidos, materiais_empresa):
    mat_empresa = {material['descricao']: {'total': material['quantidadeAnual'], 'medida': material['unidade'], 'categoria': material['categoria']} for material in materiais_empresa} # Formato facilitado
    for nome in mat_empresa.keys(): # Itera pelo nome dos objetos
        if not materiais_dos_pedidos.get(nome):
            materiais_dos_pedidos[nome] = {'utilizado': 0, 'categoria': mat_empresa[nome]['categoria']}
        materiais_dos_pedidos[nome]['total'] = float(mat_empresa[nome]['total']) # Aloca no dicionario do item especifico uma key chamada total que recebe a quantidade anual
        materiais_dos_pedidos[nome]['medida'] = mat_empresa[nome]['medida'] # Coloca a unidade de medida
    return materiais_dos_pedidos # Não precisa retornar pq mexemos no original, mas tá aí

def formata_materiais(materiais_dict):
    materiais = list()
    for nome in materiais_dict.keys():
        materiais.append({
            'nome': nome,
            'utilizado': materiais_dict[nome]['utilizado'],
            'total': materiais_dict[nome]['total'],
            'categoria': materiais_dict[nome]['categoria'],
            'medida': materiais_dict[nome]['medida']
            })
    return materiais


@router.get("/quantitativos", summary="Obtem uma lista de objetos relacionados aos quantitativos de consumo de materiais de uma determinada empresa.",
    dependencies=[Depends(permissions_user_role(approved_roles=[
            RoleName.admin, RoleName.fiscal, RoleName.assistente
            ]))])
async def collect_quantitativos(empresa: str, mes: int = Query(default=5, gt=0, lt=13), ano: int = Query(default=2021, gt=2000, lt=3000)):
    todos_pedidos = getPedidos(empresa=empresa) # Esses são só os pedidos
    if not todos_pedidos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pedidos não encontrados para a empresa {empresa}.")
    for pedido in todos_pedidos:
        pedido['_id'] = str(pedido['_id'])

    todos_materiais = getMateriais(empresa=empresa) # Esses são só os materiais
    if not todos_materiais:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Materiais não encontrados para a empresa {empresa}.")
    for material in todos_materiais:
        material['_id'] = str(material['_id'])

    # Etapa 1: Obter os pedidos da epoca correta
    pedidos_epoca_correta = filter_pedidos_por_mes_ano(todos_pedidos, mes, ano)
    # Etapa 2: Obter os materiais requisitados de pedidos ativos e validos da epoca correta
    materiais_na_epoca = filter_pedidos_validos(pedidos_epoca_correta, empresa)
    # Etapa 3: Obter apenas os materiais que foram recebidos nessa epoca
    materiais_recebidos = filter_materiais_ja_recebidos(materiais_na_epoca)
    # Etapa 4: Obter apenas os materiais fixos e sob demanda (contratuais, basicamente)
    materiais_validos = filter_materiais_contratuais(materiais_recebidos)
    # Etapa 5: Acumular os materiais em um unico conjunto, aproveitando a informaçao de quantidade comprada ate o momento e categoria
    materiais_comprados_agrupados = agrupa_materiais(materiais_validos) # Formato {"nome_do_item": {"utilizado": 10, "categoria": "Sob demanda"}}
    # Etapa 6: Buscar a informação do quantitativo anual do material na planilha da empresa
    materiais_com_qtde_anual = insere_quantidade_anual(materiais_comprados_agrupados, todos_materiais)
    # Etapa 7: Formatar o dicionario para transformá-lo em uma lista
    materiais_final = formata_materiais(materiais_com_qtde_anual)
    return materiais_final

@router.post("/pdfs", summary="Obtem os links para download dos PDFs associados.",
    dependencies=[Depends(permissions_user_role(approved_roles=[
            RoleName.admin, RoleName.fiscal, RoleName.assistente, RoleName.regular
            ]))])
async def collect_pdfs(pdfs_ids: dict = Body(...)):
    pdfs_links = dict()
    for dept, pdf_id in pdfs_ids.items():
        pdfs_links[dept] = get_pdf_link_for_download(pdf_id)
    return pdfs_links

@router.put("/redo-pdfs/{pedido_id}", summary="Remonta os PDFs para o pedido em questão.",
    dependencies=[Depends(permissions_user_role(approved_roles=[
            RoleName.admin, RoleName.fiscal
            ]))])
def redo_pdfs(pedido_id: str, pedido = Body(...)):
    pedido_in_db = getPedido(pedido_id) # Verifica se existe o pedido
    if pedido_in_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado.")

    # Obtem os ids dos pdfs antigos, caso existam. Se tudo ocorrer bem com a atualização, eles serão deletados
    old_pdfs_ids = pedido.get('pdfs_ids') 

    # Filtra os itens validos do pedido
    items_demap, items_empresa, items_almoxarifado = filter_valid_items_from_pedido(pedido)
    filename = get_name_padrao_para_pedido(pedido['number'])
    json_data = generate_padronized_data_for_pdfmonkey(pedido, filename)

    pdfs_ids = dict() # pdfs_ids é povoado com os novos ids respectivos
    # As funções abaixo alteram o dicionario original
    stage_new_pdf_for_group(items_empresa, Departamentos.empresa, json_data, pdfs_ids)
    stage_new_pdf_for_group(items_demap, Departamentos.demap, json_data, pdfs_ids)
    stage_new_pdf_for_group(items_almoxarifado, Departamentos.almoxarife, json_data, pdfs_ids)

    # Agora pdfs_ids contem os novos pdfs para cada um dos itens alterados do pedido
    pedido['pdfs_ids'] = pdfs_ids

    del pedido['_id'] # Deleta a key de _id para não ocorrer conflito
    res = putPedido(pedido_id, pedido) # pedido é um dict

    # Se res TRUE, quer dizer que a alteração foi um sucesso e os arquivos antigos de PDFs gerados podem ser apagados
    if res:
        if old_pdfs_ids: # Verifica se old_pdfs_ids não é null. Isso pode acontecer nos casos em que os PDFs não foram gerados automaticamente antes
            for pdf_id in old_pdfs_ids.values():
                delete_pdf_by_id(pdf_id)

    return {"pdfs_ids": pdfs_ids}
