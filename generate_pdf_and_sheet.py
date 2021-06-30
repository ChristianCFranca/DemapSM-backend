from fastapi import status as status_code
from fastapi import APIRouter, Body
from fastapi.exceptions import HTTPException
import requests
import base64
import os
from send_email import SEND_EMAIL, set_contents_for_compra, send_email_with_pdf, send_email_with_xlsx
from cargos import Departamentos
from auth import get_dests
from openpyxl import load_workbook
from tempfile import NamedTemporaryFile
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

TEMPLATES_FOR_COMPRA = {
    "demap": "1C6D60D1-B722-48E1-9B8C-3E116E4AC5D6".lower()
}
TEMPLATES_FOR_DEPARTAMENTO = {
    Departamentos.demap: "BFDE2B7D-4255-4ACA-9525-0209F55C0CFC".lower(),
    Departamentos.almoxarife: "91C4B381-8608-4782-86B5-A8F92DE672BA".lower()
}
DEPARTAMENTO_TO_TEMPLATES = {value : key for key, value in TEMPLATES_FOR_DEPARTAMENTO.items()}

# Classe para lidar com a abertura do arquivo xlsx base da engemil
class EngemilHandlerXLS():
    def __init__(self, filename):
        self.filename = filename
        self.wb = load_workbook(filename)
        self.sheet = self.wb.active
        self.pedido = None
        
    def fmt_far(self, number):
        fmt_nbr = "{:,.2f}".format(number)
        return "R$ " + fmt_nbr.replace(',', 'a').replace('.', ',').replace('a', '.')

    def set_pedido(self, pedido):
        self.pedido = pedido.copy()
        
    def set_data(self):
        self.sheet['G2'] = self.pedido['dataAprovacaoAlmoxarife']
        
    def set_numero(self):
        self.sheet['J2'] = self.pedido['_id']
    
    def set_responsavel(self):
        self.sheet['E6'] = f"{self.pedido['fiscal']} - {self.pedido['emailFiscal']}"
    
    def set_items(self):
        for i, item in enumerate(self.pedido['items']):
            # Começa A9
            self.sheet[f"A{i+9}"] = i + 1
            #self.sheet[f"B12"] = item.codigoDilog
            self.sheet[f"B{i+9}"] = item['nome']
            self.sheet[f"F{i+9}"] = item['unidade']
            self.sheet[f"G{i+9}"] = item['quantidade']
            try:
                self.sheet[f"H{i+9}"] = self.fmt_far(float(item['valorUnitario']))
                self.sheet[f"J{i+9}"] = self.fmt_far(float(item['valorTotal']))
            except TypeError:
                raise HTTPException(status_code=status_code.HTTP_400_BAD_REQUEST, detail="Itens não cadastrados não podem ser comprados pela Engemil.")
        # Soma total
        try:
            self.sheet[f"J16"] = self.fmt_far(sum([float(item['valorTotal']) for item in self.pedido['items']]))
        except TypeError:
            raise HTTPException(status_code=status_code.HTTP_400_BAD_REQUEST, detail="Itens não cadastrados não podem ser comprados pela Engemil.")
        
    def set_finalidade(self):
        self.sheet['A20'] = self.pedido['finalidade']
    
    def set_obs(self):
        self.sheet['A24'] = f"Para atendimento da OS {self.pedido['os']}"
    
    def set_assinatura(self):
        self.sheet['G20'] = f"Sistema Demap SM\nFiscal: {self.pedido['fiscal']}\nE-mail: {self.pedido['emailFiscal']}\nautorizado em {self.pedido['dataAprovacaoFiscal']}\nàs {self.pedido['horarioAprovacaoFiscal']}"
    
    def set_final_sheet(self):
        self.set_numero()
        self.set_data()
        self.set_responsavel()
        self.set_items()
        self.set_finalidade()
        self.set_obs()
        self.set_assinatura()
    
    def get_b64_file(self):
        with NamedTemporaryFile() as tmp:
            self.wb.save(tmp)
            tmp.seek(0)
            stream = tmp.read()
        return base64.b64encode(stream).decode()
    
    def get_filename(self):
        return f"pedido_de_compra_{self.pedido['_id']}.xlsx"

    def unset_pedido(self):
        self.pedido = None

PATH_ENGEMIL_XLSX = "noncode/engemil_base.xlsx"
if not os.path.exists(PATH_ENGEMIL_XLSX):
    raise Exception("Arquivo engemil_base.xlsx não está no diretório previsto.")

engemil_xls = EngemilHandlerXLS(PATH_ENGEMIL_XLSX)

# Funções --------------------------------------------------------------------------------------------------------------------------------

