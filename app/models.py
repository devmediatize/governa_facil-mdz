from sqlalchemy import Column, Date, Integer, String, TIMESTAMP, ForeignKey, Text, text, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuario"

    usuario_id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(300), nullable=False)
    email = Column(String(300), nullable=False, unique=True)
    senha = Column(String(300), nullable=False)
    endereco = Column(String(300), nullable=True)
    cidade = Column(String(200), nullable=True)
    estado = Column(String(2), nullable=True)
    ativo = Column(Integer, default=1)
    data_hora_cadastro = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    cliente_id = Column(Integer, nullable=False)
    celular = Column(String(15), nullable=True)
    nivel = Column(Integer, default=0)
    foto = Column(String(500), nullable=True)

class Categoria(Base):
    __tablename__ = "categoria"

    categoria_id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(200), nullable=False)
    icone = Column(String(100), default='bi-tag')
    cor = Column(String(7), default='#6366f1')
    ativo = Column(Integer, default=1)
    data_hora_cadastro = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))


class Prioridade(Base):
    __tablename__ = "prioridade"
    
    prioridade_id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(200), nullable=False)
    ativo = Column(Integer, default=1)
    

class Status(Base):
    __tablename__ = "status"
    
    status_id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(300), nullable=False)
    ativo = Column(Integer, default=1)

class Incidencia(Base):
    __tablename__ = "incidencia"
    
    incidencia_id = Column(Integer, primary_key=True, autoincrement=True)
    categoria_id = Column(Integer, ForeignKey('categoria.categoria_id'), nullable=False)
    cidadao_id = Column(Integer, ForeignKey('cidadao.cidadao_id'), nullable=False)
    foto = Column(String(1000))
    data_hora = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    status = Column(Integer, ForeignKey('status.status_id'))
    data_ultimo_status = Column(TIMESTAMP)
    descricao = Column(String)
    prioridade = Column(Integer)
    endereco = Column(String(1000))
    cidade = Column(String(200))
    estado = Column(String(2))
    lat = Column(String(300))
    long = Column(String(300))
    bairro = Column(String(200))
    cliente_id = Column(Integer, nullable=False)

class ChatBot(Base):
   __tablename__ = "chat_bot"
   
   chat_bot_id = Column(Integer, primary_key=True)
   pergunta = Column(String(300), nullable=False)
   pergunta_data_hora = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
   reposta = Column(Text, nullable=False)
   reposta_data_hora = Column(TIMESTAMP)
   reposta_geral = Column(Text, nullable=False)
   sql = Column(String(1000))


class UsuarioCategoria(Base):
    __tablename__ = "usuario_categoria"
    
    usuario_categoria_id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, default=0)
    categoria_id = Column(Integer, default=0)
    notifica_email = Column(Integer, default=0)
    notifica_sms = Column(Integer, default=0)


class Cliente(Base):
    __tablename__ = 'cliente'

    cliente_id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(1000), nullable=False)
    cnpj = Column(String(20), nullable=False)
    endereco = Column(String(400), nullable=False)
    cidade = Column(String(50), nullable=False)
    estado = Column(String(2), nullable=False)
    logo = Column(String(100), nullable=True)
    data_inicio = Column(Date, nullable=True)
    cor_primaria = Column(String(7), nullable=True, default='#0F58AD')
    cor_secundaria = Column(String(7), nullable=True, default='#0092A6')


class IncidenciaInteracao(Base):
    __tablename__ = "incidencia_interacao"
    
    incidencia_interacao_id = Column(Integer, primary_key=True, index=True)
    incidencia_id = Column(Integer, ForeignKey("incidencia.incidencia_id"))
    usuario_id = Column(Integer, ForeignKey("usuario.usuario_id"))
    comentario = Column(String)
    status_id = Column(Integer, ForeignKey("status.status_id"))
    data = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    
class Cidadao(Base):
    __tablename__ = "cidadao"

    cidadao_id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(300), nullable=False)
    email = Column(String(300), nullable=False)
    senha = Column(String(300), nullable=False)
    celular = Column(String(20), nullable=False)
    endereco = Column(String(300), nullable=True)
    bairro = Column(String(300), nullable=True)
    cep = Column(String(20), nullable=False)
    cidade = Column(String(200), nullable=True)
    estado = Column(String(2), nullable=True)
    ativo = Column(Integer, nullable=False, default=1)
    data_hora_cadastro = Column(DateTime, default=text('CURRENT_TIMESTAMP'))


class ConfigAI(Base):
    __tablename__ = "config_ai"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cliente_id = Column(Integer, nullable=False)
    provider = Column(String(50), default='openai')
    model_name = Column(String(100), default='gpt-4o')
    api_url = Column(String(255))
    api_key = Column(Text)
    temperature = Column(Integer, default=7)
    max_tokens = Column(Integer, default=4096)
    context_window = Column(Integer, default=128000)
    timeout = Column(Integer, default=300)
    chat_habilitado = Column(Integer, default=0)
    system_prompt = Column(Text)
    created_at = Column(DateTime, default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(DateTime)