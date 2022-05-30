from fastapi import APIRouter, HTTPException, status, Depends, Body

from auth import permissions_user_role
from cargos import RoleName, Departamentos

from generate_pdf_and_sheet import get_pdf_link_for_download, delete_pdf_by_id

from crud_pedidos import getPedido, putPedido, generate_padronized_data_for_pdfmonkey, stage_new_pdf_for_group, filter_valid_items_from_pedido

# Define nosso router
router = APIRouter(prefix="/collect-data", tags=["Pedidos de Compra"])

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
            RoleName.admin
            ]))])
def redo_pdfs(pedido_id: str, pedido = Body(...)):
    pedido_in_db = getPedido(pedido_id) # Verifica se existe o pedido
    if pedido_in_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado.")

    # Obtem os ids dos pdfs antigos, caso existam. Se tudo ocorrer bem com a atualização, eles serão deletados
    old_pdfs_ids = pedido.get('pdfs_ids') 

    # Filtra os itens validos do pedido
    items_demap, items_empresa, items_almoxarifado = filter_valid_items_from_pedido(pedido)
    json_data = generate_padronized_data_for_pdfmonkey(pedido)

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
        for pdf_id in old_pdfs_ids.values():
            delete_pdf_by_id(pdf_id)

    return {"pdfs_ids": pdfs_ids}
