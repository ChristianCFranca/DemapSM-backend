from fastapi import status as status_code
from fastapi import APIRouter, Body
from fastapi.exceptions import HTTPException
import requests
import base64
import os
from send_email import SEND_EMAIL, set_contents_for_compra, send_email_with_pdf
from cargos import Departamentos
from auth import get_all_users_by_role, get_dests

import json

# Define nosso router
router = APIRouter(prefix="/pdf", tags=["Setar Continuidade no envio do PDF"])

PDFMONKEY_API_KEY = os.environ.get("PDFMONKEY_API_KEY")
if not PDFMONKEY_API_KEY:
    raise Exception("No PDF GENERATOR API KEY available...")
else:
    print("\033[94m"+"PDF:" + "\033[0m" + "\t  PDF GENERATOR Api Key environment data available! Loaded.")

BASE_URL = "https://api.pdfmonkey.io/api/v1/documents/"
AUTH_HEADER = {"Authorization": f"Bearer {PDFMONKEY_API_KEY}"}

TEMPLATES_FOR_DEPARTAMENTO = {
    Departamentos.demap: "BFDE2B7D-4255-4ACA-9525-0209F55C0CFC".lower()
}
DEPARTAMENTO_TO_TEMPLATES = {value : key for key, value in TEMPLATES_FOR_DEPARTAMENTO.items()}

def stage_pdf(json_data, departamento):
    json_data['document']['document_template_id'] = TEMPLATES_FOR_DEPARTAMENTO[departamento]
    for counter in range(10, 0, -1):
        response = requests.post(BASE_URL, json=json_data, headers=AUTH_HEADER)
        if response.status_code == 201 or response.status_code == 200:
            print("\033[94mPDF:\033[0m" + "\t  PDF postado com sucesso.")
            return
        else:
            print("\033[93mPDF:\033[0m" + f"\t  Não foi possível postar o PDF. Tentando novamente... Tentativas restantes: {counter}")
    raise HTTPException(status_code=status_code.HTTP_500_INTERNAL_SERVER_ERROR, detail="Não foi possível postar a criação do PDF.")


@router.post("/webhook", summary="Recebe o sinal de geração finalizada do pdf")
async def post_staged_pdf_info(data: dict = Body(...)):
    print("\033[94mPDF:\033[0m" + "\t  PDF gerado detectado.")
    if not SEND_EMAIL:
        print("\033[94mPDF:\033[0m" + "\t  Envio de PDF's desativado.")
        raise HTTPException(status_code=status_code.HTTP_200_OK)

    if 'document' not in data:
        raise HTTPException(status_code=status_code.HTTP_400_BAD_REQUEST, detail="Document data not present")

    template_id = data['document']['document_template_id']
    departamento = DEPARTAMENTO_TO_TEMPLATES[template_id]

    pedido_id = json.loads(data['document']['payload'])['_id']
    pdf_name = f"pedido_de_compra_{pedido_id}.pdf"

    dests = get_dests(role_name="fiscal")

    download_url = data['document']['download_url']
    pdf_b64string = None
    for counter in range(10, 0, -1):
        response = requests.get(download_url)
        if response.status_code == 200:
            print("\033[94mPDF:\033[0m" + "\t  PDF baixado com sucesso.")
            pdf_b64string = base64.b64encode(response.content).decode()
            break
        else:
            print("\033[93mPDF:\033[0m" + f"\t  Não foi possível recuperar o pdf através da URL fornecida. Tentando novamente... Tentativas restantes: {counter}")

    if not pdf_b64string:
        raise HTTPException(status_code=status_code.HTTP_400_BAD_REQUEST, detail="\'download_url\' not working")

    subject, content = set_contents_for_compra(departamento)
    print("\033[94mPDF:\033[0m" + "\t  Enviando...")
    send_email_with_pdf(subject, content, pdf_b64string, pdf_name, dests)

    return