def stage_pdf(json_data, departamento):
    json_data['document']['document_template_id'] = TEMPLATES_FOR_DEPARTAMENTO[departamento]
    for counter in range(5, 0, -1): # 5 tentativas
        response = requests.post(BASE_URL, json=json_data, headers=AUTH_HEADER)
        if response.status_code == 201 or response.status_code == 200:
            print("\033[94mPDF:\033[0m" + f"\t  PDF postado para {departamento} com sucesso.")
            return
        else:
            print("\033[93mPDF:\033[0m" + f"\t  Não foi possível postar o PDF. Tentando novamente... Tentativas restantes: {counter}")
    raise HTTPException(status_code=status_code.HTTP_500_INTERNAL_SERVER_ERROR, detail="Não foi possível postar a criação do PDF.")

def stage_and_download_pdf_compras_demap(json_data):
    json_data['document']['document_template_id'] = TEMPLATES_FOR_COMPRA["demap"]
    for counter in range(5, 0, -1): # 5 tentativas
        response = requests.post(BASE_URL, json=json_data, headers=AUTH_HEADER)
        if response.status_code == 201 or response.status_code == 200:
            print("\033[94mPDF:\033[0m" + f"\t  PDF postado para COMPRAS-DEMAP com sucesso.")
            pdf_id = response.json()['document']['id']

            for counter_2 in range(10, 0, -1): # 10 tentativas
                response = requests.get(f"{BASE_URL}/{pdf_id}", headers=AUTH_HEADER)
                if response.status_code == 201 or response.status_code == 200:
                    respose_json = response.json()
                    status = respose_json['document']['status']
                    if status == "failure":
                        print("\033[93mPDF:\033[0m" + f"\t  O pdf falhou na geração.")
                        raise HTTPException(status_code=status_code.HTTP_500_INTERNAL_SERVER_ERROR, detail="Não foi possível gerar o PDF externamente.")

                    elif status == "success":
                        download_url = respose_json['document']['download_url']
                        pdf_b64string = None
                        for counter_3 in range(10, 0, -1):
                            response = requests.get(download_url)
                            if response.status_code == 200:
                                print("\033[94mPDF:\033[0m" + "\t  PDF baixado com sucesso.")
                                pdf_bytes = response.content
                                return pdf_bytes
                            else:
                                print("\033[93mPDF:\033[0m" + f"\t  Não foi possível recuperar o pdf através da URL fornecida. Tentando novamente... Tentativas restantes: {counter_3}")
                        if not pdf_b64string:
                            raise HTTPException(status_code=status_code.HTTP_400_BAD_REQUEST, detail="\'download_url\' not working")

                    else:
                        time.sleep(0.1)

        else:
            print("\033[93mPDF:\033[0m" + f"\t  Não foi possível postar o PDF. Tentando novamente... Tentativas restantes: {counter}")
    raise HTTPException(status_code=status_code.HTTP_500_INTERNAL_SERVER_ERROR, detail="Não foi possível postar a criação do PDF.")


def stage_xlsx(pedido, dept):
    engemil_xls.set_pedido(pedido)
    engemil_xls.set_final_sheet()
    xlsx_b64 = engemil_xls.get_b64_file()
    xlsx_name = engemil_xls.get_filename()
    dests = get_dests(role_name="fiscal")
    dests += ['ricardo.furtuoso@bcb.gov.br']
    subject, content = set_contents_for_compra(dept, pedido['_number'])
    send_email_with_xlsx(subject, content, xlsx_b64, xlsx_name, dests)
    engemil_xls.unset_pedido()


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
    if DEPARTAMENTO_TO_TEMPLATES.get(template_id) is None:
        print("\033[94mPDF:\033[0m" + f"\t  O template não existe para envio de emails. Assumindo pdf de download direto.")
        raise HTTPException(status_code=status_code.HTTP_202_ACCEPTED, detail="O template não existe para o envio de email. Assumindo pdf de download direto.")

    departamento = DEPARTAMENTO_TO_TEMPLATES[template_id]

    pedido_number = json.loads(data['document']['payload'])['_number'] # Carrega o numero do documento
    pdf_name = f"pedido_de_compra_{pedido_number}.pdf"

    dests = get_dests(role_name="fiscal")
    if departamento == Departamentos.almoxarife:
        dests += ['ricardo.furtuoso@bcb.gov.br']

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

    subject, content = set_contents_for_compra(departamento, pedido_number)
    print("\033[94mPDF:\033[0m" + "\t  Enviando...")
    send_email_with_pdf(subject, content, pdf_b64string, pdf_name, dests)

    return