from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from auth import permissions_user_role
from cargos import RoleName

from crud_pedidos import getPedidos, map_pedidos_for_compra_demap

from generate_pdf_and_sheet import stage_and_download_pdf_compras_demap

from io import StringIO, BytesIO
import pandas as pd

# Define nosso router
router = APIRouter(prefix="/collect-data", tags=["Pedidos de Compra"])

def getCorrectDF(df):
    new_df = pd.DataFrame(columns=df.drop('items', axis=1).rename({'quantidade': 'quantidadeDeItens'}, axis=1).columns.tolist() + 
    ['item_id'] +
    list(df['items'][0][0].keys())) # Dataframe vazio

    j = 0
    for i, row in df.iterrows():
        item_id = 0
        cols_from_original = df.iloc[i].drop('items').rename({'quantidade': 'quantidadeDeItens'}, axis=1).to_dict() # Tendo a base de repetição
        cols_from_original['_id'] = str(cols_from_original['_id']) # Transforma aquele _id pro formato string
        for item in row['items']: # item é um dict
            cols_from_original.update(item) # Atualizamos todas as colunas do original com as novas colunas do item
            item = pd.Series(cols_from_original)
            item['item_id'] = item_id 

            new_df.loc[j] = item

            j += 1
            item_id += 1

    int_cols = ['statusStep', 'item_id', 'quantidadeDeItens']
    bool_cols = ['active', 'aprovadoAssistente', 'aprovadoFiscal', 'almoxarifadoPossui']
    float_cols = ['quantidade']

    new_df[int_cols] = new_df[int_cols].astype('int64')
    new_df[bool_cols] = new_df[bool_cols].astype('boolean')
    new_df[float_cols] = new_df[float_cols].astype('float')

    return new_df


@router.get("/andamentos", summary="Get todos os pedidos como arquivo", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente
        ]))])
async def collect_andamentos():
    all_pedidos = getPedidos()
    pedidos_df = pd.DataFrame.from_records(all_pedidos)
    pedidos_df = getCorrectDF(pedidos_df)

    csv_file = StringIO()
    pedidos_df.to_csv(csv_file, index=False, sep=';', encoding='latin')

    return StreamingResponse(
        iter([csv_file.getvalue()]),
        headers={"Content-Disposition": "inline; filename=\"data.csv\""},
        media_type='text/csv'
    )

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