from time import time
from fastapi import status as status_code
from fastapi import APIRouter, Body
from fastapi.exceptions import HTTPException
import requests
import base64
import os

from yaml import FlowMappingStartToken
from send_email import SEND_EMAIL, set_contents_for_compra, send_email_with_pdf
from cargos import Departamentos, emails_encarregados_por_empresa
from auth import get_dests
import json
import time

# Define nosso router
router = APIRouter(prefix="/pdf", tags=["Setar Continuidade no envio do PDF"])

PDFMONKEY_API_KEY = os.environ.get("PDFMONKEY_API_KEY")
if not PDFMONKEY_API_KEY:
    raise Exception("No PDF GENERATOR API KEY available...")
else:
    print("\033[94m"+"PDF:" + "\033[0m" + "\t  PDF GENERATOR Api Key environment data available! Loaded.")

BASE_URL = "https://api.pdfmonkey.io/api/v1/documents"
AUTH_HEADER = {"Authorization": f"Bearer {PDFMONKEY_API_KEY}"}

TEMPLATE_FOR_FATURAMENTO = "8e600f10-195a-4263-96dd-ecea6da316d7"

TEMPLATES_FOR_DEPARTAMENTO = {
    Departamentos.demap: "BFDE2B7D-4255-4ACA-9525-0209F55C0CFC".lower(),
    Departamentos.almoxarife: "91C4B381-8608-4782-86B5-A8F92DE672BA".lower(),
    Departamentos.empresa: "10AE62D0-CAAE-4FD1-9781-3989F10AF5AA".lower()
}
TEMPLATES_TO_DEPARTAMENTOS = {value : key for key, value in TEMPLATES_FOR_DEPARTAMENTO.items()}

# Funções --------------------------------------------------------------------------------------------------------------------------------

def check_if_pdf_exists_by_id(pdf_id):
    response = requests.get(f"{BASE_URL}/{pdf_id}", headers=AUTH_HEADER)
    if response.status_code == 404:
        return False
    return True

