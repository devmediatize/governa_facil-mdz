from fastapi.openapi.utils import get_openapi
from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Request, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
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
import httpx  # Para chamadas HTTP async (IA Vision)

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


async def enviar_email_alerta(destinatario: str, nome_usuario: str, alertas: list, cliente_nome: str = "Gestao Interativa"):
    """
    Envia email de alerta para o usuario com os alertas consolidados.

    Args:
        destinatario: Email do destinatario
        nome_usuario: Nome do usuario para personalizacao
        alertas: Lista de alertas a serem enviados
        cliente_nome: Nome do cliente para o cabecalho do email

    Returns:
        dict: Resultado do envio com status e mensagem
    """
    try:
        # Verificar se ha alertas para enviar
        if not alertas:
            return {"success": False, "message": "Nenhum alerta para enviar"}

        # Montar HTML do email
        alertas_html = ""
        for alerta in alertas:
            # Definir cor baseada na severidade
            if alerta.get('severidade') == 'critico':
                cor_badge = '#dc3545'
                cor_borda = '#dc3545'
                icone = '&#9888;'  # Warning triangle
            elif alerta.get('severidade') == 'atencao':
                cor_badge = '#ffc107'
                cor_borda = '#ffc107'
                icone = '&#9888;'
            else:
                cor_badge = '#17a2b8'
                cor_borda = '#17a2b8'
                icone = '&#8505;'  # Info

            alertas_html += f"""
            <div style="border-left: 4px solid {cor_borda}; padding: 15px; margin-bottom: 15px; background-color: #f8f9fa; border-radius: 0 8px 8px 0;">
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <span style="background-color: {cor_badge}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; text-transform: uppercase;">
                        {icone} {alerta.get('severidade', 'info').upper()}
                    </span>
                    <span style="margin-left: 10px; color: #6c757d; font-size: 12px;">
                        {alerta.get('tipo', '').upper()} - {alerta.get('referencia', '')}
                    </span>
                </div>
                <p style="margin: 0; color: #333; font-size: 14px; line-height: 1.5;">
                    {alerta.get('mensagem', '')}
                </p>
                <div style="margin-top: 10px; font-size: 12px; color: #6c757d;">
                    <span style="margin-right: 15px;"><strong>Valor:</strong> {alerta.get('valor', 0)}</span>
                    <span><strong>Comparativo:</strong> {alerta.get('comparativo', '-')}</span>
                </div>
            </div>
            """

        # Template HTML completo do email
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
                <tr>
                    <td align="center">
                        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                            <!-- Header -->
                            <tr>
                                <td style="background: linear-gradient(135deg, #0F58AD 0%, #0092A6 100%); padding: 30px; text-align: center;">
                                    <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 600;">
                                        {cliente_nome}
                                    </h1>
                                    <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 14px;">
                                        Sistema de Gestao de Incidencias
                                    </p>
                                </td>
                            </tr>

                            <!-- Greeting -->
                            <tr>
                                <td style="padding: 30px 30px 15px 30px;">
                                    <h2 style="color: #333; margin: 0 0 10px 0; font-size: 20px;">
                                        Ola, {nome_usuario}!
                                    </h2>
                                    <p style="color: #666; margin: 0; font-size: 14px; line-height: 1.6;">
                                        Voce possui <strong style="color: #0F58AD;">{len(alertas)} alerta(s)</strong> que requerem sua atencao.
                                        Confira os detalhes abaixo:
                                    </p>
                                </td>
                            </tr>

                            <!-- Alerts Section -->
                            <tr>
                                <td style="padding: 15px 30px 30px 30px;">
                                    <h3 style="color: #333; margin: 0 0 20px 0; font-size: 16px; border-bottom: 2px solid #0F58AD; padding-bottom: 10px;">
                                        Alertas do Sistema
                                    </h3>
                                    {alertas_html}
                                </td>
                            </tr>

                            <!-- CTA Button -->
                            <tr>
                                <td style="padding: 0 30px 30px 30px; text-align: center;">
                                    <a href="#" style="display: inline-block; background: linear-gradient(135deg, #0F58AD 0%, #0092A6 100%); color: #ffffff; text-decoration: none; padding: 15px 40px; border-radius: 30px; font-weight: 600; font-size: 14px; box-shadow: 0 4px 15px rgba(15, 88, 173, 0.3);">
                                        Acessar o Sistema
                                    </a>
                                </td>
                            </tr>

                            <!-- Footer -->
                            <tr>
                                <td style="background-color: #f8f9fa; padding: 20px 30px; border-top: 1px solid #e9ecef;">
                                    <p style="color: #6c757d; margin: 0; font-size: 12px; text-align: center; line-height: 1.6;">
                                        Este email foi enviado automaticamente pelo sistema {cliente_nome}.<br>
                                        Voce esta recebendo este email porque esta configurado para receber alertas.
                                    </p>
                                </td>
                            </tr>
                        </table>

                        <!-- Copyright -->
                        <p style="color: #999; font-size: 11px; margin-top: 20px; text-align: center;">
                            &copy; {datetime.now().year} {cliente_nome}. Todos os direitos reservados.
                        </p>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

        # Configurar email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[{cliente_nome}] Voce tem {len(alertas)} alerta(s) pendente(s)"
        msg['From'] = EMAIL_CONTA
        msg['To'] = destinatario

        # Adicionar conteudo HTML
        parte_html = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(parte_html)

        # Enviar email
        with smtplib.SMTP(EMAIL_SMTP, int(EMAIL_PORTA)) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_SENHA)
            server.sendmail(EMAIL_CONTA, destinatario, msg.as_string())

        return {"success": True, "message": f"Email enviado com sucesso para {destinatario}"}

    except smtplib.SMTPAuthenticationError:
        return {"success": False, "message": "Erro de autenticacao SMTP"}
    except smtplib.SMTPException as e:
        return {"success": False, "message": f"Erro SMTP: {str(e)}"}
    except Exception as e:
        return {"success": False, "message": f"Erro ao enviar email: {str(e)}"}


app = FastAPI(
    title="Gestão Interativa API",
    description="API para o sistema de Gestão Interativa",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ============================================
# ENDPOINT HEALTH CHECK
# ============================================
@app.get("/api/health")
async def health_check():
    """
    Endpoint de health check para verificar se a API está online.
    Usado pelo app Flutter para verificar conectividade.
    """
    return {"status": "ok", "message": "API funcionando"}

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
            "/api/configuracao/ia/chat-status",  # Status do chat IA
            "/api/alertas/enviar-emails",  # Endpoint para cron job de envio de emails
            "/api/health"  # Health check para conectividade do app
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
    template_routes = ["/", "/dashboard", "/incidencias", "/incidencia", "/mapa", "/usuarios", "/categorias", "/status", "/relatorios", "/estatisticas", "/configuracao", "/cidadaos", "/ranking", "/feedbacks", "/alertas"]

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

@app.get("/alertas", response_class=HTMLResponse)
async def alertas_page(request: Request):
    """Pagina de visualizacao de todos os alertas do sistema."""
    return templates.TemplateResponse("alertas.html", {"request": request})

@app.get("/incidencias", response_class=HTMLResponse)
async def incidencias(request: Request):
    return templates.TemplateResponse("incidencias.html", {"request": request})

@app.get("/incidencias/{id}", response_class=HTMLResponse)
async def read_incidencia(request: Request, id: int):
    return templates.TemplateResponse(
        "incidencias.html",
        {"request": request, "id": id}  # Inclui o id no contexto do template
    )

@app.get("/incidencia/{incidencia_id}/detalhe", response_class=HTMLResponse)
async def pagina_incidencia_detalhe(request: Request, incidencia_id: int):
    """
    Pagina de detalhe da incidencia com timeline visual.
    Renderiza o template com o ID da incidencia para carregar dados via API.
    """
    return templates.TemplateResponse(
        "incidencia_detalhe.html",
        {"request": request, "incidencia_id": incidencia_id}
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

@app.get("/estatisticas", response_class=HTMLResponse)
async def estatisticas(request: Request):
    """
    Pagina de Estatisticas Publicas do sistema.
    Exibe graficos e metricas de incidencias.
    """
    return templates.TemplateResponse("estatisticas.html", {"request": request})

@app.get("/feedbacks", response_class=HTMLResponse)
async def feedbacks_page(request: Request):
    return templates.TemplateResponse("feedbacks.html", {"request": request})

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

# ========== ENDPOINTS DE LOGIN PARA CIDADAOS (APP) ==========

@app.post("/api/cidadao/login")
async def login_cidadao(
    request: Request,
    db: Session = Depends(get_db)
):
    """Login para cidadãos do app mobile"""
    dados = await request.json()
    email = dados.get("email", "").strip().lower()
    senha = dados.get("senha", "")

    if not email or not senha:
        raise HTTPException(status_code=400, detail="Email e senha são obrigatórios")

    # Buscar cidadão pelo email
    cidadao = db.query(models.Cidadao).filter(models.Cidadao.email == email).first()

    if not cidadao:
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    # Verificar senha com bcrypt
    if not verify_password(senha, cidadao.senha):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    # Gerar token JWT (cliente_id fixo por enquanto - cidadãos não tem cliente vinculado)
    cliente_id_padrao = 3
    access_token = create_access_token(
        data={
            "sub": cidadao.email,
            "cidadao_id": cidadao.cidadao_id,
            "cliente_id": cliente_id_padrao,
            "nome": cidadao.nome,
            "tipo": "cidadao"
        }
    )

    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "cidadao_id": cidadao.cidadao_id,
        "nome": cidadao.nome,
        "email": cidadao.email,
        "cliente_id": cliente_id_padrao,
        "celular": cidadao.celular or "",
        "cidade": cidadao.cidade or "",
        "estado": cidadao.estado or "",
        "foto": ""
    }

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
        cliente_id=cliente_id,
        cargo=user.cargo,
        lotacao=user.lotacao
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
            "nivel": u.nivel,
            "cargo": u.cargo,
            "lotacao": u.lotacao,
            "foto": u.foto
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
    bairro: Optional[str] = None,
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

    if bairro:
        query = query.filter(models.Incidencia.bairro.ilike(f"%{bairro}%"))

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

# Endpoints para criar e atualizar incidencias (usados pelo formulario)
@app.post("/incidencias/")
async def criar_incidencia(
    dados: dict = Body(...),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Cria uma nova incidencia"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception

    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuario nao identificado")

    # Criar a nova incidencia
    nova_incidencia = models.Incidencia(
        categoria_id=dados.get('categoria_id'),
        cidadao_id=1,  # Valor padrao - pode ser ajustado conforme necessidade
        descricao=dados.get('descricao'),
        prioridade=dados.get('prioridade'),
        endereco=dados.get('endereco'),
        bairro=dados.get('bairro'),
        cidade=dados.get('cidade'),
        estado=dados.get('estado'),
        cep=dados.get('cep'),
        lat=dados.get('lat'),
        long=dados.get('long'),
        foto=dados.get('foto'),
        status=1,  # Status inicial: Novo
        cliente_id=cliente_id
    )

    db.add(nova_incidencia)
    db.commit()
    db.refresh(nova_incidencia)

    return {"message": "Incidencia criada com sucesso", "incidencia_id": nova_incidencia.incidencia_id}

@app.put("/incidencias/{incidencia_id}")
async def atualizar_incidencia(
    incidencia_id: int,
    dados: dict = Body(...),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Atualiza uma incidencia existente"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception

    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuario nao identificado")

    # Buscar a incidencia
    incidencia = db.query(models.Incidencia).filter(
        models.Incidencia.incidencia_id == incidencia_id,
        models.Incidencia.cliente_id == cliente_id
    ).first()

    if not incidencia:
        raise HTTPException(status_code=404, detail="Incidencia nao encontrada")

    # Atualizar os campos
    if 'categoria_id' in dados:
        incidencia.categoria_id = dados['categoria_id']
    if 'descricao' in dados:
        incidencia.descricao = dados['descricao']
    if 'prioridade' in dados:
        incidencia.prioridade = dados['prioridade']
    if 'endereco' in dados:
        incidencia.endereco = dados['endereco']
    if 'bairro' in dados:
        incidencia.bairro = dados['bairro']
    if 'cidade' in dados:
        incidencia.cidade = dados['cidade']
    if 'estado' in dados:
        incidencia.estado = dados['estado']
    if 'cep' in dados:
        incidencia.cep = dados['cep']
    if 'lat' in dados:
        incidencia.lat = dados['lat']
    if 'long' in dados:
        incidencia.long = dados['long']
    if 'foto' in dados and dados['foto']:
        incidencia.foto = dados['foto']

    db.commit()
    db.refresh(incidencia)

    return {"message": "Incidencia atualizada com sucesso", "incidencia_id": incidencia.incidencia_id}


# ============================================
# ENDPOINT DE BUSCA AVANCADA DE INCIDENCIAS (APP FLUTTER)
# ============================================
@app.get("/api/incidencias/busca")
async def buscar_incidencias(
    q: Optional[str] = None,  # texto livre (busca em descricao e endereco)
    categoria_id: Optional[int] = None,
    bairro: Optional[str] = None,
    status: Optional[int] = None,
    data_inicio: Optional[str] = None,  # formato: YYYY-MM-DD
    data_fim: Optional[str] = None,  # formato: YYYY-MM-DD
    ordenar: Optional[str] = "recentes",  # recentes, antigas, prioridade
    pagina: Optional[int] = 1,
    limite: Optional[int] = 20,
    cidadao_id: Optional[int] = None,  # filtrar por cidadao especifico
    db: Session = Depends(get_db)
):
    """
    Endpoint de busca avancada de incidencias para o app Flutter.
    Permite busca por texto, filtros por categoria, bairro, status e periodo.
    Retorna resultados paginados com informacoes completas.
    """
    try:
        # Query base com joins para obter nomes
        query = db.query(
            models.Incidencia,
            models.Categoria.nome.label('categoria_nome'),
            models.Categoria.icone.label('categoria_icone'),
            models.Categoria.cor.label('categoria_cor'),
            models.Status.nome.label('status_nome')
        ).join(
            models.Categoria,
            models.Incidencia.categoria_id == models.Categoria.categoria_id
        ).join(
            models.Status,
            models.Incidencia.status == models.Status.status_id
        )

        # Filtro por texto (busca em descricao, endereco e bairro)
        if q and q.strip():
            texto_busca = q.strip()
            query = query.filter(or_(
                models.Incidencia.descricao.ilike(f"%{texto_busca}%"),
                models.Incidencia.endereco.ilike(f"%{texto_busca}%"),
                models.Incidencia.bairro.ilike(f"%{texto_busca}%"),
                models.Incidencia.cidade.ilike(f"%{texto_busca}%")
            ))

        # Filtro por categoria
        if categoria_id:
            query = query.filter(models.Incidencia.categoria_id == categoria_id)

        # Filtro por bairro
        if bairro and bairro.strip():
            query = query.filter(models.Incidencia.bairro.ilike(f"%{bairro.strip()}%"))

        # Filtro por status
        if status:
            query = query.filter(models.Incidencia.status == status)

        # Filtro por cidadao
        if cidadao_id:
            query = query.filter(models.Incidencia.cidadao_id == cidadao_id)

        # Filtro por periodo
        if data_inicio:
            try:
                dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
                query = query.filter(cast(models.Incidencia.data_hora, Date) >= dt_inicio)
            except ValueError:
                pass  # Ignora data invalida

        if data_fim:
            try:
                dt_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
                query = query.filter(cast(models.Incidencia.data_hora, Date) <= dt_fim)
            except ValueError:
                pass  # Ignora data invalida

        # Ordenacao
        if ordenar == "antigas":
            query = query.order_by(models.Incidencia.data_hora.asc())
        elif ordenar == "prioridade":
            query = query.order_by(models.Incidencia.prioridade.desc(), models.Incidencia.data_hora.desc())
        else:  # recentes (padrao)
            query = query.order_by(models.Incidencia.data_hora.desc())

        # Contar total antes da paginacao
        total = query.count()

        # Paginacao
        offset = (pagina - 1) * limite
        query = query.offset(offset).limit(limite)

        # Executar query
        resultados = query.all()

        # Formatar resposta
        incidencias = []
        for row in resultados:
            incidencia = row[0]
            incidencias.append({
                "incidencia_id": incidencia.incidencia_id,
                "categoria_id": incidencia.categoria_id,
                "categoria_nome": row.categoria_nome,
                "categoria_icone": row.categoria_icone,
                "categoria_cor": row.categoria_cor,
                "cidadao_id": incidencia.cidadao_id,
                "descricao": incidencia.descricao,
                "endereco": incidencia.endereco,
                "bairro": incidencia.bairro,
                "cidade": incidencia.cidade,
                "estado": incidencia.estado,
                "cep": incidencia.cep,
                "lat": incidencia.lat,
                "long": incidencia.long,
                "foto": incidencia.foto,
                "status": incidencia.status,
                "status_nome": row.status_nome,
                "prioridade": incidencia.prioridade,
                "data_hora": incidencia.data_hora.isoformat() if incidencia.data_hora else None,
                "data_ultimo_status": incidencia.data_ultimo_status.isoformat() if incidencia.data_ultimo_status else None,
                "cliente_id": incidencia.cliente_id
            })

        return {
            "success": True,
            "total": total,
            "pagina": pagina,
            "limite": limite,
            "total_paginas": (total + limite - 1) // limite,
            "incidencias": incidencias
        }

    except Exception as e:
        print(f"Erro na busca de incidencias: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar incidencias: {str(e)}")


# Endpoint para listar bairros disponiveis (para autocomplete)
@app.get("/api/bairros")
async def listar_bairros(
    q: Optional[str] = None,
    limite: Optional[int] = 20,
    db: Session = Depends(get_db)
):
    """
    Lista bairros distintos das incidencias para autocomplete.
    """
    try:
        query = db.query(models.Incidencia.bairro).distinct()

        if q and q.strip():
            query = query.filter(models.Incidencia.bairro.ilike(f"%{q.strip()}%"))

        query = query.filter(models.Incidencia.bairro.isnot(None))
        query = query.filter(models.Incidencia.bairro != '')
        query = query.order_by(models.Incidencia.bairro)
        query = query.limit(limite)

        resultados = query.all()
        bairros = [r[0] for r in resultados if r[0]]

        return {"bairros": bairros}

    except Exception as e:
        print(f"Erro ao listar bairros: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar bairros: {str(e)}")


@app.delete("/incidencias/{incidencia_id}")
async def excluir_incidencia(
    incidencia_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Exclui uma incidencia"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception

    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuario nao identificado")

    # Buscar a incidencia
    incidencia = db.query(models.Incidencia).filter(
        models.Incidencia.incidencia_id == incidencia_id,
        models.Incidencia.cliente_id == cliente_id
    ).first()

    if not incidencia:
        raise HTTPException(status_code=404, detail="Incidencia nao encontrada")

    db.delete(incidencia)
    db.commit()

    return {"message": "Incidencia excluida com sucesso"}

@app.on_event("startup")
async def startup_event():
    templates_path = "templates"
    # Criar colunas de cor automaticamente se não existirem
    try:
        with database.engine.connect() as conn:
            conn.execute(text("ALTER TABLE cliente ADD COLUMN IF NOT EXISTS cor_primaria VARCHAR(7) DEFAULT '#086218'"))
            conn.execute(text("ALTER TABLE cliente ADD COLUMN IF NOT EXISTS cor_secundaria VARCHAR(7) DEFAULT '#001F5B'"))
            conn.execute(text("ALTER TABLE cliente ADD COLUMN IF NOT EXISTS imagem_fundo VARCHAR(500)"))
            conn.commit()
            print("Colunas de cor e imagem_fundo verificadas/criadas com sucesso!")
    except Exception as e:
        print(f"Aviso ao verificar colunas de cor/imagem_fundo: {e}")

    # Criar colunas de IA (system_prompt, context_window, embedding) se não existirem
    try:
        with database.engine.connect() as conn:
            conn.execute(text("ALTER TABLE config_ai ADD COLUMN IF NOT EXISTS system_prompt TEXT"))
            conn.execute(text("ALTER TABLE config_ai ADD COLUMN IF NOT EXISTS context_window INTEGER DEFAULT 128000"))
            conn.execute(text("ALTER TABLE config_ai ADD COLUMN IF NOT EXISTS retry_attempts INTEGER DEFAULT 3"))
            conn.execute(text("ALTER TABLE config_ai ADD COLUMN IF NOT EXISTS embedding_provider VARCHAR(50) DEFAULT 'openai'"))
            conn.execute(text("ALTER TABLE config_ai ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(100) DEFAULT 'text-embedding-3-small'"))
            conn.execute(text("ALTER TABLE config_ai ADD COLUMN IF NOT EXISTS embedding_api_url VARCHAR(255)"))
            conn.execute(text("ALTER TABLE config_ai ADD COLUMN IF NOT EXISTS embedding_api_key TEXT"))
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

    # Criar coluna cep na tabela incidencia se não existir
    try:
        with database.engine.connect() as conn:
            conn.execute(text("ALTER TABLE incidencia ADD COLUMN IF NOT EXISTS cep VARCHAR(10)"))
            conn.commit()
            print("Coluna cep da incidencia verificada/criada com sucesso!")
    except Exception as e:
        print(f"Aviso ao verificar coluna cep da incidencia: {e}")

    # Criar coluna codigo_acompanhamento para incidencias anonimas
    try:
        with database.engine.connect() as conn:
            conn.execute(text("ALTER TABLE incidencia ADD COLUMN IF NOT EXISTS codigo_acompanhamento VARCHAR(20)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_codigo_acompanhamento ON incidencia(codigo_acompanhamento) WHERE codigo_acompanhamento IS NOT NULL"))
            # Tornar cidadao_id nullable para incidencias anonimas
            conn.execute(text("ALTER TABLE incidencia ALTER COLUMN cidadao_id DROP NOT NULL"))
            conn.commit()
            print("Coluna codigo_acompanhamento e indice para incidencias anonimas criados com sucesso!")
    except Exception as e:
        print(f"Aviso ao verificar coluna codigo_acompanhamento: {e}")

    # Criar coluna foto na tabela cidadao se não existir
    try:
        with database.engine.connect() as conn:
            conn.execute(text("ALTER TABLE cidadao ADD COLUMN IF NOT EXISTS foto VARCHAR(500)"))
            conn.commit()
            print("Coluna foto do cidadao verificada/criada com sucesso!")
    except Exception as e:
        print(f"Aviso ao verificar coluna foto do cidadao: {e}")

    # Criar coluna permitir_anonimo na tabela cliente se nao existir
    try:
        with database.engine.connect() as conn:
            conn.execute(text("ALTER TABLE cliente ADD COLUMN IF NOT EXISTS permitir_anonimo INTEGER DEFAULT 0"))
            conn.commit()
            print("Coluna permitir_anonimo do cliente verificada/criada com sucesso!")
    except Exception as e:
        print(f"Aviso ao verificar coluna permitir_anonimo: {e}")

    # Criar tabela de feedback de incidencias se nao existir
    try:
        with database.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS feedback_incidencia (
                    feedback_id SERIAL PRIMARY KEY,
                    incidencia_id INTEGER NOT NULL REFERENCES incidencia(incidencia_id),
                    cidadao_id INTEGER NOT NULL REFERENCES cidadao(cidadao_id),
                    avaliacao INTEGER NOT NULL CHECK (avaliacao >= 1 AND avaliacao <= 5),
                    comentario TEXT,
                    foto_confirmacao VARCHAR(500),
                    resolvido INTEGER NOT NULL DEFAULT 1,
                    data_feedback TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            print("Tabela feedback_incidencia verificada/criada com sucesso!")
    except Exception as e:
        print(f"Aviso ao verificar tabela feedback_incidencia: {e}")

    # Criar tabela de device tokens para push notifications se nao existir
    try:
        with database.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS device_token (
                    id SERIAL PRIMARY KEY,
                    cidadao_id INTEGER NOT NULL REFERENCES cidadao(cidadao_id),
                    token VARCHAR(500) NOT NULL UNIQUE,
                    platform VARCHAR(20) NOT NULL DEFAULT 'android',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            print("Tabela device_token verificada/criada com sucesso!")
    except Exception as e:
        print(f"Aviso ao verificar tabela device_token: {e}")

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
    # IMPORTANTE: Filtrar por cliente_id E categorias_ids - cada query separada
    total = db.query(models.Incidencia).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.categoria_id.in_(categorias_ids)
    ).count()

    resolvidos = db.query(models.Incidencia).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.categoria_id.in_(categorias_ids),
        models.Incidencia.status == 3
    ).count()

    em_andamento = db.query(models.Incidencia).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.categoria_id.in_(categorias_ids),
        models.Incidencia.status == 2
    ).count()

    novos = db.query(models.Incidencia).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.categoria_id.in_(categorias_ids),
        models.Incidencia.status == 1
    ).count()

   
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

@app.get("/api/incidencias/bairros")
async def get_bairros(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Lista todos os bairros distintos das incidencias"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise credentials_exception

    bairros = db.query(models.Incidencia.bairro).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.bairro.isnot(None),
        models.Incidencia.bairro != ""
    ).distinct().order_by(models.Incidencia.bairro).all()

    return [b[0] for b in bairros if b[0]]

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

    results = db.query(models.Categoria)

    # Se tem categorias vinculadas, filtra por elas; senão mostra todas
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
        models.Categoria.icone.label('categoria_icone'),
        models.Categoria.cor.label('categoria_cor'),
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
                "categoria_icone": r.categoria_icone or "bi-tag",
                "categoria_cor": r.categoria_cor or "#6366f1",
                "prioridade": r.prioridade_nome
            })

    # Calcular centro do mapa
    if lats and lngs:
        centro = {"lat": sum(lats) / len(lats), "lng": sum(lngs) / len(lngs)}
    else:
        # Buscar cidade do cliente para usar como centro padrão
        cliente = db.query(models.Cliente).filter(models.Cliente.cliente_id == cliente_id).first()
        if cliente and cliente.cidade:
            # Coordenadas de cidades brasileiras comuns
            cidades_coords = {
                "cuiaba": {"lat": -15.5989, "lng": -56.0949},
                "cuiabá": {"lat": -15.5989, "lng": -56.0949},
                "brasilia": {"lat": -15.7942, "lng": -47.8822},
                "brasília": {"lat": -15.7942, "lng": -47.8822},
                "sao paulo": {"lat": -23.5505, "lng": -46.6333},
                "são paulo": {"lat": -23.5505, "lng": -46.6333},
                "rio de janeiro": {"lat": -22.9068, "lng": -43.1729},
                "belo horizonte": {"lat": -19.9167, "lng": -43.9345},
                "salvador": {"lat": -12.9714, "lng": -38.5014},
                "fortaleza": {"lat": -3.7172, "lng": -38.5433},
                "recife": {"lat": -8.0476, "lng": -34.8770},
                "porto alegre": {"lat": -30.0346, "lng": -51.2177},
                "manaus": {"lat": -3.1190, "lng": -60.0217},
                "goiania": {"lat": -16.6869, "lng": -49.2648},
                "goiânia": {"lat": -16.6869, "lng": -49.2648},
                "varzea grande": {"lat": -15.6458, "lng": -56.1325},
                "várzea grande": {"lat": -15.6458, "lng": -56.1325},
                "sinop": {"lat": -11.8642, "lng": -55.5093},
                "rondonopolis": {"lat": -16.4673, "lng": -54.6372},
                "rondonópolis": {"lat": -16.4673, "lng": -54.6372},
                "tangara da serra": {"lat": -14.6229, "lng": -57.4978},
                "tangará da serra": {"lat": -14.6229, "lng": -57.4978},
                "caceres": {"lat": -16.0706, "lng": -57.6833},
                "cáceres": {"lat": -16.0706, "lng": -57.6833},
            }
            cidade_lower = cliente.cidade.lower().strip()
            centro = cidades_coords.get(cidade_lower, {"lat": -15.5989, "lng": -56.0949})  # Default: Cuiabá
        else:
            centro = {"lat": -15.5989, "lng": -56.0949}  # Cuiabá como padrão para MT

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

    # Query base
    query = db.query(
        models.Categoria.nome.label('categoria'),
        func.count(models.Incidencia.incidencia_id).label('total')
    ).join(
        models.Incidencia,
        models.Categoria.categoria_id == models.Incidencia.categoria_id
    ).filter(
        models.Incidencia.cliente_id == cliente_id
    )

    # Se tem categorias vinculadas, filtra por elas
    if categorias_ids:
        query = query.filter(models.Incidencia.categoria_id.in_(categorias_ids))

    result = query.group_by(models.Categoria.nome).order_by(func.count(models.Incidencia.incidencia_id).desc()).all()

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
    maior_crescimento = -999
    categoria_em_alta = "N/A"
    categoria_em_alta_crescimento = 0
    maior_total = 0

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

        # Se não houver crescimento, pegar a com mais incidências
        if cat.total > maior_total:
            maior_total = cat.total
            if maior_crescimento <= 0:
                categoria_em_alta = cat.nome
                categoria_em_alta_crescimento = 0

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


