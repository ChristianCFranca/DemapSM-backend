from sendgrid import SendGridAPIClient # Envio de emails utilizando o SendGrid
from sendgrid.helpers.mail import Mail

import os

from auth import RoleName, get_all_users_by_role

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
if not SENDGRID_API_KEY:
    raise Exception("No email API KEY available...")
else:
    print("\033[94m"+"INFO:" + "\033[0m" + "\t  Email Api Key environment data available! Loaded.")

STEPS_TO_ROLES = {
    2: RoleName.assistente,
    3: RoleName.fiscal,
    4: RoleName.almoxarife,
    5: RoleName.assistente
}
def send_email_to_role(status_step: int):
    role_name = STEPS_TO_ROLES.get(status_step) # Obtem o role responsável por aquele pedido
    if role_name is None:
        print("\033[93m"+"WARNING:" + "\033[0m" + "\t  Não foi possível obter o role responsável pela etapa em questão.")
        return
    users_with_specific_role = get_all_users_by_role(role_name) # Obtem todos os usuarios que são daquele role em específico
    if users_with_specific_role is None: # Se não houverem usuários, ocorre um warning e não envia emails
        print("\033[93m"+"WARNING:" + "\033[0m" + "\t  Não existem usuários com o role especificado. Nenhum email será enviado.")
        return

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