def delete_pdf_by_id(pdf_id):
    response = requests.delete(f"{BASE_URL}/{pdf_id}", headers=AUTH_HEADER)
    print(response.status_code)
    if response.status_code != 204 and response.status_code != 404:
        errors = response.json()['errors'][0]
        print(errors)
        raise HTTPException(status_code=status_code.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Não foi possível apagar o PDF: {errors['detail']}")

def stage_pdf_faturamento(json_data):
    json_data['document']['document_template_id'] = TEMPLATE_FOR_FATURAMENTO
    for counter in range(5, 0, -1): # 5 tentativas
        response = requests.post(BASE_URL, json=json_data, headers=AUTH_HEADER)
        if response.status_code == 201 or response.status_code == 200:
            print("\033[94mPDF:\033[0m" + f"\t  PDF postado para faturamento com sucesso.")
            return response.json()
        else:
            print("\033[93mPDF:\033[0m" + f"\t  Não foi possível postar o PDF do faturamento. Tentando novamente... Tentativas restantes: {counter}")
    raise HTTPException(status_code=status_code.HTTP_500_INTERNAL_SERVER_ERROR, detail="Não foi possível postar o PDF para o serviço de PDFs.")

def stage_pdf(json_data, departamento):
    if departamento not in TEMPLATES_FOR_DEPARTAMENTO:
        raise HTTPException(status_code=status_code.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"O departamento \'{departamento}\' não apresenta uma chave no dicionário de templates.")
    json_data['document']['document_template_id'] = TEMPLATES_FOR_DEPARTAMENTO[departamento]
    for counter in range(5, 0, -1): # 5 tentativas
        response = requests.post(BASE_URL, json=json_data, headers=AUTH_HEADER)
        if response.status_code == 201 or response.status_code == 200:
            print("\033[94mPDF:\033[0m" + f"\t  PDF postado para {departamento} com sucesso.")
            return response.json()
        else:
            print("\033[93mPDF:\033[0m" + f"\t  Não foi possível postar o PDF. Tentando novamente... Tentativas restantes: {counter}")
    raise HTTPException(status_code=status_code.HTTP_500_INTERNAL_SERVER_ERROR, detail="Não foi possível postar a criação do PDF.")

def get_pdf_link_for_download(pdf_id):
    for counter in range(5, 0, -1): # 5 tentativas
        response = requests.get(f"{BASE_URL}/{pdf_id}", headers=AUTH_HEADER)
        print(response.status_code)
        if response.status_code == 200:
            if not response.json()['document']['download_url']:
                print("\033[93mPDF:\033[0m" + f"\t  Link de download ainda não disponível. Tentando novamente... Tentativas restantes: {counter}")
                time.sleep(1)
                continue
            print("\033[94mPDF:\033[0m" + f"\t  Link do PDF obtido para download com sucesso.")
            return response.json()['document']['download_url']
        elif response.status_code == 401:
            raise HTTPException(status_code=status_code.HTTP_400_BAD_REQUEST, detail="Um dos ID's passados não existe nos PDFs do banco de dados.")
        else:
            raise HTTPException(status_code=status_code.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ocorreu um erro ao tentar coletar os PDFs.")
    raise HTTPException(status_code=status_code.HTTP_408_REQUEST_TIMEOUT, detail="O link para download não ficou disponível ainda. Tente mais tarde.")

# Rota -----------------------------------------------------------------------------------------------------------------------------------

@router.post("/webhook", summary="Recebe o sinal de geração finalizada do pdf")
async def post_staged_pdf_info(data: dict = Body(...)):
    print("\033[94mPDF:\033[0m" + "\t  PDF gerado detectado.")
    if not SEND_EMAIL:
        print("\033[94mPDF:\033[0m" + "\t  Envio de PDF's desativado.")
        raise HTTPException(status_code=status_code.HTTP_200_OK)

    if 'document' not in data:
        raise HTTPException(status_code=status_code.HTTP_400_BAD_REQUEST, detail="Document data not present")

    template_id = data['document']['document_template_id']
    if TEMPLATES_TO_DEPARTAMENTOS.get(template_id) is None:
        print("\033[94mPDF:\033[0m" + f"\t  O template não existe para envio de emails. Assumindo pdf de download direto.")
        raise HTTPException(status_code=status_code.HTTP_200_OK, detail="O template não existe para o envio de email. Assumindo pdf de download direto.")

    departamento = TEMPLATES_TO_DEPARTAMENTOS[template_id]

    pedido = json.loads(data['document']['payload'])
    pedido_number = pedido['number'] # Carrega o numero do documento
    empresa_associada = pedido['empresa']
    pdf_name = f"pedido_de_compra_{pedido_number}.pdf"

    dests = get_dests(role_name="fiscal", correct_empresa=empresa_associada, verbose=True)
    if departamento == Departamentos.empresa or departamento == Departamentos.almoxarife:
        if empresa_associada in emails_encarregados_por_empresa:
            dests.extend(emails_encarregados_por_empresa[empresa_associada])
        else:
            print("\033[93mPDF:\033[0m" + f"\t  A empresa \'{empresa_associada}\' não apresenta um encarregado cadastrado. Recomenda-se o cadastro imediato.")

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

    titulo = "ERRO"
    ato = "ERRO"
    if departamento == Departamentos.empresa:
        titulo = "compra"
        ato = f"compra por parte da própria empresa"
    elif departamento == Departamentos.demap:
        titulo = "compra"
        ato = f"compra pelo <b>Cartão Corporativo</b>"
    elif departamento == Departamentos.almoxarife:
        titulo = "retirada"
        ato = f"retirada no <b>Almoxarife</b>"
    else:
        print("\033[93mPDF:\033[0m" + f"\t  O departamento \'{departamento}\' não está presente nos departamentos aceitos. O email será enviado sem informações.")

    info = {
        "pedido_number": pedido_number,
        "empresa": empresa_associada,
        "titulo": titulo,
        "ato": ato
    }
    subject, content = set_contents_for_compra(info)
    print("\033[94mPDF:\033[0m" + "\t  Enviando...")
    send_email_with_pdf(subject, content, pdf_b64string, pdf_name, dests)
