from fastapi import FastAPI, Depends, HTTPException, APIRouter, status, Request

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, EmailError
from typing import Optional, List
from enum import Enum

from datetime import datetime, timedelta # Lidar com a relação de tempo do JWT

from jose import JWTError, jwt
from passlib.context import CryptContext

from database import db # Importamos a conexão do banco de dados

# Define nosso router
router = APIRouter(prefix="/auth", tags=["Autenticação"])

COLLECTION = "users"
collection = db[COLLECTION] # Definimos a conexão com a collection users

SECRET_KEY = "abff49d6ea20daec2f0c1278863268858dd00b44e9c2d9ea5b236f4c200a6f18" # Não deve estar exposto em código
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1

# Modelos -------------------------------
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    role: str

class UserInDB(User):
    hashed_password: str

class RoleName(str, Enum):
    admin = "admin"
    fiscal = "fiscal"
    assistente = "assistente"
    regular = "regular"

# ---------------------------------------

# Define o contexto de criptografia
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Define o esquema OAuth2 para autenticacao
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# Cria o token de acesso
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy() # Copia o dicionário em um novo
    if expires_delta:
        expire = datetime.utcnow() + expires_delta # Se houve tempo de expiração, o expire recebe o horário atual + o horário da diferença (logo, agora + 30 minutos)
    else:
        expire = datetime.utcnow() + timedelta(minutes=5) # Se não, utiliza o padrão (agora + 5 minutos)
    to_encode.update({"exp": expire}) # Atualiza o dicionario to_encode com a informação de expiração
    encoded_jwt = jwt.encode( # Podemos agora criar a string JWT
        to_encode, # Passamos o dicionario que esta no formato {"sub": username, "expire": horario_de_agora}
        SECRET_KEY, # Passamos a secret key para a assinatura. NÃO DEVE SER COMPARTILHADA COM NADA NEM NINGUÉM
        algorithm=ALGORITHM # O algoritmo é o HS256 (só a aplicação do servidor terá controle sobre quem usa, não é necessário RS256, outro motivo pra manter a SECRET_KEY muito bem guardada)
        )
    return encoded_jwt # Retorna a string XXXX.XXXX.XXXX

# Obtemos o usuário atual. Essa é a função que cuida de verificar se o usuário que está logado ainda não expirou
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try: # O bloco try existe pois o jwt.decode gera uma exceção JWTError se a assinatura tiver sido inválida. Se ocorrer outra coisa fora o JWT o programa é derrubado
        payload = jwt.decode( # Decodifica o JWT, ficando atento à data de expiração
            token, # Utiliza o token string
            SECRET_KEY, # Utiliza a SECRET_KEY
            algorithms=[ALGORITHM] # Utiliza o mesmo algoritmo utilizado na codificação
            )
        username: str = payload.get("sub") # Obtém o usuário interno "subject" do JWT
        if username is None: # Verifica se ele não foi None (key não existe no dicionario)
            raise credentials_exception
        token_data = TokenData(username=username) # A informação dentro do token é o usuário
    except JWTError:
        raise credentials_exception
    user = get_user(username=token_data.username) # Utilizando o username, encontramos o username no banco de dados
    if user is None: # Se não encontrar o usuario, ocorreu erro de credenciais
        raise credentials_exception
    return user # Devolve o usuario com as informações

def check_strict_current_user_role(role): # Função (callable) que retorna outra funcao
    async def check_strict_user_role(token: str = Depends(oauth2_scheme)):
        user = await get_current_user(token)
        if user.role != role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário não tem permissão para fazer isso."
            )
        return user
    return check_strict_user_role

# Funções de utilidade geral -------------------------------------------------------------------------------------------------------------------------------------------------

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# Recebe o usuário e a senha
def authenticate_user(username: str, password: str):
    user = get_user(username) # A função retorna None se o usuário não existir no banco de dados. Se existir, retorna o objeto user
    if not user:
        return False
    if not verify_password(password, user.hashed_password): # Verifica se a senha está correta
        return False
    return user

def validate_email(username: str):
    username = username.lower()
    try:
        EmailStr.validate(username)
        if not username.endswith("@bcb.gov.br"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domínio do email inválido."
            )
    except EmailError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário deve ser um email válido."
        )
    return username
    
def corr_roles(role1, role2):
    if role1 == "admin":
        return True
    if role1 == "fiscal":
        if role2 != "assistente" and role2 != "regular":
            return False
        return True
    if role1 == "assistente":
        if role2 != "regular":
            return False
        return True

# funções CRUD ---------------------------------------------------------------------------------------------------------------------------------------------------------------
def get_all_users():
    users = list(collection.find())
    return users

def del_user(username: str):
    result = collection.delete_one({"username": username})
    return result.deleted_count

def get_user(username: str):
    if collection.find_one({"username": username}) is not None:
        user_dict = collection.find_one({"username": username})
        return UserInDB(**user_dict)

def insert_new_user_if_not_exist(user: UserInDB):
    if get_user(user.username) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nome de usuário já existe."
        )
    if not isinstance(user, dict):
        user = user.dict()
    user_inserted = collection.insert_one(user)
    if not user_inserted.acknowledged:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nome de usuário já existe."
        )
    return user_inserted
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# A autenticação começa aqui. Se tudo der certo, a resposta é do modelo {"token": SEU_TOKEN, "token_type": "bearer"}
@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()): # Utiliza a dependencia OAuth2PasswordRequestForm, que captura as informacoes no padrao OAuth2 (form-data, etc)
    user = authenticate_user(form_data.username, form_data.password) # Tenta autenticar esse usuario com o usuario e o password. Só funciona se o usuário já existe
    if not user: # A função anterior retorna None se o usuário não existir no banco de dados ou existir e a senha estiver errada
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, # Status code de não autorizado
            detail="Nome de usuário ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)  # Representa a diferença entre dois objetos datetime. Aqui a configuração está em minutos
    access_token = create_access_token( # Cria o token de acesso pro usuário que acabou de realizar login
        data={"sub": user.username},  # Passa o usuario (sempre é possível obtê-lo do JWT depois), mas pode ser absolutamente qualquer informacao
        expires_delta=access_token_expires # Passamos o tempo de expiração
    )
    return {"access_token": access_token, "token_type": "bearer"} # Isso é salvo pela aplicação, que pode usar como bem entender

@router.post("/users/create/{role_name}", response_model=User) # Criação de usuarios
async def create_user(role_name: RoleName, request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    if role_name != "regular":
        user = await get_current_user(await oauth2_scheme(request)) # Verifica se o usuário é valido
        if not corr_roles(user.role, role_name): # Pega o role do usuario atual e verifica sua permissao em relacao ao role colocado
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário não tem permissão para criar esse role."
            )
    username = validate_email(form_data.username) # Valida o formato do email
    hashed_password = pwd_context.hash(form_data.password)
    user = UserInDB(username=username, hashed_password=hashed_password, role=role_name)
    user_inserted = insert_new_user_if_not_exist(user)
    return user

@router.delete("/users/delete/{username}")
async def delete_user(username: str, current_user: User = Depends(get_current_user)): # O membro de acima tem permissão de deletar qualquer membro de baixo
    username = validate_email(username)
    user = get_user(username=username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Usuário não existe."
        )
    if not corr_roles(current_user.role, user.role):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Usuário não tem permissão para fazer isso."
        )
    del_count = del_user(username=username)
    return {"deleted_count": del_count}

@router.get("/users/", response_model=List[User])
async def read_users_me(current_user: User = Depends(get_current_user)):
    users = get_all_users()
    return users