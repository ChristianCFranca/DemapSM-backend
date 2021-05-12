from enum import Enum

class RoleName(str, Enum):
    admin = "admin"
    fiscal = "fiscal"
    assistente = "assistente"
    almoxarife = "almoxarife"
    regular = "regular"