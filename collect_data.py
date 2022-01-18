from fastapi import APIRouter, Depends, Body
from fastapi.responses import StreamingResponse

from auth import permissions_user_role
from cargos import RoleName

from crud_pedidos import map_pedidos_for_compra_demap

from generate_pdf_and_sheet import stage_and_download_pdf_compras_demap, get_pdf_link_for_download

from io import BytesIO

# Define nosso router
router = APIRouter(prefix="/collect-data", tags=["Pedidos de Compra"])

@router.get("/compras-demap", summary="Get todos os pedidos pendentes para o DEMAP como um pdf", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente
        ]))])
def collect_compra_demap():
    pedidos_para_comprar = map_pedidos_for_compra_demap()
    json_data = {
        "document": {
                    "document_template_id": None,
                    "meta": {
                        "_filename": f"compra_demap.pdf"
                    },
                    "payload": {
                        "pedidos": pedidos_para_comprar
                    },
                    "status": "pending"
                }
    }
    pdf_file = BytesIO()
    pdf_bytes = stage_and_download_pdf_compras_demap(json_data)
    pdf_file.write(pdf_bytes)

    return StreamingResponse(
        iter([pdf_file.getvalue()]),
        media_type='application/pdf'
    )

@router.post("/pdfs", summary="Get os links para download dos PDFs associados.",
    dependencies=[Depends(permissions_user_role(approved_roles=[
            RoleName.admin, RoleName.fiscal, RoleName.assistente, RoleName.regular
            ]))])
async def collect_pdfs(pdfs_ids: dict = Body(...)):
    pdfs_links = dict()
    for dept, pdf_id in pdfs_ids.items():
        pdfs_links[dept] = get_pdf_link_for_download(pdf_id)
    return pdfs_links
