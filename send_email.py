from sendgrid import SendGridAPIClient # Envio de emails utilizando o SendGrid
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

from fastapi import HTTPException, status

import os

from cargos import Departamentos

DEVELOPMENT_ADM_EMAIL = os.environ.get("DEVELOPMENT_ADM_EMAIL")
if not DEVELOPMENT_ADM_EMAIL:
    raise Exception("No DEVELOPMENT ADM EMAIL env available...")
else:
    try:
        if DEVELOPMENT_ADM_EMAIL.lower() == "true":
            DEVELOPMENT_ADM_EMAIL = True
        else:
            DEVELOPMENT_ADM_EMAIL = False
        print("\033[94m"+"EMAIL:" + "\033[0m" + f"\t  DEVELOPMENT ADM EMAIL environment data available: \033[1m{DEVELOPMENT_ADM_EMAIL}\033[0m - Loaded.")
    except:
        raise Exception("DEVELOPMENT ADM EMAIL env is available but cannot be casted to boolean...")

SEND_EMAIL = os.environ.get("SEND_EMAIL")
if not SEND_EMAIL:
    raise Exception("No SEND EMAIL env available...")
else:
    try:
        if SEND_EMAIL.lower() == "true":
            SEND_EMAIL = True
        else:
            SEND_EMAIL = False
        print("\033[94m"+"EMAIL:" + "\033[0m" + f"\t  SEND EMAIL environment data available: \033[1m{SEND_EMAIL}\033[0m - Loaded.")
    except:
        raise Exception("SEND EMAIL env is available but cannot be casted to boolean...")

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
if not SENDGRID_API_KEY:
    raise Exception("No email API KEY available...")
else:
    print("\033[94m"+"EMAIL:" + "\033[0m" + "\t  EMAIL API KEY environment data available! Loaded.")


# Funções -----------------------------------------------------------------------------------------------------------------------------

def set_contents_for_compra(for_dept):
    subject = "Nulo"
    content = "Nulo"
    if for_dept == Departamentos.demap:
        subject = "Um novo pedido de compra foi liberado para DEMAP"
        content="""
        <div>
            <div>
                Um novo pedido de compra foi liberado para compra com <b>cartão corporativo</b>!
            </div>
            <br>
            <div>
                O pdf em anexo contém as informações necessárias.
            </div>
        </div>
        """
    elif for_dept == Departamentos.almoxarife:
        subject = "Um novo pedido foi liberado para retirada de itens no ALMOXARIFE"
        content="""
        <div>
            <div>
                Um novo pedido de compra teve seus itens liberados para retirada no ALMOXARIFE.
            </div>
            <br>
            <div>
                O pdf em anexo contém as informações necessárias.
            </div>
        </div>
        """
    elif for_dept == Departamentos.engemil:
        subject = "Um novo pedido de compra foi liberado para ENGEMIL"
        content="""
        <div>
            <div>
                Um novo pedido de compra foi liberado para compra pela <b>ENGEMIL</b>!
            </div>
            <br>
            <div>
                As planilhas em anexo contém as informações necessárias.
            </div>
        </div>
        """
    return subject, content


def send_email_with_new_password(dest, user_id, new_password):
    subject = "Confirmação para Troca de Senha"
    content=f"""
    <div>
        Você solicitou uma nova senha.</div>
    </div>
    <br>
    <div>
        Sua nova senha é:
        <strong>{new_password}</strong>
    </div>
    <br>
    <div>
        Para essa senha entrar em vigor é necessária a confirmação clicando no link abaixo:
    </div>
    <div>
        <a href=\"https://demapsm-backend.herokuapp.com/auth/users/password/reset/?user_id={user_id}&alpha_key={new_password}\">Link para confirmação</a>
    </div>
    <br>
    <div>
        Se você não solicitou a troca de senha, ignore este email.
    </div>
    """
    
    message = Mail(
        from_email="smdemap@gmail.com",
        to_emails=dest,
        subject=subject,
        html_content=content
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print("\033[94m"+"EMAIL:" + "\033[0m" + f"\t  Email sent successfully \033[94m {response.status_code} Accepted\033[0m")
    except Exception:
        print("\033[91m"+"EMAIL:" + "\033[0m" + "\t  Ocorreu um erro ao enviar o email.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error in sending the email...")


def send_email_to_role(dests):
    if DEVELOPMENT_ADM_EMAIL:
        dests = ["christian.franca@bcb.gov.br"]

    subject = "Um novo pedido de compra precisa da sua confirmação!"
    content="""
    <div>
        Um novo pedido de compra foi registrado e está aguardando a sua <strong>confirmação</strong>!</div>
    </div>
    <br>
    <div>
        Você pode acessar os pedidos que precisam de sua confirmação no link a seguir:
    </div>
    <br>
    <div>
        <a href=\"https://demapsm.herokuapp.com/andamentos/\">Demap SM Andamentos</a>
    </div>
    """
    
    message = Mail(
        from_email="smdemap@gmail.com",
        to_emails=dests,
        subject=subject,
        html_content=content
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print("\033[94m"+"EMAIL:" + "\033[0m" + f"\t  Email sent successfully \033[94m {response.status_code} Accepted\033[0m")
    except Exception:
        print("\033[91m"+"EMAIL:" + "\033[0m" + "\t  Ocorreu um erro ao enviar o email.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error in sending the email...")


def send_email_with_pdf(subject, content, pdf_b64string, pdf_name, dests):
    if DEVELOPMENT_ADM_EMAIL:
        dests = ["christian.franca@bcb.gov.br"]

    message = Mail(
        from_email="smdemap@gmail.com",
        to_emails=dests,
        subject=subject,
        html_content=content
    )
    
    attached_pdf = Attachment (
        file_content=FileContent(pdf_b64string),
        file_name=FileName(pdf_name),
        file_type=FileType('application/pdf'),
        disposition=Disposition('attachment')
    )

    message.attachment = attached_pdf

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print("\033[94m"+"EMAIL:" + "\033[0m" + f"\t  Email sent successfully \033[94m {response.status_code} Accepted\033[0m")
    except Exception:
        print("\033[91m"+"EMAIL:" + "\033[0m" + "\t  Ocorreu um erro ao enviar o email.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ocorreu um erro ao enviar o email de notificação com o pdf")

def send_email_with_xlsx(subject, content, xlsx_b64, xlsx_name, dests):
    if DEVELOPMENT_ADM_EMAIL:
        dests = ["christian.franca@bcb.gov.br"]

    message = Mail(
        from_email="smdemap@gmail.com",
        to_emails=dests,
        subject=subject,
        html_content=content
    )
    
    attached_xlsx = Attachment (
        file_content=FileContent(xlsx_b64),
        file_name=FileName(xlsx_name),
        file_type=FileType('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
        disposition=Disposition('attachment')
    )

    message.attachment = attached_xlsx

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print("\033[94m"+"EMAIL:" + "\033[0m" + f"\t  Email sent successfully \033[94m {response.status_code} Accepted\033[0m")
    except Exception:
        print("\033[91m"+"EMAIL:" + "\033[0m" + "\t  Ocorreu um erro ao enviar o email.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ocorreu um erro ao enviar o email de notificação com o pdf")
