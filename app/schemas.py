from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, date

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UsuarioBase(BaseModel):
    nome: str
    email: EmailStr
    endereco: str
    cidade: str
    estado: str
    ativo: int
    cliente_id: int
    celular: str
    nivel: int
    cargo: Optional[str] = None
    lotacao: Optional[str] = None
    receber_alertas_email: Optional[int] = 1
    receber_alertas_sistema: Optional[int] = 1

class UsuarioCreate(BaseModel):
    nome: str
    email: str
    senha: str
    endereco: str
    cidade: str
    estado: str
    ativo: int = 1  # Default value
    nivel: int = 0  # Default value
    cargo: Optional[str] = None
    lotacao: Optional[str] = None

class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None  # Mudado de str para EmailStr
    senha: Optional[str] = None
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    ativo: Optional[int] = None
    celular: Optional[str] = None
    nivel: int = 0  # Default value
    cargo: Optional[str] = None
    lotacao: Optional[str] = None
    receber_alertas_email: Optional[int] = None
    receber_alertas_sistema: Optional[int] = None

class Usuario(UsuarioBase):
    usuario_id: int

    class Config:
        orm_mode = True

class IncidenciaBase(BaseModel):
    categoria_id: int
    cidadao_id: int
    foto: str = None
    descricao: str = None
    prioridade: int = None
    endereco: str = None
    cidade: str = None
    estado: str = None
    lat: str = None
    long: str = None
    bairro: str = None
    cep: Optional[str] = None
    cliente_id: int

class IncidenciaCreate(IncidenciaBase):
    pass

class IncidenciaResponse(IncidenciaBase):
    incidencia_id: int
    cidadao_id: int
    status: int
    data_hora: str
    data_ultimo_status: str = None

    class Config:
        from_attributes = True

class CategoriaCreate(BaseModel):
    nome: str

class Categoria(CategoriaCreate):
    categoria_id: int
    ativo: int
    data_hora_cadastro: datetime

    class Config:
        from_attributes = True

class StatusCreate(BaseModel):
    nome: str

class Status(StatusCreate):
    status_id: int
    ativo: int

    class Config:
        from_attributes = True


class ChatBotBase(BaseModel):
   pergunta: str
   reposta: str
   reposta_geral: str
   sql: Optional[str] = None

class ChatBotCreate(ChatBotBase):
   pass

class ChatBot(ChatBotBase):
   chat_bot_id: int
   pergunta_data_hora: datetime
   reposta_data_hora: datetime

   class Config:
       from_attributes = True


class Incidencia(IncidenciaBase):
    incidencia_id: int
    cidadao_id: int
    status_nome: str
    categoria_nome: str
    prioridade_nome: str
    data_hora: datetime
    data_ultimo_status: Optional[datetime] = None
    cliente_id: int

    class Config:
        from_attributes = True


class ClienteSchema(BaseModel):
    cliente_id: int
    nome: str
    cnpj: str
    endereco: str
    cidade: str
    estado: str
    logo: Optional[str] = None
    data_inicio: Optional[date] = None

    class Config:
        orm_mode = True

class IncidenciaInteracaoSchema(BaseModel):
    incidencia_interacao_id: int  # Ajustado para corresponder ao nome no modelo
    incidencia_id: int
    comentario: str
    status_id: int
    usuario_id: int
    data: Optional[datetime] = None  # Nome ajustado se necessário
    
    class Config:
        from_attributes = True  # Versão atualizada de orm_mode

# Para receber dados ao criar uma interação
class IncidenciaInteracaoCreate(BaseModel):
    incidencia_id: int
    comentario: str
    status_id: int  # Se você estiver usando status_id em vez de novo_status_id

# Para listar interações com informações adicionais
class IncidenciaInteracaoResponse(IncidenciaInteracaoSchema):
    status_nome: str
    usuario_nome: str

# Schema para criação de um novo cidadão
class CidadaoCreate(BaseModel):
    nome: str 
    email: EmailStr
    senha: str 
    celular: str 
    endereco: Optional[str] 
    bairro: Optional[str] 
    cep: Optional[str] = None 
    cidade: Optional[str] 
    estado: Optional[str] 

# Schema para atualização de um cidadão existente
class CidadaoUpdate(BaseModel):
    nome: Optional[str] 
    email: Optional[EmailStr] = None
    celular: Optional[str] 
    endereco: Optional[str] 
    bairro: Optional[str]
    cep: Optional[str] 
    cidade: Optional[str] 
    estado: Optional[str] 
    ativo: Optional[int] 

# Schema para alterar senha
class CidadaoAlterarSenha(BaseModel):
    senha_atual: str
    nova_senha: str 

# Schema para resposta/consulta de cidadão
class Cidadao(BaseModel):
    cidadao_id: int
    nome: str
    email: str
    celular: str
    endereco: Optional[str] = None
    bairro: Optional[str] = None
    cep: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    ativo: int
    data_hora_cadastro: datetime

    class Config:
        from_attributes = True  # Permite conversão do modelo SQLAlchemy para Pydantic

# Schema para uso em cenários onde não é necessário exibir todas as informações
class CidadaoBasico(BaseModel):
    cidadao_id: int
    nome: str
    email: str
    ativo: int

    class Config:
        from_attributes = True


# Schemas para Historico de Alertas
class HistoricoAlertaBase(BaseModel):
    tipo: str  # 'bairro' ou 'categoria'
    referencia: str  # nome do bairro ou categoria
    mensagem: str
    severidade: str  # 'critico', 'atencao', 'info'
    valor: int  # quantidade de incidencias
    comparativo: Optional[str] = None  # ex: "3x acima da media"


class HistoricoAlertaCreate(HistoricoAlertaBase):
    cliente_id: int


class HistoricoAlertaResponse(HistoricoAlertaBase):
    alerta_id: int
    cliente_id: int
    data_criacao: datetime
    lido: int
    notificado_email: int

    class Config:
        from_attributes = True


class AlertasNaoLidosResponse(BaseModel):
    total_nao_lidos: int


# Schema para atualizar notificacoes do usuario
class UsuarioNotificacoesUpdate(BaseModel):
    receber_alertas_email: Optional[int] = None
    receber_alertas_sistema: Optional[int] = None
    categorias_notificacao: Optional[list] = None  # Lista de {categoria_id, notifica_email}