# Endpoint: Ranking de Bairros
@app.get("/api/dashboard/ranking-bairros")
async def get_ranking_bairros(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Retorna os 10 bairros com mais incidências.
    Inclui: nome do bairro, total de incidências, percentual do total.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception

    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuário não identificado")

    try:
        # Categorias permitidas para o usuário
        categorias_permitidas = db.query(
            models.UsuarioCategoria.categoria_id
        ).filter(
            models.UsuarioCategoria.usuario_id == usuario_id
        ).all()
        categorias_ids = [cat[0] for cat in categorias_permitidas]

        # Se o usuário não tem categorias permitidas, retornar vazio
        if not categorias_ids:
            return {"ranking": [], "total_geral": 0}

        # Total geral de incidências (filtro por cliente_id E categorias_ids)
        total_geral = db.query(func.count(models.Incidencia.incidencia_id)).filter(
            models.Incidencia.cliente_id == cliente_id,
            models.Incidencia.categoria_id.in_(categorias_ids),
            models.Incidencia.bairro.isnot(None)
        ).scalar() or 0

        if total_geral == 0:
            return {"ranking": [], "total_geral": 0}

        # Ranking dos 10 bairros com mais incidências
        ranking_query = db.query(
            models.Incidencia.bairro,
            func.count(models.Incidencia.incidencia_id).label('total')
        ).filter(
            models.Incidencia.cliente_id == cliente_id,
            models.Incidencia.categoria_id.in_(categorias_ids),
            models.Incidencia.bairro.isnot(None)
        )

        ranking_query = ranking_query.group_by(
            models.Incidencia.bairro
        ).order_by(
            func.count(models.Incidencia.incidencia_id).desc()
        ).limit(10).all()

        ranking = []
        for item in ranking_query:
            percentual = round((item.total / total_geral) * 100, 1) if total_geral > 0 else 0
            ranking.append({
                "bairro": item.bairro,
                "total": item.total,
                "percentual": percentual
            })

        return {
            "ranking": ranking,
            "total_geral": total_geral
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar ranking de bairros: {str(e)}")


# Endpoint: Evolução Temporal
@app.get("/api/dashboard/evolucao-temporal")
async def get_evolucao_temporal(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Retorna incidências agrupadas por dia nos últimos 30 dias.
    Formato: [{data: "2024-01-15", total: 5}, ...]
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception

    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuário não identificado")

    try:
        # Categorias permitidas para o usuário
        categorias_permitidas = db.query(
            models.UsuarioCategoria.categoria_id
        ).filter(
            models.UsuarioCategoria.usuario_id == usuario_id
        ).all()
        categorias_ids = [cat[0] for cat in categorias_permitidas]

        if not categorias_ids:
            return {"evolucao": [], "periodo": {"inicio": None, "fim": None}}

        from datetime import date, timedelta
        hoje = date.today()
        inicio_periodo = hoje - timedelta(days=30)

        # Buscar incidências agrupadas por dia
        evolucao_query = db.query(
            cast(models.Incidencia.data_hora, Date).label('data'),
            func.count(models.Incidencia.incidencia_id).label('total')
        ).filter(
            models.Incidencia.cliente_id == cliente_id,
            models.Incidencia.categoria_id.in_(categorias_ids),
            cast(models.Incidencia.data_hora, Date) >= inicio_periodo,
            cast(models.Incidencia.data_hora, Date) <= hoje
        ).group_by(
            cast(models.Incidencia.data_hora, Date)
        ).order_by(
            cast(models.Incidencia.data_hora, Date)
        ).all()

        # Criar dicionário com os resultados
        resultados_dict = {str(item.data): item.total for item in evolucao_query}

        # Preencher todos os dias do período (incluindo dias sem incidências)
        evolucao = []
        data_atual = inicio_periodo
        while data_atual <= hoje:
            data_str = str(data_atual)
            evolucao.append({
                "data": data_str,
                "total": resultados_dict.get(data_str, 0)
            })
            data_atual += timedelta(days=1)

        return {
            "evolucao": evolucao,
            "periodo": {
                "inicio": str(inicio_periodo),
                "fim": str(hoje)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar evolução temporal: {str(e)}")


# Endpoint: Alertas Automáticos
@app.get("/api/dashboard/alertas")
async def get_alertas(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Retorna alertas automáticos:
    - Bairros com 3x mais incidências que a média
    - Categorias com aumento significativo na última semana
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception

    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuário não identificado")

    try:
        # Categorias permitidas para o usuário
        categorias_permitidas = db.query(
            models.UsuarioCategoria.categoria_id
        ).filter(
            models.UsuarioCategoria.usuario_id == usuario_id
        ).all()
        categorias_ids = [cat[0] for cat in categorias_permitidas]

        if not categorias_ids:
            return {"alertas_bairros": [], "alertas_categorias": [], "total_alertas": 0}

        from datetime import date, timedelta
        hoje = date.today()
        inicio_semana_atual = hoje - timedelta(days=7)
        inicio_semana_anterior = hoje - timedelta(days=14)

        alertas_bairros = []
        alertas_categorias = []

        # 1. ALERTAS DE BAIRROS - Bairros com 3x mais incidências que a média
        # Calcular incidências por bairro
        incidencias_por_bairro = db.query(
            models.Incidencia.bairro,
            func.count(models.Incidencia.incidencia_id).label('total')
        ).filter(
            models.Incidencia.cliente_id == cliente_id,
            models.Incidencia.categoria_id.in_(categorias_ids),
            models.Incidencia.bairro.isnot(None),
            models.Incidencia.bairro != ''
        ).group_by(
            models.Incidencia.bairro
        ).all()

        if incidencias_por_bairro:
            totais = [item.total for item in incidencias_por_bairro]
            media_bairros = sum(totais) / len(totais) if totais else 0
            limite_alerta = media_bairros * 3

            for item in incidencias_por_bairro:
                if item.total >= limite_alerta and media_bairros > 0:
                    vezes_media = round(item.total / media_bairros, 1)
                    alertas_bairros.append({
                        "bairro": item.bairro,
                        "total_incidencias": item.total,
                        "media_geral": round(media_bairros, 1),
                        "vezes_acima_media": vezes_media,
                        "tipo": "critico",
                        "mensagem": f"O bairro {item.bairro} possui {item.total} incidências, {vezes_media}x acima da média"
                    })

        # 2. ALERTAS DE CATEGORIAS - Categorias com aumento significativo na última semana
        # Incidências por categoria na semana atual
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
        ).group_by(
            models.Categoria.nome,
            models.Categoria.categoria_id
        ).all()

        # Incidências por categoria na semana anterior
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
        ).group_by(
            models.Categoria.categoria_id
        ).all()

        dict_anterior = {cat.categoria_id: cat.total for cat in categorias_semana_anterior}

        # Verificar aumento significativo (mais de 50% de aumento)
        for cat in categorias_semana_atual:
            anterior = dict_anterior.get(cat.categoria_id, 0)
            if anterior > 0:
                aumento_percentual = ((cat.total - anterior) / anterior) * 100
                # Alerta se aumento for maior que 50%
                if aumento_percentual >= 50:
                    alertas_categorias.append({
                        "categoria": cat.nome,
                        "total_atual": cat.total,
                        "total_anterior": anterior,
                        "aumento_percentual": round(aumento_percentual, 1),
                        "tipo": "atencao" if aumento_percentual < 100 else "critico",
                        "mensagem": f"A categoria {cat.nome} teve aumento de {round(aumento_percentual, 1)}% em relação à semana anterior"
                    })
            elif cat.total >= 5:
                # Nova categoria com volume significativo
                alertas_categorias.append({
                    "categoria": cat.nome,
                    "total_atual": cat.total,
                    "total_anterior": 0,
                    "aumento_percentual": 100,
                    "tipo": "atencao",
                    "mensagem": f"A categoria {cat.nome} registrou {cat.total} novas incidências esta semana (não havia registros na semana anterior)"
                })

        # Ordenar alertas por criticidade
        alertas_bairros.sort(key=lambda x: x['total_incidencias'], reverse=True)
        alertas_categorias.sort(key=lambda x: x['aumento_percentual'], reverse=True)

        # Salvar alertas no historico (evitando duplicatas do mesmo dia)
        for alerta in alertas_bairros:
            # Verificar se ja existe alerta para este bairro no mesmo dia
            alerta_existente = db.query(models.HistoricoAlerta).filter(
                models.HistoricoAlerta.cliente_id == cliente_id,
                models.HistoricoAlerta.tipo == 'bairro',
                models.HistoricoAlerta.referencia == alerta['bairro'],
                cast(models.HistoricoAlerta.data_criacao, Date) == hoje
            ).first()

            if not alerta_existente:
                novo_alerta = models.HistoricoAlerta(
                    cliente_id=cliente_id,
                    tipo='bairro',
                    referencia=alerta['bairro'],
                    mensagem=alerta['mensagem'],
                    severidade=alerta['tipo'],
                    valor=alerta['total_incidencias'],
                    comparativo=f"{alerta['vezes_acima_media']}x acima da media"
                )
                db.add(novo_alerta)

        for alerta in alertas_categorias:
            # Verificar se ja existe alerta para esta categoria no mesmo dia
            alerta_existente = db.query(models.HistoricoAlerta).filter(
                models.HistoricoAlerta.cliente_id == cliente_id,
                models.HistoricoAlerta.tipo == 'categoria',
                models.HistoricoAlerta.referencia == alerta['categoria'],
                cast(models.HistoricoAlerta.data_criacao, Date) == hoje
            ).first()

            if not alerta_existente:
                novo_alerta = models.HistoricoAlerta(
                    cliente_id=cliente_id,
                    tipo='categoria',
                    referencia=alerta['categoria'],
                    mensagem=alerta['mensagem'],
                    severidade=alerta['tipo'],
                    valor=alerta['total_atual'],
                    comparativo=f"+{alerta['aumento_percentual']}% em relacao a semana anterior"
                )
                db.add(novo_alerta)

        db.commit()

        return {
            "alertas_bairros": alertas_bairros,
            "alertas_categorias": alertas_categorias,
            "total_alertas": len(alertas_bairros) + len(alertas_categorias),
            "data_analise": str(hoje)
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao buscar alertas: {str(e)}")


# Endpoint: Listar historico de alertas do cliente
@app.get("/api/alertas/historico")
async def get_historico_alertas(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
    apenas_nao_lidos: bool = False
):
    """
    Retorna o historico de alertas do cliente.
    Parametros opcionais:
    - limit: quantidade maxima de registros (default: 50)
    - offset: paginacao (default: 0)
    - apenas_nao_lidos: filtrar apenas alertas nao lidos (default: False)
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise credentials_exception

    if not cliente_id:
        raise HTTPException(status_code=401, detail="Cliente nao identificado")

    try:
        query = db.query(models.HistoricoAlerta).filter(
            models.HistoricoAlerta.cliente_id == cliente_id
        )

        if apenas_nao_lidos:
            query = query.filter(models.HistoricoAlerta.lido == 0)

        total = query.count()

        alertas = query.order_by(
            models.HistoricoAlerta.data_criacao.desc()
        ).offset(offset).limit(limit).all()

        return {
            "alertas": [
                {
                    "alerta_id": a.alerta_id,
                    "tipo": a.tipo,
                    "referencia": a.referencia,
                    "mensagem": a.mensagem,
                    "severidade": a.severidade,
                    "valor": a.valor,
                    "comparativo": a.comparativo,
                    "data_criacao": str(a.data_criacao),
                    "lido": a.lido,
                    "notificado_email": a.notificado_email
                } for a in alertas
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar historico de alertas: {str(e)}")


# Endpoint: Marcar alerta como lido
@app.post("/api/alertas/marcar-lido/{alerta_id}")
@app.put("/api/alertas/{alerta_id}/marcar-lido")
async def marcar_alerta_lido(
    alerta_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Marca um alerta especifico como lido.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise credentials_exception

    if not cliente_id:
        raise HTTPException(status_code=401, detail="Cliente nao identificado")

    try:
        alerta = db.query(models.HistoricoAlerta).filter(
            models.HistoricoAlerta.alerta_id == alerta_id,
            models.HistoricoAlerta.cliente_id == cliente_id
        ).first()

        if not alerta:
            raise HTTPException(status_code=404, detail="Alerta nao encontrado")

        alerta.lido = 1
        db.commit()

        return {"success": True, "message": "Alerta marcado como lido"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao marcar alerta como lido: {str(e)}")


@app.put("/api/alertas/marcar-todos-lidos")
async def marcar_todos_alertas_lidos(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Marca todos os alertas do cliente como lidos.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise credentials_exception

    if not cliente_id:
        raise HTTPException(status_code=401, detail="Cliente nao identificado")

    try:
        db.query(models.HistoricoAlerta).filter(
            models.HistoricoAlerta.cliente_id == cliente_id,
            models.HistoricoAlerta.lido == 0
        ).update({"lido": 1})
        db.commit()

        return {"success": True, "message": "Todos os alertas foram marcados como lidos"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao marcar alertas como lidos: {str(e)}")


# Endpoint: Contar alertas nao lidos
@app.get("/api/alertas/nao-lidos")
async def get_alertas_nao_lidos(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Retorna os alertas nao lidos do cliente com contagem total.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise credentials_exception

    if not cliente_id:
        raise HTTPException(status_code=401, detail="Cliente nao identificado")

    try:
        # Buscar alertas não lidos (últimos 20)
        alertas = db.query(models.HistoricoAlerta).filter(
            models.HistoricoAlerta.cliente_id == cliente_id,
            models.HistoricoAlerta.lido == 0
        ).order_by(models.HistoricoAlerta.data_criacao.desc()).limit(20).all()

        # Contar total
        total = db.query(models.HistoricoAlerta).filter(
            models.HistoricoAlerta.cliente_id == cliente_id,
            models.HistoricoAlerta.lido == 0
        ).count()

        return {
            "alertas": [
                {
                    "id": a.alerta_id,
                    "titulo": f"Alerta de {a.tipo.title()}" if a.tipo else "Alerta",
                    "mensagem": a.mensagem,
                    "nivel": a.severidade or "info",
                    "lido": bool(a.lido),
                    "data_criacao": a.data_criacao.isoformat() if a.data_criacao else None,
                    "referencia": a.referencia,
                    "valor": a.valor,
                    "comparativo": a.comparativo
                }
                for a in alertas
            ],
            "total": total
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar alertas nao lidos: {str(e)}")


# Endpoint: Enviar emails de alertas (para cron job externo)
@app.post("/api/alertas/enviar-emails")
async def enviar_emails_alertas(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint para envio de emails de alertas.
    Pode ser chamado por um cron job externo ou agendador.

    Funcionamento:
    1. Busca usuarios com receber_alertas_email=1
    2. Para cada usuario, busca alertas das categorias que ele tem permissao
       E que tem notifica_email=1 na tabela usuario_categoria
    3. Filtra apenas alertas com notificado_email=0 (ainda nao notificados)
    4. Envia email consolidado com todos os alertas
    5. Marca alertas como notificado_email=1

    Autenticacao:
    - Aceita token Bearer no header Authorization
    - Ou chave secreta no header X-Cron-Key (para uso com cron jobs)
    """
    # Verificar autenticacao (token ou chave de cron)
    auth_header = request.headers.get('Authorization')
    cron_key = request.headers.get('X-Cron-Key')

    cliente_id = None
    todos_clientes = False

    if cron_key:
        # Verificar chave do cron (usando SECRET_KEY como chave)
        if cron_key != SECRET_KEY:
            raise HTTPException(status_code=401, detail="Chave de cron invalida")
        todos_clientes = True
    elif auth_header and auth_header.startswith('Bearer '):
        try:
            token = auth_header.split(' ')[1]
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            cliente_id = payload.get("cliente_id")
        except JWTError:
            raise HTTPException(status_code=401, detail="Token invalido")
    else:
        raise HTTPException(status_code=401, detail="Autenticacao necessaria")

    try:
        resultados = {
            "enviados": 0,
            "falhas": 0,
            "usuarios_processados": 0,
            "alertas_notificados": 0,
            "detalhes": []
        }

        # Buscar usuarios que querem receber alertas por email
        query_usuarios = db.query(models.Usuario).filter(
            models.Usuario.receber_alertas_email == 1,
            models.Usuario.ativo == 1
        )

        if cliente_id and not todos_clientes:
            query_usuarios = query_usuarios.filter(models.Usuario.cliente_id == cliente_id)

        usuarios = query_usuarios.all()

        for usuario in usuarios:
            resultados["usuarios_processados"] += 1

            # Buscar categorias que o usuario tem permissao E que notifica_email=1
            categorias_usuario = db.query(models.UsuarioCategoria.categoria_id).filter(
                models.UsuarioCategoria.usuario_id == usuario.usuario_id,
                models.UsuarioCategoria.notifica_email == 1
            ).all()

            categorias_ids = [cat[0] for cat in categorias_usuario]

            if not categorias_ids:
                continue

            # Buscar nomes das categorias para filtrar alertas
            categorias_nomes = db.query(models.Categoria.nome).filter(
                models.Categoria.categoria_id.in_(categorias_ids)
            ).all()
            categorias_nomes_list = [cat[0] for cat in categorias_nomes]

            # Buscar alertas nao notificados do cliente do usuario
            # Filtrar por tipo='categoria' e referencia nas categorias permitidas
            # OU tipo='bairro' (alertas de bairro vao para todos que tem alguma categoria)
            alertas = db.query(models.HistoricoAlerta).filter(
                models.HistoricoAlerta.cliente_id == usuario.cliente_id,
                models.HistoricoAlerta.notificado_email == 0,
                or_(
                    and_(
                        models.HistoricoAlerta.tipo == 'categoria',
                        models.HistoricoAlerta.referencia.in_(categorias_nomes_list)
                    ),
                    models.HistoricoAlerta.tipo == 'bairro'
                )
            ).all()

            if not alertas:
                continue

            # Buscar nome do cliente para o email
            cliente = db.query(models.Cliente).filter(
                models.Cliente.cliente_id == usuario.cliente_id
            ).first()
            cliente_nome = cliente.nome if cliente else "Gestao Interativa"

            # Preparar lista de alertas para o email
            alertas_para_email = [
                {
                    "alerta_id": a.alerta_id,
                    "tipo": a.tipo,
                    "referencia": a.referencia,
                    "mensagem": a.mensagem,
                    "severidade": a.severidade,
                    "valor": a.valor,
                    "comparativo": a.comparativo,
                    "data_criacao": str(a.data_criacao)
                } for a in alertas
            ]

            # Enviar email
            resultado_email = await enviar_email_alerta(
                destinatario=usuario.email,
                nome_usuario=usuario.nome,
                alertas=alertas_para_email,
                cliente_nome=cliente_nome
            )

            if resultado_email["success"]:
                resultados["enviados"] += 1

                # Marcar alertas como notificados
                for alerta in alertas:
                    alerta.notificado_email = 1
                    resultados["alertas_notificados"] += 1

                db.commit()

                resultados["detalhes"].append({
                    "usuario": usuario.nome,
                    "email": usuario.email,
                    "alertas_enviados": len(alertas),
                    "status": "sucesso"
                })
            else:
                resultados["falhas"] += 1
                resultados["detalhes"].append({
                    "usuario": usuario.nome,
                    "email": usuario.email,
                    "status": "falha",
                    "erro": resultado_email["message"]
                })

        return {
            "success": True,
            "message": f"Processo concluido: {resultados['enviados']} emails enviados, {resultados['falhas']} falhas",
            "resultados": resultados
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao processar envio de emails: {str(e)}")


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


@app.put("/api/usuario/notificacoes")
async def atualizar_notificacoes_usuario(
    request: Request,
    dados: schemas.UsuarioNotificacoesUpdate,
    db: Session = Depends(get_db)
):
    """
    Atualiza as configuracoes de notificacao do usuario logado.
    Permite atualizar:
    - receber_alertas_email: 1 para ativar, 0 para desativar
    - receber_alertas_sistema: 1 para ativar, 0 para desativar
    - categorias_notificacao: lista de objetos com categoria_id e notifica_email
    """
    # Obter token do header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Token nao fornecido")

    try:
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id = payload.get("user_id")
        if not usuario_id:
            raise HTTPException(status_code=401, detail="Token invalido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")

    # Buscar usuario
    usuario = db.query(models.Usuario).filter(models.Usuario.usuario_id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    try:
        # Atualizar configuracoes gerais de notificacao do usuario
        if dados.receber_alertas_email is not None:
            usuario.receber_alertas_email = dados.receber_alertas_email

        if dados.receber_alertas_sistema is not None:
            usuario.receber_alertas_sistema = dados.receber_alertas_sistema

        # Atualizar notificacoes por categoria se fornecido
        if dados.categorias_notificacao:
            for cat_config in dados.categorias_notificacao:
                categoria_id = cat_config.get('categoria_id')
                notifica_email = cat_config.get('notifica_email')

                if categoria_id is not None and notifica_email is not None:
                    vinculo = db.query(models.UsuarioCategoria).filter(
                        models.UsuarioCategoria.usuario_id == usuario_id,
                        models.UsuarioCategoria.categoria_id == categoria_id
                    ).first()

                    if vinculo:
                        vinculo.notifica_email = notifica_email

        db.commit()
        db.refresh(usuario)

        return {
            "message": "Configuracoes de notificacao atualizadas com sucesso",
            "receber_alertas_email": usuario.receber_alertas_email,
            "receber_alertas_sistema": usuario.receber_alertas_sistema
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/usuario/notificacoes")
async def obter_notificacoes_usuario(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Obtem as configuracoes de notificacao do usuario logado,
    incluindo configuracoes gerais e por categoria.
    """
    # Obter token do header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Token nao fornecido")

    try:
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id = payload.get("user_id")
        if not usuario_id:
            raise HTTPException(status_code=401, detail="Token invalido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")

    # Buscar usuario
    usuario = db.query(models.Usuario).filter(models.Usuario.usuario_id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    # Buscar configuracoes de notificacao por categoria
    categorias_vinculadas = db.query(
        models.UsuarioCategoria.categoria_id,
        models.UsuarioCategoria.notifica_email,
        models.Categoria.nome
    ).join(
        models.Categoria,
        models.UsuarioCategoria.categoria_id == models.Categoria.categoria_id
    ).filter(
        models.UsuarioCategoria.usuario_id == usuario_id
    ).all()

    categorias_config = [
        {
            "categoria_id": cat.categoria_id,
            "nome": cat.nome,
            "notifica_email": cat.notifica_email
        }
        for cat in categorias_vinculadas
    ]

    return {
        "receber_alertas_email": usuario.receber_alertas_email,
        "receber_alertas_sistema": usuario.receber_alertas_sistema,
        "categorias_notificacao": categorias_config
    }


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



@app.post("/interagir/upload-foto")
async def upload_foto_interacao(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload de foto para interacao de incidencia.
    Retorna o caminho da foto salva para ser enviado junto com a interacao.
    """
    # Obter token do header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Token nao fornecido")

    try:
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id = payload.get("user_id")

        if not usuario_id:
            raise HTTPException(status_code=401, detail="Usuario nao identificado no token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")

    # Validar extensao do arquivo
    extensoes_permitidas = ['.png', '.jpg', '.jpeg']
    extensao = os.path.splitext(file.filename)[1].lower()
    if extensao not in extensoes_permitidas:
        raise HTTPException(
            status_code=400,
            detail="Formato de arquivo nao permitido. Use: PNG, JPG ou JPEG"
        )

    # Validar content type
    content_types_permitidos = ['image/png', 'image/jpeg', 'image/jpg']
    if file.content_type not in content_types_permitidos:
        raise HTTPException(
            status_code=400,
            detail="Tipo de arquivo nao permitido. Envie uma imagem PNG ou JPG"
        )

    # Gerar nome unico para o arquivo
    nome_unico = f"interacao_{usuario_id}_{uuid.uuid4().hex[:8]}{extensao}"
    caminho_arquivo = f"fotos/interacoes/{nome_unico}"

    # Criar diretorio se nao existir
    os.makedirs("fotos/interacoes", exist_ok=True)

    # Salvar arquivo
    try:
        content = await file.read()
        with open(caminho_arquivo, "wb") as buffer:
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {str(e)}")

    return JSONResponse(
        content={
            "success": True,
            "foto_path": f"/{caminho_arquivo}",
            "message": "Foto enviada com sucesso"
        },
        media_type="application/json; charset=utf-8"
    )


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
    foto_path = dados.get("foto")  # Caminho da foto ja feito upload

    # Verificação básica: incidencia_id é obrigatório
    if not incidencia_id:
        raise HTTPException(status_code=400, detail="O campo incidencia_id é obrigatório")

    # Pelo menos um dos dois deve existir: comentario OU novo_status_id
    if not comentario and not novo_status_id:
        raise HTTPException(status_code=400, detail="Pelo menos um dos campos deve ser informado: comentario ou novo_status_id")
    
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
   
    # Verificar se o status existe (somente se novo_status_id foi informado)
    status_obj = None
    if novo_status_id:
        status_obj = db.query(models.Status).filter(
            models.Status.status_id == novo_status_id
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
        comentario=comentario if comentario else None,
        status_id=novo_status_id if novo_status_id else None,
        data=datetime.now(),
        foto=foto_path if foto_path else None
    )

    db.add(nova_interacao)

    # Atualizar o status da incidência (somente se novo_status_id foi informado)
    if novo_status_id:
        incidencia.status = novo_status_id
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

    # === PUSH NOTIFICATION ===
    # Enviar push notification para o cidadao dono da incidencia
    push_enviado = False
    if cidadao_criador:
        push_titulo = f"Atualização na sua incidência #{incidencia_id}"
        push_corpo = f"Status: {status_obj.nome}"
        push_dados = {
            "tipo": "atualizacao_incidencia",
            "incidencia_id": str(incidencia_id),
            "status_id": str(novo_status_id),
            "status_nome": status_obj.nome
        }

        push_result = enviar_push_para_cidadao(
            cidadao_id=incidencia.cidadao_id,
            titulo=push_titulo,
            corpo=push_corpo,
            dados=push_dados,
            db=db
        )
        push_enviado = push_result.get("success", False)

    retorno = {
        "mensagem": "Interação registrada com sucesso",
        "incidencia_id": incidencia_id,
        "novo_status": status_obj.nome,
        "email_enviado": cidadao_criador is not None and cidadao_criador.email is not None,
        "push_enviado": push_enviado
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

# Endpoint para upload de imagem de fundo do cliente
@app.post("/api/configuracao/upload-imagem-fundo")
async def upload_imagem_fundo(
    file: UploadFile = File(...),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    # Verificar autenticacao e obter cliente_id
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        nivel = payload.get("nivel")
    except JWTError:
        raise credentials_exception

    # Apenas administradores podem alterar a imagem de fundo
    if nivel != 1:
        raise HTTPException(status_code=403, detail="Apenas administradores podem alterar a imagem de fundo")

    # Verificar extensao do arquivo
    extensoes_permitidas = ['.png', '.jpg', '.jpeg', '.gif', '.webp']
    extensao = os.path.splitext(file.filename)[1].lower()
    if extensao not in extensoes_permitidas:
        raise HTTPException(status_code=400, detail="Formato de arquivo nao permitido. Use: PNG, JPG, JPEG, GIF ou WEBP")

    # Criar nome unico para o arquivo
    nome_arquivo = f"fundo_{cliente_id}{extensao}"
    caminho_arquivo = f"static/uploads/{nome_arquivo}"

    # Criar diretorio se nao existir
    os.makedirs("static/uploads", exist_ok=True)

    # Salvar arquivo
    with open(caminho_arquivo, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Atualizar no banco de dados
    cliente = db.query(models.Cliente).filter(models.Cliente.cliente_id == cliente_id).first()
    if cliente:
        cliente.imagem_fundo = nome_arquivo
        db.commit()

    return {"message": "Imagem de fundo atualizada com sucesso", "imagem_fundo": nome_arquivo}

@app.delete("/api/configuracao/imagem-fundo")
async def delete_imagem_fundo(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    # Verificar autenticacao e obter cliente_id
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        nivel = payload.get("nivel")
    except JWTError:
        raise credentials_exception

    # Apenas administradores podem remover a imagem de fundo
    if nivel != 1:
        raise HTTPException(status_code=403, detail="Apenas administradores podem remover a imagem de fundo")

    cliente = db.query(models.Cliente).filter(models.Cliente.cliente_id == cliente_id).first()
    if cliente and cliente.imagem_fundo:
        # Remover arquivo se existir
        caminho_arquivo = f"static/uploads/{cliente.imagem_fundo}"
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)

        # Limpar campo no banco
        cliente.imagem_fundo = None
        db.commit()

    return {"message": "Imagem de fundo removida com sucesso"}

@app.get("/api/configuracao/imagem-fundo")
async def get_imagem_fundo(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Verificar autenticacao e obter cliente_id
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise credentials_exception

    try:
        result = db.execute(text(
            "SELECT imagem_fundo FROM cliente WHERE cliente_id = :id"
        ), {"id": cliente_id}).fetchone()

        if result and result[0]:
            return {"imagem_fundo": f"/static/uploads/{result[0]}"}
    except Exception:
        pass

    return {"imagem_fundo": None}

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
    # Endpoint público para buscar logo, cores, imagem de fundo, nome da empresa e configs na tela de login
    try:
        result = db.execute(text(
            """SELECT logo, cor_primaria, cor_secundaria, imagem_fundo, nome,
                      COALESCE(permitir_anonimo, 0) as permitir_anonimo
               FROM cliente WHERE cliente_id = :id"""
        ), {"id": cliente_id}).fetchone()

        if result:
            logo = result[0]
            cor_primaria = result[1] if result[1] else '#086218'
            cor_secundaria = result[2] if result[2] else '#001F5B'
            imagem_fundo = result[3]
            nome_empresa = result[4] if result[4] else 'Governa Fácil'
            permitir_anonimo = result[5] if result[5] else 0
            return {
                "logo": f"/static/images/logos/{logo}" if logo else None,
                "cor_primaria": cor_primaria,
                "cor_secundaria": cor_secundaria,
                "imagem_fundo": f"/static/uploads/{imagem_fundo}" if imagem_fundo else None,
                "nome_empresa": nome_empresa,
                "permitir_anonimo": permitir_anonimo == 1
            }
    except Exception:
        result = db.execute(text(
            "SELECT logo, nome FROM cliente WHERE cliente_id = :id"
        ), {"id": cliente_id}).fetchone()

        if result and result[0]:
            return {
                "logo": f"/static/images/logos/{result[0]}",
                "cor_primaria": '#086218',
                "cor_secundaria": '#001F5B',
                "imagem_fundo": None,
                "nome_empresa": result[1] if result[1] else 'Governa Fácil',
                "permitir_anonimo": False
            }

    return {"logo": None, "cor_primaria": '#086218', "cor_secundaria": '#001F5B', "imagem_fundo": None, "nome_empresa": "Governa Fácil", "permitir_anonimo": False}

@app.get("/api/configuracao/cliente")
async def get_cliente_dados(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Obter dados do cliente
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise credentials_exception

    try:
        # Tenta buscar com as colunas de cor e permitir_anonimo
        result = db.execute(text(
            """SELECT cliente_id, nome, cnpj, endereco, cidade, estado, logo, cor_primaria, cor_secundaria,
                      COALESCE(permitir_anonimo, 0) as permitir_anonimo
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
                "cor_secundaria": result[8] or '#001F5B',
                "permitir_anonimo": result[9]
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

@app.put("/api/configuracao/sistema")
async def update_sistema_config(
    dados: dict = Body(...),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Atualiza configuracoes do sistema (permitir_anonimo, etc)"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        nivel = payload.get("nivel")
    except JWTError:
        raise credentials_exception

    if nivel != 1:
        raise HTTPException(status_code=403, detail="Apenas administradores podem alterar configuracoes do sistema")

    cliente = db.query(models.Cliente).filter(models.Cliente.cliente_id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    # Atualizar configuracoes
    if "permitir_anonimo" in dados:
        cliente.permitir_anonimo = 1 if dados["permitir_anonimo"] else 0

    db.commit()
    return {"message": "Configuracoes do sistema atualizadas com sucesso"}

# Endpoints para gerenciar categorias
@app.get("/api/configuracao/categorias")
async def get_todas_categorias(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception

    categorias = db.query(models.Categoria).order_by(models.Categoria.nome).all()
    return [{"categoria_id": c.categoria_id, "nome": c.nome, "icone": c.icone or "bi-tag", "cor": c.cor or "#6366f1", "ativo": c.ativo} for c in categorias]

# Endpoint alternativo para a pagina de categorias
@app.get("/api/categorias")
async def get_categorias_api(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception

    categorias = db.query(models.Categoria).filter(models.Categoria.ativo == 1).order_by(models.Categoria.nome).all()
    dados = [{"categoria_id": c.categoria_id, "nome": c.nome, "descricao": c.descricao or "", "icone": c.icone or "bi-tag", "cor": c.cor or "#6366f1", "ativo": c.ativo} for c in categorias]

    # Retornar com encoding UTF-8 explícito para acentos
    return JSONResponse(
        content=dados,
        media_type="application/json; charset=utf-8"
    )

@app.get("/api/categorias/{categoria_id}")
async def get_categoria_por_id(categoria_id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Buscar uma categoria específica por ID"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception

    categoria = db.query(models.Categoria).filter(models.Categoria.categoria_id == categoria_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria nao encontrada")

    return JSONResponse(
        content={
            "categoria_id": categoria.categoria_id,
            "nome": categoria.nome,
            "descricao": categoria.descricao or "",
            "icone": categoria.icone or "bi-tag",
            "cor": categoria.cor or "#6366f1",
            "ativo": categoria.ativo
        },
        media_type="application/json; charset=utf-8"
    )

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
        descricao=dados.get("descricao", ""),
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
    if "descricao" in dados:
        categoria.descricao = dados["descricao"]
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
    if "descricao" in dados:
        categoria.descricao = dados["descricao"]
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
        # Buscar configuracao global de IA (primeira config disponivel)
        result = db.execute(text(
            """SELECT provider, model_name, api_url, api_key, temperature, max_tokens,
               timeout, chat_habilitado, system_prompt, context_window, retry_attempts,
               embedding_provider, embedding_model, embedding_api_url, embedding_api_key
               FROM config_ai LIMIT 1"""
        )).fetchone()

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
                "context_window": result[9] if result[9] is not None else 128000,
                "retry_attempts": result[10] if result[10] is not None else 3,
                "embedding_provider": result[11] or "openai",
                "embedding_model": result[12] or "text-embedding-3-small",
                "embedding_api_url": result[13] or "",
                "embedding_api_key": result[14] or ""
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
        "retry_attempts": 3,
        "chat_habilitado": False,
        "system_prompt": "",
        "embedding_provider": "openai",
        "embedding_model": "text-embedding-3-small",
        "embedding_api_url": "",
        "embedding_api_key": ""
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
                retry_attempts INTEGER DEFAULT 3,
                chat_habilitado INTEGER DEFAULT 0,
                system_prompt TEXT,
                embedding_provider VARCHAR(50) DEFAULT 'openai',
                embedding_model VARCHAR(100) DEFAULT 'text-embedding-3-small',
                embedding_api_url VARCHAR(255),
                embedding_api_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """))
        db.commit()
    except Exception:
        pass

    # Adicionar colunas de embedding caso a tabela já exista sem elas
    try:
        db.execute(text("ALTER TABLE config_ai ADD COLUMN IF NOT EXISTS retry_attempts INTEGER DEFAULT 3"))
        db.execute(text("ALTER TABLE config_ai ADD COLUMN IF NOT EXISTS embedding_provider VARCHAR(50) DEFAULT 'openai'"))
        db.execute(text("ALTER TABLE config_ai ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(100) DEFAULT 'text-embedding-3-small'"))
        db.execute(text("ALTER TABLE config_ai ADD COLUMN IF NOT EXISTS embedding_api_url VARCHAR(255)"))
        db.execute(text("ALTER TABLE config_ai ADD COLUMN IF NOT EXISTS embedding_api_key TEXT"))
        db.commit()
    except Exception as e:
        print(f"Aviso ao adicionar colunas de embedding: {e}")

    # Verificar se já existe configuração global
    existing = db.execute(text(
        "SELECT id FROM config_ai LIMIT 1"
    )).fetchone()

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
                retry_attempts = :retry_attempts,
                chat_habilitado = :chat_habilitado,
                system_prompt = :system_prompt,
                embedding_provider = :embedding_provider,
                embedding_model = :embedding_model,
                embedding_api_url = :embedding_api_url,
                embedding_api_key = :embedding_api_key,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :config_id
        """), {
            "provider": dados.get("provider", "openai"),
            "model_name": dados.get("model_name", "gpt-4o"),
            "api_url": dados.get("api_url", ""),
            "api_key": dados.get("api_key", ""),
            "temperature": dados.get("temperature", 7),
            "max_tokens": dados.get("max_tokens", 4096),
            "context_window": dados.get("context_window", 128000),
            "timeout": dados.get("timeout", 300),
            "retry_attempts": dados.get("retry_attempts", 3),
            "chat_habilitado": 1 if dados.get("chat_habilitado") else 0,
            "system_prompt": dados.get("system_prompt", ""),
            "embedding_provider": dados.get("embedding_provider", "openai"),
            "embedding_model": dados.get("embedding_model", "text-embedding-3-small"),
            "embedding_api_url": dados.get("embedding_api_url", ""),
            "embedding_api_key": dados.get("embedding_api_key", ""),
            "config_id": existing[0]
        })
    else:
        # Criar config global (cliente_id = 1 por padrao)
        db.execute(text("""
            INSERT INTO config_ai (cliente_id, provider, model_name, api_url, api_key, temperature, max_tokens, context_window, timeout, retry_attempts, chat_habilitado, system_prompt, embedding_provider, embedding_model, embedding_api_url, embedding_api_key)
            VALUES (1, :provider, :model_name, :api_url, :api_key, :temperature, :max_tokens, :context_window, :timeout, :retry_attempts, :chat_habilitado, :system_prompt, :embedding_provider, :embedding_model, :embedding_api_url, :embedding_api_key)
        """), {
            "provider": dados.get("provider", "openai"),
            "model_name": dados.get("model_name", "gpt-4o"),
            "api_url": dados.get("api_url", ""),
            "api_key": dados.get("api_key", ""),
            "temperature": dados.get("temperature", 7),
            "max_tokens": dados.get("max_tokens", 4096),
            "context_window": dados.get("context_window", 128000),
            "timeout": dados.get("timeout", 300),
            "retry_attempts": dados.get("retry_attempts", 3),
            "chat_habilitado": 1 if dados.get("chat_habilitado") else 0,
            "system_prompt": dados.get("system_prompt", ""),
            "embedding_provider": dados.get("embedding_provider", "openai"),
            "embedding_model": dados.get("embedding_model", "text-embedding-3-small"),
            "embedding_api_url": dados.get("embedding_api_url", ""),
            "embedding_api_key": dados.get("embedding_api_key", "")
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

    if not config.get("api_key"):
        raise HTTPException(status_code=400, detail="API Key não configurada")

    try:
        import requests
        # Testar com uma requisição simples de chat
        api_url = config.get('api_url', 'https://openrouter.ai/api/v1')
        response = requests.post(
            f"{api_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json"
            },
            json={
                "model": config.get('model_name', 'openai/gpt-4o-mini'),
                "messages": [{"role": "user", "content": "Diga apenas: OK"}],
                "max_tokens": 10
            },
            timeout=15
        )
        if response.status_code == 200:
            return {"success": True, "message": f"Conexão com {config['provider']} estabelecida com sucesso!"}
        else:
            error_detail = response.json().get('error', {}).get('message', response.text[:200])
            raise HTTPException(status_code=400, detail=f"Erro: {error_detail}")
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=400, detail="Timeout ao conectar com a API")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao conectar: {str(e)}")

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


# ========== CONFIGURACAO DE ARMAZENAMENTO (MinIO/S3) ==========

@app.get("/api/configuracao/storage")
async def get_config_storage(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Obter configuracao de armazenamento MinIO/S3"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise credentials_exception

    try:
        result = db.execute(text(
            """SELECT minio_url, minio_bucket, minio_access_key, minio_secret_key, ativo
               FROM config_storage WHERE cliente_id = :cliente_id LIMIT 1"""
        ), {"cliente_id": cliente_id}).fetchone()

        if result:
            return {
                "minio_url": result[0] or "",
                "minio_bucket": result[1] or "",
                "minio_access_key": result[2] or "",
                "minio_secret_key": result[3] or "",
                "ativo": bool(result[4]) if result[4] is not None else False
            }
    except Exception as e:
        print(f"Erro ao buscar config storage: {e}")

    # Retornar valores padrao
    return {
        "minio_url": "",
        "minio_bucket": "",
        "minio_access_key": "",
        "minio_secret_key": "",
        "ativo": False
    }


@app.put("/api/configuracao/storage")
async def save_config_storage(
    dados: dict = Body(...),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Salvar configuracao de armazenamento MinIO/S3"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        nivel = payload.get("nivel")
    except JWTError:
        raise credentials_exception

    if nivel != 1:
        raise HTTPException(status_code=403, detail="Apenas administradores podem configurar armazenamento")

    # Criar tabela se nao existir
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS config_storage (
                id SERIAL PRIMARY KEY,
                cliente_id INTEGER NOT NULL,
                minio_url VARCHAR(500),
                minio_bucket VARCHAR(100),
                minio_access_key VARCHAR(255),
                minio_secret_key TEXT,
                ativo INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """))
        db.commit()
    except Exception:
        pass

    # Verificar se ja existe configuracao para este cliente
    existing = db.execute(text(
        "SELECT id FROM config_storage WHERE cliente_id = :cliente_id LIMIT 1"
    ), {"cliente_id": cliente_id}).fetchone()

    if existing:
        db.execute(text("""
            UPDATE config_storage SET
                minio_url = :minio_url,
                minio_bucket = :minio_bucket,
                minio_access_key = :minio_access_key,
                minio_secret_key = :minio_secret_key,
                ativo = :ativo,
                updated_at = CURRENT_TIMESTAMP
            WHERE cliente_id = :cliente_id
        """), {
            "minio_url": dados.get("minio_url", ""),
            "minio_bucket": dados.get("minio_bucket", ""),
            "minio_access_key": dados.get("minio_access_key", ""),
            "minio_secret_key": dados.get("minio_secret_key", ""),
            "ativo": 1 if dados.get("ativo") else 0,
            "cliente_id": cliente_id
        })
    else:
        db.execute(text("""
            INSERT INTO config_storage (cliente_id, minio_url, minio_bucket, minio_access_key, minio_secret_key, ativo)
            VALUES (:cliente_id, :minio_url, :minio_bucket, :minio_access_key, :minio_secret_key, :ativo)
        """), {
            "cliente_id": cliente_id,
            "minio_url": dados.get("minio_url", ""),
            "minio_bucket": dados.get("minio_bucket", ""),
            "minio_access_key": dados.get("minio_access_key", ""),
            "minio_secret_key": dados.get("minio_secret_key", ""),
            "ativo": 1 if dados.get("ativo") else 0
        })

    db.commit()
    return {"message": "Configuracoes de armazenamento salvas com sucesso"}


@app.post("/api/configuracao/storage/testar")
async def testar_conexao_storage(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Testar conexao com o servidor MinIO/S3"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise credentials_exception

    config = await get_config_storage(token, db)

    if not config.get("minio_url"):
        raise HTTPException(status_code=400, detail="URL do servidor nao configurada")

    if not config.get("minio_bucket"):
        raise HTTPException(status_code=400, detail="Nome do bucket nao configurado")

    try:
        import requests as http_requests
        # Testar conexao com o servidor MinIO
        minio_url = config.get("minio_url", "").rstrip("/")
        bucket = config.get("minio_bucket", "")

        # Tentar acessar o bucket (lista de objetos)
        test_url = f"{minio_url}/{bucket}/"
        response = http_requests.head(test_url, timeout=10)

        # Status 200, 403 ou 404 indica que o servidor esta acessivel
        if response.status_code in [200, 403, 404]:
            return {"success": True, "message": f"Conexao com {minio_url} estabelecida com sucesso!"}
        else:
            raise HTTPException(status_code=400, detail=f"Servidor retornou status {response.status_code}")

    except http_requests.exceptions.Timeout:
        raise HTTPException(status_code=400, detail="Timeout ao conectar com o servidor")
    except http_requests.exceptions.ConnectionError:
        raise HTTPException(status_code=400, detail="Nao foi possivel conectar ao servidor. Verifique a URL.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao conectar: {str(e)}")


# ========== CONFIGURACAO DE NOTIFICACOES (Email/SMS) ==========

@app.get("/api/configuracao/notificacoes")
async def get_config_notificacoes(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Obter configuracao de notificacoes (Email/SMS)"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise credentials_exception

    try:
        result = db.execute(text(
            """SELECT smtp_servidor, smtp_porta, smtp_usuario, smtp_senha,
                      smtp_email_remetente, smtp_nome_remetente, smtp_usar_tls,
                      sms_provedor, sms_api_url, sms_account_sid, sms_auth_token, sms_numero_remetente,
                      email_ao_abrir, email_ao_mudar_status, sms_ao_abrir, sms_ao_mudar_status
               FROM config_notificacoes WHERE cliente_id = :cliente_id LIMIT 1"""
        ), {"cliente_id": cliente_id}).fetchone()

        if result:
            return {
                "smtp_servidor": result[0] or "",
                "smtp_porta": result[1] or 587,
                "smtp_usuario": result[2] or "",
                "smtp_senha": result[3] or "",
                "smtp_email_remetente": result[4] or "",
                "smtp_nome_remetente": result[5] or "",
                "smtp_usar_tls": bool(result[6]) if result[6] is not None else True,
                "sms_provedor": result[7] or "",
                "sms_api_url": result[8] or "",
                "sms_account_sid": result[9] or "",
                "sms_auth_token": result[10] or "",
                "sms_numero_remetente": result[11] or "",
                "email_ao_abrir": bool(result[12]) if result[12] is not None else False,
                "email_ao_mudar_status": bool(result[13]) if result[13] is not None else False,
                "sms_ao_abrir": bool(result[14]) if result[14] is not None else False,
                "sms_ao_mudar_status": bool(result[15]) if result[15] is not None else False
            }
    except Exception as e:
        print(f"Erro ao buscar config notificacoes: {e}")

    # Retornar valores padrao
    return {
        "smtp_servidor": "",
        "smtp_porta": 587,
        "smtp_usuario": "",
        "smtp_senha": "",
        "smtp_email_remetente": "",
        "smtp_nome_remetente": "",
        "smtp_usar_tls": True,
        "sms_provedor": "",
        "sms_api_url": "",
        "sms_account_sid": "",
        "sms_auth_token": "",
        "sms_numero_remetente": "",
        "email_ao_abrir": False,
        "email_ao_mudar_status": False,
        "sms_ao_abrir": False,
        "sms_ao_mudar_status": False
    }


@app.put("/api/configuracao/notificacoes")
async def save_config_notificacoes(
    dados: dict = Body(...),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Salvar configuracao de notificacoes (Email/SMS)"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        nivel = payload.get("nivel")
    except JWTError:
        raise credentials_exception

    if nivel != 1:
        raise HTTPException(status_code=403, detail="Apenas administradores podem configurar notificacoes")

    # Criar tabela se nao existir
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS config_notificacoes (
                id SERIAL PRIMARY KEY,
                cliente_id INTEGER NOT NULL,
                smtp_servidor VARCHAR(255),
                smtp_porta INTEGER DEFAULT 587,
                smtp_usuario VARCHAR(255),
                smtp_senha TEXT,
                smtp_email_remetente VARCHAR(255),
                smtp_nome_remetente VARCHAR(255),
                smtp_usar_tls INTEGER DEFAULT 1,
                sms_provedor VARCHAR(50),
                sms_api_url VARCHAR(500),
                sms_account_sid VARCHAR(255),
                sms_auth_token TEXT,
                sms_numero_remetente VARCHAR(20),
                email_ao_abrir INTEGER DEFAULT 0,
                email_ao_mudar_status INTEGER DEFAULT 0,
                sms_ao_abrir INTEGER DEFAULT 0,
                sms_ao_mudar_status INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """))
        db.commit()
    except Exception:
        pass

    # Verificar se ja existe configuracao para este cliente
    existing = db.execute(text(
        "SELECT id FROM config_notificacoes WHERE cliente_id = :cliente_id LIMIT 1"
    ), {"cliente_id": cliente_id}).fetchone()

    if existing:
        db.execute(text("""
            UPDATE config_notificacoes SET
                smtp_servidor = :smtp_servidor,
                smtp_porta = :smtp_porta,
                smtp_usuario = :smtp_usuario,
                smtp_senha = :smtp_senha,
                smtp_email_remetente = :smtp_email_remetente,
                smtp_nome_remetente = :smtp_nome_remetente,
                smtp_usar_tls = :smtp_usar_tls,
                sms_provedor = :sms_provedor,
                sms_api_url = :sms_api_url,
                sms_account_sid = :sms_account_sid,
                sms_auth_token = :sms_auth_token,
                sms_numero_remetente = :sms_numero_remetente,
                email_ao_abrir = :email_ao_abrir,
                email_ao_mudar_status = :email_ao_mudar_status,
                sms_ao_abrir = :sms_ao_abrir,
                sms_ao_mudar_status = :sms_ao_mudar_status,
                updated_at = CURRENT_TIMESTAMP
            WHERE cliente_id = :cliente_id
        """), {
            "smtp_servidor": dados.get("smtp_servidor", ""),
            "smtp_porta": dados.get("smtp_porta", 587),
            "smtp_usuario": dados.get("smtp_usuario", ""),
            "smtp_senha": dados.get("smtp_senha", ""),
            "smtp_email_remetente": dados.get("smtp_email_remetente", ""),
            "smtp_nome_remetente": dados.get("smtp_nome_remetente", ""),
            "smtp_usar_tls": 1 if dados.get("smtp_usar_tls", True) else 0,
            "sms_provedor": dados.get("sms_provedor", ""),
            "sms_api_url": dados.get("sms_api_url", ""),
            "sms_account_sid": dados.get("sms_account_sid", ""),
            "sms_auth_token": dados.get("sms_auth_token", ""),
            "sms_numero_remetente": dados.get("sms_numero_remetente", ""),
            "email_ao_abrir": 1 if dados.get("email_ao_abrir") else 0,
            "email_ao_mudar_status": 1 if dados.get("email_ao_mudar_status") else 0,
            "sms_ao_abrir": 1 if dados.get("sms_ao_abrir") else 0,
            "sms_ao_mudar_status": 1 if dados.get("sms_ao_mudar_status") else 0,
            "cliente_id": cliente_id
        })
    else:
        db.execute(text("""
            INSERT INTO config_notificacoes (
                cliente_id, smtp_servidor, smtp_porta, smtp_usuario, smtp_senha,
                smtp_email_remetente, smtp_nome_remetente, smtp_usar_tls,
                sms_provedor, sms_api_url, sms_account_sid, sms_auth_token, sms_numero_remetente,
                email_ao_abrir, email_ao_mudar_status, sms_ao_abrir, sms_ao_mudar_status
            ) VALUES (
                :cliente_id, :smtp_servidor, :smtp_porta, :smtp_usuario, :smtp_senha,
                :smtp_email_remetente, :smtp_nome_remetente, :smtp_usar_tls,
                :sms_provedor, :sms_api_url, :sms_account_sid, :sms_auth_token, :sms_numero_remetente,
                :email_ao_abrir, :email_ao_mudar_status, :sms_ao_abrir, :sms_ao_mudar_status
            )
        """), {
            "cliente_id": cliente_id,
            "smtp_servidor": dados.get("smtp_servidor", ""),
            "smtp_porta": dados.get("smtp_porta", 587),
            "smtp_usuario": dados.get("smtp_usuario", ""),
            "smtp_senha": dados.get("smtp_senha", ""),
            "smtp_email_remetente": dados.get("smtp_email_remetente", ""),
            "smtp_nome_remetente": dados.get("smtp_nome_remetente", ""),
            "smtp_usar_tls": 1 if dados.get("smtp_usar_tls", True) else 0,
            "sms_provedor": dados.get("sms_provedor", ""),
            "sms_api_url": dados.get("sms_api_url", ""),
            "sms_account_sid": dados.get("sms_account_sid", ""),
            "sms_auth_token": dados.get("sms_auth_token", ""),
            "sms_numero_remetente": dados.get("sms_numero_remetente", ""),
            "email_ao_abrir": 1 if dados.get("email_ao_abrir") else 0,
            "email_ao_mudar_status": 1 if dados.get("email_ao_mudar_status") else 0,
            "sms_ao_abrir": 1 if dados.get("sms_ao_abrir") else 0,
            "sms_ao_mudar_status": 1 if dados.get("sms_ao_mudar_status") else 0
        })

    db.commit()
    return {"message": "Configuracoes de notificacao salvas com sucesso"}


@app.post("/api/configuracao/notificacoes/testar-email")
async def testar_envio_email(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Testar envio de email com as configuracoes atuais"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception

    # Buscar configuracoes de email
    config = await get_config_notificacoes(token, db)

    if not config.get("smtp_servidor"):
        raise HTTPException(status_code=400, detail="Servidor SMTP nao configurado")

    if not config.get("smtp_usuario"):
        raise HTTPException(status_code=400, detail="Usuario SMTP nao configurado")

    # Buscar email do usuario para enviar o teste
    usuario = db.execute(text(
        "SELECT email, nome FROM usuario WHERE usuario_id = :usuario_id"
    ), {"usuario_id": usuario_id}).fetchone()

    if not usuario or not usuario[0]:
        raise HTTPException(status_code=400, detail="Email do usuario nao encontrado")

    email_destino = usuario[0]
    nome_usuario = usuario[1] or "Usuario"

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        # Configurar servidor SMTP
        servidor_smtp = config.get("smtp_servidor")
        porta_smtp = config.get("smtp_porta", 587)
        usuario_smtp = config.get("smtp_usuario")
        senha_smtp = config.get("smtp_senha")
        email_remetente = config.get("smtp_email_remetente") or usuario_smtp
        nome_remetente = config.get("smtp_nome_remetente") or "Sistema de Incidencias"
        usar_tls = config.get("smtp_usar_tls", True)

        # Criar mensagem
        msg = MIMEMultipart()
        msg['From'] = f"{nome_remetente} <{email_remetente}>"
        msg['To'] = email_destino
        msg['Subject'] = "Teste de Configuracao de Email - Governa Facil"

        corpo = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #086218;">Teste de Email - Governa Facil</h2>
            <p>Ola {nome_usuario},</p>
            <p>Este e um email de teste para verificar se as configuracoes de SMTP estao funcionando corretamente.</p>
            <p>Se voce recebeu este email, as configuracoes estao corretas!</p>
            <hr style="border: 1px solid #e2e8f0;">
            <p style="color: #64748b; font-size: 12px;">
                Este email foi enviado automaticamente pelo sistema Governa Facil.<br>
                Servidor SMTP: {servidor_smtp}:{porta_smtp}<br>
                TLS: {'Ativado' if usar_tls else 'Desativado'}
            </p>
        </body>
        </html>
        """

        msg.attach(MIMEText(corpo, 'html'))

        # Conectar e enviar
        if usar_tls:
            server = smtplib.SMTP(servidor_smtp, porta_smtp)
            server.starttls()
        else:
            server = smtplib.SMTP(servidor_smtp, porta_smtp)

        server.login(usuario_smtp, senha_smtp)
        server.send_message(msg)
        server.quit()

        return {"success": True, "message": f"Email de teste enviado com sucesso para {email_destino}!"}

    except smtplib.SMTPAuthenticationError:
        raise HTTPException(status_code=400, detail="Erro de autenticacao SMTP. Verifique usuario e senha.")
    except smtplib.SMTPConnectError:
        raise HTTPException(status_code=400, detail="Nao foi possivel conectar ao servidor SMTP.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao enviar email: {str(e)}")


@app.post("/api/configuracao/notificacoes/testar-sms")
async def testar_envio_sms(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Testar envio de SMS com as configuracoes atuais"""
    import requests as http_requests

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception

    # Buscar configuracoes de SMS
    config = await get_config_notificacoes(token, db)

    if not config.get("sms_provedor"):
        raise HTTPException(status_code=400, detail="Provedor de SMS nao configurado")

    if not config.get("sms_account_sid"):
        raise HTTPException(status_code=400, detail="Account SID / API Key nao configurado")

    if not config.get("sms_auth_token"):
        raise HTTPException(status_code=400, detail="Auth Token / Secret nao configurado")

    if not config.get("sms_numero_remetente"):
        raise HTTPException(status_code=400, detail="Numero remetente nao configurado")

    # Buscar celular do usuario para enviar o teste
    usuario = db.execute(text(
        "SELECT celular, nome FROM usuario WHERE usuario_id = :usuario_id"
    ), {"usuario_id": usuario_id}).fetchone()

    if not usuario or not usuario[0]:
        raise HTTPException(status_code=400, detail="Celular do usuario nao encontrado. Cadastre seu celular no perfil.")

    celular_destino = usuario[0]
    nome_usuario = usuario[1] or "Usuario"

    provedor = config.get("sms_provedor")
    account_sid = config.get("sms_account_sid")
    auth_token = config.get("sms_auth_token")
    numero_remetente = config.get("sms_numero_remetente")
    api_url = config.get("sms_api_url", "")

    mensagem = f"Governa Facil: Teste de SMS. Ola {nome_usuario}, suas configuracoes de SMS estao funcionando!"

    try:
        if provedor == "twilio":
            # Twilio API
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
            data = {
                "To": celular_destino,
                "From": numero_remetente,
                "Body": mensagem
            }
            response = http_requests.post(url, data=data, auth=(account_sid, auth_token), timeout=30)

            if response.status_code == 201:
                return {"success": True, "message": f"SMS de teste enviado com sucesso para {celular_destino}!"}
            else:
                error_msg = response.json().get("message", "Erro desconhecido")
                raise HTTPException(status_code=400, detail=f"Erro Twilio: {error_msg}")

        elif provedor == "zenvia":
            # Zenvia API
            url = api_url or "https://api.zenvia.com/v2/channels/sms/messages"
            headers_zenvia = {
                "Content-Type": "application/json",
                "X-API-TOKEN": auth_token
            }
            data = {
                "from": numero_remetente,
                "to": celular_destino,
                "contents": [{"type": "text", "text": mensagem}]
            }
            response = http_requests.post(url, json=data, headers=headers_zenvia, timeout=30)

            if response.status_code in [200, 201]:
                return {"success": True, "message": f"SMS de teste enviado com sucesso para {celular_destino}!"}
            else:
                raise HTTPException(status_code=400, detail=f"Erro Zenvia: {response.text}")

        elif provedor == "aws_sns":
            # AWS SNS - requer boto3
            try:
                import boto3
                client = boto3.client(
                    'sns',
                    aws_access_key_id=account_sid,
                    aws_secret_access_key=auth_token,
                    region_name='us-east-1'
                )
                response = client.publish(
                    PhoneNumber=celular_destino,
                    Message=mensagem
                )
                return {"success": True, "message": f"SMS de teste enviado com sucesso para {celular_destino}!"}
            except ImportError:
                raise HTTPException(status_code=400, detail="Biblioteca boto3 nao instalada para AWS SNS")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Erro AWS SNS: {str(e)}")

        else:
            # Provedor generico - tentar API customizada
            if not api_url:
                raise HTTPException(status_code=400, detail="URL da API nao configurada para este provedor")

            headers_generic = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}"
            }
            data = {
                "from": numero_remetente,
                "to": celular_destino,
                "message": mensagem
            }
            response = http_requests.post(api_url, json=data, headers=headers_generic, timeout=30)

            if response.status_code in [200, 201]:
                return {"success": True, "message": f"SMS de teste enviado com sucesso para {celular_destino}!"}
            else:
                raise HTTPException(status_code=400, detail=f"Erro: {response.text}")

    except http_requests.exceptions.Timeout:
        raise HTTPException(status_code=400, detail="Timeout ao conectar com o provedor de SMS")
    except http_requests.exceptions.ConnectionError:
        raise HTTPException(status_code=400, detail="Nao foi possivel conectar ao provedor de SMS")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao enviar SMS: {str(e)}")


@app.post("/api/assistente-ia/chat")
async def assistente_ia_chat(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Endpoint para processar mensagens do assistente IA"""
    import requests as http_requests

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

    # Buscar configuração de IA do cliente usando a função existente
    try:
        config = await get_config_ia(token, db)

        # Verificar se tem API key configurada
        if not config.get("api_key"):
            return {"message": "O assistente IA não está configurado. Configure a API na tela de Configuração > Inteligência Artificial."}

        # Verificar se o chat está habilitado
        if not config.get("chat_habilitado"):
            return {"message": "O chat com IA está desabilitado. Habilite-o na tela de Configuração > Inteligência Artificial."}

        # Extrair configurações
        api_key = config["api_key"]
        api_url = config.get("api_url", "https://api.openai.com/v1")
        modelo = config.get("model_name", "gpt-4o")
        system_prompt_custom = config.get("system_prompt", "")
        temperatura = (config.get("temperature", 7)) / 10  # Converter para 0.0 - 1.0
        max_tokens = config.get("max_tokens", 4096)
        timeout = config.get("timeout", 300)

        # Contexto do sistema
        schema_info = gerar_schema_info(models.Base)

        # Primeiro, verificar se a pergunta precisa de dados do banco
        # Se sim, gerar e executar SQL
        dados_contexto = ""

        # Perguntas que provavelmente precisam de dados
        palavras_dados = ['quantas', 'quantos', 'total', 'listar', 'mostrar', 'quais', 'onde', 'ranking',
                         'média', 'media', 'maior', 'menor', 'últimas', 'ultimas', 'recentes', 'pendentes',
                         'abertas', 'resolvidas', 'bairro', 'bairros', 'categoria', 'categorias',
                         'incidência', 'incidencia', 'incidencias', 'incidências',
                         'estatística', 'estatisticas', 'estatísticas', 'dados', 'resumo', 'relatório',
                         'cidadao', 'cidadaos', 'usuario', 'usuarios', 'status', 'geral', 'gerais']

        precisa_dados = any(p in mensagem.lower() for p in palavras_dados)
        print(f"[Assistente IA] ========== NOVA REQUISICAO ==========", flush=True)
        print(f"[Assistente IA] Mensagem: {mensagem}", flush=True)
        print(f"[Assistente IA] Precisa de dados do banco: {precisa_dados}", flush=True)

        sql_executado = False
        sql_gerado = ""

        if precisa_dados:
            print(f"[Assistente IA] Iniciando geracao de SQL...", flush=True)

            # Pedir para o LLM gerar apenas o SQL
            sql_prompt = f"""Baseado na estrutura do banco de dados abaixo, gere APENAS uma query SQL PostgreSQL para responder: "{mensagem}"

Estrutura do banco:
{schema_info}

REGRAS IMPORTANTES:
- Retorne APENAS o SQL puro, sem explicacoes, sem markdown, sem ```
- Use sintaxe PostgreSQL
- Limite resultados a 50 linhas com LIMIT 50
- Para incidencias, SEMPRE filtre por cliente_id = {cliente_id}
- Tabela incidencia tem: incidencia_id, categoria_id, cidadao_id, status (1=Aberta, 2=Em Andamento, 3=Concluida), bairro, descricao, data_hora, cliente_id
- Tabela categoria tem: categoria_id, nome
- Tabela status tem: status_id, nome
- Para contar por bairro: SELECT bairro, COUNT(*) as total FROM incidencia WHERE cliente_id = {cliente_id} GROUP BY bairro ORDER BY total DESC LIMIT 50
- Use LEFT JOIN para relacionamentos entre tabelas"""

            # Construir URL da API
            sql_api_url = api_url.rstrip('/') + '/chat/completions' if not api_url.endswith('/chat/completions') else api_url
            print(f"[Assistente IA] URL da API: {sql_api_url}", flush=True)
            print(f"[Assistente IA] Modelo: {modelo}", flush=True)

            try:
                # Gerar SQL
                sql_response = http_requests.post(
                    sql_api_url,
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                    json={"model": modelo, "messages": [{"role": "user", "content": sql_prompt}], "max_tokens": 500, "temperature": 0.1},
                    timeout=30
                )

                print(f"[Assistente IA] Resposta API SQL - Status: {sql_response.status_code}", flush=True)

                if sql_response.status_code == 200:
                    sql_gerado = sql_response.json()["choices"][0]["message"]["content"].strip()
                    print(f"[Assistente IA] SQL bruto recebido: {sql_gerado}", flush=True)

                    # Limpar o SQL - remover markdown
                    sql_gerado = sql_gerado.replace("```sql", "").replace("```SQL", "").replace("```", "").strip()

                    # Encontrar o SELECT ou WITH no texto
                    sql_upper = sql_gerado.upper()
                    select_pos = sql_upper.find('SELECT')
                    with_pos = sql_upper.find('WITH')

                    if select_pos >= 0 or with_pos >= 0:
                        # Pegar a partir do primeiro SELECT ou WITH
                        start_pos = min([p for p in [select_pos, with_pos] if p >= 0])
                        sql_gerado = sql_gerado[start_pos:].strip()
                        # Remover texto apos o ponto e virgula final
                        if ';' in sql_gerado:
                            sql_gerado = sql_gerado[:sql_gerado.rfind(';')+1]
                        # Remover ponto e virgula para evitar erros
                        sql_gerado = sql_gerado.rstrip(';').strip()

                    print(f"[Assistente IA] SQL limpo para execucao: {sql_gerado}", flush=True)

                    # Executar SQL (apenas SELECT)
                    sql_upper_clean = sql_gerado.upper().strip()
                    if sql_upper_clean.startswith("SELECT") or sql_upper_clean.startswith("WITH"):
                        print(f"[Assistente IA] Executando SQL no banco...", flush=True)
                        try:
                            result = db.execute(text(sql_gerado))
                            rows = result.fetchall()
                            columns = list(result.keys())
                            sql_executado = True

                            print(f"[Assistente IA] SQL executado com SUCESSO!", flush=True)
                            print(f"[Assistente IA] Colunas: {columns}", flush=True)
                            print(f"[Assistente IA] Numero de linhas: {len(rows)}", flush=True)

                            if rows:
                                dados_contexto = f"\n\n=== DADOS OBTIDOS DO BANCO DE DADOS ===\nVoce DEVE usar estes dados para responder ao usuario. NAO sugira SQL.\n\nResultados da consulta:\n"
                                for idx, row in enumerate(rows[:30]):  # Limitar a 30 linhas
                                    row_dict = dict(zip(columns, row))
                                    dados_contexto += f"Registro {idx+1}: {row_dict}\n"
                                dados_contexto += f"\nTotal de registros retornados: {len(rows)}"
                                if len(rows) > 30:
                                    dados_contexto += f" (mostrando primeiros 30)"
                                dados_contexto += "\n=== FIM DOS DADOS ==="
                                print(f"[Assistente IA] Dados contexto gerado com {len(rows)} registros", flush=True)
                            else:
                                dados_contexto = "\n\n=== DADOS DO BANCO ===\nA consulta foi executada mas nao retornou resultados. Informe ao usuario que nao ha dados para esta consulta.\n=== FIM DOS DADOS ==="
                                print(f"[Assistente IA] Consulta retornou 0 registros", flush=True)
                        except Exception as e:
                            print(f"[Assistente IA] ERRO ao executar SQL: {type(e).__name__}: {e}", flush=True)
                            dados_contexto = f"\n\n=== ERRO NA CONSULTA ===\nOcorreu um erro ao buscar os dados. Informe ao usuario que houve um problema tecnico.\n=== FIM ==="
                    else:
                        print(f"[Assistente IA] SQL nao comeca com SELECT ou WITH, ignorando execucao", flush=True)
                        dados_contexto = ""
                else:
                    error_text = sql_response.text[:500] if sql_response.text else "Sem detalhes"
                    print(f"[Assistente IA] ERRO na API de SQL: {sql_response.status_code} - {error_text}", flush=True)
                    dados_contexto = ""
            except Exception as e:
                print(f"[Assistente IA] EXCECAO ao chamar API de SQL: {type(e).__name__}: {e}", flush=True)
                dados_contexto = ""

        print(f"[Assistente IA] SQL executado: {sql_executado}", flush=True)
        print(f"[Assistente IA] Tamanho dados_contexto: {len(dados_contexto)} caracteres", flush=True)

        # Usar system_prompt personalizado ou padrao
        # Determinar se temos dados para mostrar
        tem_dados = len(dados_contexto) > 50 and "DADOS" in dados_contexto

        if tem_dados:
            prompt_sistema = f"""Voce e um assistente do sistema Governa Facil. Voce RECEBEU DADOS DO BANCO DE DADOS abaixo.

REGRAS ABSOLUTAS - SIGA EXATAMENTE:
1. NUNCA mostre codigo SQL, queries, SELECT, FROM, WHERE ou qualquer comando de banco de dados
2. NUNCA diga "voce pode usar a seguinte consulta SQL" ou "para obter esses dados, use..."
3. NUNCA sugira que o usuario execute consultas - voce JA TEM OS DADOS
4. APRESENTE os dados que estao abaixo de forma clara, organizada e amigavel
5. Se perguntaram sobre quantidades, some os valores e apresente o total
6. Use tabelas HTML para apresentar listas de dados

FORMATO DE RESPOSTA:
- Use portugues brasileiro
- Para listas e tabelas, use HTML: <table class="table table-sm table-striped"><thead><tr><th>Coluna</th></tr></thead><tbody><tr><td>Valor</td></tr></tbody></table>
- Para estatisticas, apresente de forma organizada com totais
- Seja direto, objetivo e amigavel
- Destaque os principais insights dos dados

CONTEXTO:
- Sistema de gestao de incidencias/ocorrencias urbanas
- Status: 1=Novo, 2=Em Andamento, 3=Concluido
{dados_contexto}"""
        else:
            prompt_sistema = f"""Voce e um assistente do sistema Governa Facil de gestao de incidencias urbanas.

REGRAS:
1. NUNCA mostre codigo SQL ou sugira consultas ao usuario
2. Responda de forma amigavel e util
3. Se a pergunta for sobre dados especificos que voce nao tem, informe que nao foi possivel obter os dados neste momento
4. Ajude com duvidas gerais sobre o sistema

CONTEXTO:
- Sistema de gestao de incidencias/ocorrencias urbanas
- Status: 1=Novo, 2=Em Andamento, 3=Concluido
- Categorias: problemas urbanos como buracos, iluminacao, lixo, etc"""

        print(f"[Assistente IA] Tem dados para resposta: {tem_dados}", flush=True)

        # Fazer chamada HTTP para API (compativel com OpenAI e outros providers)
        # Garantir que api_url termina corretamente
        final_api_url = api_url
        if not final_api_url.endswith('/chat/completions'):
            final_api_url = final_api_url.rstrip('/') + '/chat/completions'

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        payload_request = {
            "model": modelo,
            "messages": [
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": mensagem}
            ],
            "max_tokens": min(max_tokens, 4000),
            "temperature": temperatura
        }

        print(f"[Assistente IA] Enviando para LLM final...", flush=True)
        print(f"[Assistente IA] URL: {final_api_url}", flush=True)

        response = http_requests.post(
            final_api_url,
            headers=headers,
            json=payload_request,
            timeout=timeout
        )

        print(f"[Assistente IA] Resposta LLM final - Status: {response.status_code}", flush=True)

        if response.status_code == 200:
            result = response.json()
            resposta = result["choices"][0]["message"]["content"].strip()
            # Limpar quebras de linha excessivas (mais de 2 consecutivas)
            # Primeiro remover espacos em linhas vazias
            resposta = re.sub(r'\n[ \t]+\n', '\n\n', resposta)
            # Depois reduzir multiplas quebras para no maximo 2
            resposta = re.sub(r'\n{2,}', '\n\n', resposta)
            print(f"[Assistente IA] Resposta gerada com {len(resposta)} caracteres", flush=True)
            print(f"[Assistente IA] ========== FIM REQUISICAO ==========", flush=True)
            return {"message": resposta}
        else:
            error_detail = response.text[:200] if response.text else "Erro desconhecido"
            print(f"[Assistente IA] ERRO na API final ({response.status_code}): {error_detail}", flush=True)
            return {"message": f"Erro ao comunicar com a API de IA. Verifique suas configuracoes."}

    except http_requests.exceptions.Timeout:
        return {"message": "A requisição excedeu o tempo limite. Tente novamente."}
    except http_requests.exceptions.RequestException as e:
        print(f"Erro de conexão no assistente IA: {e}")
        return {"message": "Erro de conexão com a API de IA. Verifique a URL e suas configurações."}
    except Exception as e:
        print(f"Erro no assistente IA: {e}")
        return {"message": f"Desculpe, ocorreu um erro ao processar sua pergunta. Verifique as configurações de IA."}


# ========== ENDPOINTS DE CIDADAOS ==========

@app.get("/cidadaos", response_class=HTMLResponse)
async def cidadaos_page(request: Request):
    return templates.TemplateResponse("cidadaos.html", {"request": request})

@app.get("/api/cidadaos")
async def get_cidadaos(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Listar todos os cidadaos"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception

    cidadaos = db.query(models.Cidadao).order_by(models.Cidadao.nome).all()
    return [
        {
            "cidadao_id": c.cidadao_id,
            "nome": c.nome,
            "email": c.email,
            "celular": c.celular,
            "endereco": c.endereco,
            "bairro": c.bairro,
            "cep": c.cep,
            "cidade": c.cidade,
            "estado": c.estado,
            "foto": c.foto or "",
            "ativo": c.ativo,
            "data_hora_cadastro": c.data_hora_cadastro.isoformat() if c.data_hora_cadastro else None
        }
        for c in cidadaos
    ]

@app.get("/api/cidadaos/{cidadao_id}")
async def get_cidadao(cidadao_id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Obter um cidadao especifico"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception

    cidadao = db.query(models.Cidadao).filter(models.Cidadao.cidadao_id == cidadao_id).first()
    if not cidadao:
        raise HTTPException(status_code=404, detail="Cidadao nao encontrado")

    return {
        "cidadao_id": cidadao.cidadao_id,
        "nome": cidadao.nome,
        "email": cidadao.email,
        "celular": cidadao.celular,
        "endereco": cidadao.endereco,
        "bairro": cidadao.bairro,
        "cep": cidadao.cep,
        "cidade": cidadao.cidade,
        "estado": cidadao.estado,
        "foto": cidadao.foto or "",
        "ativo": cidadao.ativo,
        "data_hora_cadastro": cidadao.data_hora_cadastro.isoformat() if cidadao.data_hora_cadastro else None
    }

@app.post("/api/cidadaos")
async def criar_cidadao(
    dados: dict = Body(...),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Criar um novo cidadao"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception

    # Validar campos obrigatorios
    if not dados.get("nome"):
        raise HTTPException(status_code=400, detail="Nome e obrigatorio")
    if not dados.get("email"):
        raise HTTPException(status_code=400, detail="Email e obrigatorio")
    if not dados.get("senha"):
        raise HTTPException(status_code=400, detail="Senha e obrigatoria")
    if not dados.get("celular"):
        raise HTTPException(status_code=400, detail="Celular e obrigatorio")
    if not dados.get("cep"):
        raise HTTPException(status_code=400, detail="CEP e obrigatorio")

    # Verificar se email ja existe
    email_existente = db.query(models.Cidadao).filter(models.Cidadao.email == dados["email"]).first()
    if email_existente:
        raise HTTPException(status_code=400, detail="Email ja cadastrado")

    # Hash da senha
    senha_hash = get_password_hash(dados["senha"])

    novo_cidadao = models.Cidadao(
        nome=dados["nome"],
        email=dados["email"],
        senha=senha_hash,
        celular=dados["celular"],
        endereco=dados.get("endereco"),
        bairro=dados.get("bairro"),
        cep=dados["cep"],
        cidade=dados.get("cidade"),
        estado=dados.get("estado"),
        ativo=dados.get("ativo", 1)
    )

    db.add(novo_cidadao)
    db.commit()
    db.refresh(novo_cidadao)

    return {"message": "Cidadao criado com sucesso", "cidadao_id": novo_cidadao.cidadao_id}

@app.put("/api/cidadaos/{cidadao_id}")
async def atualizar_cidadao(
    cidadao_id: int,
    dados: dict = Body(...),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Atualizar um cidadao existente"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception

    cidadao = db.query(models.Cidadao).filter(models.Cidadao.cidadao_id == cidadao_id).first()
    if not cidadao:
        raise HTTPException(status_code=404, detail="Cidadao nao encontrado")

    # Verificar se email ja existe em outro cidadao
    if dados.get("email") and dados["email"] != cidadao.email:
        email_existente = db.query(models.Cidadao).filter(
            models.Cidadao.email == dados["email"],
            models.Cidadao.cidadao_id != cidadao_id
        ).first()
        if email_existente:
            raise HTTPException(status_code=400, detail="Email ja cadastrado para outro cidadao")

    # Atualizar campos
    if dados.get("nome"):
        cidadao.nome = dados["nome"]
    if dados.get("email"):
        cidadao.email = dados["email"]
    if dados.get("senha"):
        cidadao.senha = get_password_hash(dados["senha"])
    if dados.get("celular"):
        cidadao.celular = dados["celular"]
    if "endereco" in dados:
        cidadao.endereco = dados["endereco"]
    if "bairro" in dados:
        cidadao.bairro = dados["bairro"]
    if dados.get("cep"):
        cidadao.cep = dados["cep"]
    if "cidade" in dados:
        cidadao.cidade = dados["cidade"]
    if "estado" in dados:
        cidadao.estado = dados["estado"]
    if "foto" in dados:
        cidadao.foto = dados["foto"]
    if "ativo" in dados:
        cidadao.ativo = dados["ativo"]

    db.commit()
    return {"message": "Cidadao atualizado com sucesso"}

@app.delete("/api/cidadaos/{cidadao_id}")
async def deletar_cidadao(
    cidadao_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Excluir um cidadao"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        nivel = payload.get("nivel")
    except JWTError:
        raise credentials_exception

    # Apenas administradores podem excluir
    if nivel != 1:
        raise HTTPException(status_code=403, detail="Apenas administradores podem excluir cidadaos")

    cidadao = db.query(models.Cidadao).filter(models.Cidadao.cidadao_id == cidadao_id).first()
    if not cidadao:
        raise HTTPException(status_code=404, detail="Cidadao nao encontrado")

    # Verificar se cidadao tem incidencias vinculadas
    incidencias = db.query(models.Incidencia).filter(models.Incidencia.cidadao_id == cidadao_id).count()
    if incidencias > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cidadao possui {incidencias} incidencia(s) vinculada(s). Desative ao inves de excluir."
        )

    db.delete(cidadao)
    db.commit()
    return {"message": "Cidadao excluido com sucesso"}


# ========== ENDPOINT DE NOTIFICAÇÕES PARA O APP ==========

@app.get("/api/notificacoes/cidadao/{cidadao_id}")
async def get_notificacoes_cidadao(
    cidadao_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Busca notificações (interações não vistas) das incidências do cidadão"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception

    # Buscar incidências do cidadão
    incidencias = db.query(models.Incidencia).filter(
        models.Incidencia.cidadao_id == cidadao_id
    ).all()

    if not incidencias:
        return []

    # Buscar interações dessas incidências
    incidencia_ids = [i.incidencia_id for i in incidencias]

    interacoes = db.query(models.IncidenciaInteracao).filter(
        models.IncidenciaInteracao.incidencia_id.in_(incidencia_ids)
    ).order_by(models.IncidenciaInteracao.data.desc()).limit(10).all()

    resultado = []
    for interacao in interacoes:
        resultado.append({
            "incidencia_interacao_id": interacao.incidencia_interacao_id,
            "incidencia_id": interacao.incidencia_id,
            "usuario_id": interacao.usuario_id,
            "comentario": interacao.comentario,
            "status_id": interacao.status_id,
            "data_interacao": interacao.data.isoformat() if interacao.data else None,
            "visto": False,  # Por enquanto sempre false
            "cidadao_id": cidadao_id
        })

    return resultado


# ========== ENDPOINT DE TIMELINE DA INCIDÊNCIA (APP MOBILE) ==========

@app.get("/api/incidencias/{incidencia_id}/timeline")
async def get_timeline_incidencia(
    incidencia_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Retorna a timeline completa de uma incidência com todas as interações.
    Inclui:
    - Dados da incidência original (abertura)
    - Todas as interações ordenadas por data
    - Status de cada etapa com cores e ícones
    - Usuário responsável por cada ação
    - Fotos associadas à incidência
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception

    # Buscar a incidência
    incidencia = db.query(models.Incidencia).filter(
        models.Incidencia.incidencia_id == incidencia_id
    ).first()

    if not incidencia:
        raise HTTPException(
            status_code=404,
            detail=f"Incidência com ID {incidencia_id} não encontrada"
        )

    # Buscar categoria da incidência
    categoria = db.query(models.Categoria).filter(
        models.Categoria.categoria_id == incidencia.categoria_id
    ).first()

    # Buscar cidadão que criou a incidência
    cidadao = db.query(models.Cidadao).filter(
        models.Cidadao.cidadao_id == incidencia.cidadao_id
    ).first()

    # Buscar status atual
    status_atual = db.query(models.Status).filter(
        models.Status.status_id == incidencia.status
    ).first()

    # Buscar todas as interações desta incidência com joins
    # Usar outerjoin para Status pois status_id pode ser NULL (apenas comentario)
    interacoes = db.query(
        models.IncidenciaInteracao,
        models.Usuario,
        models.Status
    ).join(
        models.Usuario,
        models.IncidenciaInteracao.usuario_id == models.Usuario.usuario_id
    ).outerjoin(
        models.Status,
        models.IncidenciaInteracao.status_id == models.Status.status_id
    ).filter(
        models.IncidenciaInteracao.incidencia_id == incidencia_id
    ).order_by(
        models.IncidenciaInteracao.data.asc()
    ).all()

    # Mapear status para cores e ícones
    def get_status_style(status_nome: str) -> dict:
        status_lower = status_nome.lower() if status_nome else ""

        if "resolv" in status_lower or "conclu" in status_lower or "finaliz" in status_lower:
            return {
                "cor": "#4CAF50",      # Verde
                "cor_fundo": "#E8F5E9",
                "icone": "check_circle",
                "tipo": "resolvida"
            }
        elif "andamento" in status_lower or "execu" in status_lower or "trabalh" in status_lower:
            return {
                "cor": "#FF9800",      # Laranja/Amarelo
                "cor_fundo": "#FFF3E0",
                "icone": "engineering",
                "tipo": "andamento"
            }
        elif "analis" in status_lower or "avali" in status_lower or "verific" in status_lower:
            return {
                "cor": "#2196F3",      # Azul
                "cor_fundo": "#E3F2FD",
                "icone": "search",
                "tipo": "analise"
            }
        elif "aberta" in status_lower or "nova" in status_lower or "penden" in status_lower:
            return {
                "cor": "#9E9E9E",      # Cinza
                "cor_fundo": "#F5F5F5",
                "icone": "fiber_new",
                "tipo": "aberta"
            }
        elif "cancel" in status_lower or "rejeit" in status_lower:
            return {
                "cor": "#F44336",      # Vermelho
                "cor_fundo": "#FFEBEE",
                "icone": "cancel",
                "tipo": "cancelada"
            }
        else:
            return {
                "cor": "#607D8B",      # Cinza azulado
                "cor_fundo": "#ECEFF1",
                "icone": "info",
                "tipo": "outro"
            }

    # Construir timeline
    timeline = []

    # 1. Evento de abertura da incidência
    abertura_style = get_status_style("aberta")
    timeline.append({
        "id": 0,
        "tipo_evento": "abertura",
        "data_hora": incidencia.data_hora.isoformat() if incidencia.data_hora else None,
        "titulo": "Incidência Registrada",
        "descricao": (incidencia.descricao or "Sem descrição").strip(),
        "usuario_nome": cidadao.nome if cidadao else "Cidadão",
        "usuario_tipo": "cidadao",
        "status_nome": "Aberta",
        "status_id": None,
        "cor": abertura_style["cor"],
        "cor_fundo": abertura_style["cor_fundo"],
        "icone": "add_circle",
        "tipo_status": "abertura",
        "fotos": [incidencia.foto] if incidencia.foto else [],
        "endereco": incidencia.endereco,
        "bairro": incidencia.bairro,
        "categoria": categoria.nome if categoria else None
    })

    # 2. Eventos de interação
    for interacao, usuario, status in interacoes:
        style = get_status_style(status.nome if status else "")

        # Incluir foto da interacao se existir
        fotos_interacao = [interacao.foto] if hasattr(interacao, 'foto') and interacao.foto else []

        timeline.append({
            "id": interacao.incidencia_interacao_id,
            "tipo_evento": "interacao",
            "data_hora": interacao.data.isoformat() if interacao.data else None,
            "titulo": f"Status: {status.nome}" if status else "Atualização",
            "descricao": (interacao.comentario or "Sem comentário").strip(),
            "usuario_nome": usuario.nome if usuario else "Usuário",
            "usuario_tipo": "funcionario",
            "status_nome": status.nome if status else None,
            "status_id": status.status_id if status else None,
            "cor": style["cor"],
            "cor_fundo": style["cor_fundo"],
            "icone": style["icone"],
            "tipo_status": style["tipo"],
            "fotos": fotos_interacao,
            "endereco": None,
            "bairro": None,
            "categoria": None
        })

    # Resposta completa
    response_data = {
        "incidencia": {
            "id": incidencia.incidencia_id,
            "categoria_id": incidencia.categoria_id,
            "categoria_nome": categoria.nome if categoria else None,
            "categoria_icone": categoria.icone if categoria else None,
            "categoria_cor": categoria.cor if categoria else None,
            "status_atual": {
                "id": status_atual.status_id if status_atual else None,
                "nome": status_atual.nome if status_atual else "Desconhecido",
                "style": get_status_style(status_atual.nome if status_atual else "")
            },
            "endereco": incidencia.endereco,
            "bairro": incidencia.bairro,
            "cidade": incidencia.cidade,
            "estado": incidencia.estado,
            "lat": incidencia.lat,
            "long": incidencia.long,
            "foto_principal": incidencia.foto,
            "data_abertura": incidencia.data_hora.isoformat() if incidencia.data_hora else None,
            "data_ultimo_status": incidencia.data_ultimo_status.isoformat() if incidencia.data_ultimo_status else None,
            "cidadao_nome": cidadao.nome if cidadao else None
        },
        "timeline": timeline,
        "total_interacoes": len(interacoes),
        "resumo": {
            "dias_aberta": (datetime.now() - incidencia.data_hora).days if incidencia.data_hora else 0,
            "esta_resolvida": status_atual.nome.lower() in ["resolvida", "concluída", "finalizada"] if status_atual and status_atual.nome else False
        }
    }

    return JSONResponse(content=response_data, media_type="application/json; charset=utf-8")


# ========== ENDPOINT DO MAPA DE INCIDENCIAS (APP MOBILE) ==========

@app.get("/api/incidencias/mapa")
async def get_incidencias_mapa_app(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Retorna incidencias abertas para exibicao no mapa do app mobile.
    Filtra por cliente_id do token e retorna apenas os ultimos 30 dias.

    Retorno:
    {
        "incidencias": [
            {
                "incidencia_id": int,
                "lat": float,
                "long": float,
                "categoria_id": int,
                "categoria_nome": str,
                "categoria_icone": str,
                "categoria_cor": str,
                "status_nome": str,
                "data_hora": str,
                "bairro": str,
                "foto": str,
                "descricao": str
            }
        ],
        "centro": {"lat": float, "lng": float},
        "total": int
    }
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        cidadao_id = payload.get("cidadao_id")
    except JWTError:
        raise credentials_exception

    if not cliente_id:
        raise HTTPException(status_code=401, detail="Cliente nao identificado")

    # Calcular data limite (ultimos 30 dias)
    data_limite = datetime.now() - timedelta(days=30)

    # Buscar incidencias abertas (status != 3 que e Resolvida)
    # com coordenadas validas dos ultimos 30 dias
    results = db.query(
        models.Incidencia.incidencia_id,
        models.Incidencia.cidadao_id,  # Para verificar se e do usuario logado
        models.Incidencia.lat,
        models.Incidencia.long,
        models.Incidencia.categoria_id,
        models.Incidencia.bairro,
        models.Incidencia.foto,
        models.Incidencia.descricao,
        models.Incidencia.data_hora,
        models.Status.nome.label('status_nome'),
        models.Categoria.nome.label('categoria_nome'),
        models.Categoria.icone.label('categoria_icone'),
        models.Categoria.cor.label('categoria_cor')
    ).join(
        models.Status,
        models.Incidencia.status == models.Status.status_id
    ).join(
        models.Categoria,
        models.Incidencia.categoria_id == models.Categoria.categoria_id
    ).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.status != 3,  # Exclui resolvidas
        models.Incidencia.data_hora >= data_limite,
        # Filtrar coordenadas validas
        models.Incidencia.lat.isnot(None),
        models.Incidencia.lat != '',
        models.Incidencia.lat != '0',
        models.Incidencia.long.isnot(None),
        models.Incidencia.long != '',
        models.Incidencia.long != '0'
    ).order_by(
        models.Incidencia.data_hora.desc()
    ).all()

    # Funcao auxiliar para validar coordenadas
    def is_valid_coordinate(lat_str, lng_str):
        try:
            if not lat_str or not lng_str:
                return False, None, None
            lat = float(str(lat_str).strip())
            lng = float(str(lng_str).strip())
            # Verificar se nao sao zero
            if lat == 0 and lng == 0:
                return False, None, None
            if lat == 0 or lng == 0:
                return False, None, None
            # Verificar limites geograficos validos
            if not (-90 <= lat <= 90):
                return False, None, None
            if not (-180 <= lng <= 180):
                return False, None, None
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
                "incidencia_id": r.incidencia_id,
                "cidadao_id": r.cidadao_id,  # Para verificar se e do usuario logado
                "is_minha": r.cidadao_id == cidadao_id,  # Flag se e do usuario logado
                "lat": lat,
                "long": lng,
                "categoria_id": r.categoria_id,
                "categoria_nome": r.categoria_nome or "Categoria",
                "categoria_icone": r.categoria_icone or "bi-tag",
                "categoria_cor": r.categoria_cor or "#6366f1",
                "status_nome": r.status_nome or "Status",
                "data_hora": r.data_hora.strftime("%d/%m/%Y %H:%M") if r.data_hora else "",
                "bairro": r.bairro or "",
                "foto": r.foto or "",
                "descricao": (r.descricao[:150] + "...") if r.descricao and len(r.descricao) > 150 else (r.descricao or "")
            })

    # Calcular centro do mapa
    if lats and lngs:
        centro = {"lat": sum(lats) / len(lats), "lng": sum(lngs) / len(lngs)}
    else:
        # Buscar cidade do cliente para usar como centro padrão
        cliente = db.query(models.Cliente).filter(models.Cliente.cliente_id == cliente_id).first()
        if cliente and cliente.cidade:
            # Coordenadas de cidades brasileiras comuns
            cidades_coords = {
                "cuiaba": {"lat": -15.5989, "lng": -56.0949},
                "cuiabá": {"lat": -15.5989, "lng": -56.0949},
                "brasilia": {"lat": -15.7942, "lng": -47.8822},
                "brasília": {"lat": -15.7942, "lng": -47.8822},
                "sao paulo": {"lat": -23.5505, "lng": -46.6333},
                "são paulo": {"lat": -23.5505, "lng": -46.6333},
                "rio de janeiro": {"lat": -22.9068, "lng": -43.1729},
                "belo horizonte": {"lat": -19.9167, "lng": -43.9345},
                "salvador": {"lat": -12.9714, "lng": -38.5014},
                "fortaleza": {"lat": -3.7172, "lng": -38.5433},
                "recife": {"lat": -8.0476, "lng": -34.8770},
                "porto alegre": {"lat": -30.0346, "lng": -51.2177},
                "manaus": {"lat": -3.1190, "lng": -60.0217},
                "goiania": {"lat": -16.6869, "lng": -49.2648},
                "goiânia": {"lat": -16.6869, "lng": -49.2648},
                "varzea grande": {"lat": -15.6458, "lng": -56.1325},
                "várzea grande": {"lat": -15.6458, "lng": -56.1325},
                "sinop": {"lat": -11.8642, "lng": -55.5093},
                "rondonopolis": {"lat": -16.4673, "lng": -54.6372},
                "rondonópolis": {"lat": -16.4673, "lng": -54.6372},
                "tangara da serra": {"lat": -14.6229, "lng": -57.4978},
                "tangará da serra": {"lat": -14.6229, "lng": -57.4978},
                "caceres": {"lat": -16.0706, "lng": -57.6833},
                "cáceres": {"lat": -16.0706, "lng": -57.6833},
            }
            cidade_lower = cliente.cidade.lower().strip()
            centro = cidades_coords.get(cidade_lower, {"lat": -15.5989, "lng": -56.0949})  # Default: Cuiabá
        else:
            centro = {"lat": -15.5989, "lng": -56.0949}  # Cuiabá como padrão para MT

    return {
        "incidencias": incidencias,
        "centro": centro,
        "total": len(incidencias)
    }


# ========== ENDPOINT DE ESTATÍSTICAS PÚBLICAS (APP MOBILE) ==========

@app.get("/api/estatisticas/publicas")
async def get_estatisticas_publicas(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Retorna estatísticas públicas para o app mobile:
    - Total de incidências resolvidas no mês atual
    - Total de incidências abertas
    - Tempo médio de resolução (em dias)
    - Top 5 bairros com mais incidências
    - Top 5 categorias mais reportadas
    - Evolução mensal (últimos 6 meses)
    - Taxa de resolução (% resolvidas vs total)
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise credentials_exception

    from datetime import date, timedelta
    from calendar import monthrange

    hoje = date.today()
    primeiro_dia_mes = hoje.replace(day=1)

    # ===== 1. TOTAL DE INCIDÊNCIAS RESOLVIDAS NO MÊS ATUAL =====
    resolvidas_mes = db.query(func.count(models.Incidencia.incidencia_id)).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.status == 3,  # Status 3 = Resolvida
        cast(models.Incidencia.data_ultimo_status, Date) >= primeiro_dia_mes
    ).scalar() or 0

    # ===== 2. TOTAL DE INCIDÊNCIAS ABERTAS =====
    # Status diferente de 3 (resolvida)
    total_abertas = db.query(func.count(models.Incidencia.incidencia_id)).filter(
        models.Incidencia.cliente_id == cliente_id,
        or_(models.Incidencia.status != 3, models.Incidencia.status.is_(None))
    ).scalar() or 0

    # ===== 3. TEMPO MÉDIO DE RESOLUÇÃO (em dias) =====
    incidencias_resolvidas = db.query(
        models.Incidencia.data_hora,
        models.Incidencia.data_ultimo_status
    ).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.status == 3,
        models.Incidencia.data_hora.isnot(None),
        models.Incidencia.data_ultimo_status.isnot(None)
    ).all()

    tempo_medio_dias = 0.0
    if incidencias_resolvidas:
        tempos = []
        for inc in incidencias_resolvidas:
            if inc.data_hora and inc.data_ultimo_status:
                try:
                    diff = inc.data_ultimo_status - inc.data_hora
                    dias = diff.total_seconds() / (24 * 3600)
                    if dias >= 0:  # Ignora valores negativos
                        tempos.append(dias)
                except:
                    pass
        if tempos:
            tempo_medio_dias = round(sum(tempos) / len(tempos), 1)

    # ===== 4. TOP 5 BAIRROS COM MAIS INCIDÊNCIAS =====
    top_bairros_query = db.query(
        models.Incidencia.bairro,
        func.count(models.Incidencia.incidencia_id).label('total')
    ).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.bairro.isnot(None),
        models.Incidencia.bairro != ''
    ).group_by(models.Incidencia.bairro).order_by(
        func.count(models.Incidencia.incidencia_id).desc()
    ).limit(5).all()

    top_bairros = [
        {"nome": b.bairro, "total": b.total}
        for b in top_bairros_query
    ]

    # ===== 5. TOP 5 CATEGORIAS MAIS REPORTADAS =====
    top_categorias_query = db.query(
        models.Categoria.nome,
        models.Categoria.cor,
        models.Categoria.icone,
        func.count(models.Incidencia.incidencia_id).label('total')
    ).join(
        models.Incidencia,
        models.Incidencia.categoria_id == models.Categoria.categoria_id
    ).filter(
        models.Incidencia.cliente_id == cliente_id
    ).group_by(
        models.Categoria.categoria_id,
        models.Categoria.nome,
        models.Categoria.cor,
        models.Categoria.icone
    ).order_by(
        func.count(models.Incidencia.incidencia_id).desc()
    ).limit(5).all()

    top_categorias = [
        {
            "nome": c.nome,
            "total": c.total,
            "cor": c.cor or "#6366f1",
            "icone": c.icone or "bi-tag"
        }
        for c in top_categorias_query
    ]

    # ===== 6. EVOLUÇÃO MENSAL (ÚLTIMOS 6 MESES) =====
    evolucao_mensal = []
    for i in range(5, -1, -1):  # De 5 meses atrás até o mês atual
        # Calcular primeiro e último dia do mês
        mes_ref = hoje - timedelta(days=i * 30)
        primeiro_dia = mes_ref.replace(day=1)
        ultimo_dia_num = monthrange(mes_ref.year, mes_ref.month)[1]
        ultimo_dia = mes_ref.replace(day=ultimo_dia_num)

        # Total de incidências no mês
        total_mes = db.query(func.count(models.Incidencia.incidencia_id)).filter(
            models.Incidencia.cliente_id == cliente_id,
            cast(models.Incidencia.data_hora, Date) >= primeiro_dia,
            cast(models.Incidencia.data_hora, Date) <= ultimo_dia
        ).scalar() or 0

        # Resolvidas no mês
        resolvidas_no_mes = db.query(func.count(models.Incidencia.incidencia_id)).filter(
            models.Incidencia.cliente_id == cliente_id,
            models.Incidencia.status == 3,
            cast(models.Incidencia.data_ultimo_status, Date) >= primeiro_dia,
            cast(models.Incidencia.data_ultimo_status, Date) <= ultimo_dia
        ).scalar() or 0

        # Nome do mês em português
        nomes_meses = [
            "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set", "Out", "Nov", "Dez"
        ]
        nome_mes = nomes_meses[primeiro_dia.month - 1]

        evolucao_mensal.append({
            "mes": nome_mes,
            "ano": primeiro_dia.year,
            "total": total_mes,
            "resolvidas": resolvidas_no_mes
        })

    # ===== 7. TAXA DE RESOLUÇÃO =====
    total_incidencias = db.query(func.count(models.Incidencia.incidencia_id)).filter(
        models.Incidencia.cliente_id == cliente_id
    ).scalar() or 0

    total_resolvidas = db.query(func.count(models.Incidencia.incidencia_id)).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.Incidencia.status == 3
    ).scalar() or 0

    taxa_resolucao = round((total_resolvidas / total_incidencias * 100), 1) if total_incidencias > 0 else 0.0

    # ===== RESPOSTA FINAL =====
    data = {
        "resolvidas_mes_atual": resolvidas_mes,
        "total_abertas": total_abertas,
        "tempo_medio_resolucao_dias": tempo_medio_dias,
        "top_bairros": top_bairros,
        "top_categorias": top_categorias,
        "evolucao_mensal": evolucao_mensal,
        "taxa_resolucao": taxa_resolucao,
        "total_incidencias": total_incidencias,
        "total_resolvidas": total_resolvidas,
        "mes_referencia": primeiro_dia_mes.strftime("%B/%Y"),
        "data_atualizacao": datetime.now().isoformat()
    }

    return JSONResponse(content=data, media_type="application/json; charset=utf-8")


# ========== ENDPOINT PARA CRIAR INCIDENCIA (APP MOBILE COM GAMIFICACAO) ==========

@app.post("/api/incidencias/criar")
async def criar_incidencia_mobile(
    request: Request,
    dados: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Cria uma nova incidencia pelo app mobile e adiciona pontos ao cidadao.

    Body esperado:
    {
        "categoria_id": int,
        "cidadao_id": int,
        "foto": "path/da/foto",
        "status": 1,
        "descricao": "descricao do problema",
        "prioridade": int,
        "cliente_id": int,
        "lat": "latitude",
        "long": "longitude",
        "endereco": "endereco completo",
        "cidade": "cidade",
        "estado": "UF",
        "bairro": "bairro"
    }
    """
    # Obter token do header (opcional, pode usar cidadao_id do body)
    auth_header = request.headers.get('Authorization')
    cidadao_id = dados.get("cidadao_id")

    # Tentar validar token se fornecido
    if auth_header and auth_header.startswith('Bearer '):
        try:
            token = auth_header.split(' ')[1]
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            token_cidadao_id = payload.get("cidadao_id")
            if token_cidadao_id:
                cidadao_id = token_cidadao_id
        except JWTError:
            pass  # Continua com cidadao_id do body

    if not cidadao_id:
        raise HTTPException(status_code=400, detail="cidadao_id e obrigatorio")

    # Validar campos obrigatorios
    if not dados.get("categoria_id"):
        raise HTTPException(status_code=400, detail="categoria_id e obrigatorio")

    # Criar a incidencia
    nova_incidencia = models.Incidencia(
        categoria_id=dados.get('categoria_id'),
        cidadao_id=cidadao_id,
        descricao=dados.get('descricao', ''),
        prioridade=dados.get('prioridade', 4),
        endereco=dados.get('endereco', ''),
        bairro=dados.get('bairro', ''),
        cidade=dados.get('cidade', ''),
        estado=dados.get('estado', ''),
        cep=dados.get('cep', ''),
        lat=dados.get('lat', ''),
        long=dados.get('long', ''),
        foto=dados.get('foto', ''),
        status=dados.get('status', 1),
        cliente_id=dados.get('cliente_id', 1)
    )

    try:
        db.add(nova_incidencia)
        db.commit()
        db.refresh(nova_incidencia)

        # Adicionar pontos por criar incidencia (gamificacao)
        try:
            resultado_pontos = await adicionar_pontos(
                cidadao_id=cidadao_id,
                motivo='incidencia_enviada',
                pontos=PONTOS_INCIDENCIA_ENVIADA,
                referencia_id=nova_incidencia.incidencia_id,
                db=db
            )
        except Exception as e:
            print(f"[GAMIFICACAO] Erro ao adicionar pontos de incidencia: {str(e)}")
            resultado_pontos = {}

        resposta = {
            "success": True,
            "message": "Incidencia criada com sucesso!",
            "incidencia_id": nova_incidencia.incidencia_id,
            "gamificacao": resultado_pontos
        }

        return JSONResponse(content=resposta, status_code=201, media_type="application/json; charset=utf-8")

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar incidencia: {str(e)}")


# ========== ENDPOINT DE PREVISAO DE TEMPO DE RESOLUCAO (APP MOBILE) ==========

@app.get("/api/incidencias/previsao/{categoria_id}")
async def previsao_resolucao(
    categoria_id: int,
    bairro: str = None,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Calcula a previsao de tempo de resolucao baseado no historico de incidencias.

    Parametros:
    - categoria_id: ID da categoria para calcular a media
    - bairro: (opcional) Filtrar por bairro especifico

    Retorna:
    - dias_estimados: Media de dias para resolucao
    - total_amostras: Quantidade de incidencias usadas no calculo
    - confianca: Nivel de confianca (alta, media, baixa, insuficiente)
    - tempo_minimo: Menor tempo de resolucao encontrado
    - tempo_maximo: Maior tempo de resolucao encontrado
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception

    # Calcular data limite (6 meses atras)
    data_limite = datetime.now() - timedelta(days=180)

    # Query base: incidencias resolvidas (status=3) da categoria especificada
    query = db.query(
        models.Incidencia.data_hora,
        models.Incidencia.data_ultimo_status
    ).filter(
        models.Incidencia.categoria_id == categoria_id,
        models.Incidencia.status == 3,  # Status 3 = Resolvida
        models.Incidencia.data_hora >= data_limite,
        models.Incidencia.data_ultimo_status.isnot(None)
    )

    # Filtrar por bairro se fornecido
    if bairro:
        query = query.filter(models.Incidencia.bairro == bairro)

    resultados = query.all()

    # Calcular tempos de resolucao em dias
    tempos_resolucao = []
    for data_hora, data_ultimo_status in resultados:
        if data_hora and data_ultimo_status:
            diferenca = (data_ultimo_status - data_hora).total_seconds() / 86400  # Converter para dias
            if diferenca >= 0:  # Ignorar valores negativos (dados inconsistentes)
                tempos_resolucao.append(diferenca)

    total_amostras = len(tempos_resolucao)

    # Se tiver menos de 5 amostras, dados insuficientes
    if total_amostras < 5:
        return JSONResponse(content={
            "sucesso": True,
            "dados_suficientes": False,
            "dias_estimados": None,
            "total_amostras": total_amostras,
            "confianca": "insuficiente",
            "mensagem": "Dados insuficientes para estimar tempo de resolucao",
            "tempo_minimo": None,
            "tempo_maximo": None,
            "desvio_padrao": None
        }, media_type="application/json; charset=utf-8")

    # Calcular estatisticas
    import statistics

    media_dias = statistics.mean(tempos_resolucao)
    tempo_minimo = min(tempos_resolucao)
    tempo_maximo = max(tempos_resolucao)
    desvio_padrao = statistics.stdev(tempos_resolucao) if total_amostras > 1 else 0

    # Determinar nivel de confianca baseado no tamanho da amostra e desvio padrao
    if total_amostras >= 30 and desvio_padrao <= media_dias * 0.5:
        confianca = "alta"
    elif total_amostras >= 15:
        confianca = "media"
    elif total_amostras >= 5:
        confianca = "baixa"
    else:
        confianca = "insuficiente"

    return JSONResponse(content={
        "sucesso": True,
        "dados_suficientes": True,
        "dias_estimados": round(media_dias, 1),
        "total_amostras": total_amostras,
        "confianca": confianca,
        "mensagem": f"Baseado em {total_amostras} incidencias resolvidas nos ultimos 6 meses",
        "tempo_minimo": round(tempo_minimo, 1),
        "tempo_maximo": round(tempo_maximo, 1),
        "desvio_padrao": round(desvio_padrao, 1)
    }, media_type="application/json; charset=utf-8")


# ========== ENDPOINTS DE FEEDBACK POS-RESOLUCAO (APP MOBILE) ==========

@app.post("/api/incidencias/{incidencia_id}/feedback")
async def enviar_feedback_incidencia(
    incidencia_id: int,
    request: Request,
    dados: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Envia feedback do cidadao sobre a resolucao de uma incidencia.

    Body esperado:
    {
        "avaliacao": 1-5 (estrelas),
        "comentario": "texto opcional",
        "foto_confirmacao": "path da foto (opcional)",
        "resolvido": true/false (cidadao confirma se foi resolvido)
    }
    """
    # Obter token do header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Token nao fornecido")

    try:
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cidadao_id = payload.get("cidadao_id")

        if not cidadao_id:
            raise HTTPException(status_code=401, detail="Cidadao nao identificado no token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")

    # Validar se a incidencia existe
    incidencia = db.query(models.Incidencia).filter(
        models.Incidencia.incidencia_id == incidencia_id
    ).first()

    if not incidencia:
        raise HTTPException(status_code=404, detail="Incidencia nao encontrada")

    # Verificar se a incidencia pertence ao cidadao
    if incidencia.cidadao_id != cidadao_id:
        raise HTTPException(
            status_code=403,
            detail="Voce so pode enviar feedback para suas proprias incidencias"
        )

    # Verificar se a incidencia esta resolvida (status = 3)
    if incidencia.status != 3:
        raise HTTPException(
            status_code=400,
            detail="Feedback so pode ser enviado para incidencias com status 'Resolvida'"
        )

    # Verificar se ja existe feedback para esta incidencia
    feedback_existente = db.query(models.FeedbackIncidencia).filter(
        models.FeedbackIncidencia.incidencia_id == incidencia_id,
        models.FeedbackIncidencia.cidadao_id == cidadao_id
    ).first()

    if feedback_existente:
        raise HTTPException(
            status_code=400,
            detail="Voce ja enviou feedback para esta incidencia"
        )

    # Validar avaliacao (1 a 5)
    avaliacao = dados.get("avaliacao")
    if not avaliacao or not isinstance(avaliacao, int) or avaliacao < 1 or avaliacao > 5:
        raise HTTPException(
            status_code=400,
            detail="Avaliacao deve ser um numero de 1 a 5"
        )

    # Validar campo resolvido
    resolvido = dados.get("resolvido")
    if resolvido is None:
        raise HTTPException(
            status_code=400,
            detail="Campo 'resolvido' e obrigatorio (true/false)"
        )

    # Converter resolvido para inteiro
    resolvido_int = 1 if resolvido else 0

    # Criar o feedback
    novo_feedback = models.FeedbackIncidencia(
        incidencia_id=incidencia_id,
        cidadao_id=cidadao_id,
        avaliacao=avaliacao,
        comentario=dados.get("comentario", ""),
        foto_confirmacao=dados.get("foto_confirmacao", ""),
        resolvido=resolvido_int
    )

    try:
        db.add(novo_feedback)

        # Se o cidadao indicou que NAO foi resolvido, reabrir a incidencia
        if resolvido_int == 0:
            incidencia.status = 2  # Volta para "Em Andamento"
            incidencia.data_ultimo_status = datetime.now()

            # Criar interacao informando a reabertura
            interacao = models.IncidenciaInteracao(
                incidencia_id=incidencia_id,
                usuario_id=None,  # Gerado pelo sistema
                comentario=f"Incidencia reaberta pelo cidadao via feedback. Motivo: {dados.get('comentario', 'Nao especificado')}",
                status_id=2
            )
            db.add(interacao)

        db.commit()
        db.refresh(novo_feedback)

        # Adicionar pontos por feedback (gamificacao)
        try:
            resultado_pontos = await adicionar_pontos(
                cidadao_id=cidadao_id,
                motivo='feedback',
                pontos=PONTOS_FEEDBACK,
                referencia_id=novo_feedback.feedback_id,
                db=db
            )
        except Exception as e:
            print(f"[GAMIFICACAO] Erro ao adicionar pontos de feedback: {str(e)}")
            resultado_pontos = {}

        resposta = {
            "success": True,
            "message": "Feedback enviado com sucesso! Obrigado pela sua avaliacao.",
            "feedback_id": novo_feedback.feedback_id,
            "reaberto": resolvido_int == 0,
            "gamificacao": resultado_pontos
        }

        if resolvido_int == 0:
            resposta["message"] = "Feedback recebido! A incidencia foi reaberta para nova analise."

        return JSONResponse(content=resposta, media_type="application/json; charset=utf-8")

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao salvar feedback: {str(e)}")


@app.get("/api/incidencias/{incidencia_id}/feedback")
async def buscar_feedback_incidencia(
    incidencia_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Busca o feedback existente de uma incidencia.
    Retorna null se nao houver feedback.
    """
    # Obter token do header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Token nao fornecido")

    try:
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cidadao_id = payload.get("cidadao_id")

        if not cidadao_id:
            raise HTTPException(status_code=401, detail="Cidadao nao identificado no token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")

    # Validar se a incidencia existe
    incidencia = db.query(models.Incidencia).filter(
        models.Incidencia.incidencia_id == incidencia_id
    ).first()

    if not incidencia:
        raise HTTPException(status_code=404, detail="Incidencia nao encontrada")

    # Buscar feedback
    feedback = db.query(models.FeedbackIncidencia).filter(
        models.FeedbackIncidencia.incidencia_id == incidencia_id,
        models.FeedbackIncidencia.cidadao_id == cidadao_id
    ).first()

    if not feedback:
        return JSONResponse(
            content={"exists": False, "feedback": None},
            media_type="application/json; charset=utf-8"
        )

    data = {
        "exists": True,
        "feedback": {
            "feedback_id": feedback.feedback_id,
            "incidencia_id": feedback.incidencia_id,
            "cidadao_id": feedback.cidadao_id,
            "avaliacao": feedback.avaliacao,
            "comentario": feedback.comentario,
            "foto_confirmacao": feedback.foto_confirmacao,
            "resolvido": bool(feedback.resolvido),
            "data_feedback": feedback.data_feedback.isoformat() if feedback.data_feedback else None
        }
    }

    return JSONResponse(content=data, media_type="application/json; charset=utf-8")


@app.post("/api/feedback/upload-foto")
async def upload_foto_feedback(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload de foto de confirmacao para feedback.
    Retorna o caminho da foto salva.
    """
    # Obter token do header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Token nao fornecido")

    try:
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cidadao_id = payload.get("cidadao_id")

        if not cidadao_id:
            raise HTTPException(status_code=401, detail="Cidadao nao identificado no token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")

    # Validar extensao do arquivo
    extensoes_permitidas = ['.png', '.jpg', '.jpeg']
    extensao = os.path.splitext(file.filename)[1].lower()
    if extensao not in extensoes_permitidas:
        raise HTTPException(
            status_code=400,
            detail="Formato de arquivo nao permitido. Use: PNG, JPG ou JPEG"
        )

    # Validar content type
    content_types_permitidos = ['image/png', 'image/jpeg', 'image/jpg']
    if file.content_type not in content_types_permitidos:
        raise HTTPException(
            status_code=400,
            detail="Tipo de arquivo nao permitido. Envie uma imagem PNG ou JPG"
        )

    # Gerar nome unico para o arquivo
    nome_unico = f"feedback_{cidadao_id}_{uuid.uuid4().hex[:8]}{extensao}"
    caminho_arquivo = f"fotos/feedback/{nome_unico}"

    # Criar diretorio se nao existir
    os.makedirs("fotos/feedback", exist_ok=True)

    # Salvar arquivo
    try:
        content = await file.read()
        with open(caminho_arquivo, "wb") as buffer:
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {str(e)}")

    return JSONResponse(
        content={
            "success": True,
            "foto_path": f"/{caminho_arquivo}",
            "message": "Foto enviada com sucesso"
        },
        media_type="application/json; charset=utf-8"
    )


@app.get("/api/feedback/estatisticas")
async def get_estatisticas_feedback(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Retorna estatisticas de feedback para o dashboard administrativo.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise credentials_exception

    # Total de feedbacks
    total_feedbacks = db.query(func.count(models.FeedbackIncidencia.feedback_id)).join(
        models.Incidencia,
        models.FeedbackIncidencia.incidencia_id == models.Incidencia.incidencia_id
    ).filter(
        models.Incidencia.cliente_id == cliente_id
    ).scalar() or 0

    # Media de avaliacao
    media_avaliacao = db.query(func.avg(models.FeedbackIncidencia.avaliacao)).join(
        models.Incidencia,
        models.FeedbackIncidencia.incidencia_id == models.Incidencia.incidencia_id
    ).filter(
        models.Incidencia.cliente_id == cliente_id
    ).scalar() or 0.0

    # Total confirmados como resolvidos
    confirmados_resolvidos = db.query(func.count(models.FeedbackIncidencia.feedback_id)).join(
        models.Incidencia,
        models.FeedbackIncidencia.incidencia_id == models.Incidencia.incidencia_id
    ).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.FeedbackIncidencia.resolvido == 1
    ).scalar() or 0

    # Total NAO resolvidos (reabertos)
    nao_resolvidos = db.query(func.count(models.FeedbackIncidencia.feedback_id)).join(
        models.Incidencia,
        models.FeedbackIncidencia.incidencia_id == models.Incidencia.incidencia_id
    ).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.FeedbackIncidencia.resolvido == 0
    ).scalar() or 0

    # Distribuicao por avaliacao (1 a 5 estrelas)
    distribuicao = []
    for estrelas in range(1, 6):
        qtd = db.query(func.count(models.FeedbackIncidencia.feedback_id)).join(
            models.Incidencia,
            models.FeedbackIncidencia.incidencia_id == models.Incidencia.incidencia_id
        ).filter(
            models.Incidencia.cliente_id == cliente_id,
            models.FeedbackIncidencia.avaliacao == estrelas
        ).scalar() or 0
        distribuicao.append({"estrelas": estrelas, "quantidade": qtd})

    # Taxa de satisfacao (4 ou 5 estrelas)
    satisfeitos = db.query(func.count(models.FeedbackIncidencia.feedback_id)).join(
        models.Incidencia,
        models.FeedbackIncidencia.incidencia_id == models.Incidencia.incidencia_id
    ).filter(
        models.Incidencia.cliente_id == cliente_id,
        models.FeedbackIncidencia.avaliacao >= 4
    ).scalar() or 0

    taxa_satisfacao = round((satisfeitos / total_feedbacks * 100), 1) if total_feedbacks > 0 else 0.0

    data = {
        "total_feedbacks": total_feedbacks,
        "media_avaliacao": round(float(media_avaliacao), 2),
        "confirmados_resolvidos": confirmados_resolvidos,
        "nao_resolvidos": nao_resolvidos,
        "taxa_confirmacao": round((confirmados_resolvidos / total_feedbacks * 100), 1) if total_feedbacks > 0 else 0.0,
        "distribuicao_avaliacoes": distribuicao,
        "taxa_satisfacao": taxa_satisfacao,
        "total_satisfeitos": satisfeitos
    }

    return JSONResponse(content=data, media_type="application/json; charset=utf-8")


@app.get("/api/feedbacks")
async def listar_feedbacks(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    periodo: Optional[str] = None,
    categoria_id: Optional[int] = None,
    bairro: Optional[str] = None,
    avaliacao: Optional[int] = None,
    resolvido: Optional[int] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Lista todos os feedbacks recebidos com dados da incidencia e cidadao.
    Filtros opcionais: periodo (dd/mm/yyyy ate dd/mm/yyyy), categoria_id, bairro, avaliacao (1-5), resolvido (0 ou 1)
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception

    if not cliente_id:
        raise HTTPException(status_code=401, detail="Cliente nao identificado")

    # Categorias permitidas para o usuario
    categorias_permitidas = db.query(
        models.UsuarioCategoria.categoria_id
    ).filter(
        models.UsuarioCategoria.usuario_id == usuario_id
    ).all()
    categorias_ids = [cat[0] for cat in categorias_permitidas]

    # Query base com joins
    query = db.query(
        models.FeedbackIncidencia,
        models.Incidencia.incidencia_id,
        models.Incidencia.descricao.label('incidencia_descricao'),
        models.Incidencia.bairro,
        models.Incidencia.foto.label('incidencia_foto'),
        models.Categoria.nome.label('categoria_nome'),
        models.Cidadao.nome.label('cidadao_nome'),
        models.Cidadao.email.label('cidadao_email')
    ).join(
        models.Incidencia,
        models.FeedbackIncidencia.incidencia_id == models.Incidencia.incidencia_id
    ).join(
        models.Categoria,
        models.Incidencia.categoria_id == models.Categoria.categoria_id
    ).join(
        models.Cidadao,
        models.FeedbackIncidencia.cidadao_id == models.Cidadao.cidadao_id
    ).filter(
        models.Incidencia.cliente_id == cliente_id
    )

    # Filtrar por categorias permitidas
    if categorias_ids:
        query = query.filter(models.Incidencia.categoria_id.in_(categorias_ids))

    # Aplicar filtros opcionais
    # Filtro por periodo (formato: "dd/mm/yyyy ate dd/mm/yyyy")
    if periodo:
        try:
            partes = periodo.split(" ate ")
            if len(partes) == 2:
                data_inicio = datetime.strptime(partes[0].strip(), "%d/%m/%Y")
                data_fim = datetime.strptime(partes[1].strip(), "%d/%m/%Y")
                # Ajustar data_fim para incluir o dia inteiro
                data_fim = data_fim.replace(hour=23, minute=59, second=59)
                query = query.filter(
                    models.FeedbackIncidencia.data_feedback >= data_inicio,
                    models.FeedbackIncidencia.data_feedback <= data_fim
                )
        except Exception as e:
            print(f"Erro ao parsear periodo: {e}")

    # Filtro por categoria
    if categoria_id is not None:
        query = query.filter(models.Incidencia.categoria_id == categoria_id)

    # Filtro por bairro (busca parcial case-insensitive)
    if bairro:
        query = query.filter(models.Incidencia.bairro.ilike(f"%{bairro}%"))

    if avaliacao is not None:
        query = query.filter(models.FeedbackIncidencia.avaliacao == avaliacao)

    if resolvido is not None:
        query = query.filter(models.FeedbackIncidencia.resolvido == resolvido)

    # Contar total antes de paginar
    total = query.count()

    # Ordenar e paginar
    results = query.order_by(
        models.FeedbackIncidencia.data_feedback.desc()
    ).offset(offset).limit(limit).all()

    # Formatar resultados
    feedbacks = []
    for row in results:
        feedback = row[0]  # FeedbackIncidencia object
        feedbacks.append({
            "feedback_id": feedback.feedback_id,
            "incidencia_id": row.incidencia_id,
            "incidencia_descricao": row.incidencia_descricao[:100] + "..." if row.incidencia_descricao and len(row.incidencia_descricao) > 100 else row.incidencia_descricao,
            "incidencia_foto": row.incidencia_foto,
            "bairro": row.bairro,
            "categoria_nome": row.categoria_nome,
            "cidadao_nome": row.cidadao_nome,
            "cidadao_email": row.cidadao_email,
            "avaliacao": feedback.avaliacao,
            "comentario": feedback.comentario,
            "foto_confirmacao": feedback.foto_confirmacao,
            "resolvido": bool(feedback.resolvido),
            "data_feedback": feedback.data_feedback.strftime("%d/%m/%Y %H:%M") if feedback.data_feedback else None
        })

    return {
        "feedbacks": feedbacks,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.get("/api/incidencias/{incidencia_id}/feedback-info")
async def get_feedback_info_incidencia(
    incidencia_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Retorna informacoes de feedback de uma incidencia para exibicao na lista de incidencias.
    Usado para mostrar estrelas e badge na tabela de incidencias.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise credentials_exception

    # Buscar feedback da incidencia
    feedback = db.query(models.FeedbackIncidencia).filter(
        models.FeedbackIncidencia.incidencia_id == incidencia_id
    ).first()

    if not feedback:
        return {"has_feedback": False, "feedback": None}

    return {
        "has_feedback": True,
        "feedback": {
            "feedback_id": feedback.feedback_id,
            "avaliacao": feedback.avaliacao,
            "resolvido": bool(feedback.resolvido),
            "comentario": feedback.comentario,
            "data_feedback": feedback.data_feedback.strftime("%d/%m/%Y %H:%M") if feedback.data_feedback else None
        }
    }


# ============================================================
# PUSH NOTIFICATIONS - Device Token Management
# ============================================================

# Carregar FCM Server Key do .env
FCM_SERVER_KEY = os.getenv("FCM_SERVER_KEY", "")

def enviar_push_notification(token: str, titulo: str, corpo: str, dados: dict = None):
    """
    Envia push notification via Firebase Cloud Messaging (FCM).

    Args:
        token: FCM token do dispositivo
        titulo: Titulo da notificacao
        corpo: Corpo/mensagem da notificacao
        dados: Dados adicionais (ex: incidencia_id para navegacao)

    Returns:
        dict: Resultado do envio com sucesso e mensagem
    """
    import requests

    if not FCM_SERVER_KEY:
        print("[PUSH] FCM_SERVER_KEY nao configurada")
        return {"success": False, "message": "FCM_SERVER_KEY nao configurada"}

    url = "https://fcm.googleapis.com/fcm/send"

    headers = {
        "Authorization": f"key={FCM_SERVER_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "to": token,
        "notification": {
            "title": titulo,
            "body": corpo,
            "sound": "default",
            "click_action": "FLUTTER_NOTIFICATION_CLICK"
        },
        "data": dados or {},
        "priority": "high"
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        result = response.json()

        if response.status_code == 200 and result.get("success") == 1:
            print(f"[PUSH] Notificacao enviada com sucesso para token: {token[:20]}...")
            return {"success": True, "message": "Notificacao enviada"}
        else:
            print(f"[PUSH] Erro ao enviar notificacao: {result}")
            return {"success": False, "message": str(result)}
    except Exception as e:
        print(f"[PUSH] Excecao ao enviar notificacao: {str(e)}")
        return {"success": False, "message": str(e)}


def enviar_push_para_cidadao(cidadao_id: int, titulo: str, corpo: str, dados: dict, db: Session):
    """
    Envia push notification para todos os dispositivos de um cidadao.

    Args:
        cidadao_id: ID do cidadao
        titulo: Titulo da notificacao
        corpo: Corpo/mensagem da notificacao
        dados: Dados adicionais (ex: incidencia_id)
        db: Sessao do banco de dados

    Returns:
        dict: Resultado com quantidade de envios bem-sucedidos
    """
    # Buscar todos os tokens do cidadao
    tokens = db.query(models.DeviceToken).filter(
        models.DeviceToken.cidadao_id == cidadao_id
    ).all()

    if not tokens:
        print(f"[PUSH] Nenhum dispositivo registrado para cidadao {cidadao_id}")
        return {"success": False, "message": "Nenhum dispositivo registrado", "enviados": 0}

    enviados = 0
    for device_token in tokens:
        result = enviar_push_notification(device_token.token, titulo, corpo, dados)
        if result.get("success"):
            enviados += 1

    print(f"[PUSH] Enviadas {enviados}/{len(tokens)} notificacoes para cidadao {cidadao_id}")
    return {"success": enviados > 0, "message": f"Enviadas {enviados} notificacoes", "enviados": enviados}


@app.post("/api/device-tokens")
async def registrar_device_token(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Registra ou atualiza token FCM de um dispositivo.

    Body esperado:
    {
        "token": "fcm_token_string",
        "platform": "android" | "ios" | "web"
    }
    """
    # Obter token do header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Token de autenticacao nao fornecido")

    try:
        jwt_token = auth_header.split(' ')[1]
        payload = jwt.decode(jwt_token, SECRET_KEY, algorithms=[ALGORITHM])
        cidadao_id = payload.get("cidadao_id")

        if not cidadao_id:
            raise HTTPException(status_code=401, detail="Cidadao nao identificado no token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token de autenticacao invalido")

    # Obter dados do body
    dados = await request.json()
    fcm_token = dados.get("token")
    platform = dados.get("platform", "android")

    if not fcm_token:
        raise HTTPException(status_code=400, detail="Token FCM nao fornecido")

    if platform not in ["android", "ios", "web"]:
        platform = "android"  # Default

    # Verificar se o token ja existe
    existing_token = db.query(models.DeviceToken).filter(
        models.DeviceToken.token == fcm_token
    ).first()

    if existing_token:
        # Atualizar cidadao_id se mudou (mesmo dispositivo, login diferente)
        if existing_token.cidadao_id != cidadao_id:
            existing_token.cidadao_id = cidadao_id
            existing_token.platform = platform
            db.commit()
            print(f"[PUSH] Token atualizado para cidadao {cidadao_id}")
        return JSONResponse(
            content={"success": True, "message": "Token ja registrado"},
            status_code=200
        )

    # Criar novo registro
    novo_token = models.DeviceToken(
        cidadao_id=cidadao_id,
        token=fcm_token,
        platform=platform
    )

    db.add(novo_token)

    try:
        db.commit()
        print(f"[PUSH] Novo token registrado para cidadao {cidadao_id}, platform: {platform}")
        return JSONResponse(
            content={"success": True, "message": "Token registrado com sucesso"},
            status_code=201
        )
    except Exception as e:
        db.rollback()
        print(f"[PUSH] Erro ao registrar token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao registrar token: {str(e)}")


@app.delete("/api/device-tokens/{token}")
async def remover_device_token(
    token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Remove token FCM de um dispositivo (logout ou desinstalacao).
    """
    # Buscar e remover o token
    device_token = db.query(models.DeviceToken).filter(
        models.DeviceToken.token == token
    ).first()

    if not device_token:
        return JSONResponse(
            content={"success": True, "message": "Token nao encontrado"},
            status_code=200
        )

    try:
        db.delete(device_token)
        db.commit()
        print(f"[PUSH] Token removido: {token[:20]}...")
        return JSONResponse(
            content={"success": True, "message": "Token removido com sucesso"},
            status_code=200
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao remover token: {str(e)}")


# ========== ENDPOINT DE IA PARA IDENTIFICACAO DE CATEGORIA POR FOTO ==========

@app.post("/api/ia/identificar-categoria")
async def identificar_categoria_por_foto(
    dados: dict = Body(...),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Endpoint que recebe uma imagem em base64 e usa IA (GPT-4 Vision ou modelo configurado)
    para identificar automaticamente a categoria do problema urbano.

    Request Body:
        - imagem_base64: string com a imagem codificada em base64

    Returns:
        - categoria_id: ID da categoria sugerida
        - categoria_nome: Nome da categoria sugerida
        - confianca_percentual: Nivel de confianca da IA (0-100%)
        - descricao_problema: Descricao do problema identificado pela IA
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise credentials_exception

    # Obter imagem em base64
    imagem_base64 = dados.get("imagem_base64", "")
    if not imagem_base64:
        raise HTTPException(status_code=400, detail="Imagem em base64 e obrigatoria")

    # Remover prefixo data:image se existir
    if "base64," in imagem_base64:
        imagem_base64 = imagem_base64.split("base64,")[1]

    # Buscar configuracao de IA (global do sistema)
    config_ia = db.query(models.ConfigAI).first()

    if not config_ia or not config_ia.api_key:
        raise HTTPException(
            status_code=400,
            detail="Configuracao de IA nao encontrada. Configure a API key nas configuracoes."
        )

    # Buscar categorias ativas
    categorias = db.query(models.Categoria).filter(
        models.Categoria.ativo == 1
    ).all()

    if not categorias:
        raise HTTPException(status_code=400, detail="Nenhuma categoria ativa encontrada")

    # Montar lista de categorias para o prompt
    lista_categorias = []
    categorias_dict = {}
    for cat in categorias:
        lista_categorias.append(f"- ID {cat.categoria_id}: {cat.nome}")
        categorias_dict[cat.categoria_id] = cat.nome
        categorias_dict[cat.nome.lower()] = cat.categoria_id

    categorias_texto = "\n".join(lista_categorias)

    # Montar prompt para a IA
    prompt_sistema = """Voce e um assistente especializado em identificar problemas urbanos atraves de imagens.
Analise a imagem enviada e identifique qual tipo de problema urbano ela representa.
Voce deve retornar APENAS um JSON valido, sem texto adicional."""

    prompt_usuario = f"""Analise esta imagem e identifique o problema urbano mostrado.

Categorias disponiveis:
{categorias_texto}

Retorne APENAS um JSON no seguinte formato, sem explicacoes adicionais:
{{
    "categoria_id": <numero do ID da categoria mais adequada>,
    "categoria_nome": "<nome da categoria>",
    "confianca_percentual": <numero de 0 a 100 indicando sua confianca>,
    "descricao_problema": "<breve descricao do problema identificado na imagem>"
}}

Se nao conseguir identificar claramente o problema, use a categoria que mais se aproxima e indique confianca baixa.
Se a imagem nao mostrar um problema urbano, retorne confianca 0."""

    try:
        # Determinar URL da API baseado no provider
        api_url = config_ia.api_url or "https://api.openai.com/v1"
        if not api_url.endswith("/chat/completions"):
            api_url = api_url.rstrip("/") + "/chat/completions"

        # Determinar modelo - usar gpt-4o ou gpt-4-vision para analise de imagem
        modelo = config_ia.model_name or "gpt-4o"
        # Se for modelo sem visao, usar gpt-4o que tem vision
        if modelo in ["gpt-3.5-turbo", "gpt-4-turbo"]:
            modelo = "gpt-4o"

        # Fazer requisicao para a API de IA
        headers = {
            "Authorization": f"Bearer {config_ia.api_key}",
            "Content-Type": "application/json"
        }

        # Montar payload para API com visao
        payload_ia = {
            "model": modelo,
            "messages": [
                {
                    "role": "system",
                    "content": prompt_sistema
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt_usuario
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{imagem_base64}",
                                "detail": "low"  # Usar low para ser mais rapido e economico
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 500,
            "temperature": 0.3  # Baixa temperatura para respostas mais consistentes
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(api_url, headers=headers, json=payload_ia)

        if response.status_code != 200:
            print(f"Erro na API de IA: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao comunicar com a IA: {response.status_code}"
            )

        resultado_ia = response.json()

        # Extrair resposta do modelo
        resposta_texto = resultado_ia.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Tentar fazer parse do JSON da resposta
        # Remover possivel markdown
        resposta_texto = resposta_texto.strip()
        if resposta_texto.startswith("```json"):
            resposta_texto = resposta_texto[7:]
        if resposta_texto.startswith("```"):
            resposta_texto = resposta_texto[3:]
        if resposta_texto.endswith("```"):
            resposta_texto = resposta_texto[:-3]
        resposta_texto = resposta_texto.strip()

        try:
            resultado = json.loads(resposta_texto)
        except json.JSONDecodeError as e:
            print(f"Erro ao fazer parse do JSON: {e}")
            print(f"Resposta da IA: {resposta_texto}")
            # Tentar extrair informacoes manualmente
            resultado = {
                "categoria_id": categorias[0].categoria_id,
                "categoria_nome": categorias[0].nome,
                "confianca_percentual": 50,
                "descricao_problema": "Nao foi possivel analisar a imagem com precisao"
            }

        # Validar categoria_id
        categoria_id = resultado.get("categoria_id")
        if categoria_id not in categorias_dict:
            # Tentar encontrar pelo nome
            nome_sugerido = resultado.get("categoria_nome", "").lower()
            if nome_sugerido in categorias_dict:
                categoria_id = categorias_dict[nome_sugerido]
            else:
                # Usar primeira categoria como fallback
                categoria_id = categorias[0].categoria_id

        # Garantir que categoria_nome esta correto
        categoria_nome = categorias_dict.get(categoria_id, categorias[0].nome)

        # Garantir confianca entre 0 e 100
        confianca = min(100, max(0, int(resultado.get("confianca_percentual", 50))))

        return {
            "success": True,
            "categoria_id": categoria_id,
            "categoria_nome": categoria_nome,
            "confianca_percentual": confianca,
            "descricao_problema": resultado.get("descricao_problema", "Problema urbano identificado"),
            "modelo_usado": modelo
        }

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Timeout ao comunicar com a IA")
    except httpx.RequestError as e:
        print(f"Erro de requisicao: {e}")
        raise HTTPException(status_code=500, detail="Erro ao comunicar com o servico de IA")
    except Exception as e:
        print(f"Erro inesperado na identificacao de categoria: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


# ============================================================
# SISTEMA DE GAMIFICACAO - Pontos e Badges
# ============================================================

# Constantes de pontuacao
PONTOS_INCIDENCIA_ENVIADA = 10
PONTOS_INCIDENCIA_RESOLVIDA = 20
PONTOS_FEEDBACK = 5

# Niveis e seus requisitos de pontos
NIVEIS = {
    1: 0,
    2: 50,
    3: 150,
    4: 300,
    5: 500,
    6: 750,
    7: 1000,
    8: 1500,
    9: 2000,
    10: 3000
}


def calcular_nivel(pontos: int) -> int:
    """Calcula o nivel baseado nos pontos totais."""
    nivel = 1
    for n, pts in sorted(NIVEIS.items(), reverse=True):
        if pontos >= pts:
            nivel = n
            break
    return nivel


def pontos_para_proximo_nivel(pontos: int, nivel_atual: int) -> dict:
    """Retorna informacoes sobre o progresso para o proximo nivel."""
    proximo_nivel = nivel_atual + 1
    if proximo_nivel > 10:
        return {"proximo_nivel": None, "pontos_faltam": 0, "progresso_percentual": 100}

    pontos_nivel_atual = NIVEIS.get(nivel_atual, 0)
    pontos_proximo_nivel = NIVEIS.get(proximo_nivel, NIVEIS[10])
    pontos_necessarios = pontos_proximo_nivel - pontos_nivel_atual
    pontos_atuais_no_nivel = pontos - pontos_nivel_atual
    progresso = min(100, int((pontos_atuais_no_nivel / pontos_necessarios) * 100))

    return {
        "proximo_nivel": proximo_nivel,
        "pontos_faltam": max(0, pontos_proximo_nivel - pontos),
        "progresso_percentual": progresso
    }


async def adicionar_pontos(cidadao_id: int, motivo: str, pontos: int, referencia_id: int, db: Session) -> dict:
    """
    Adiciona pontos ao cidadao e verifica badges desbloqueados.

    Motivos aceitos:
    - 'incidencia_enviada': Quando cidadao cria uma nova incidencia
    - 'incidencia_resolvida': Quando uma incidencia do cidadao e resolvida
    - 'feedback': Quando cidadao envia feedback sobre resolucao

    Returns:
        dict com novos_pontos, nivel_atual, badges_desbloqueados
    """
    try:
        # Buscar ou criar registro de pontuacao
        pontuacao = db.query(models.PontuacaoCidadao).filter(
            models.PontuacaoCidadao.cidadao_id == cidadao_id
        ).first()

        if not pontuacao:
            pontuacao = models.PontuacaoCidadao(
                cidadao_id=cidadao_id,
                pontos_totais=0,
                nivel=1
            )
            db.add(pontuacao)
            db.flush()

        # Adicionar pontos
        pontuacao.pontos_totais += pontos
        novo_nivel = calcular_nivel(pontuacao.pontos_totais)
        subiu_nivel = novo_nivel > pontuacao.nivel
        pontuacao.nivel = novo_nivel

        # Registrar historico
        historico = models.HistoricoPontos(
            cidadao_id=cidadao_id,
            pontos=pontos,
            motivo=motivo,
            referencia_id=referencia_id
        )
        db.add(historico)

        # Verificar badges desbloqueados
        badges_novos = await verificar_badges(cidadao_id, db)

        db.commit()

        print(f"[GAMIFICACAO] Cidadao {cidadao_id}: +{pontos} pontos por '{motivo}'. Total: {pontuacao.pontos_totais}, Nivel: {novo_nivel}")

        return {
            "pontos_adicionados": pontos,
            "pontos_totais": pontuacao.pontos_totais,
            "nivel": novo_nivel,
            "subiu_nivel": subiu_nivel,
            "badges_novos": badges_novos
        }
    except Exception as e:
        db.rollback()
        print(f"[GAMIFICACAO] Erro ao adicionar pontos: {str(e)}")
        return {"erro": str(e)}


async def verificar_badges(cidadao_id: int, db: Session) -> list:
    """
    Verifica e concede badges que o cidadao desbloqueou.
    Retorna lista de novos badges desbloqueados.
    """
    badges_novos = []

    # Buscar todos os badges ativos
    badges = db.query(models.Badge).filter(models.Badge.ativo == 1).all()

    # Buscar badges ja conquistados pelo cidadao
    badges_conquistados = db.query(models.CidadaoBadge.badge_id).filter(
        models.CidadaoBadge.cidadao_id == cidadao_id
    ).all()
    badges_conquistados_ids = [b.badge_id for b in badges_conquistados]

    # Buscar pontuacao atual
    pontuacao = db.query(models.PontuacaoCidadao).filter(
        models.PontuacaoCidadao.cidadao_id == cidadao_id
    ).first()

    pontos_totais = pontuacao.pontos_totais if pontuacao else 0

    # Contar incidencias do cidadao
    total_incidencias = db.query(func.count(models.Incidencia.incidencia_id)).filter(
        models.Incidencia.cidadao_id == cidadao_id
    ).scalar() or 0

    # Contar incidencias resolvidas
    incidencias_resolvidas = db.query(func.count(models.Incidencia.incidencia_id)).filter(
        models.Incidencia.cidadao_id == cidadao_id,
        models.Incidencia.status == 3  # Status Resolvido
    ).scalar() or 0

    # Verificar incidencias por bairro (para badge "Guardiao do Bairro")
    incidencias_por_bairro = db.query(
        models.Incidencia.bairro,
        func.count(models.Incidencia.incidencia_id).label('total')
    ).filter(
        models.Incidencia.cidadao_id == cidadao_id,
        models.Incidencia.bairro.isnot(None)
    ).group_by(models.Incidencia.bairro).all()

    max_incidencias_bairro = max([i.total for i in incidencias_por_bairro]) if incidencias_por_bairro else 0

    for badge in badges:
        # Pular se ja conquistado
        if badge.badge_id in badges_conquistados_ids:
            continue

        desbloqueado = False

        # Verificar criterios
        if badge.criterio_tipo == 'incidencias_total':
            desbloqueado = total_incidencias >= badge.criterio_valor
        elif badge.criterio_tipo == 'incidencias_bairro':
            desbloqueado = max_incidencias_bairro >= badge.criterio_valor
        elif badge.criterio_tipo == 'resolvidas':
            desbloqueado = incidencias_resolvidas >= badge.criterio_valor
        elif badge.criterio_tipo == 'pontos':
            desbloqueado = pontos_totais >= badge.pontos_necessarios

        if desbloqueado:
            # Conceder badge
            cidadao_badge = models.CidadaoBadge(
                cidadao_id=cidadao_id,
                badge_id=badge.badge_id
            )
            db.add(cidadao_badge)

            badges_novos.append({
                "badge_id": badge.badge_id,
                "nome": badge.nome,
                "descricao": badge.descricao,
                "icone": badge.icone,
                "cor": badge.cor
            })

            print(f"[GAMIFICACAO] Cidadao {cidadao_id} desbloqueou badge: {badge.nome}")

    return badges_novos


# Criar tabelas de gamificacao e inserir badges padrao
@app.on_event("startup")
async def criar_tabelas_gamificacao():
    """Cria as tabelas de gamificacao e insere badges padrao se nao existirem."""
    try:
        with database.engine.connect() as conn:
            # Criar tabela pontuacao_cidadao
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS pontuacao_cidadao (
                    id SERIAL PRIMARY KEY,
                    cidadao_id INTEGER NOT NULL UNIQUE REFERENCES cidadao(cidadao_id),
                    pontos_totais INTEGER DEFAULT 0,
                    nivel INTEGER DEFAULT 1,
                    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Criar tabela badge
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS badge (
                    badge_id SERIAL PRIMARY KEY,
                    nome VARCHAR(100) NOT NULL,
                    descricao VARCHAR(300),
                    icone VARCHAR(50) DEFAULT 'star',
                    cor VARCHAR(7) DEFAULT '#FFD700',
                    pontos_necessarios INTEGER DEFAULT 0,
                    criterio_tipo VARCHAR(50),
                    criterio_valor INTEGER DEFAULT 1,
                    ativo INTEGER DEFAULT 1
                )
            """))

            # Criar tabela cidadao_badge
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS cidadao_badge (
                    id SERIAL PRIMARY KEY,
                    cidadao_id INTEGER NOT NULL REFERENCES cidadao(cidadao_id),
                    badge_id INTEGER NOT NULL REFERENCES badge(badge_id),
                    data_conquista TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(cidadao_id, badge_id)
                )
            """))

            # Criar tabela historico_pontos
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS historico_pontos (
                    id SERIAL PRIMARY KEY,
                    cidadao_id INTEGER NOT NULL REFERENCES cidadao(cidadao_id),
                    pontos INTEGER NOT NULL,
                    motivo VARCHAR(100) NOT NULL,
                    referencia_id INTEGER,
                    data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            conn.commit()
            print("[GAMIFICACAO] Tabelas de gamificacao criadas/verificadas com sucesso!")

            # Inserir badges padrao se nao existirem
            result = conn.execute(text("SELECT COUNT(*) FROM badge")).fetchone()
            if result[0] == 0:
                badges_padrao = [
                    ("Primeiro Passo", "Enviou sua primeira incidencia", "flag", "#4CAF50", 10, "incidencias_total", 1),
                    ("Guardiao do Bairro", "5 incidencias no mesmo bairro", "shield", "#2196F3", 50, "incidencias_bairro", 5),
                    ("Cidadao Ativo", "10 incidencias enviadas", "verified_user", "#9C27B0", 100, "incidencias_total", 10),
                    ("Fiscal Urbano", "25 incidencias enviadas", "search", "#FF9800", 250, "incidencias_total", 25),
                    ("Agente de Mudanca", "50 incidencias resolvidas", "stars", "#FFD700", 500, "resolvidas", 50),
                    ("Colaborador Bronze", "Acumulou 100 pontos", "emoji_events", "#CD7F32", 100, "pontos", 100),
                    ("Colaborador Prata", "Acumulou 500 pontos", "emoji_events", "#C0C0C0", 500, "pontos", 500),
                    ("Colaborador Ouro", "Acumulou 1000 pontos", "emoji_events", "#FFD700", 1000, "pontos", 1000),
                ]

                for nome, descricao, icone, cor, pontos_necessarios, criterio_tipo, criterio_valor in badges_padrao:
                    conn.execute(text("""
                        INSERT INTO badge (nome, descricao, icone, cor, pontos_necessarios, criterio_tipo, criterio_valor)
                        VALUES (:nome, :descricao, :icone, :cor, :pontos_necessarios, :criterio_tipo, :criterio_valor)
                    """), {
                        "nome": nome,
                        "descricao": descricao,
                        "icone": icone,
                        "cor": cor,
                        "pontos_necessarios": pontos_necessarios,
                        "criterio_tipo": criterio_tipo,
                        "criterio_valor": criterio_valor
                    })

                conn.commit()
                print("[GAMIFICACAO] Badges padrao inseridos com sucesso!")

    except Exception as e:
        print(f"[GAMIFICACAO] Erro ao criar tabelas: {str(e)}")


@app.get("/api/cidadaos/{cidadao_id}/pontuacao")
async def get_pontuacao_cidadao(
    cidadao_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Retorna a pontuacao, nivel e badges de um cidadao.
    """
    # Validar token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Token nao fornecido")

    try:
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_cidadao_id = payload.get("cidadao_id")

        # Permitir apenas consultar propria pontuacao ou admin
        if token_cidadao_id != cidadao_id and payload.get("tipo") != "admin":
            # Para admins, verificar se tem nivel alto
            if payload.get("nivel") is None or payload.get("nivel") > 2:
                raise HTTPException(status_code=403, detail="Acesso nao autorizado")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")

    # Buscar ou criar pontuacao
    pontuacao = db.query(models.PontuacaoCidadao).filter(
        models.PontuacaoCidadao.cidadao_id == cidadao_id
    ).first()

    if not pontuacao:
        # Criar registro inicial
        pontuacao = models.PontuacaoCidadao(
            cidadao_id=cidadao_id,
            pontos_totais=0,
            nivel=1
        )
        db.add(pontuacao)
        db.commit()
        db.refresh(pontuacao)

    # Calcular progresso para proximo nivel
    progresso = pontos_para_proximo_nivel(pontuacao.pontos_totais, pontuacao.nivel)

    # Buscar badges do cidadao
    badges_cidadao = db.query(
        models.Badge.badge_id,
        models.Badge.nome,
        models.Badge.descricao,
        models.Badge.icone,
        models.Badge.cor,
        models.CidadaoBadge.data_conquista
    ).join(
        models.CidadaoBadge,
        models.Badge.badge_id == models.CidadaoBadge.badge_id
    ).filter(
        models.CidadaoBadge.cidadao_id == cidadao_id
    ).all()

    badges_conquistados = [
        {
            "badge_id": b.badge_id,
            "nome": b.nome,
            "descricao": b.descricao,
            "icone": b.icone,
            "cor": b.cor,
            "data_conquista": b.data_conquista.isoformat() if b.data_conquista else None,
            "conquistado": True
        }
        for b in badges_cidadao
    ]

    # Buscar todos os badges para mostrar os nao conquistados
    todos_badges = db.query(models.Badge).filter(models.Badge.ativo == 1).all()
    badges_conquistados_ids = [b["badge_id"] for b in badges_conquistados]

    badges_nao_conquistados = [
        {
            "badge_id": b.badge_id,
            "nome": b.nome,
            "descricao": b.descricao,
            "icone": b.icone,
            "cor": b.cor,
            "pontos_necessarios": b.pontos_necessarios,
            "conquistado": False
        }
        for b in todos_badges if b.badge_id not in badges_conquistados_ids
    ]

    # Buscar estatisticas
    total_incidencias = db.query(func.count(models.Incidencia.incidencia_id)).filter(
        models.Incidencia.cidadao_id == cidadao_id
    ).scalar() or 0

    incidencias_resolvidas = db.query(func.count(models.Incidencia.incidencia_id)).filter(
        models.Incidencia.cidadao_id == cidadao_id,
        models.Incidencia.status == 3
    ).scalar() or 0

    data = {
        "cidadao_id": cidadao_id,
        "pontos_totais": pontuacao.pontos_totais,
        "nivel": pontuacao.nivel,
        "proximo_nivel": progresso["proximo_nivel"],
        "pontos_faltam": progresso["pontos_faltam"],
        "progresso_percentual": progresso["progresso_percentual"],
        "badges_conquistados": badges_conquistados,
        "badges_disponiveis": badges_nao_conquistados,
        "total_badges": len(badges_conquistados),
        "estatisticas": {
            "total_incidencias": total_incidencias,
            "incidencias_resolvidas": incidencias_resolvidas
        }
    }

    return JSONResponse(content=data, media_type="application/json; charset=utf-8")


@app.get("/api/badges")
async def get_badges(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Lista todos os badges disponiveis no sistema.
    """
    # Validar token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Token nao fornecido")

    try:
        token = auth_header.split(' ')[1]
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")

    badges = db.query(models.Badge).filter(models.Badge.ativo == 1).order_by(
        models.Badge.pontos_necessarios
    ).all()

    data = [
        {
            "badge_id": b.badge_id,
            "nome": b.nome,
            "descricao": b.descricao,
            "icone": b.icone,
            "cor": b.cor,
            "pontos_necessarios": b.pontos_necessarios,
            "criterio_tipo": b.criterio_tipo,
            "criterio_valor": b.criterio_valor
        }
        for b in badges
    ]

    return JSONResponse(content=data, media_type="application/json; charset=utf-8")


@app.get("/api/ranking")
async def get_ranking(
    request: Request,
    limite: int = 10,
    db: Session = Depends(get_db)
):
    """
    Retorna o ranking dos cidadaos com mais pontos.
    """
    # Validar token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Token nao fornecido")

    try:
        token = auth_header.split(' ')[1]
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")

    # Buscar top cidadaos por pontuacao
    ranking = db.query(
        models.PontuacaoCidadao.cidadao_id,
        models.PontuacaoCidadao.pontos_totais,
        models.PontuacaoCidadao.nivel,
        models.Cidadao.nome,
        models.Cidadao.foto
    ).join(
        models.Cidadao,
        models.PontuacaoCidadao.cidadao_id == models.Cidadao.cidadao_id
    ).order_by(
        models.PontuacaoCidadao.pontos_totais.desc()
    ).limit(limite).all()

    data = [
        {
            "posicao": idx + 1,
            "cidadao_id": r.cidadao_id,
            "nome": r.nome,
            "foto": r.foto,
            "pontos_totais": r.pontos_totais,
            "nivel": r.nivel
        }
        for idx, r in enumerate(ranking)
    ]

    return JSONResponse(content=data, media_type="application/json; charset=utf-8")


# ========== PAGINA DE RANKING ==========

@app.get("/ranking", response_class=HTMLResponse)
async def pagina_ranking(request: Request):
    """
    Pagina de ranking/gamificacao com top cidadaos mais ativos.
    """
    return templates.TemplateResponse("ranking.html", {"request": request})


@app.get("/api/ranking/estatisticas")
async def get_ranking_estatisticas(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Retorna estatisticas gerais de engajamento e gamificacao.
    """
    # Validar token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Token nao fornecido")

    try:
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido")

    # Total de incidencias reportadas
    total_incidencias = db.query(func.count(models.Incidencia.incidencia_id)).filter(
        models.Incidencia.cliente_id == cliente_id
    ).scalar() or 0

    # Total de cidadaos participantes (com pelo menos 1 ponto)
    total_participantes = db.query(func.count(models.PontuacaoCidadao.id)).filter(
        models.PontuacaoCidadao.pontos_totais > 0
    ).scalar() or 0

    # Total de pontos distribuidos
    total_pontos = db.query(func.sum(models.PontuacaoCidadao.pontos_totais)).scalar() or 0

    # Total de badges conquistados
    total_badges = db.query(func.count(models.CidadaoBadge.id)).scalar() or 0

    data = {
        "total_incidencias": total_incidencias,
        "total_participantes": total_participantes,
        "total_pontos": total_pontos,
        "total_badges": total_badges
    }

    return JSONResponse(content=data, media_type="application/json; charset=utf-8")


# ========== ENDPOINTS POSTGREST-LIKE PARA APP FLUTTER ==========
# Esses endpoints substituem o PostgREST que estava na porta 33005

@app.get("/incidencia")
async def postgrest_incidencia(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint PostgREST-like para buscar incidencias.
    Aceita parametros como: cidadao_id=eq.11, categoria_id=eq.4, status=neq.3, order=data_hora.desc
    """
    params = dict(request.query_params)

    query = db.query(models.Incidencia)

    # Processar cada parametro de filtro
    for key, value in params.items():
        if key == 'order':
            # Ordenacao: order=data_hora.desc ou order=data_hora.asc
            parts = value.split('.')
            col_name = parts[0]
            direction = parts[1] if len(parts) > 1 else 'asc'
            if hasattr(models.Incidencia, col_name):
                col = getattr(models.Incidencia, col_name)
                query = query.order_by(col.desc() if direction == 'desc' else col.asc())
        elif key == 'select':
            # Ignorar select por enquanto (retornamos tudo)
            continue
        elif value.startswith('eq.'):
            # Igual: campo=eq.valor
            val = value[3:]
            if hasattr(models.Incidencia, key):
                query = query.filter(getattr(models.Incidencia, key) == val)
        elif value.startswith('neq.'):
            # Diferente: campo=neq.valor
            val = value[4:]
            if hasattr(models.Incidencia, key):
                query = query.filter(getattr(models.Incidencia, key) != val)
        elif value.startswith('gt.'):
            # Maior que
            val = value[3:]
            if hasattr(models.Incidencia, key):
                query = query.filter(getattr(models.Incidencia, key) > val)
        elif value.startswith('lt.'):
            # Menor que
            val = value[3:]
            if hasattr(models.Incidencia, key):
                query = query.filter(getattr(models.Incidencia, key) < val)

    results = query.all()

    # Converter para lista de dicionarios
    data = []
    for inc in results:
        data.append({
            "incidencia_id": inc.incidencia_id,
            "cidadao_id": inc.cidadao_id,
            "categoria_id": inc.categoria_id,
            "foto": inc.foto,
            "status": inc.status,
            "descricao": inc.descricao,
            "prioridade": inc.prioridade,
            "cliente_id": inc.cliente_id,
            "endereco": inc.endereco,
            "bairro": inc.bairro,
            "cidade": inc.cidade,
            "estado": inc.estado,
            "lat": str(inc.lat) if inc.lat else None,
            "long": str(inc.long) if inc.long else None,
            "data_hora": inc.data_hora.isoformat() if inc.data_hora else None,
            "data_ultimo_status": inc.data_ultimo_status.isoformat() if inc.data_ultimo_status else None,
            "cep": inc.cep if hasattr(inc, 'cep') else None,
            "codigo_acompanhamento": inc.codigo_acompanhamento if hasattr(inc, 'codigo_acompanhamento') else None
        })

    return JSONResponse(content=data, media_type="application/json; charset=utf-8")


@app.get("/cidadao")
async def postgrest_cidadao(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint PostgREST-like para buscar cidadaos.
    """
    params = dict(request.query_params)

    query = db.query(models.Cidadao)

    for key, value in params.items():
        if key == 'select':
            continue
        elif key.startswith('and='):
            # Filtro AND complexo - simplificar por enquanto
            continue
        elif value.startswith('eq.'):
            val = value[3:]
            if hasattr(models.Cidadao, key):
                query = query.filter(getattr(models.Cidadao, key) == val)

    results = query.all()

    data = []
    for cid in results:
        data.append({
            "cidadao_id": cid.cidadao_id,
            "nome": cid.nome,
            "email": cid.email,
            "celular": cid.celular if hasattr(cid, 'celular') else None,
            "endereco": cid.endereco,
            "bairro": cid.bairro,
            "cep": cid.cep,
            "cidade": cid.cidade,
            "estado": cid.estado,
            "foto": cid.foto if hasattr(cid, 'foto') else None,
            "ativo": cid.ativo
        })

    return JSONResponse(content=data, media_type="application/json; charset=utf-8")


@app.get("/categoria")
async def postgrest_categoria(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint PostgREST-like para buscar categorias.
    """
    params = dict(request.query_params)

    query = db.query(models.Categoria)

    for key, value in params.items():
        if key == 'select':
            continue
        elif value.startswith('eq.'):
            val = value[3:]
            if hasattr(models.Categoria, key):
                query = query.filter(getattr(models.Categoria, key) == val)

    results = query.all()

    data = []
    for cat in results:
        data.append({
            "categoria_id": cat.categoria_id,
            "nome": cat.nome,
            "descricao": cat.descricao,
            "icone": cat.icone,
            "cor": cat.cor,
            "ativo": cat.ativo
        })

    return JSONResponse(content=data, media_type="application/json; charset=utf-8")


@app.get("/status_lista")
async def postgrest_status(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint PostgREST-like para buscar status.
    Renomeado para /status_lista para evitar conflito com rota HTML /status
    """
    params = dict(request.query_params)

    query = db.query(models.Status)

    for key, value in params.items():
        if key == 'select':
            continue
        elif value.startswith('eq.'):
            val = value[3:]
            if hasattr(models.Status, key):
                query = query.filter(getattr(models.Status, key) == val)

    results = query.all()

    data = []
    for st in results:
        data.append({
            "status_id": st.status_id,
            "nome": st.nome,
            "descricao": st.descricao if hasattr(st, 'descricao') else None,
            "ativo": st.ativo if hasattr(st, 'ativo') else 1
        })

    return JSONResponse(content=data, media_type="application/json; charset=utf-8")


@app.get("/prioridade")
async def postgrest_prioridade(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint PostgREST-like para buscar prioridades.
    """
    params = dict(request.query_params)

    query = db.query(models.Prioridade)

    for key, value in params.items():
        if key == 'select':
            continue
        elif value.startswith('eq.'):
            val = value[3:]
            if hasattr(models.Prioridade, key):
                query = query.filter(getattr(models.Prioridade, key) == val)

    results = query.all()

    data = []
    for pr in results:
        data.append({
            "prioridade_id": pr.prioridade_id,
            "nome": pr.nome,
            "descricao": pr.descricao if hasattr(pr, 'descricao') else None
        })

    return JSONResponse(content=data, media_type="application/json; charset=utf-8")


# ========== ENDPOINT PUBLICO PARA COMPARTILHAMENTO (SEM AUTENTICACAO) ==========

@app.get("/api/incidencias/{incidencia_id}/publico")
async def incidencia_publica(
    incidencia_id: int,
    db: Session = Depends(get_db)
):
    """
    Retorna dados publicos de uma incidencia para compartilhamento em redes sociais.
    NAO requer autenticacao - ideal para preview em WhatsApp, Facebook, Twitter.

    Retorna:
    - foto: URL da foto principal
    - categoria: Nome da categoria
    - bairro: Localizacao
    - status: Status atual com cor
    - data: Data de abertura formatada
    - resumo: Texto para preview
    """
    # Buscar a incidencia
    incidencia = db.query(models.Incidencia).filter(
        models.Incidencia.incidencia_id == incidencia_id
    ).first()

    if not incidencia:
        raise HTTPException(
            status_code=404,
            detail=f"Incidencia com ID {incidencia_id} nao encontrada"
        )

    # Buscar categoria
    categoria = db.query(models.Categoria).filter(
        models.Categoria.categoria_id == incidencia.categoria_id
    ).first()

    # Buscar status atual
    status_atual = db.query(models.Status).filter(
        models.Status.status_id == incidencia.status
    ).first()

    # Buscar cliente para logo
    cliente = db.query(models.Cliente).filter(
        models.Cliente.cliente_id == incidencia.cliente_id
    ).first() if hasattr(incidencia, 'cliente_id') and incidencia.cliente_id else None

    # Mapear cor do status
    def get_status_cor(status_nome: str) -> str:
        if not status_nome:
            return "#607D8B"
        status_lower = status_nome.lower()
        if "resolv" in status_lower or "conclu" in status_lower or "finaliz" in status_lower:
            return "#4CAF50"  # Verde
        elif "andamento" in status_lower or "execu" in status_lower or "trabalh" in status_lower:
            return "#FF9800"  # Laranja
        elif "analis" in status_lower or "avali" in status_lower or "verific" in status_lower:
            return "#2196F3"  # Azul
        elif "cancel" in status_lower or "rejeit" in status_lower:
            return "#F44336"  # Vermelho
        else:
            return "#9E9E9E"  # Cinza

    # Formatar data
    data_formatada = None
    if incidencia.data_hora:
        data_formatada = incidencia.data_hora.strftime("%d/%m/%Y")

    # Construir URL da foto
    foto_url = None
    if incidencia.foto:
        # Se ja e uma URL completa, usa direto
        if incidencia.foto.startswith('http'):
            foto_url = incidencia.foto
        else:
            # Constroi URL baseada no servidor
            foto_url = f"/fotos/{incidencia.foto}"

    # Montar resposta
    response_data = {
        "incidencia_id": incidencia.incidencia_id,
        "foto": foto_url,
        "categoria": categoria.nome if categoria else "Sem categoria",
        "categoria_icone": categoria.icone if categoria and hasattr(categoria, 'icone') else None,
        "bairro": incidencia.bairro or "Bairro nao informado",
        "endereco": incidencia.endereco,
        "status": {
            "nome": status_atual.nome if status_atual else "Pendente",
            "cor": get_status_cor(status_atual.nome if status_atual else "")
        },
        "data_abertura": data_formatada,
        "data_iso": incidencia.data_hora.isoformat() if incidencia.data_hora else None,
        "descricao": incidencia.descricao[:200] + "..." if incidencia.descricao and len(incidencia.descricao) > 200 else incidencia.descricao,
        "cliente": {
            "nome": cliente.nome if cliente else "Governa Facil",
            "logo": cliente.logo if cliente and hasattr(cliente, 'logo') else None
        } if cliente else None,
        "resumo": f"{categoria.nome if categoria else 'Incidencia'} em {incidencia.bairro or 'local nao informado'} - Status: {status_atual.nome if status_atual else 'Pendente'}"
    }

    return JSONResponse(
        content=response_data,
        media_type="application/json; charset=utf-8"
    )


@app.patch("/incidencia")
async def postgrest_incidencia_patch(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint PostgREST-like para atualizar incidencias.
    """
    params = dict(request.query_params)
    body = await request.json()

    query = db.query(models.Incidencia)

    for key, value in params.items():
        if value.startswith('eq.'):
            val = value[3:]
            if hasattr(models.Incidencia, key):
                query = query.filter(getattr(models.Incidencia, key) == val)

    # Atualizar registros
    count = 0
    for inc in query.all():
        for field, val in body.items():
            if hasattr(inc, field):
                setattr(inc, field, val)
        count += 1

    db.commit()

    return JSONResponse(content={"updated": count}, media_type="application/json; charset=utf-8")


# ========== CHATBOT DE SUPORTE PARA APP MOBILE ==========

@app.post("/api/chatbot/mensagem")
async def chatbot_mensagem(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Endpoint do chatbot de suporte para o app mobile Governa Facil.
    Usa OpenAI GPT para responder perguntas sobre o sistema de incidencias urbanas.
    Pode consultar incidencias do usuario para respostas contextuais.
    """
    import requests as http_requests

    # Validar token e obter dados do usuario
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
        cidadao_id = payload.get("cidadao_id")
        usuario_nome = payload.get("nome", "Cidadao")
    except JWTError:
        raise credentials_exception

    # Obter mensagem do body
    dados = await request.json()
    mensagem = dados.get("mensagem", "").strip()

    if not mensagem:
        return {"resposta": "Por favor, digite uma mensagem."}

    print(f"[CHATBOT] ========== NOVA MENSAGEM ==========", flush=True)
    print(f"[CHATBOT] Cidadao ID: {cidadao_id}", flush=True)
    print(f"[CHATBOT] Mensagem: {mensagem}", flush=True)

    # Buscar configuracao de IA do cliente
    try:
        config = await get_config_ia(token, db)

        if not config.get("api_key"):
            return {"resposta": "Desculpe, o assistente virtual nao esta configurado no momento. Tente novamente mais tarde."}

    except Exception as e:
        print(f"[CHATBOT] Erro ao buscar config IA: {e}", flush=True)
        return {"resposta": "Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente."}

    # Extrair configuracoes
    api_key = config["api_key"]
    api_url = config.get("api_url", "https://api.openai.com/v1")
    modelo = config.get("model_name", "gpt-4o")
    temperatura = (config.get("temperature", 7)) / 10
    max_tokens = min(config.get("max_tokens", 2048), 2048)
    timeout = config.get("timeout", 60)

    # Buscar contexto do usuario (incidencias)
    contexto_usuario = ""
    try:
        if cidadao_id:
            # Buscar incidencias do cidadao
            incidencias = db.query(models.Incidencia).filter(
                models.Incidencia.cidadao_id == cidadao_id
            ).order_by(models.Incidencia.data_hora.desc()).limit(10).all()

            if incidencias:
                contexto_usuario = "\n\n=== INCIDENCIAS DO CIDADAO ===\n"
                for inc in incidencias:
                    # Buscar categoria
                    categoria = db.query(models.Categoria).filter(
                        models.Categoria.categoria_id == inc.categoria_id
                    ).first()
                    categoria_nome = categoria.nome if categoria else "Sem categoria"

                    # Mapear status
                    status_map = {1: "Aberta", 2: "Em Andamento", 3: "Concluida"}
                    status_nome = status_map.get(inc.status, "Desconhecido")

                    # Data formatada
                    data_str = inc.data_hora.strftime("%d/%m/%Y") if inc.data_hora else "Sem data"

                    contexto_usuario += f"- #{inc.incidencia_id}: {categoria_nome} em {inc.bairro or 'local nao informado'} - Status: {status_nome} - Data: {data_str}\n"

                contexto_usuario += "=== FIM DAS INCIDENCIAS ===\n"
                print(f"[CHATBOT] Encontradas {len(incidencias)} incidencias do cidadao", flush=True)
            else:
                contexto_usuario = "\n\nO cidadao ainda nao tem incidencias registradas.\n"
                print(f"[CHATBOT] Cidadao sem incidencias", flush=True)
    except Exception as e:
        print(f"[CHATBOT] Erro ao buscar incidencias: {e}", flush=True)

    # Buscar estatisticas gerais do sistema
    estatisticas_sistema = ""
    try:
        # Total de incidencias por status
        total_abertas = db.query(func.count(models.Incidencia.incidencia_id)).filter(
            models.Incidencia.cliente_id == cliente_id,
            models.Incidencia.status == 1
        ).scalar() or 0

        total_andamento = db.query(func.count(models.Incidencia.incidencia_id)).filter(
            models.Incidencia.cliente_id == cliente_id,
            models.Incidencia.status == 2
        ).scalar() or 0

        total_concluidas = db.query(func.count(models.Incidencia.incidencia_id)).filter(
            models.Incidencia.cliente_id == cliente_id,
            models.Incidencia.status == 3
        ).scalar() or 0

        total_geral = total_abertas + total_andamento + total_concluidas

        # Total de cidadaos ativos
        total_cidadaos = db.query(func.count(models.Cidadao.cidadao_id)).filter(
            models.Cidadao.cliente_id == cliente_id,
            models.Cidadao.ativo == 1
        ).scalar() or 0

        # Taxa de resolucao
        taxa_resolucao = round((total_concluidas / total_geral * 100), 1) if total_geral > 0 else 0

        estatisticas_sistema = f"""

=== ESTATISTICAS GERAIS DO SISTEMA ===
- Total de incidencias: {total_geral}
- Incidencias abertas: {total_abertas}
- Incidencias em andamento: {total_andamento}
- Incidencias concluidas: {total_concluidas}
- Taxa de resolucao: {taxa_resolucao}%
- Total de cidadaos ativos: {total_cidadaos}
=== FIM DAS ESTATISTICAS ===
"""
        print(f"[CHATBOT] Estatisticas carregadas", flush=True)
    except Exception as e:
        print(f"[CHATBOT] Erro ao buscar estatisticas: {e}", flush=True)

    # Prompt do sistema para o chatbot
    system_prompt = f"""Voce e o assistente virtual do app Governa Facil, um sistema de gestao de incidencias urbanas usado por cidadaos para reportar problemas na cidade.

SOBRE O SISTEMA:
- Os cidadaos podem reportar problemas como buracos, iluminacao publica, lixo, calcadas danificadas, etc.
- Cada problema reportado e chamado de "incidencia"
- As incidencias passam por status: Aberta (1) -> Em Andamento (2) -> Concluida (3)
- Os cidadaos ganham pontos por reportar problemas (gamificacao)
- Ha um ranking de cidadaos mais ativos
- O tempo medio de resolucao varia conforme a categoria e complexidade

COMO REPORTAR UM PROBLEMA:
1. Clique no botao de camera (reportar) na tela inicial
2. Tire uma foto do problema ou selecione da galeria
3. A IA ira sugerir automaticamente a categoria
4. Confirme a localizacao no mapa
5. Adicione uma descricao detalhada
6. Envie a incidencia

SISTEMA DE PONTOS:
- Cada incidencia reportada vale pontos
- Incidencias validadas e resolvidas dao bonus
- Ha badges e conquistas por participacao
- O ranking mostra os cidadaos mais engajados

TEMPO DE RESOLUCAO:
- Problemas simples: 7 a 15 dias
- Problemas complexos: 15 a 45 dias
- Emergencias: atendimento prioritario

REGRAS DE COMPORTAMENTO:
1. Seja sempre educado, prestativo e amigavel
2. Responda em portugues brasileiro
3. Use linguagem simples e acessivel
4. Se nao souber a resposta, seja honesto
5. Sugira usar o app para reportar novos problemas
6. Incentive a participacao cidada
7. Mantenha respostas concisas (max 3 paragrafos)
8. NAO invente dados ou numeros - use apenas as informacoes fornecidas
9. Quando perguntarem sobre estatisticas, use os dados fornecidos abaixo
{contexto_usuario}{estatisticas_sistema}"""

    try:
        # Montar URL da API
        final_api_url = api_url.rstrip('/') + '/chat/completions' if not api_url.endswith('/chat/completions') else api_url

        print(f"[CHATBOT] Enviando para: {final_api_url}", flush=True)
        print(f"[CHATBOT] Modelo: {modelo}", flush=True)

        # Fazer requisicao para a API
        response = http_requests.post(
            final_api_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "model": modelo,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": mensagem}
                ],
                "max_tokens": max_tokens,
                "temperature": temperatura
            },
            timeout=timeout
        )

        print(f"[CHATBOT] Status da resposta: {response.status_code}", flush=True)

        if response.status_code == 200:
            # Garantir que a resposta seja decodificada como UTF-8
            response.encoding = 'utf-8'
            result = response.json()
            resposta = result["choices"][0]["message"]["content"].strip()
            print(f"[CHATBOT] Resposta gerada com {len(resposta)} caracteres", flush=True)
            return JSONResponse(
                content={"resposta": resposta},
                media_type="application/json; charset=utf-8"
            )
        else:
            error_detail = response.text[:200] if response.text else "Erro desconhecido"
            print(f"[CHATBOT] Erro da API: {response.status_code} - {error_detail}", flush=True)
            return JSONResponse(
                content={"resposta": "Desculpe, estou com dificuldades técnicas no momento. Tente novamente em alguns instantes."},
                media_type="application/json; charset=utf-8"
            )

    except http_requests.exceptions.Timeout:
        print(f"[CHATBOT] Timeout na requisicao", flush=True)
        return JSONResponse(
            content={"resposta": "Desculpe, a resposta está demorando muito. Tente novamente."},
            media_type="application/json; charset=utf-8"
        )
    except http_requests.exceptions.RequestException as e:
        print(f"[CHATBOT] Erro de conexao: {e}", flush=True)
        return JSONResponse(
            content={"resposta": "Desculpe, não foi possível conectar ao servidor. Verifique sua conexão."},
            media_type="application/json; charset=utf-8"
        )
    except Exception as e:
        print(f"[CHATBOT] Erro inesperado: {e}", flush=True)
        return JSONResponse(
            content={"resposta": "Desculpe, ocorreu um erro inesperado. Tente novamente mais tarde."},
            media_type="application/json; charset=utf-8"
        )


# ========== ENDPOINT POSTGREST-LIKE POST /incidencia (SUPORTA ANONIMO) ==========

import random
import string

def gerar_codigo_acompanhamento():
    """Gera codigo unico para acompanhamento de incidencia anonima: INC-ABC123"""
    letras = ''.join(random.choices(string.ascii_uppercase, k=3))
    numeros = ''.join(random.choices(string.digits, k=3))
    return f"INC-{letras}{numeros}"


@app.post("/incidencia")
async def postgrest_incidencia_post(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint PostgREST-like para criar incidencias via POST.
    Suporta modo anonimo - quando anonimo=true, cidadao_id sera NULL
    e um codigo de acompanhamento sera gerado.

    Body esperado:
    {
        "categoria_id": int,
        "cidadao_id": int (opcional se anonimo),
        "foto": "path/da/foto",
        "status": 1,
        "descricao": "descricao do problema",
        "prioridade": int,
        "cliente_id": int,
        "lat": "latitude",
        "long": "longitude",
        "endereco": "endereco completo",
        "cidade": "cidade",
        "estado": "UF",
        "bairro": "bairro",
        "anonimo": bool (opcional, default false)
    }
    """
    try:
        body = await request.json()
    except:
        raise HTTPException(status_code=400, detail="JSON invalido")

    # Verificar campos obrigatorios
    if not body.get("categoria_id"):
        raise HTTPException(status_code=400, detail="categoria_id e obrigatorio")

    # Verificar modo anonimo
    is_anonimo = body.get("anonimo", False)
    cidadao_id = None if is_anonimo else body.get("cidadao_id")
    codigo_acompanhamento = None

    # Se nao for anonimo, cidadao_id e obrigatorio
    if not is_anonimo and not cidadao_id:
        raise HTTPException(status_code=400, detail="cidadao_id e obrigatorio quando nao e anonimo")

    # Gerar codigo de acompanhamento para incidencias anonimas
    if is_anonimo:
        # Garantir unicidade do codigo
        for _ in range(10):
            codigo_acompanhamento = gerar_codigo_acompanhamento()
            existente = db.query(models.Incidencia).filter(
                models.Incidencia.codigo_acompanhamento == codigo_acompanhamento
            ).first()
            if not existente:
                break

    # Criar a incidencia
    nova_incidencia = models.Incidencia(
        categoria_id=body.get('categoria_id'),
        cidadao_id=cidadao_id,
        descricao=body.get('descricao', ''),
        prioridade=body.get('prioridade', 4),
        endereco=body.get('endereco', ''),
        bairro=body.get('bairro', ''),
        cidade=body.get('cidade', ''),
        estado=body.get('estado', ''),
        cep=body.get('cep', ''),
        lat=body.get('lat', ''),
        long=body.get('long', ''),
        foto=body.get('foto', ''),
        status=body.get('status', 1),
        cliente_id=body.get('cliente_id', 1),
        codigo_acompanhamento=codigo_acompanhamento
    )

    try:
        db.add(nova_incidencia)
        db.commit()
        db.refresh(nova_incidencia)

        resposta = {
            "success": True,
            "message": "Incidencia criada com sucesso!",
            "incidencia_id": nova_incidencia.incidencia_id,
            "anonimo": is_anonimo
        }

        # Incluir codigo de acompanhamento se for anonimo
        if is_anonimo and codigo_acompanhamento:
            resposta["codigo_acompanhamento"] = codigo_acompanhamento
            resposta["message"] = f"Incidencia anonima criada! Seu codigo de acompanhamento: {codigo_acompanhamento}"

        # Se nao for anonimo, adicionar pontos (gamificacao)
        if not is_anonimo and cidadao_id:
            try:
                resultado_pontos = await adicionar_pontos(
                    cidadao_id=cidadao_id,
                    motivo='incidencia_enviada',
                    pontos=PONTOS_INCIDENCIA_ENVIADA,
                    referencia_id=nova_incidencia.incidencia_id,
                    db=db
                )
                resposta["gamificacao"] = resultado_pontos
            except Exception as e:
                print(f"[GAMIFICACAO] Erro ao adicionar pontos: {str(e)}")

        return JSONResponse(content=resposta, status_code=201, media_type="application/json; charset=utf-8")

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar incidencia: {str(e)}")


# ========== ENDPOINT PARA CONSULTAR INCIDENCIA POR CODIGO (SEM LOGIN) ==========

@app.get("/api/incidencias/consultar/{codigo}")
async def consultar_incidencia_por_codigo(
    codigo: str,
    db: Session = Depends(get_db)
):
    """
    Consulta o status de uma incidencia pelo codigo de acompanhamento.
    NAO requer autenticacao - usado para incidencias anonimas.

    Parametros:
    - codigo: Codigo de acompanhamento (ex: INC-ABC123)

    Retorna:
    - Dados basicos da incidencia (sem dados pessoais)
    - Status atual
    - Historico de atualizacoes
    """
    # Normalizar codigo (uppercase, sem espacos)
    codigo = codigo.strip().upper()

    # Buscar incidencia pelo codigo
    incidencia = db.query(models.Incidencia).filter(
        models.Incidencia.codigo_acompanhamento == codigo
    ).first()

    if not incidencia:
        raise HTTPException(
            status_code=404,
            detail=f"Incidencia com codigo '{codigo}' nao encontrada"
        )

    # Buscar categoria
    categoria = db.query(models.Categoria).filter(
        models.Categoria.categoria_id == incidencia.categoria_id
    ).first()

    # Buscar status
    status_obj = db.query(models.Status).filter(
        models.Status.status_id == incidencia.status
    ).first()

    # Mapear cor do status
    def get_status_cor(status_nome: str) -> str:
        if not status_nome:
            return "#607D8B"
        status_lower = status_nome.lower()
        if "resolv" in status_lower or "conclu" in status_lower or "finaliz" in status_lower:
            return "#4CAF50"  # Verde
        elif "andamento" in status_lower or "execu" in status_lower or "trabalh" in status_lower:
            return "#FF9800"  # Laranja
        elif "analis" in status_lower or "avali" in status_lower or "verific" in status_lower:
            return "#2196F3"  # Azul
        elif "cancel" in status_lower or "rejeit" in status_lower:
            return "#F44336"  # Vermelho
        else:
            return "#9E9E9E"  # Cinza

    # Buscar historico/timeline
    timeline = []
    try:
        interacoes = db.query(models.Interacao).filter(
            models.Interacao.incidencia_id == incidencia.incidencia_id
        ).order_by(models.Interacao.data_hora.desc()).limit(10).all()

        for interacao in interacoes:
            timeline.append({
                "data": interacao.data_hora.isoformat() if interacao.data_hora else None,
                "descricao": (interacao.descricao or "Atualizacao").strip(),
                "tipo": "interacao"
            })
    except:
        pass  # Tabela de interacao pode nao existir

    # Calcular tempo decorrido
    tempo_decorrido = None
    if incidencia.data_hora:
        delta = datetime.now() - incidencia.data_hora
        dias = delta.days
        if dias == 0:
            horas = delta.seconds // 3600
            tempo_decorrido = f"{horas} hora(s)" if horas > 0 else "Hoje"
        elif dias == 1:
            tempo_decorrido = "Ontem"
        else:
            tempo_decorrido = f"{dias} dias"

    resposta = {
        "codigo": codigo,
        "incidencia_id": incidencia.incidencia_id,
        "categoria": categoria.nome if categoria else "Nao informada",
        "categoria_icone": categoria.icone if categoria and hasattr(categoria, 'icone') else None,
        "descricao": incidencia.descricao or "",
        "bairro": incidencia.bairro or "Nao informado",
        "endereco": incidencia.endereco or "",
        "cidade": incidencia.cidade or "",
        "estado": incidencia.estado or "",
        "status": {
            "id": incidencia.status,
            "nome": status_obj.nome if status_obj else "Pendente",
            "cor": get_status_cor(status_obj.nome if status_obj else "")
        },
        "foto": incidencia.foto or None,
        "data_abertura": incidencia.data_hora.isoformat() if incidencia.data_hora else None,
        "data_ultima_atualizacao": incidencia.data_ultimo_status.isoformat() if incidencia.data_ultimo_status else None,
        "tempo_decorrido": tempo_decorrido,
        "lat": str(incidencia.lat) if incidencia.lat else None,
        "long": str(incidencia.long) if incidencia.long else None,
        "timeline": timeline,
        "is_anonima": incidencia.cidadao_id is None
    }

    return JSONResponse(content=resposta, media_type="application/json; charset=utf-8")


# ========== ENDPOINT DE ALERTAS DO SISTEMA ==========

@app.get("/api/alertas/sistema")
async def get_alertas_sistema(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Retorna alertas dinamicos do sistema baseados em:
    1. Incidencias urgentes (prioridade alta sem atendimento - status=1)
    2. Incidencias sem resposta ha mais de 5 dias
    3. Feedbacks negativos recentes (avaliacao <= 2)
    4. Novas incidencias nas ultimas 24h
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cliente_id = payload.get("cliente_id")
    except JWTError:
        raise credentials_exception

    if not cliente_id:
        raise HTTPException(status_code=401, detail="Cliente nao identificado")

    try:
        from datetime import date, timedelta
        agora = datetime.now()
        hoje = date.today()
        cinco_dias_atras = agora - timedelta(days=5)
        vinte_quatro_horas_atras = agora - timedelta(hours=24)
        sete_dias_atras = agora - timedelta(days=7)

        alertas = []

        # 1. Incidencias urgentes (prioridade alta = 3, sem atendimento = status 1)
        incidencias_urgentes = db.query(models.Incidencia).filter(
            models.Incidencia.cliente_id == cliente_id,
            models.Incidencia.prioridade == 3,  # Prioridade alta
            models.Incidencia.status == 1  # Status: Novo/Aguardando
        ).order_by(models.Incidencia.data_hora.desc()).limit(10).all()

        for inc in incidencias_urgentes:
            categoria = db.query(models.Categoria).filter(
                models.Categoria.categoria_id == inc.categoria_id
            ).first()

            alertas.append({
                "id": f"urgente_{inc.incidencia_id}",
                "tipo": "urgente",
                "severidade": "critico",
                "titulo": "Incidencia Urgente",
                "mensagem": f"Incidencia #{inc.incidencia_id} - {categoria.nome if categoria else 'Sem categoria'} em {inc.bairro or 'bairro nao informado'} aguardando atendimento",
                "referencia": f"Incidencia #{inc.incidencia_id}",
                "link": f"/incidencia/{inc.incidencia_id}/detalhe",
                "data_criacao": inc.data_hora.isoformat() if inc.data_hora else None,
                "icone": "bi-exclamation-octagon-fill",
                "lido": False,
                "incidencia_id": inc.incidencia_id
            })

        # 2. Incidencias sem resposta ha mais de 5 dias (status = 1)
        incidencias_sem_resposta = db.query(models.Incidencia).filter(
            models.Incidencia.cliente_id == cliente_id,
            models.Incidencia.status == 1,  # Status: Novo/Aguardando
            models.Incidencia.data_hora <= cinco_dias_atras
        ).order_by(models.Incidencia.data_hora.asc()).limit(10).all()

        for inc in incidencias_sem_resposta:
            # Evitar duplicatas com urgentes
            if any(a.get('incidencia_id') == inc.incidencia_id for a in alertas):
                continue

            categoria = db.query(models.Categoria).filter(
                models.Categoria.categoria_id == inc.categoria_id
            ).first()

            dias_sem_resposta = (agora - inc.data_hora).days if inc.data_hora else 0

            alertas.append({
                "id": f"sem_resposta_{inc.incidencia_id}",
                "tipo": "sem_resposta",
                "severidade": "alto" if dias_sem_resposta > 7 else "atencao",
                "titulo": f"Sem Resposta ha {dias_sem_resposta} dias",
                "mensagem": f"Incidencia #{inc.incidencia_id} - {categoria.nome if categoria else 'Sem categoria'} em {inc.bairro or 'local nao informado'} esta aguardando ha {dias_sem_resposta} dias",
                "referencia": f"Incidencia #{inc.incidencia_id}",
                "link": f"/incidencia/{inc.incidencia_id}/detalhe",
                "data_criacao": inc.data_hora.isoformat() if inc.data_hora else None,
                "icone": "bi-clock-history",
                "lido": False,
                "incidencia_id": inc.incidencia_id
            })

        # 3. Feedbacks negativos recentes (avaliacao <= 2, ultimos 7 dias)
        feedbacks_negativos = db.query(models.FeedbackIncidencia).join(
            models.Incidencia,
            models.FeedbackIncidencia.incidencia_id == models.Incidencia.incidencia_id
        ).filter(
            models.Incidencia.cliente_id == cliente_id,
            models.FeedbackIncidencia.avaliacao <= 2,
            models.FeedbackIncidencia.data_feedback >= sete_dias_atras
        ).order_by(models.FeedbackIncidencia.data_feedback.desc()).limit(10).all()

        for fb in feedbacks_negativos:
            incidencia = db.query(models.Incidencia).filter(
                models.Incidencia.incidencia_id == fb.incidencia_id
            ).first()

            estrelas = "".join(["*" for _ in range(fb.avaliacao)])

            alertas.append({
                "id": f"feedback_{fb.feedback_id}",
                "tipo": "feedback_negativo",
                "severidade": "critico" if fb.avaliacao == 1 else "atencao",
                "titulo": f"Feedback Negativo ({fb.avaliacao} estrela{'s' if fb.avaliacao > 1 else ''})",
                "mensagem": fb.comentario or f"Cidadao insatisfeito com a resolucao da incidencia #{fb.incidencia_id}",
                "referencia": f"Incidencia #{fb.incidencia_id}",
                "link": f"/incidencia/{fb.incidencia_id}/detalhe",
                "data_criacao": fb.data_feedback.isoformat() if fb.data_feedback else None,
                "icone": "bi-emoji-frown-fill",
                "lido": False,
                "incidencia_id": fb.incidencia_id
            })

        # 4. Novas incidencias nas ultimas 24h
        incidencias_novas = db.query(models.Incidencia).filter(
            models.Incidencia.cliente_id == cliente_id,
            models.Incidencia.data_hora >= vinte_quatro_horas_atras
        ).order_by(models.Incidencia.data_hora.desc()).all()

        total_novas_24h = len(incidencias_novas)

        if total_novas_24h > 0:
            # Agrupar por categoria para resumo
            categorias_novas = {}
            for inc in incidencias_novas:
                cat_id = inc.categoria_id
                if cat_id not in categorias_novas:
                    categorias_novas[cat_id] = {"total": 0, "nome": None}
                categorias_novas[cat_id]["total"] += 1

            # Buscar nomes das categorias
            for cat_id in categorias_novas:
                cat = db.query(models.Categoria).filter(
                    models.Categoria.categoria_id == cat_id
                ).first()
                categorias_novas[cat_id]["nome"] = cat.nome if cat else "Sem categoria"

            # Resumo das categorias
            resumo_categorias = ", ".join([
                f"{v['nome']} ({v['total']})"
                for k, v in sorted(categorias_novas.items(), key=lambda x: x[1]['total'], reverse=True)[:3]
            ])

            alertas.append({
                "id": f"novas_24h_{hoje.isoformat()}",
                "tipo": "novas_incidencias",
                "severidade": "info" if total_novas_24h <= 5 else ("atencao" if total_novas_24h <= 15 else "alto"),
                "titulo": f"{total_novas_24h} Nova{'s' if total_novas_24h > 1 else ''} Incidencia{'s' if total_novas_24h > 1 else ''} (24h)",
                "mensagem": f"Foram registradas {total_novas_24h} incidencias nas ultimas 24 horas. Categorias: {resumo_categorias}",
                "referencia": "Ultimas 24 horas",
                "link": "/incidencias",
                "data_criacao": agora.isoformat(),
                "icone": "bi-plus-circle-fill",
                "lido": False,
                "incidencia_id": None
            })

        # 5. Adicionar alertas do historico (nao lidos)
        alertas_historico = db.query(models.HistoricoAlerta).filter(
            models.HistoricoAlerta.cliente_id == cliente_id,
            models.HistoricoAlerta.lido == 0
        ).order_by(models.HistoricoAlerta.data_criacao.desc()).limit(20).all()

        for ah in alertas_historico:
            alertas.append({
                "id": f"historico_{ah.alerta_id}",
                "alerta_id": ah.alerta_id,
                "tipo": ah.tipo or "sistema",
                "severidade": ah.severidade or "info",
                "titulo": f"Alerta de {(ah.tipo or 'sistema').title().replace('_', ' ')}",
                "mensagem": ah.mensagem,
                "referencia": ah.referencia,
                "link": None,
                "data_criacao": ah.data_criacao.isoformat() if ah.data_criacao else None,
                "icone": "bi-bell-fill",
                "lido": bool(ah.lido),
                "incidencia_id": None,
                "valor": ah.valor,
                "comparativo": ah.comparativo
            })

        # Ordenar por severidade e data
        ordem_severidade = {"critico": 0, "alto": 1, "atencao": 2, "info": 3}
        alertas.sort(key=lambda x: (
            ordem_severidade.get(x.get("severidade", "info"), 4),
            x.get("data_criacao") or ""
        ), reverse=False)

        # Contadores para resumo
        resumo = {
            "total": len(alertas),
            "criticos": len([a for a in alertas if a.get("severidade") == "critico"]),
            "altos": len([a for a in alertas if a.get("severidade") == "alto"]),
            "atencao": len([a for a in alertas if a.get("severidade") == "atencao"]),
            "info": len([a for a in alertas if a.get("severidade") == "info"]),
            "nao_lidos": len([a for a in alertas if not a.get("lido")]),
            "urgentes": len([a for a in alertas if a.get("tipo") == "urgente"]),
            "sem_resposta": len([a for a in alertas if a.get("tipo") == "sem_resposta"]),
            "feedbacks_negativos": len([a for a in alertas if a.get("tipo") == "feedback_negativo"]),
            "novas_24h": total_novas_24h
        }

        return {
            "alertas": alertas,
            "resumo": resumo,
            "data_consulta": agora.isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar alertas do sistema: {str(e)}")


if __name__ == "__main__":
   import uvicorn
   uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


