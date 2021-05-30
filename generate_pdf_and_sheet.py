from auth import del_user
from fastapi import status as status_code
from fastapi import APIRouter, Body
from fastapi.exceptions import HTTPException
import requests
import base64
import os
from send_email import SEND_EMAIL, set_contents_for_compra, send_email_with_pdf

# Define nosso router
router = APIRouter(prefix="/pdf", tags=["Setar Continuidade no envio do PDF"])

PDFMONKEY_API_KEY = os.environ.get("PDFMONKEY_API_KEY")
if not PDFMONKEY_API_KEY:
    raise Exception("No PDF GENERATOR API KEY available...")
else:
    print("\033[94m"+"PDF:" + "\033[0m" + "\t  PDF GENERATOR Api Key environment data available! Loaded.")

BASE_URL = "https://api.pdfmonkey.io/api/v1/documents/"
AUTH_HEADER = {"Authorization": f"Bearer {PDFMONKEY_API_KEY}"}

class PDFController():
    def __init__(self):
        self.staged_pdf_id = None
        self.dept = None
        self.pdf_name = None
        self.dests = None
    
    def stage_pdf(self, pdf_id, departamento, pdf_name, dests):
        self.staged_pdf_id = pdf_id
        self.dept = departamento
        self.pdf_name = pdf_name
        self.dests = dests

    def unstage_pdf(self):
        self.staged_pdf_id = None
        self.dept = None
        self.pdf_name = None
        self.dests = None

    def is_staged(self):
        return self.staged_pdf_id is not None

pdf_controller = PDFController()

def stage_pdf(json_data, departamento, dests):
    pdf_name = json_data['document']['meta']['_filename']
    for counter in range(10, 0, -1):
        response = requests.post(BASE_URL, json=json_data, headers=AUTH_HEADER)
        if response.status_code == 201 or response.status_code == 200:
            json_response = response.json()
            document_id = json_response['document']['id']
            pdf_controller.stage_pdf(pdf_id=document_id, departamento=departamento, pdf_name=pdf_name, dests=dests)
            print("\033[94mPDF:\033[0m" + "\t  PDF postado com sucesso.")
            return
        else:
            print("\033[93mPDF:\033[0m" + f"\t  Não foi possível postar o PDF. Tentando novamente... Tentativas restantes: {counter}")
    raise Exception("Não foi possível postar a criação do PDF.")


@router.post("/webhook", summary="Recebe o sinal de geração finalizada do pdf")
async def post_staged_pdf_info(data: dict = Body(...)):
    if not SEND_EMAIL:
        raise HTTPException(status_code=status_code.HTTP_200_OK)

    if 'document' not in data:
        raise HTTPException(status_code=status_code.HTTP_400_BAD_REQUEST, detail="Document data not present")

    if not pdf_controller.is_staged():
        print("\033[94mPDF:\033[0m" + "\t  Nenhum PDF não está registrado para stage no momento.")
        raise HTTPException(status_code=status_code.HTTP_200_OK)

    staged_pdf_id = data['document']['id']
    if staged_pdf_id != pdf_controller.staged_pdf_id:
        print("\033[94mPDF:\033[0m" + "\t  Este PDF específico não está registrado para stage no momento.")
        raise HTTPException(status_code=status_code.HTTP_200_OK)

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

    subject, content = set_contents_for_compra(pdf_controller.dept)

    send_email_with_pdf(subject, content, pdf_b64string, pdf_controller.pdf_name, pdf_controller.dests)

    pdf_controller.unstage_pdf()

    return