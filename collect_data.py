from fastapi import FastAPI, APIRouter, status, Depends
from fastapi.responses import StreamingResponse
from bson import ObjectId

from auth import permissions_user_role, RoleName

from cargos import cargo_key, checkKey
from crud_pedidos import getPedidos, collection

from io import StringIO
import pandas as pd

# Define nosso router
router = APIRouter(prefix="/collect_data", tags=["Pedidos de Compra"])

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


@router.get("/", summary="Get todos os pedidos como arquivo", 
    dependencies=[Depends(permissions_user_role(approved_roles=[
        RoleName.admin, RoleName.fiscal, RoleName.assistente, RoleName.almoxarife
        ]))])
async def get_pedidos():
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