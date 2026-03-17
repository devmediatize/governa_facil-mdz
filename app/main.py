from fastapi.openapi.utils import get_openapi
from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Request, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from requests import request
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
import os
import re
import uuid
from jose import jwt, JWTError
from passlib.context import CryptContext
from dotenv import load_dotenv
import sys
from fastapi.openapi.docs import get_swagger_ui_html
from sqlalchemy import func, cast, Date, or_
from sqlalchemy import text
from sqlalchemy.orm import Session
import openai  # Ensure this import is correct and the package is installed
import json
from starlette.middleware.base import BaseHTTPMiddleware
from app.auth import authenticate_user  # Add this import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import models, schemas, database
from app.database import engine, get_db
from typing import Optional
from datetime import datetime, time
from .routers.relatorios import router as relatorios_router
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy import and_
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciais inválidas",
    headers={"WWW-Authenticate": "Bearer"},
)

# Configurações
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
openai.api_key = os.getenv("OPENAI_API_KEY")

EMAIL_SMTP=os.getenv("EMAIL_SMTP")
EMAIL_PORTA=os.getenv("EMAIL_PORTA")  
EMAIL_USER=os.getenv("EMAIL_USER")
EMAIL_CONTA=os.getenv("EMAIL_CONTA")
EMAIL_SENHA=os.getenv("EMAIL_SENHA")

app = FastAPI(
    title="Gestão Interativa API",
    description="API para o sistema de Gestão Interativa",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Criar tabelas automaticamente no banco de dados
models.Base.metadata.create_all(bind=engine)

@app.middleware("http")
async def exception_handling(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        # Log detalhado do erro
        import traceback
        error_detail = traceback.format_exc()
        print(f"Erro no middleware: {error_detail}")
        
        # Retorna um erro 500 com detalhes em formato JSON
        return JSONResponse(
            status_code=500,
            content={"detail": f"Erro interno do servidor: {str(e)}"}
        )

# 1. Primeiro o SessionMiddleware
app.add_middleware(
    SessionMiddleware, 
    secret_key="G3st401nT3r4t1v4"
)

# 2. Depois o CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CheckLoggedMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Rotas que não precisam de autenticação
        public_paths = [
            "/",  # Pagina inicial (login)
            "/token",  # Rota de autenticacao
            "/logout",  # Rota de logout
            "/docs",
            "/redoc",
            "/openapi.json",
            "/static",  # Arquivos estaticos
            "/favicon.ico",
            "/api/configuracao/logo-publica",  # Logo publica para tela de login
            "/api/configuracao/ia/chat-status"  # Status do chat IA
        ]
        
        # Se não for uma rota pública, verifica autenticação
        if not any(request.url.path.startswith(path) for path in public_paths):
            # Verifica o token no header Authorization
            auth_header = request.headers.get('Authorization')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                # Se não tiver token válido, redireciona para login
                print("Token não encontrado ou inválido - redirecionando para login")
                return RedirectResponse(url="/", status_code=303)
            try:
                token = auth_header.split(' ')[1]
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                if not payload:
                    return RedirectResponse(url="/", status_code=303)
            except (JWTError, IndexError):
                return RedirectResponse(url="/", status_code=303)
        return await call_next(request)

app.add_middleware(CheckLoggedMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/fotos", StaticFiles(directory="fotos"), name="fotos")
templates = Jinja2Templates(directory="templates")

@app.middleware("http")
async def add_global_context(request: Request, call_next):
    template_routes = ["/", "/dashboard", "/incidencias", "/mapa", "/usuarios", "/categorias", "/status", "/relatorios", "/configuracao"]

    # Verificar se a rota atual começa com alguma das rotas de template
    is_template_route = any(
        request.url.path == route or request.url.path.startswith(route + "/")
        for route in template_routes
    )

    if is_template_route:
        try:
            # Pegar o token do cookie e limpar as aspas extras
            cookie_token = request.cookies.get('access_token', '')
            if cookie_token:
                # Remover aspas e espaços extras
                cookie_token = cookie_token.strip('"')
                # Remover o prefixo "Bearer" se existir
                token = cookie_token.replace('Bearer ', '')
                
                # Decodificar o token
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                nivel = payload.get("nivel")
                request.state.nivel = nivel
            else:
                request.state.nivel = None
                
        except Exception as e:
            print(f"Erro ao processar token: {e}")
            request.state.nivel = None

    response = await call_next(request)
    return response

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    # Verifica se já está autenticado
    token = request.headers.get('Authorization')
    if token:
        try:
            payload = jwt.decode(token.replace('Bearer ', ''), SECRET_KEY, algorithms=[ALGORITHM])
            if payload:
                return RedirectResponse(url="/dashboard", status_code=303)
        except:
            pass
    
    return templates.TemplateResponse("login.html", {"request": request})


# Configuração de segurança
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Funções auxiliares
def verify_password(plain_password, hashed_password):
   return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
   return pwd_context.hash(password)

def create_access_token(data: dict):
   to_encode = data.copy()
   expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
   to_encode.update({"exp": expire})
   encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
   return encoded_jwt

# Dependência para obter usuário atual
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
   credentials_exception = HTTPException(
       status_code=status.HTTP_401_UNAUTHORIZED,
       detail="Could not validate credentials",
       headers={"WWW-Authenticate": "Bearer"},
   )
   
   try:
       payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
       email: str = payload.get("sub")
       if email is None:
           print("Email not found in token payload")
           raise credentials_exception
       print(f"Token payload: {payload}")
   except JWTError as e:
       print(f"JWTError: {e}")
       raise credentials_exception
   user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
   if user is None:
       print("User not found in database")
       raise credentials_exception
   print(f"User found: {user.email}")
   return user

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.JWTError:
        raise HTTPException(status_code=400, detail="Algum erro ocorreu")
    return email

# Rotas
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):    
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/incidencias", response_class=HTMLResponse)
async def incidencias(request: Request):
    return templates.TemplateResponse("incidencias.html", {"request": request})

@app.get("/incidencias/{id}", response_class=HTMLResponse)
async def read_incidencia(request: Request, id: int):
    return templates.TemplateResponse(
        "incidencias.html",
        {"request": request, "id": id}  # Inclui o id no contexto do template
    )

@app.get("/mapa", response_class=HTMLResponse)
async def mapa(request: Request):
    return templates.TemplateResponse("mapa.html", {"request": request})

@app.get("/categorias", response_class=HTMLResponse)
async def categorias(request: Request):
    return templates.TemplateResponse("categorias.html", {"request": request})

@app.get("/usuarios", response_class=HTMLResponse)
async def usuarios(request: Request):
    return templates.TemplateResponse("usuarios.html", {"request": request})

@app.get("/status", response_class=HTMLResponse)
async def status_page(request: Request):
    return templates.TemplateResponse("status.html", {"request": request})

@app.get("/relatorios", response_class=HTMLResponse)
async def relatorios(request: Request):    
    return templates.TemplateResponse("relatorios.html", {"request": request})

@app.get("/configuracao", response_class=HTMLResponse)
async def configuracao(request: Request):    
    return templates.TemplateResponse("configuracao.html", {"request": request})

@app.post("/token")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),  
    db: Session = Depends(get_db)
):
    print(f"Recebida tentativa de login para: {form_data.username}")
    
    user = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.senha):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Senha ou email incorretos, favor verificar!",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={
            "sub": user.email,
            "cliente_id": user.cliente_id,
            "user_id": user.usuario_id,
            "nivel": user.nivel
        }
    )

    response = JSONResponse(content={
        "access_token": access_token,
        "token_type": "bearer",
        "cliente_id": user.cliente_id
    })

    # Configurar o cookie sem aspas extras
    response.set_cookie(
        key="access_token",
        value=access_token,  # Sem o prefixo "Bearer"
        httponly=True,
        secure=False  # Mude para True em produção
    )

    return response

