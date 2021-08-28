from enum import Enum

class RoleName(str, Enum):
    admin = "admin"
    fiscal = "fiscal"
    assistente = "assistente"
    almoxarife = "almoxarife"
    regular = "regular"

class Departamentos(str, Enum):
    demap = "demap"
    almoxarife = "almoxarife"
    empresa = "empresa"

emails_encarregados_por_empresa = {
    "Engemil": "ricardo.furtuoso@bcb.gov.br"
}