from sendgrid import SendGridAPIClient # Envio de emails utilizando o SendGrid
from sendgrid.helpers.mail import Mail

import os

SEND_EMAIL = os.environ.get("SEND_EMAIL")
if not SEND_EMAIL:
    raise Exception("No SEND EMAIL env available...")
else:
    try:
        if SEND_EMAIL.lower() == "true":
            SEND_EMAIL = True
        else:
            SEND_EMAIL = False
        print("\033[94m"+"INFO:" + "\033[0m" + f"\t  SEND EMAIL environment data available: \033[1m{SEND_EMAIL}\033[0m - Loaded.")
    except:
        raise Exception("SEND EMAIL env is available but cannot be casted to boolean...")

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
if not SENDGRID_API_KEY:
    raise Exception("No email API KEY available...")
else:
    print("\033[94m"+"INFO:" + "\033[0m" + "\t  Email Api Key environment data available! Loaded.")

def send_email_to_role(users_with_specific_role):
    dests = list(map(lambda user: user['username'], users_with_specific_role))  # Obtem todos os emails dos usuarios com o role especificado
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
        print("\033[94m"+"INFO:" + "\033[0m" + f"\t  Email sent successfully \033[94m {response.status_code} Accepted\033[0m")
    except Exception:
        print("\033[91m"+"ERRO:" + "\033[0m" + "\t  Ocorreu um erro ao enviar o email.")
        raise Exception("Error in sending the email...")

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
        print("\033[94m"+"INFO:" + "\033[0m" + f"\t  Email sent successfully \033[94m {response.status_code} Accepted\033[0m")
    except Exception:
        print("\033[91m"+"ERRO:" + "\033[0m" + "\t  Ocorreu um erro ao enviar o email.")
        raise Exception("Error in sending the email...")