# DemapSM-backend
Implementação da API do servidor do Sistema de Solicitação de Materiais não oficial do Departamento de Infraestrutura e Gestão Patrimonial do Banco Central do Brasil. O sistema é uma REST API implementada em Python utilizando o framework [FastAPI](https://fastapi.tiangolo.com/).

![FastAPI Logo](https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png)

O banco de dados atualmente utilizado é o [MongoDB](https://www.mongodb.com/). A URL do cluster do MongoDB Atlas pode ser inserida diretamente no arquivo `database.py` ou deve ser setada em variáveis do ambiente `DATABASE_LOGIN` e `DATABASE_PASSWORD`. Sugiro para isso utilizar um arquivo local `.env` (a aplicação já o espera localmente para desenvolvimento).

## Instalação e Execução

Caso deseje rodar este projeto localmente, aqui estão apresentadas as soluções.

### Python
1 - Clone este repositório localmente (necessário Python 3 funcionando na máquina host para as etapas seguintes):
> git clone https://github.com/ChristianCFranca/DemapSCI-backend.git

2 - Instale as dependências utilizando o gerenciador de pacotes python `pip` (sugiro criar um ambiente virtual antes: https://docs.python.org/3/library/venv.html):
> pip install -r requirements.txt

3.1 - Rode a API utilizando o comando:

`python main.py`
```
INFO:     Started server process [12852] \
INFO:     Waiting for application startup. \
INFO:     Application startup complete. \
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit) \
```

3.2 - Também é possível rodar utilizando diretamente o `uvicorn`:

`uvicorn main:app`
```
INFO:     Started server process [12852] \
INFO:     Waiting for application startup. \
INFO:     Application startup complete. \
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit) \
```

4 - Acesse o endereço fornecido pela API (geralmente http://localhost/8000/docs) e verifique o correto funcionamento.