# Função para decodificar o token (adicione isto)
def get_current_user_data(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        cliente_id: int = payload.get("cliente_id")
        usuario_id: int = payload.get("usuario_id")
        nivel: int = payload.get("nivel")
        if email is None:
            raise credentials_exception
        return {"email": email, "cliente_id": cliente_id, "usuario_id": usuario_id}
    except JWTError:
        raise credentials_exception

# Rotas Usuarios

@app.post("/novo_usuario/", response_model=schemas.Usuario)
async def create_user(user: schemas.UsuarioCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    # Check for existing user
    db_user = db.query(models.Usuario).filter(models.Usuario.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Get hashed password
    hashed_password = get_password_hash(user.senha)
    
    # Get cliente_id from token
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    cliente_id = payload.get("cliente_id")
    if not cliente_id:
        raise credentials_exception

    # Create new user with all required fields
    db_user = models.Usuario(
        nome=user.nome,
        email=user.email,
        senha=hashed_password,
        endereco=user.endereco,
        cidade=user.cidade,
        estado=user.estado,
        ativo=1,
        cliente_id=cliente_id
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user



@app.put("/editar_usuario/{user_id}", response_model=schemas.Usuario)
async def update_user(user_id: int, user: schemas.UsuarioUpdate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    
    db_user = db.query(models.Usuario).filter(models.Usuario.usuario_id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user.dict(exclude_unset=True)
    if 'senha' in update_data and update_data['senha']:  # Verifica se senha existe e não é nula
        update_data['senha'] = get_password_hash(update_data['senha'])
    elif 'senha' in update_data:  # Remove senha se for nula
        del update_data['senha']
    
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@app.delete("/deletar_usuario/{user_id}")
async def delete_user(user_id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
   db_user = db.query(models.Usuario).filter(models.Usuario.usuario_id == user_id).first()
   if not db_user:
       raise HTTPException(status_code=404, detail="User not found")
   
   db.delete(db_user)
   db.commit()
   return {"message": "User deleted successfully"}

@app.get("/lista_usuarios/")
async def get_usuarios(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        print("Buscando usuários...") # Debug
        usuarios = db.query(models.Usuario).all()
        print(f"Usuários encontrados: {len(usuarios)}") # Debug

        result = [{
            "usuario_id": u.usuario_id,
            "nome": u.nome,
            "email": u.email,
            "celular": u.celular,            
            "cidade": u.cidade,
            "endereco": u.endereco,
            "estado": u.estado,
            "nivel": u.nivel
        } for u in usuarios]

        print("Dados formatados:", result) # Debug
        return result

    except Exception as e:
        print(f"Erro ao buscar usuários: {str(e)}") # Debug
        raise HTTPException(status_code=500, detail=str(e))
#

# Rota Incidencias

@app.post("/nova_incidencia/", response_model=schemas.Incidencia)
async def create_incidencia(
   incidencia: schemas.IncidenciaCreate,
   current_user: models.Usuario = Depends(get_current_user),
   db: Session = Depends(get_db)
):
   db_incidencia = models.Incidencia(**incidencia.dict(), usuario_id=current_user.usuario_id)
   db.add(db_incidencia)
   db.commit()
   db.refresh(db_incidencia)
   return db_incidencia

@app.get("/lista_incidencias/", response_model=List[schemas.Incidencia])
async def get_incidencias(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db),
    categoria_id: Optional[int] = None,
    status_id: Optional[int] = None,
    prioridade_id: Optional[int] = None,
    data_hora: Optional[str] = None,
    texto: Optional[str] = None
    ):
   
    # Decodificar o token para obter o cliente_id
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception
    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuário não identificado")
    
    # Primeiro, pegamos as categorias permitidas para o usuário
    categorias_permitidas = db.query(
        models.UsuarioCategoria.categoria_id
    ).filter(
        models.UsuarioCategoria.usuario_id == usuario_id
    ).all()
    # Converter lista de tuplas para lista simples
    categorias_ids = [cat[0] for cat in categorias_permitidas]
    if not categorias_ids:
        return []  # Retorna lista vazia se não tiver permissões
       
    query = db.query(
        models.Incidencia,
        models.Categoria.nome.label('categoria_nome'),
        models.Prioridade.nome.label('prioridade_nome'),
        models.Status.nome.label('status_nome')
    ).join(
        models.Categoria,
        models.Incidencia.categoria_id == models.Categoria.categoria_id
    ).join(
        models.Status,
        models.Incidencia.status == models.Status.status_id
    ).join(
        models.Prioridade,
        models.Incidencia.prioridade == models.Prioridade.prioridade_id
    )  
    
    # Filtrar por categorias permitidas
    query = query.filter(models.Incidencia.categoria_id.in_(categorias_ids))
    
    # Filtrar por cliente_id
    query = query.filter(models.Incidencia.cliente_id == cliente_id)
    
    if categoria_id:
        query = query.filter(models.Incidencia.categoria_id == categoria_id)
    
    if status_id:
        query = query.filter(models.Incidencia.status == status_id)
    
    if prioridade_id:
        query = query.filter(models.Incidencia.prioridade == prioridade_id)
    
    # Processamento da data_hora dentro do bloco condicional
    if data_hora:
        data_inicio_str, data_fim_str = data_hora.split(" até ")
        
        # Converter para datetime (assumindo formato DD/MM/YYYY) e pegar apenas a data
        data_inicio = datetime.strptime(data_inicio_str, "%d/%m/%Y").date()
        data_fim = datetime.strptime(data_fim_str, "%d/%m/%Y").date()
        
        # Verificar os valores antes de enviar ao banco
        print("Data de início:", data_inicio)  # Deve sair como 2025-01-26
        print("Data de fim:", data_fim)        # Deve sair como 2025-02-01
        
        # Aplicar filtro garantindo que a comparação seja feita corretamente com DATE
        query = query.filter(
            cast(models.Incidencia.data_hora, Date).between(data_inicio, data_fim)
        )
    
    if texto:
        # Alterado para usar filter também aqui e para usar OR entre as condições
        query = query.filter(or_(
            models.Incidencia.descricao.ilike(f"%{texto}%"),
            models.Incidencia.endereco.ilike(f"%{texto}%"),
            models.Incidencia.cidade.ilike(f"%{texto}%"),
            models.Incidencia.estado.ilike(f"%{texto}%"),
            models.Incidencia.bairro.ilike(f"%{texto}%")
        ))
    
    query = query.order_by(models.Incidencia.data_hora.desc())
    
    # Por fim, executamos a query
    result = query.all()
    
    return [
        {
            **i[0].__dict__,
            'categoria_nome': i.categoria_nome,
            'prioridade_nome': i.prioridade_nome,
            'status_nome': i.status_nome
        } for i in result
    ]

@app.post("/upload-foto/")
async def upload_foto(
   file: UploadFile = File(...),
   current_user: models.Usuario = Depends(get_current_user)
):
   file_location = f"static/fotos/{file.filename}"
   os.makedirs("static/fotos", exist_ok=True)
   with open(file_location, "wb+") as file_object:
       file_object.write(await file.read())
   return {"filename": file.filename}

@app.on_event("startup")
async def startup_event():
    templates_path = "templates"
    # Criar colunas de cor automaticamente se não existirem
    try:
        with database.engine.connect() as conn:
            conn.execute(text("ALTER TABLE cliente ADD COLUMN IF NOT EXISTS cor_primaria VARCHAR(7) DEFAULT '#086218'"))
            conn.execute(text("ALTER TABLE cliente ADD COLUMN IF NOT EXISTS cor_secundaria VARCHAR(7) DEFAULT '#001F5B'"))
            conn.commit()
            print("Colunas de cor verificadas/criadas com sucesso!")
    except Exception as e:
        print(f"Aviso ao verificar colunas de cor: {e}")

    # Criar colunas de IA (system_prompt e context_window) se não existirem
    try:
        with database.engine.connect() as conn:
            conn.execute(text("ALTER TABLE config_ai ADD COLUMN IF NOT EXISTS system_prompt TEXT"))
            conn.execute(text("ALTER TABLE config_ai ADD COLUMN IF NOT EXISTS context_window INTEGER DEFAULT 128000"))
            conn.commit()
            print("Colunas de IA verificadas/criadas com sucesso!")
    except Exception as e:
        print(f"Aviso ao verificar colunas de IA: {e}")

    # Criar coluna foto na tabela usuario se não existir
    try:
        with database.engine.connect() as conn:
            conn.execute(text("ALTER TABLE usuario ADD COLUMN IF NOT EXISTS foto VARCHAR(500)"))
            conn.commit()
            print("Coluna foto do usuario verificada/criada com sucesso!")
    except Exception as e:
        print(f"Aviso ao verificar coluna foto do usuario: {e}")

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    #print("Docs acessada")  # Log
    return get_swagger_ui_html(openapi_url="/openapi.json", title="API")

# Metodos Dashboard

@app.get("/api/dashboard/counters2")
async def get_counters(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception
    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuário não identificado")

    # Primeiro, pegamos as categorias permitidas para o usuário
    categorias_permitidas = db.query(
        models.UsuarioCategoria.categoria_id
    ).filter(
        models.UsuarioCategoria.usuario_id == usuario_id
    ).all()

    # Converter lista de tuplas para lista simples
    categorias_ids = [cat[0] for cat in categorias_permitidas]
    if not categorias_ids:
        return []  # Retorna lista vazia se não tiver permissões

    # Executar cada consulta independentemente com seu próprio filtro
    total = db.query(models.Incidencia).filter(models.Incidencia.categoria_id.in_(categorias_ids)).count()
    resolvidos = db.query(models.Incidencia).filter(models.Incidencia.categoria_id.in_(categorias_ids)).filter(models.Incidencia.status == 3).count()
    em_andamento = db.query(models.Incidencia).filter(models.Incidencia.categoria_id.in_(categorias_ids)).filter(models.Incidencia.status == 2).count()
    novos = db.query(models.Incidencia).filter(models.Incidencia.categoria_id.in_(categorias_ids)).filter(models.Incidencia.status == 1).count()

   
    return {
        "incidencias": total,
        "resolvidos": resolvidos,
        "emandamento": em_andamento,
        "novos": novos
    }

@app.get("/dados-usuarios")
async def get_Usuario(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Decodificar o token para obter o cliente_id e usuario_id
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception

    # Executa a query e traz os resultados com .all()
    results = (
        db.query(
            models.Usuario.usuario_id,
            models.Usuario.nome,
            models.Usuario.email,
            models.Usuario.celular,
            models.Usuario.foto,
            models.Cliente.nome.label("nome_cliente")
        )
          .join(models.Cliente, models.Cliente.cliente_id == models.Usuario.cliente_id)
          .where(models.Usuario.usuario_id == usuario_id)
          .all()
    )

    # Converte os resultados para uma lista de dicionários
    return [dict(row._mapping) for row in results]

    
@app.get("/api/dashboard/ultimas-incidencias")
async def get_ultimas_incidencias(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):

    # Decodificar o token para obter o cliente_id
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception

    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuário não identificado")

    # Primeiro, pegamos as categorias permitidas para o usuário
    categorias_permitidas = db.query(
        models.UsuarioCategoria.categoria_id
    ).filter(
        models.UsuarioCategoria.usuario_id == usuario_id
    ).all()

    # Converter lista de tuplas para lista simples
    categorias_ids = [cat[0] for cat in categorias_permitidas]

    if not categorias_ids:
        return []  # Retorna lista vazia se não tiver permissões

    results = db.query(
        models.Incidencia.incidencia_id,
        models.Incidencia.endereco,
        models.Incidencia.bairro,
        models.Incidencia.data_hora,        
        models.Status.nome.label('status_nome'),
        models.Categoria.nome.label('categoria_nome'),
        models.Incidencia.foto
    ).join(
        models.Status,
        models.Incidencia.status == models.Status.status_id 
    ).join(
        models.Categoria,
        models.Incidencia.categoria_id == models.Categoria.categoria_id
    ).where(models.Incidencia.status != 3
    )

    results = results.where(models.Incidencia.categoria_id.in_(categorias_ids))
    results = results.where(models.Incidencia.cliente_id == cliente_id)
    results = results.order_by(models.Incidencia.incidencia_id.desc()).limit(10).all()

    return [dict(row._mapping) for row in results]
  
#

@app.get("/lista_status")
async def get_status(db: Session = Depends(get_db)):
    return db.query(models.Status).where(models.Status.ativo==1).order_by(models.Status.nome).all()

@app.get("/lista_categorias")
async def get_categorias(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Decodificar o token para obter o cliente_id
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception
    
    # Primeiro, pegamos as categorias permitidas para o usuário
    categorias_permitidas = db.query(
        models.UsuarioCategoria.categoria_id
    ).filter(
        models.UsuarioCategoria.usuario_id == usuario_id
    ).all()

    # Converter lista de tuplas para lista simples
    categorias_ids = [cat[0] for cat in categorias_permitidas]

    if not categorias_ids:
        return []  # Retorna lista vazia se não tiver permissões
 
    results = db.query(models.Categoria)    
    
    if categorias_ids:
        results = results.where(models.Categoria.categoria_id.in_(categorias_ids))

    results = results.where(models.Categoria.ativo == 1).order_by(models.Categoria.nome).all()
    
    return results

@app.get("/lista_prioridades")
async def get_prioridades(db: Session = Depends(get_db)):
    return db.query(models.Prioridade).where(models.Prioridade.ativo==1).order_by(models.Prioridade.nome).all()

# API para mapa do dashboard - todas incidências com coordenadas
@app.get("/api/dashboard/mapa-incidencias")
async def get_mapa_incidencias(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception

    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuário não identificado")

    # Categorias permitidas para o usuário
    categorias_permitidas = db.query(
        models.UsuarioCategoria.categoria_id
    ).filter(
        models.UsuarioCategoria.usuario_id == usuario_id
    ).all()
    categorias_ids = [cat[0] for cat in categorias_permitidas]

    if not categorias_ids:
        return {"incidencias": [], "centro": {"lat": -15.7942, "lng": -47.8822}}

    # Buscar incidências com coordenadas
    results = db.query(
        models.Incidencia.incidencia_id,
        models.Incidencia.lat,
        models.Incidencia.long,
        models.Incidencia.endereco,
        models.Incidencia.bairro,
        models.Incidencia.descricao,
        models.Incidencia.foto,
        models.Incidencia.data_hora,
        models.Incidencia.status,
        models.Status.nome.label('status_nome'),
        models.Categoria.nome.label('categoria_nome'),
        models.Prioridade.nome.label('prioridade_nome')
    ).join(
        models.Status,
        models.Incidencia.status == models.Status.status_id
    ).join(
        models.Categoria,
        models.Incidencia.categoria_id == models.Categoria.categoria_id
    ).join(
        models.Prioridade,
        models.Incidencia.prioridade == models.Prioridade.prioridade_id
    ).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.categoria_id.in_(categorias_ids),
        # Filtrar coordenadas nulas E strings vazias
        models.Incidencia.lat.isnot(None),
        models.Incidencia.lat != '',
        models.Incidencia.lat != '0',
        models.Incidencia.long.isnot(None),
        models.Incidencia.long != '',
        models.Incidencia.long != '0'
    ).all()

    # Funcao auxiliar para validar coordenadas
    def is_valid_coordinate(lat_str, lng_str):
        """Verifica se as coordenadas sao validas e plausíveis"""
        try:
            if not lat_str or not lng_str:
                return False, None, None
            lat = float(str(lat_str).strip())
            lng = float(str(lng_str).strip())
            # Verificar se estao dentro dos limites geograficos validos
            # E se nao sao zero (coordenadas invalidas comuns)
            if lat == 0 and lng == 0:
                return False, None, None
            if lat == 0 or lng == 0:
                return False, None, None
            if not (-90 <= lat <= 90):
                return False, None, None
            if not (-180 <= lng <= 180):
                return False, None, None
            # Verificar se sao coordenadas plausíveis para Brasil (-35 a 5 lat, -75 a -30 lng)
            # Comentado para permitir outros países
            # if not (-35 <= lat <= 5) or not (-75 <= lng <= -30):
            #     return False, None, None
            return True, lat, lng
        except (ValueError, TypeError):
            return False, None, None

    incidencias = []
    lats = []
    lngs = []

    for r in results:
        is_valid, lat, lng = is_valid_coordinate(r.lat, r.long)
        if is_valid:
            lats.append(lat)
            lngs.append(lng)
            incidencias.append({
                "id": r.incidencia_id,
                "lat": lat,
                "lng": lng,
                "endereco": r.endereco or "",
                "bairro": r.bairro or "",
                "descricao": (r.descricao[:100] + "...") if r.descricao and len(r.descricao) > 100 else (r.descricao or ""),
                "foto": r.foto,
                "data": r.data_hora.strftime("%d/%m/%Y %H:%M") if r.data_hora else "",
                "status": r.status,
                "status_nome": r.status_nome,
                "categoria": r.categoria_nome,
                "prioridade": r.prioridade_nome
            })

    # Calcular centro do mapa
    if lats and lngs:
        centro = {"lat": sum(lats) / len(lats), "lng": sum(lngs) / len(lngs)}
    else:
        centro = {"lat": -15.7942, "lng": -47.8822}

    return {"incidencias": incidencias, "centro": centro}

# API para estatísticas rápidas do dashboard
@app.get("/api/dashboard/estatisticas-rapidas")
async def get_estatisticas_rapidas(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception

    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuário não identificado")

    categorias_permitidas = db.query(
        models.UsuarioCategoria.categoria_id
    ).filter(
        models.UsuarioCategoria.usuario_id == usuario_id
    ).all()
    categorias_ids = [cat[0] for cat in categorias_permitidas]

    if not categorias_ids:
        return {
            "total_hoje": 0,
            "total_semana": 0,
            "resolvidas_semana": 0,
            "tempo_medio_resolucao": 0,
            "bairro_mais_incidencias": "N/A",
            "categoria_mais_frequente": "N/A"
        }

    from datetime import date, timedelta
    hoje = date.today()
    inicio_semana = hoje - timedelta(days=7)

    # Incidências de hoje
    total_hoje = db.query(func.count(models.Incidencia.incidencia_id)).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.categoria_id.in_(categorias_ids),
        cast(models.Incidencia.data_hora, Date) == hoje
    ).scalar() or 0

    # Incidências da semana
    total_semana = db.query(func.count(models.Incidencia.incidencia_id)).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.categoria_id.in_(categorias_ids),
        cast(models.Incidencia.data_hora, Date) >= inicio_semana
    ).scalar() or 0

    # Resolvidas na semana
    resolvidas_semana = db.query(func.count(models.Incidencia.incidencia_id)).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.categoria_id.in_(categorias_ids),
        models.Incidencia.status == 3,
        cast(models.Incidencia.data_ultimo_status, Date) >= inicio_semana
    ).scalar() or 0

    # Bairro com mais incidências
    bairro_query = db.query(
        models.Incidencia.bairro,
        func.count(models.Incidencia.incidencia_id).label('total')
    ).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.categoria_id.in_(categorias_ids),
        models.Incidencia.bairro.isnot(None)
    ).group_by(models.Incidencia.bairro).order_by(func.count(models.Incidencia.incidencia_id).desc()).first()

    bairro_mais = bairro_query.bairro if bairro_query else "N/A"

    # Categoria mais frequente
    categoria_query = db.query(
        models.Categoria.nome,
        func.count(models.Incidencia.incidencia_id).label('total')
    ).join(
        models.Incidencia,
        models.Incidencia.categoria_id == models.Categoria.categoria_id
    ).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.categoria_id.in_(categorias_ids)
    ).group_by(models.Categoria.nome).order_by(func.count(models.Incidencia.incidencia_id).desc()).first()

    categoria_mais = categoria_query.nome if categoria_query else "N/A"

    return {
        "total_hoje": total_hoje,
        "total_semana": total_semana,
        "resolvidas_semana": resolvidas_semana,
        "bairro_mais_incidencias": bairro_mais,
        "categoria_mais_frequente": categoria_mais
    }

@app.get("/api/dashboard/incidencias-por-categoria")
async def get_incidencias_por_categoria(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
   
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception
    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuário não identificado")

    # Primeiro, pegamos as categorias permitidas para o usuário
    categorias_permitidas = db.query(
        models.UsuarioCategoria.categoria_id
    ).filter(
        models.UsuarioCategoria.usuario_id == usuario_id
    ).all()

    # Converter lista de tuplas para lista simples
    categorias_ids = [cat[0] for cat in categorias_permitidas]
    if not categorias_ids:
        return []  # Retorna lista vazia se não tiver permissões

    # Executar cada consulta independentemente com seu próprio filtro
    total = db.query(models.Incidencia).filter(models.Incidencia.categoria_id.in_(categorias_ids)).count()

    result = db.query(
        models.Categoria.nome.label('categoria'),
        func.count(models.Incidencia.incidencia_id).label('total')
    ).join(
        models.Incidencia,
        models.Categoria.categoria_id == models.Incidencia.categoria_id
    ).group_by(
        models.Categoria.nome
    ).filter(models.Incidencia.categoria_id.in_(categorias_ids)
    ).all()

    response = [{"categoria": r.categoria, "total": r.total} for r in result]
    print(response)  # Print the response
    return response


# API para estatísticas avançadas do dashboard
@app.get("/api/dashboard/estatisticas-avancadas")
async def get_estatisticas_avancadas(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Retorna estatísticas avançadas para o dashboard:
    - Taxa de resolução
    - Tempo médio de resolução
    - Comparativo semanal
    - Bairro crítico (mais incidências pendentes)
    - Categoria em alta (mais cresceu no período)
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception

    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuário não identificado")

    # Categorias permitidas para o usuário
    categorias_permitidas = db.query(
        models.UsuarioCategoria.categoria_id
    ).filter(
        models.UsuarioCategoria.usuario_id == usuario_id
    ).all()
    categorias_ids = [cat[0] for cat in categorias_permitidas]

    if not categorias_ids:
        return {
            "taxa_resolucao": 0,
            "tempo_medio_resolucao": 0,
            "comparativo_semanal": 0,
            "comparativo_positivo": True,
            "bairro_critico": "N/A",
            "bairro_critico_qtd": 0,
            "categoria_em_alta": "N/A",
            "categoria_em_alta_crescimento": 0
        }

    from datetime import date, timedelta
    hoje = date.today()
    inicio_semana_atual = hoje - timedelta(days=7)
    inicio_semana_anterior = hoje - timedelta(days=14)

    # 1. TAXA DE RESOLUÇÃO - Percentual de incidências resolvidas vs total
    total_incidencias = db.query(func.count(models.Incidencia.incidencia_id)).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.categoria_id.in_(categorias_ids)
    ).scalar() or 0

    total_resolvidas = db.query(func.count(models.Incidencia.incidencia_id)).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.categoria_id.in_(categorias_ids),
        models.Incidencia.status == 3
    ).scalar() or 0

    taxa_resolucao = round((total_resolvidas / total_incidencias * 100), 1) if total_incidencias > 0 else 0

    # 2. TEMPO MÉDIO DE RESOLUÇÃO - Diferença entre data_hora e data_ultimo_status para status=3
    # Buscar incidências resolvidas com datas válidas
    incidencias_resolvidas = db.query(
        models.Incidencia.data_hora,
        models.Incidencia.data_ultimo_status
    ).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.categoria_id.in_(categorias_ids),
        models.Incidencia.status == 3,
        models.Incidencia.data_hora.isnot(None),
        models.Incidencia.data_ultimo_status.isnot(None)
    ).all()

    tempo_total_dias = 0
    count_validas = 0
    for inc in incidencias_resolvidas:
        if inc.data_hora and inc.data_ultimo_status:
            diferenca = inc.data_ultimo_status - inc.data_hora
            dias = diferenca.days
            if dias >= 0:  # Apenas diferenças válidas
                tempo_total_dias += dias
                count_validas += 1

    tempo_medio_resolucao = round(tempo_total_dias / count_validas, 1) if count_validas > 0 else 0

    # 3. COMPARATIVO SEMANAL - Diferença percentual entre semana atual e anterior
    incidencias_semana_atual = db.query(func.count(models.Incidencia.incidencia_id)).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.categoria_id.in_(categorias_ids),
        cast(models.Incidencia.data_hora, Date) >= inicio_semana_atual
    ).scalar() or 0

    incidencias_semana_anterior = db.query(func.count(models.Incidencia.incidencia_id)).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.categoria_id.in_(categorias_ids),
        cast(models.Incidencia.data_hora, Date) >= inicio_semana_anterior,
        cast(models.Incidencia.data_hora, Date) < inicio_semana_atual
    ).scalar() or 0

    if incidencias_semana_anterior > 0:
        comparativo_semanal = round(((incidencias_semana_atual - incidencias_semana_anterior) / incidencias_semana_anterior * 100), 1)
    else:
        comparativo_semanal = 100 if incidencias_semana_atual > 0 else 0

    # Se o comparativo for negativo, significa que houve redução (positivo para o usuário)
    comparativo_positivo = comparativo_semanal <= 0

    # 4. BAIRRO CRÍTICO - Bairro com mais incidências pendentes (status != 3)
    bairro_critico_query = db.query(
        models.Incidencia.bairro,
        func.count(models.Incidencia.incidencia_id).label('total')
    ).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.categoria_id.in_(categorias_ids),
        models.Incidencia.status != 3,  # Não resolvidas
        models.Incidencia.bairro.isnot(None),
        models.Incidencia.bairro != ''
    ).group_by(models.Incidencia.bairro).order_by(func.count(models.Incidencia.incidencia_id).desc()).first()

    bairro_critico = bairro_critico_query.bairro if bairro_critico_query else "N/A"
    bairro_critico_qtd = bairro_critico_query.total if bairro_critico_query else 0

    # 5. CATEGORIA EM ALTA - Categoria que mais cresceu no período (comparando semanas)
    # Buscar contagem por categoria na semana atual
    categorias_semana_atual = db.query(
        models.Categoria.nome,
        models.Categoria.categoria_id,
        func.count(models.Incidencia.incidencia_id).label('total')
    ).join(
        models.Incidencia,
        models.Incidencia.categoria_id == models.Categoria.categoria_id
    ).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.categoria_id.in_(categorias_ids),
        cast(models.Incidencia.data_hora, Date) >= inicio_semana_atual
    ).group_by(models.Categoria.nome, models.Categoria.categoria_id).all()

    # Buscar contagem por categoria na semana anterior
    categorias_semana_anterior = db.query(
        models.Categoria.categoria_id,
        func.count(models.Incidencia.incidencia_id).label('total')
    ).join(
        models.Incidencia,
        models.Incidencia.categoria_id == models.Categoria.categoria_id
    ).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.categoria_id.in_(categorias_ids),
        cast(models.Incidencia.data_hora, Date) >= inicio_semana_anterior,
        cast(models.Incidencia.data_hora, Date) < inicio_semana_atual
    ).group_by(models.Categoria.categoria_id).all()

    # Criar dicionário da semana anterior para comparação
    dict_anterior = {cat.categoria_id: cat.total for cat in categorias_semana_anterior}

    # Calcular crescimento para cada categoria
    maior_crescimento = 0
    categoria_em_alta = "N/A"
    categoria_em_alta_crescimento = 0

    for cat in categorias_semana_atual:
        anterior = dict_anterior.get(cat.categoria_id, 0)
        if anterior > 0:
            crescimento = ((cat.total - anterior) / anterior) * 100
        else:
            crescimento = 100 if cat.total > 0 else 0

        if crescimento > maior_crescimento:
            maior_crescimento = crescimento
            categoria_em_alta = cat.nome
            categoria_em_alta_crescimento = round(crescimento, 1)

    return {
        "taxa_resolucao": taxa_resolucao,
        "tempo_medio_resolucao": tempo_medio_resolucao,
        "comparativo_semanal": abs(comparativo_semanal),
        "comparativo_positivo": comparativo_positivo,
        "bairro_critico": bairro_critico,
        "bairro_critico_qtd": bairro_critico_qtd,
        "categoria_em_alta": categoria_em_alta,
        "categoria_em_alta_crescimento": categoria_em_alta_crescimento,
        "total_incidencias": total_incidencias,
        "total_resolvidas": total_resolvidas,
        "incidencias_semana_atual": incidencias_semana_atual,
        "incidencias_semana_anterior": incidencias_semana_anterior
    }


@app.get("/usuario_id/{usuario_id}")
async def get_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.usuario_id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return usuario

@app.put("/usuario_id/{usuario_id}")
async def update_usuario(
    usuario_id: int, 
    usuario_data: dict,
    db: Session = Depends(get_db)
):
    db_usuario = db.query(models.Usuario).filter(models.Usuario.usuario_id == usuario_id).first()
    if not db_usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    for key, value in usuario_data.items():
        setattr(db_usuario, key, value)
    
    try:
        db.commit()
        db.refresh(db_usuario)
        return db_usuario
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/usuario/perfil")
async def atualizar_perfil(
    request: Request,
    dados: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Atualiza o perfil do usuário logado"""
    # Obter token do header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Token não fornecido")

    try:
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    # Buscar usuário pelo email
    usuario = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Atualizar dados
    if dados.get('nome'):
        usuario.nome = dados['nome']
    if dados.get('email'):
        usuario.email = dados['email']
    if dados.get('celular'):
        usuario.celular = dados['celular']

    # Atualizar senha se fornecida
    if dados.get('senha_nova') and dados.get('senha_atual'):
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        if not pwd_context.verify(dados['senha_atual'], usuario.senha):
            raise HTTPException(status_code=400, detail="Senha atual incorreta")
        usuario.senha = pwd_context.hash(dados['senha_nova'])

    try:
        db.commit()
        db.refresh(usuario)
        return {"message": "Perfil atualizado com sucesso"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/usuario/foto")
async def upload_foto_perfil(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload de foto de perfil do usuário logado"""
    # Obter token do header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Token não fornecido")

    try:
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        usuario_id = payload.get("user_id")
        if not email or not usuario_id:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    # Buscar usuário pelo email
    usuario = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Validar extensão do arquivo
    extensoes_permitidas = ['.png', '.jpg', '.jpeg']
    extensao = os.path.splitext(file.filename)[1].lower()
    if extensao not in extensoes_permitidas:
        raise HTTPException(
            status_code=400,
            detail="Formato de arquivo não permitido. Use: PNG, JPG ou JPEG"
        )

    # Validar content type
    content_types_permitidos = ['image/png', 'image/jpeg', 'image/jpg']
    if file.content_type not in content_types_permitidos:
        raise HTTPException(
            status_code=400,
            detail="Tipo de arquivo não permitido. Envie uma imagem PNG ou JPG"
        )

    # Gerar nome único para o arquivo
    nome_unico = f"user_{usuario_id}_{uuid.uuid4().hex[:8]}{extensao}"
    caminho_arquivo = f"fotos/usuarios/{nome_unico}"

    # Criar diretório se não existir
    os.makedirs("fotos/usuarios", exist_ok=True)

    # Remover foto antiga se existir
    if usuario.foto:
        caminho_antigo = usuario.foto
        if os.path.exists(caminho_antigo):
            try:
                os.remove(caminho_antigo)
            except Exception:
                pass

    # Salvar arquivo
    try:
        content = await file.read()
        with open(caminho_arquivo, "wb") as buffer:
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {str(e)}")

    # Atualizar no banco de dados
    try:
        usuario.foto = caminho_arquivo
        db.commit()
        db.refresh(usuario)
    except Exception as e:
        # Se falhar o banco, remover o arquivo salvo
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar banco de dados: {str(e)}")

    return {
        "message": "Foto de perfil atualizada com sucesso",
        "foto": f"/{caminho_arquivo}"
    }

@app.get("/usuarios/{usuario_id}/categorias-disponiveis")
async def get_categorias_disponiveis(usuario_id: int, db: Session = Depends(get_db)):
    # Subquery para pegar as categorias já vinculadas
    subquery = db.query(models.UsuarioCategoria.categoria_id).filter(
        models.UsuarioCategoria.usuario_id == usuario_id
    )
    
    # Buscar categorias não vinculadas
    categorias = db.query(
        models.Categoria.categoria_id,
        models.Categoria.nome
    ).filter(
        ~models.Categoria.categoria_id.in_(subquery)
    ).all()

    # Formatar o resultado
    return [
        {
            "categoria_id": cat.categoria_id,
            "nome": cat.nome
        }
        for cat in categorias
    ]

@app.get("/usuarios/{usuario_id}/categorias-vinculadas")
async def get_categorias_vinculadas(usuario_id: int, db: Session = Depends(get_db)):
    # Buscar as vinculações com join nas tabelas necessárias
    vinculacoes = db.query(
        models.Categoria.categoria_id,
        models.Categoria.nome,
        models.UsuarioCategoria.notifica_email,
        models.UsuarioCategoria.notifica_sms
    ).join(
        models.UsuarioCategoria,
        models.Categoria.categoria_id == models.UsuarioCategoria.categoria_id
    ).filter(
        models.UsuarioCategoria.usuario_id == usuario_id
    ).all()

    # Formatar os resultados em um formato que pode ser serializado para JSON
    return [
        {
            "categoria_id": vinc.categoria_id,
            "nome": vinc.nome,
            "notifica_email": vinc.notifica_email,
            "notifica_sms": vinc.notifica_sms
        }
        for vinc in vinculacoes
    ]

@app.post("/usuarios/{usuario_id}/vincular-categorias")
async def vincular_categorias(
    usuario_id: int,
    dados: dict,
    db: Session = Depends(get_db)
):
    for categoria_id in dados['categorias']:
        vinculo = models.UsuarioCategoria(
            usuario_id=usuario_id,
            categoria_id=categoria_id,
            notifica_email=dados['notifica_email'],
            notifica_sms=dados['notifica_sms']
        )
        db.add(vinculo)
    
    db.commit()
    return {"message": "Categorias vinculadas com sucesso"}

@app.post("/usuarios/{usuario_id}/desvincular-categorias")
async def desvincular_categorias(
    usuario_id: int,
    dados: dict,
    db: Session = Depends(get_db)
):
    db.query(models.UsuarioCategoria).filter(
        models.UsuarioCategoria.usuario_id == usuario_id,
        models.UsuarioCategoria.categoria_id.in_(dados['categorias'])
    ).delete(synchronize_session=False)
    
    db.commit()
    return {"message": "Categorias desvinculadas com sucesso"}

@app.get("/categorias-permitidas")
async def get_categorias_permitidas(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception
   
  
    # Buscar categorias permitidas para o usuário
    categorias = db.query(
        models.Categoria.categoria_id,
        models.Categoria.nome
    ).join(
        models.UsuarioCategoria,
        models.Categoria.categoria_id == models.UsuarioCategoria.categoria_id
    ).filter(
        models.UsuarioCategoria.usuario_id == usuario_id
    ).all()
   
    # Converter para formato simples
    resultado = [{"id": cat.categoria_id, "nome": cat.nome} for cat in categorias]
    
    return {"categorias": resultado}

@app.post("/usuarios/{usuario_id}/atualizar-notificacao")
async def atualizar_notificacao(
    usuario_id: int,
    dados: dict,
    db: Session = Depends(get_db)
):
    try:
        vinculo = db.query(models.UsuarioCategoria).filter(
            models.UsuarioCategoria.usuario_id == usuario_id,
            models.UsuarioCategoria.categoria_id == dados['categoria_id']
        ).first()

        if not vinculo:
            raise HTTPException(status_code=404, detail="Vinculação não encontrada")

        if dados['tipo'] == 'email':
            vinculo.notifica_email = dados['valor']
        elif dados['tipo'] == 'sms':
            vinculo.notifica_sms = dados['valor']

        db.commit()
        return {"message": "Notificação atualizada com sucesso"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    return response

# Integrador com IA

@app.post("/perguntaia")
async def pergunta_IA(request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    pergunta = form_data.get('pergunta')

    # try:
    #     payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    #     usuario_id = payload.get("user_id")
    # except JWTError:
    #     raise credentials_exception   
  
    # # Buscar categorias permitidas para o usuário
    # categorias = db.query(
    #     models.Categoria.categoria_id,
    #     models.Categoria.nome
    # ).join(
    #     models.UsuarioCategoria,
    #     models.Categoria.categoria_id == models.UsuarioCategoria.categoria_id
    # ).filter(
    #     models.UsuarioCategoria.usuario_id == usuario_id
    # ).all()
   
    # # Converter para formato simples
    # resultado = [{"id": cat.categoria_id, "nome": cat.nome} for cat in categorias]

    # pergunta = pergunta + ", apenas para as categorias com o nome de: " + resultado

    print(pergunta)

    if not pergunta:
        raise HTTPException(status_code=400, detail="Pergunta não fornecida")
    resultados = processar_pergunta(pergunta, db)
    print(resultados)
    return {"resultados": resultados}

def gerar_schema_info(base):
    schema_info = ""
    for table_name, table in base.metadata.tables.items():
        schema_info += f"Tabela: {table_name}\nColunas:\n"
        for column in table.columns:
            schema_info += f"  - {column.name} ({column.type})\n"
    return schema_info

def gerar_sql(pergunta, schema_info):
    prompt = f"""
    Você é um assistente de banco de dados. 
    Nunca compare as informações com o campo descrição da tabela de incidencias, os valores devem ser comparados nas tabelas
    relacionadas.
    Comparece apenas no campo descrição da tabela de incidencias caso a Pergunta  seja especificada para tal.
    Use ILIKE para comparações de texto para tornar case insensitive e tambem coloque percentual antes de depois. 
    Coloque sempre duas comparacao dos textos em singular ou plural.
    Sempre mostre apenas campos de textos ou datas, ou totais gerados e não campos do tipo inteiro.
    formate os campos datas no formato dd/mm/aaaa.
    oculte o campo foto.
    Gere uma consulta SQL válida baseada na seguinte pergunta:
    Pergunta: "{pergunta}"
    Estrutura do banco de dados: {schema_info}
    Não utilize campo descrição da tabela de incidencias para comparação de informações
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Você é um assistente de banco de dados."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message['content'].strip()

def executar_sqlalchemy_query(query: str, db: Session):
    try:
        # Declarar a query como texto SQL explícito
        result = db.execute(text(query))
        return [dict(row._mapping) for row in result]
    except Exception as e:
        print(f"Erro ao executar query: {e}")
        return []

def processar_pergunta(perguntaChat: str, db: Session = Depends(get_db)):
    # Insere a pergunta no log
    db_LogChat = models.ChatBot(pergunta=perguntaChat, pergunta_data_hora=datetime.now())    

    # Descrição do esquema do banco
    schema_info = gerar_schema_info(models.Base)
    
    # Atualiza a data do log com a resposta para calcular o tempo da IA
    db_LogChat.reposta_data_hora = datetime.now()

    # Gerar o SQL com base na pergunta
    retorno = gerar_sql(perguntaChat, schema_info)
    sql = extrair_sql_apenas(retorno)

    # Executar a query gerada 
    resultados = executar_sqlalchemy_query(sql, db)

    # Converter datetime para string antes da serialização JSON
    resultados_json = []
    for row in resultados:
        row_dict = {}
        for key, value in row.items():
            if isinstance(value, datetime):
                row_dict[key] = value.isoformat()
            else:
                row_dict[key] = value
        resultados_json.append(row_dict)

    # Atualiza no log com os outros campos e a resposta
    db_LogChat.reposta = json.dumps(resultados_json)  # Agora usando a versão convertida
    db_LogChat.sql = sql
    db_LogChat.reposta_geral = retorno

    # Atualiza o banco de dados do log inserido
    db.add(db_LogChat)    
    db.commit()
    db.refresh(db_LogChat)

    return resultados

def extrair_sql_apenas(texto):
    # Capturar o conteúdo do SQL entre os blocos ```sql ... ```
    match = re.search(r"```sql\s+(.*?)\s+```", texto, re.DOTALL)
    if (match):
        return match.group(1).strip()  # Retorna apenas o SQL, sem os blocos de código
    else:
        return texto  # Retorna o conteúdo completo caso não encontre o bloco

# Fim


def enviar_email(destinatario, assunto, mensagem):
    # Configurações do servidor de email
    user = EMAIL_USER
    password = EMAIL_SENHA
    sender = EMAIL_CONTA
    
    msg = MIMEText(mensagem, 'html')
    msg['Subject'] = assunto
    msg['From'] = EMAIL_SMTP
    msg['To'] = destinatario

    try:
        # Cria a conexão com o servidor SMTP e utiliza o contexto de gerenciamento "with" para garantir o fechamento da conexão
        with smtplib.SMTP(EMAIL_SMTP, EMAIL_PORTA) as s:
            s.set_debuglevel(0)
            s.starttls()
            s.login(user, password)
            s.sendmail(sender, destinatario, msg.as_string())
            #s.quit()
            print("Email enviado com sucesso!")
    except Exception as e:
        print("Ocorreu um erro ao enviar o email:")
        print(e)



@app.post("/interagir", status_code=status.HTTP_201_CREATED)
async def interagir_incidencia(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    # Obter os dados do corpo da requisição
    dados = await request.json()
    # print("Dados recebidos:", dados)
    
    # Extrair os valores do corpo da requisição
    incidencia_id = dados.get("incidencia_id")
    novo_status_id = dados.get("novo_status_id")
    comentario = dados.get("comentario")
    
    # Verificação básica
    if not all([incidencia_id, novo_status_id, comentario]):
        raise HTTPException(status_code=400, detail="Dados incompletos. Todos os campos são obrigatórios")
    
    # Verificar autenticação
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id = payload.get("user_id")
    except Exception:
        raise credentials_exception
   
    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuário não identificado")
   
    # Verificar se a incidência existe
    incidencia = db.query(models.Incidencia).filter(
        models.Incidencia.incidencia_id == incidencia_id
    ).first()
   
    if not incidencia:
        raise HTTPException(
            status_code=404,
            detail=f"Incidência com ID {incidencia_id} não encontrada"
        )
   
    # Verificar se o status existe
    status_obj = db.query(models.Status).filter(
        models.Status.status_id == novo_status_id  # Aqui usa novo_status_id
    ).first()
   
    if not status_obj:
        raise HTTPException(
            status_code=404,
            detail=f"Status com ID {novo_status_id} não encontrado"
        )
   
    # Obter dados do usuário atual
    usuario_atual = db.query(models.Usuario).filter(
        models.Usuario.usuario_id == usuario_id
    ).first()
   
    if not usuario_atual:
        raise HTTPException(
            status_code=404,
            detail=f"Usuário atual não encontrado"
        )
   
    # Registrar a interação
    nova_interacao = models.IncidenciaInteracao(
        incidencia_id=incidencia_id,
        usuario_id=usuario_id,
        comentario=comentario,
        status_id=novo_status_id,  # Aqui usa novo_status_id 
        data=datetime.now()
    )
   
    db.add(nova_interacao)
   
    # Atualizar o status da incidência
    incidencia.status = novo_status_id  # Aqui usa novo_status_id
    incidencia.data_ultimo_status = datetime.now()
   
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao salvar interação: {str(e)}"
        )
   
    # Buscar email do cidadão que criou a incidência
    cidadao_criador = db.query(models.Cidadao).filter(
        models.Cidadao.cidadao_id == incidencia.cidadao_id
    ).first()
    
    # Enviar email se o cidadão tiver um email
    if cidadao_criador and cidadao_criador.email:
        # Preparar conteúdo do email
        assunto = f"Atualização da Incidência #{incidencia_id}"
       
        mensagem_html = f"""
        <html>
        <body>
        <h1>Atualização de Incidência</h1>
        <p>Olá, {cidadao_criador.nome} - {cidadao_criador.email},</p>
        <p>A incidência <strong>#{incidencia_id}</strong> foi atualizada.</p>
        <p><strong>Novo Status:</strong> {status_obj.nome}</p>
        <p><strong>Comentário:</strong> {comentario}</p>
        <p><strong>Atualizado por:</strong> {usuario_atual.nome}</p>
        <p><strong>Data/Hora:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        <br><br><p>Para mais detalhes, acesse o sistema de Gestão Interativa.</p>
        <br><br><br><p>Atenciosamente,<br>
        Equipe de Gestão Interativa</p>
        </body>
        </html>
        """       

        # Enviar email de forma assíncrona
        enviar_email(cidadao_criador.email, assunto, mensagem_html)
   
    retorno = {
        "mensagem": "Interação registrada com sucesso",
        "incidencia_id": incidencia_id,
        "novo_status": status_obj.nome,
        "email_enviado": cidadao_criador is not None and cidadao_criador.email is not None
    }

    return retorno


@app.get("/interacoes/{incidencia_id}")
async def listar_interacoes(
    incidencia_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    # Verificar autenticação
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id = payload.get("user_id")
    except Exception:
        raise credentials_exception
   
    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuário não identificado")
   
    # Verificar se a incidência existe
    incidencia = db.query(models.Incidencia).filter(
        models.Incidencia.incidencia_id == incidencia_id
    ).first()
   
    if not incidencia:
        raise HTTPException(
            status_code=404,
            detail=f"Incidência com ID {incidencia_id} não encontrada"
        )
   
    # Buscar todas as interações desta incidência
    # Usando um método diferente para obter os dados relacionados
    interacoes = db.query(
        models.IncidenciaInteracao,
        models.Usuario,
        models.Status
    ).join(
        models.Usuario,
        models.IncidenciaInteracao.usuario_id == models.Usuario.usuario_id
    ).join(
        models.Status,
        models.IncidenciaInteracao.status_id == models.Status.status_id
    ).filter(
        models.IncidenciaInteracao.incidencia_id == incidencia_id
    ).order_by(
        models.IncidenciaInteracao.data.desc()
    ).all()
   
    # Formatar os resultados
    resultado = []
    for IncidenciaInteracao, usuario, status in interacoes:
        interacao_dict = {
            "incidencia_interacao_id": IncidenciaInteracao.incidencia_interacao_id,
            "incidencia_id": IncidenciaInteracao.incidencia_id,
            "comentario": IncidenciaInteracao.comentario,
            "data_hora": IncidenciaInteracao.data,
            "usuario_id": usuario.usuario_id,
            "usuario": {                
                "nome": usuario.nome
            },
            "status": {
                "status_id": status.status_id,
                "nome": status.nome
            }
        }
        resultado.append(interacao_dict)
   
    return {"interacoes": resultado, "usuario_atual": usuario_id}

@app.delete("/interacoes/{interacao_id}")
async def excluir_interacao(
    interacao_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    # Verificar autenticação
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id = payload.get("user_id")
    except Exception:
        raise credentials_exception
   
    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuário não identificado")
   
    # Buscar a interação
    interacao = db.query(models.IncidenciaInteracao).filter(
        models.IncidenciaInteracao.incidencia_interacao_id == interacao_id
    ).first()
   
    if not interacao:
        raise HTTPException(
            status_code=404,
            detail=f"Interação com ID {interacao_id} não encontrada"
        )
   
    # Verificar se o usuário atual é o criador da interação
    if interacao.usuario_id != usuario_id:
        raise HTTPException(
            status_code=403,
            detail="Permissão negada. Apenas o criador da interação pode excluí-la"
        )
   
    # Verificar se é a interação mais recente
    ultima_interacao = db.query(models.IncidenciaInteracao)\
        .filter(models.IncidenciaInteracao.incidencia_id == interacao.incidencia_id)\
        .order_by(models.IncidenciaInteracao.data.desc())\
        .first()
   
    if ultima_interacao.incidencia_interacao_id != interacao_id:
        raise HTTPException(
            status_code=403,
            detail="Apenas a interação mais recente pode ser excluída"
        )
   
    incidencia_id = interacao.incidencia_id
   
    try:
        # Excluir a interação
        db.delete(interacao)
        
        # Buscar a interação anterior (se houver) para atualizar o status da incidência
        interacao_anterior = db.query(models.IncidenciaInteracao)\
            .filter(models.IncidenciaInteracao.incidencia_id == incidencia_id)\
            .order_by(models.IncidenciaInteracao.data.desc())\
            .first()
        
        # Atualizar o status da incidência com base na interação anterior
        incidencia = db.query(models.Incidencia).filter(
            models.Incidencia.incidencia_id == incidencia_id
        ).first()
        
        if interacao_anterior:
            incidencia.status = interacao_anterior.status_id
            status_atual = db.query(models.Status).filter(
                models.Status.status_id == interacao_anterior.status_id
            ).first().nome
        else:
            # Se não houver interações anteriores, definir um status padrão (exemplo: 1 - Novo)
            incidencia.status = 1  # Ajuste conforme necessário
            status_atual = db.query(models.Status).filter(
                models.Status.status_id == 1
            ).first().nome
        
        db.commit()
        
        return {
            "mensagem": "Interação excluída com sucesso",
            "status_atual": status_atual
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao excluir interação: {str(e)}"
        )


# Adiciona as rotas de relatórios
app.include_router(
    relatorios_router,
    prefix="/api/relatorios",
    tags=["relatorios"]
)

from app.routers.dashboard_public import dashboard_public_router

# Inclua o router na aplicação
app.include_router(dashboard_public_router)

# Adicione uma rota para redirecionar o dashboard público para raiz
@app.get("/dashboard-publico", response_class=HTMLResponse)
async def dashboard_publico_redirect(request: Request):
    return templates.TemplateResponse(
        "projetor.html",
        {"request": request}
    )

# Endpoints para configuração de logo do cliente
@app.post("/api/configuracao/upload-logo")
async def upload_logo(
    file: UploadFile = File(...),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    # Verificar autenticação e obter cliente_id
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        nivel = payload.get("nivel")
    except JWTError:
        raise credentials_exception

    # Apenas administradores podem alterar a logo
    if nivel != 1:
        raise HTTPException(status_code=403, detail="Apenas administradores podem alterar a logo")

    # Verificar extensão do arquivo
    extensoes_permitidas = ['.png', '.jpg', '.jpeg', '.gif', '.svg']
    extensao = os.path.splitext(file.filename)[1].lower()
    if extensao not in extensoes_permitidas:
        raise HTTPException(status_code=400, detail="Formato de arquivo não permitido. Use: PNG, JPG, JPEG, GIF ou SVG")

    # Criar nome único para o arquivo
    nome_arquivo = f"logo_cliente_{cliente_id}{extensao}"
    caminho_arquivo = f"static/images/logos/{nome_arquivo}"

    # Criar diretório se não existir
    os.makedirs("static/images/logos", exist_ok=True)

    # Salvar arquivo
    with open(caminho_arquivo, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Atualizar no banco de dados
    cliente = db.query(models.Cliente).filter(models.Cliente.cliente_id == cliente_id).first()
    if cliente:
        cliente.logo = nome_arquivo
        db.commit()

    return {"message": "Logo atualizada com sucesso", "logo": nome_arquivo}

@app.get("/api/configuracao/logo")
async def get_logo(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Verificar autenticação e obter cliente_id
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise credentials_exception

    try:
        # Tenta buscar com as colunas de cor
        result = db.execute(text(
            "SELECT logo, cor_primaria, cor_secundaria FROM cliente WHERE cliente_id = :id"
        ), {"id": cliente_id}).fetchone()

        if result:
            logo = result[0]
            cor_primaria = result[1] if result[1] else '#086218'
            cor_secundaria = result[2] if result[2] else '#001F5B'
            return {
                "logo": f"/static/images/logos/{logo}" if logo else "/static/images/logo.png",
                "cor_primaria": cor_primaria,
                "cor_secundaria": cor_secundaria
            }
    except Exception:
        # Se as colunas não existirem, busca apenas a logo
        result = db.execute(text(
            "SELECT logo FROM cliente WHERE cliente_id = :id"
        ), {"id": cliente_id}).fetchone()

        if result and result[0]:
            return {
                "logo": f"/static/images/logos/{result[0]}",
                "cor_primaria": '#086218',
                "cor_secundaria": '#001F5B'
            }

    return {"logo": "/static/images/logo.png", "cor_primaria": '#086218', "cor_secundaria": '#001F5B'}

@app.get("/api/configuracao/logo-publica/{cliente_id}")
async def get_logo_publica(cliente_id: int, db: Session = Depends(get_db)):
    # Endpoint público para buscar logo e cores na tela de login
    try:
        result = db.execute(text(
            "SELECT logo, cor_primaria, cor_secundaria FROM cliente WHERE cliente_id = :id"
        ), {"id": cliente_id}).fetchone()

        if result:
            logo = result[0]
            cor_primaria = result[1] if result[1] else '#086218'
            cor_secundaria = result[2] if result[2] else '#001F5B'
            return {
                "logo": f"/static/images/logos/{logo}" if logo else "/static/images/logo.png",
                "cor_primaria": cor_primaria,
                "cor_secundaria": cor_secundaria
            }
    except Exception:
        result = db.execute(text(
            "SELECT logo FROM cliente WHERE cliente_id = :id"
        ), {"id": cliente_id}).fetchone()

        if result and result[0]:
            return {
                "logo": f"/static/images/logos/{result[0]}",
                "cor_primaria": '#086218',
                "cor_secundaria": '#001F5B'
            }

    return {"logo": "/static/images/logo.png", "cor_primaria": '#086218', "cor_secundaria": '#001F5B'}

@app.get("/api/configuracao/cliente")
async def get_cliente_dados(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Obter dados do cliente
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise credentials_exception

    try:
        # Tenta buscar com as colunas de cor
        result = db.execute(text(
            """SELECT cliente_id, nome, cnpj, endereco, cidade, estado, logo, cor_primaria, cor_secundaria
               FROM cliente WHERE cliente_id = :id"""
        ), {"id": cliente_id}).fetchone()

        if result:
            return {
                "cliente_id": result[0],
                "nome": result[1],
                "cnpj": result[2],
                "endereco": result[3],
                "cidade": result[4],
                "estado": result[5],
                "logo": result[6],
                "cor_primaria": result[7] or '#086218',
                "cor_secundaria": result[8] or '#001F5B'
            }
    except Exception:
        # Se as colunas não existirem, busca sem elas
        result = db.execute(text(
            "SELECT cliente_id, nome, cnpj, endereco, cidade, estado, logo FROM cliente WHERE cliente_id = :id"
        ), {"id": cliente_id}).fetchone()

        if result:
            return {
                "cliente_id": result[0],
                "nome": result[1],
                "cnpj": result[2],
                "endereco": result[3],
                "cidade": result[4],
                "estado": result[5],
                "logo": result[6],
                "cor_primaria": '#086218',
                "cor_secundaria": '#001F5B'
            }

    raise HTTPException(status_code=404, detail="Cliente não encontrado")

@app.put("/api/configuracao/cliente")
async def update_cliente_dados(
    dados: dict = Body(...),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    # Atualizar dados do cliente
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        nivel = payload.get("nivel")
    except JWTError:
        raise credentials_exception

    if nivel != 1:
        raise HTTPException(status_code=403, detail="Apenas administradores podem alterar dados do cliente")

    cliente = db.query(models.Cliente).filter(models.Cliente.cliente_id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    # Atualizar campos permitidos
    campos_permitidos = ['nome', 'cnpj', 'endereco', 'cidade', 'estado', 'cor_primaria', 'cor_secundaria']
    for campo in campos_permitidos:
        if campo in dados:
            setattr(cliente, campo, dados[campo])

    db.commit()
    return {"message": "Dados do cliente atualizados com sucesso"}

# Endpoints para gerenciar categorias
@app.get("/api/configuracao/categorias")
async def get_todas_categorias(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    categorias = db.query(models.Categoria).order_by(models.Categoria.nome).all()
    return [{"categoria_id": c.categoria_id, "nome": c.nome, "icone": c.icone or "bi-tag", "cor": c.cor or "#6366f1", "ativo": c.ativo} for c in categorias]

# Endpoint alternativo para a pagina de categorias
@app.get("/api/categorias")
async def get_categorias_api(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    categorias = db.query(models.Categoria).order_by(models.Categoria.nome).all()
    return [{"categoria_id": c.categoria_id, "nome": c.nome, "icone": c.icone or "bi-tag", "cor": c.cor or "#6366f1", "ativo": c.ativo} for c in categorias]

@app.post("/api/configuracao/categorias")
async def criar_categoria(
    dados: dict = Body(...),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        nivel = payload.get("nivel")
    except JWTError:
        raise credentials_exception

    if nivel != 1:
        raise HTTPException(status_code=403, detail="Apenas administradores podem criar categorias")

    nova_categoria = models.Categoria(
        nome=dados.get("nome"),
        icone=dados.get("icone", "bi-tag"),
        cor=dados.get("cor", "#6366f1"),
        ativo=1
    )
    db.add(nova_categoria)
    db.commit()
    db.refresh(nova_categoria)

    return {"message": "Categoria criada com sucesso", "categoria_id": nova_categoria.categoria_id}

# Endpoint alternativo para criar categoria
@app.post("/api/categorias")
async def criar_categoria_api(
    dados: dict = Body(...),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        nivel = payload.get("nivel")
    except JWTError:
        raise credentials_exception

    if nivel != 1:
        raise HTTPException(status_code=403, detail="Apenas administradores podem criar categorias")

    nova_categoria = models.Categoria(
        nome=dados.get("nome"),
        icone=dados.get("icone", "bi-tag"),
        cor=dados.get("cor", "#6366f1"),
        ativo=dados.get("ativo", 1)
    )
    db.add(nova_categoria)
    db.commit()
    db.refresh(nova_categoria)

    return {"message": "Categoria criada com sucesso", "categoria_id": nova_categoria.categoria_id}

@app.put("/api/configuracao/categorias/{categoria_id}")
async def atualizar_categoria(
    categoria_id: int,
    dados: dict = Body(...),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        nivel = payload.get("nivel")
    except JWTError:
        raise credentials_exception

    if nivel != 1:
        raise HTTPException(status_code=403, detail="Apenas administradores podem editar categorias")

    categoria = db.query(models.Categoria).filter(models.Categoria.categoria_id == categoria_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria nao encontrada")

    if "nome" in dados:
        categoria.nome = dados["nome"]
    if "icone" in dados:
        categoria.icone = dados["icone"]
    if "cor" in dados:
        categoria.cor = dados["cor"]
    if "ativo" in dados:
        categoria.ativo = dados["ativo"]

    db.commit()
    return {"message": "Categoria atualizada com sucesso"}

# Endpoint alternativo para atualizar categoria
@app.put("/api/categorias/{categoria_id}")
async def atualizar_categoria_api(
    categoria_id: int,
    dados: dict = Body(...),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        nivel = payload.get("nivel")
    except JWTError:
        raise credentials_exception

    if nivel != 1:
        raise HTTPException(status_code=403, detail="Apenas administradores podem editar categorias")

    categoria = db.query(models.Categoria).filter(models.Categoria.categoria_id == categoria_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria nao encontrada")

    if "nome" in dados:
        categoria.nome = dados["nome"]
    if "icone" in dados:
        categoria.icone = dados["icone"]
    if "cor" in dados:
        categoria.cor = dados["cor"]
    if "ativo" in dados:
        categoria.ativo = dados["ativo"]

    db.commit()
    return {"message": "Categoria atualizada com sucesso"}

@app.delete("/api/configuracao/categorias/{categoria_id}")
async def deletar_categoria(
    categoria_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        nivel = payload.get("nivel")
    except JWTError:
        raise credentials_exception

    if nivel != 1:
        raise HTTPException(status_code=403, detail="Apenas administradores podem deletar categorias")

    # Verificar se ha incidencias usando esta categoria
    incidencias = db.query(models.Incidencia).filter(models.Incidencia.categoria_id == categoria_id).count()
    if incidencias > 0:
        raise HTTPException(status_code=400, detail=f"Categoria possui {incidencias} incidencias vinculadas. Desative ao inves de excluir.")

    categoria = db.query(models.Categoria).filter(models.Categoria.categoria_id == categoria_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria nao encontrada")

    db.delete(categoria)
    db.commit()
    return {"message": "Categoria deletada com sucesso"}

# Endpoint alternativo para deletar categoria
@app.delete("/api/categorias/{categoria_id}")
async def deletar_categoria_api(
    categoria_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        nivel = payload.get("nivel")
    except JWTError:
        raise credentials_exception

    if nivel != 1:
        raise HTTPException(status_code=403, detail="Apenas administradores podem deletar categorias")

    # Verificar se ha incidencias usando esta categoria
    incidencias = db.query(models.Incidencia).filter(models.Incidencia.categoria_id == categoria_id).count()
    if incidencias > 0:
        raise HTTPException(status_code=400, detail=f"Categoria possui {incidencias} incidencias vinculadas. Desative ao inves de excluir.")

    categoria = db.query(models.Categoria).filter(models.Categoria.categoria_id == categoria_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria nao encontrada")

    db.delete(categoria)
    db.commit()
    return {"message": "Categoria deletada com sucesso"}

@app.delete("/api/configuracao/logo")
async def delete_logo(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    # Verificar autenticação e obter cliente_id
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        nivel = payload.get("nivel")
    except JWTError:
        raise credentials_exception

    # Apenas administradores podem remover a logo
    if nivel != 1:
        raise HTTPException(status_code=403, detail="Apenas administradores podem remover a logo")

    cliente = db.query(models.Cliente).filter(models.Cliente.cliente_id == cliente_id).first()
    if cliente and cliente.logo:
        # Remover arquivo se existir
        caminho_arquivo = f"static/images/logos/{cliente.logo}"
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)

        # Limpar campo no banco
        cliente.logo = None
        db.commit()

    return {"message": "Logo removida com sucesso"}

# ========== ENDPOINTS DE IA ==========

@app.get("/api/configuracao/ia")
async def get_config_ia(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise credentials_exception

    try:
        result = db.execute(text(
            """SELECT provider, model_name, api_url, api_key, temperature, max_tokens,
               timeout, chat_habilitado, system_prompt, context_window
               FROM config_ai WHERE cliente_id = :id"""
        ), {"id": cliente_id}).fetchone()

        if result:
            return {
                "provider": result[0] or "openai",
                "model_name": result[1] or "gpt-4o",
                "api_url": result[2] or "https://api.openai.com/v1",
                "api_key": result[3] or "",
                "temperature": result[4] if result[4] is not None else 7,
                "max_tokens": result[5] if result[5] is not None else 4096,
                "timeout": result[6] if result[6] is not None else 300,
                "chat_habilitado": bool(result[7]),
                "system_prompt": result[8] or "",
                "context_window": result[9] if result[9] is not None else 128000
            }
    except Exception as e:
        print(f"Erro ao buscar config IA: {e}")

    return {
        "provider": "openai",
        "model_name": "gpt-4o",
        "api_url": "https://api.openai.com/v1",
        "api_key": "",
        "temperature": 7,
        "max_tokens": 4096,
        "context_window": 128000,
        "timeout": 300,
        "chat_habilitado": False,
        "system_prompt": ""
    }

@app.post("/api/configuracao/ia")
async def save_config_ia(
    dados: dict = Body(...),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        nivel = payload.get("nivel")
    except JWTError:
        raise credentials_exception

    if nivel != 1:
        raise HTTPException(status_code=403, detail="Apenas administradores podem configurar IA")

    # Criar tabela se não existir
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS config_ai (
                id SERIAL PRIMARY KEY,
                cliente_id INTEGER NOT NULL,
                provider VARCHAR(50) DEFAULT 'openai',
                model_name VARCHAR(100) DEFAULT 'gpt-4o',
                api_url VARCHAR(255),
                api_key TEXT,
                temperature INTEGER DEFAULT 7,
                max_tokens INTEGER DEFAULT 4096,
                context_window INTEGER DEFAULT 128000,
                timeout INTEGER DEFAULT 300,
                chat_habilitado INTEGER DEFAULT 0,
                system_prompt TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """))
        db.commit()
    except Exception:
        pass

    # Verificar se já existe configuração
    existing = db.execute(text(
        "SELECT id FROM config_ai WHERE cliente_id = :id"
    ), {"id": cliente_id}).fetchone()

    if existing:
        db.execute(text("""
            UPDATE config_ai SET
                provider = :provider,
                model_name = :model_name,
                api_url = :api_url,
                api_key = :api_key,
                temperature = :temperature,
                max_tokens = :max_tokens,
                context_window = :context_window,
                timeout = :timeout,
                chat_habilitado = :chat_habilitado,
                system_prompt = :system_prompt,
                updated_at = CURRENT_TIMESTAMP
            WHERE cliente_id = :cliente_id
        """), {
            "provider": dados.get("provider", "openai"),
            "model_name": dados.get("model_name", "gpt-4o"),
            "api_url": dados.get("api_url", ""),
            "api_key": dados.get("api_key", ""),
            "temperature": dados.get("temperature", 7),
            "max_tokens": dados.get("max_tokens", 4096),
            "context_window": dados.get("context_window", 128000),
            "timeout": dados.get("timeout", 300),
            "chat_habilitado": 1 if dados.get("chat_habilitado") else 0,
            "system_prompt": dados.get("system_prompt", ""),
            "cliente_id": cliente_id
        })
    else:
        db.execute(text("""
            INSERT INTO config_ai (cliente_id, provider, model_name, api_url, api_key, temperature, max_tokens, context_window, timeout, chat_habilitado, system_prompt)
            VALUES (:cliente_id, :provider, :model_name, :api_url, :api_key, :temperature, :max_tokens, :context_window, :timeout, :chat_habilitado, :system_prompt)
        """), {
            "cliente_id": cliente_id,
            "provider": dados.get("provider", "openai"),
            "model_name": dados.get("model_name", "gpt-4o"),
            "api_url": dados.get("api_url", ""),
            "api_key": dados.get("api_key", ""),
            "temperature": dados.get("temperature", 7),
            "max_tokens": dados.get("max_tokens", 4096),
            "context_window": dados.get("context_window", 128000),
            "timeout": dados.get("timeout", 300),
            "chat_habilitado": 1 if dados.get("chat_habilitado") else 0,
            "system_prompt": dados.get("system_prompt", "")
        })

    db.commit()
    return {"message": "Configurações de IA salvas com sucesso"}

@app.post("/api/configuracao/ia/testar")
async def testar_conexao_ia(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise credentials_exception

    config = await get_config_ia(token, db)

    if config["provider"] == "openai":
        try:
            import requests
            response = requests.get(
                f"{config['api_url']}/models",
                headers={"Authorization": f"Bearer {config['api_key']}"},
                timeout=10
            )
            if response.status_code == 200:
                return {"success": True, "message": "Conexão com OpenAI estabelecida"}
            else:
                raise HTTPException(status_code=400, detail="Falha na autenticação com OpenAI")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Erro ao conectar: {str(e)}")
    else:
        return {"success": True, "message": "Teste não disponível para este provedor"}

@app.get("/api/configuracao/ia/chat-status")
async def get_chat_status(db: Session = Depends(get_db)):
    """Endpoint público para verificar se o chat está habilitado"""
    try:
        result = db.execute(text(
            "SELECT chat_habilitado FROM config_ai LIMIT 1"
        )).fetchone()

        if result:
            return {"chat_habilitado": bool(result[0])}
        # Se nao houver configuracao, retorna True para mostrar o botao
        return {"chat_habilitado": True}
    except Exception as e:
        print(f"[chat-status] Erro: {e}")
        # Em caso de erro, retorna True para permitir teste
        return {"chat_habilitado": True}

@app.post("/api/assistente-ia/chat")
async def assistente_ia_chat(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Endpoint para processar mensagens do assistente IA"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception

    dados = await request.json()
    mensagem = dados.get("message", "")

    if not mensagem:
        return {"message": "Por favor, digite uma mensagem."}

    # Buscar configuração de IA do cliente
    try:
        config = db.execute(text(
            "SELECT api_key, model_name, system_prompt, temperature, max_tokens FROM config_ai WHERE cliente_id = :id"
        ), {"id": cliente_id}).fetchone()

        if config and config[0]:
            # Usar API configurada
            api_key = config[0]
            modelo = config[1] or "gpt-4o"
            system_prompt_custom = config[2] or ""
            temperatura = (config[3] or 7) / 10  # Converter para 0.0 - 1.0
            max_tokens = config[4] or 4096

            # Contexto do sistema
            schema_info = gerar_schema_info(models.Base)

            # Usar system_prompt personalizado ou padrão
            if system_prompt_custom:
                prompt_sistema = f"""{system_prompt_custom}

Estrutura do banco de dados (para consultas SQL): {schema_info}"""
            else:
                prompt_sistema = f"""Você é um assistente inteligente do sistema Gestão Interativa.
O sistema gerencia incidências urbanas (buracos, iluminação, lixo, etc).
Responda de forma clara e objetiva em português brasileiro.
Você pode consultar dados usando SQL se necessário.

Estrutura do banco: {schema_info}"""

            response = openai.ChatCompletion.create(
                model=modelo,
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": mensagem}
                ],
                api_key=api_key,
                max_tokens=min(max_tokens, 4000),
                temperature=temperatura
            )

            resposta = response.choices[0].message['content'].strip()
            return {"message": resposta}
        else:
            # Sem API configurada - respostas básicas
            return {"message": "O assistente IA não está configurado. Configure a API na tela de Configuração > Inteligência Artificial."}

    except Exception as e:
        print(f"Erro no assistente IA: {e}")
        return {"message": f"Desculpe, ocorreu um erro ao processar sua pergunta. Verifique as configurações de IA."}


if __name__ == "__main__":
   import uvicorn
   uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


