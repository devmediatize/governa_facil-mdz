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
    cargo = Column(String(200), nullable=True)
    lotacao = Column(String(200), nullable=True)
    receber_alertas_email = Column(Integer, default=1)
    receber_alertas_sistema = Column(Integer, default=1)

class Categoria(Base):
    __tablename__ = "categoria"

    categoria_id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(200), nullable=False)
    descricao = Column(Text, nullable=True)
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
    cidadao_id = Column(Integer, ForeignKey('cidadao.cidadao_id'), nullable=True)  # Nullable para incidencias anonimas
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
    cep = Column(String(10))
    cliente_id = Column(Integer, nullable=False)
    codigo_acompanhamento = Column(String(20), nullable=True, unique=True)  # Codigo para incidencias anonimas (INC-ABC123)

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
    imagem_fundo = Column(String(500), nullable=True)
    data_inicio = Column(Date, nullable=True)
    cor_primaria = Column(String(7), nullable=True, default='#0F58AD')
    cor_secundaria = Column(String(7), nullable=True, default='#0092A6')
    permitir_anonimo = Column(Integer, nullable=True, default=0)  # 0=Nao, 1=Sim


class IncidenciaInteracao(Base):
    __tablename__ = "incidencia_interacao"

    incidencia_interacao_id = Column(Integer, primary_key=True, index=True)
    incidencia_id = Column(Integer, ForeignKey("incidencia.incidencia_id"))
    usuario_id = Column(Integer, ForeignKey("usuario.usuario_id"))
    comentario = Column(String)
    status_id = Column(Integer, ForeignKey("status.status_id"))
    data = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    foto = Column(String(500), nullable=True)  # Caminho da foto da interacao no MinIO
    
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
    foto = Column(String(500), nullable=True)  # Caminho da foto no MinIO
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
    retry_attempts = Column(Integer, default=3)
    chat_habilitado = Column(Integer, default=0)
    system_prompt = Column(Text)
    # Campos de Embedding
    embedding_provider = Column(String(50), default='openai')
    embedding_model = Column(String(100), default='text-embedding-3-small')
    embedding_api_url = Column(String(255))
    embedding_api_key = Column(Text)
    created_at = Column(DateTime, default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(DateTime)


class HistoricoAlerta(Base):
    __tablename__ = "historico_alerta"

    alerta_id = Column(Integer, primary_key=True, autoincrement=True)
    cliente_id = Column(Integer, nullable=False)
    tipo = Column(String(50))  # 'bairro' ou 'categoria'
    referencia = Column(String(200))  # nome do bairro ou categoria
    mensagem = Column(Text)
    severidade = Column(String(20))  # 'critico', 'atencao', 'info'
    valor = Column(Integer)  # quantidade de incidencias
    comparativo = Column(String(100))  # ex: "3x acima da media"
    data_criacao = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    lido = Column(Integer, default=0)
    notificado_email = Column(Integer, default=0)


class FeedbackIncidencia(Base):
    """
    Modelo para armazenar feedback do cidadao apos resolucao de incidencia.
    Permite que o cidadao avalie se o problema foi realmente resolvido.
    """
    __tablename__ = "feedback_incidencia"

    feedback_id = Column(Integer, primary_key=True, autoincrement=True)
    incidencia_id = Column(Integer, ForeignKey('incidencia.incidencia_id'), nullable=False)
    cidadao_id = Column(Integer, ForeignKey('cidadao.cidadao_id'), nullable=False)
    avaliacao = Column(Integer, nullable=False)  # 1 a 5 estrelas
    comentario = Column(Text, nullable=True)  # Comentario opcional do cidadao
    foto_confirmacao = Column(String(500), nullable=True)  # Path da foto de confirmacao
    resolvido = Column(Integer, nullable=False, default=1)  # 1 = Sim, foi resolvido / 0 = Nao foi resolvido
    data_feedback = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))


class DeviceToken(Base):
    """
    Modelo para armazenar tokens de dispositivos para Push Notifications.
    Permite enviar notificacoes para o app mobile quando ha atualizacoes.
    """
    __tablename__ = "device_token"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cidadao_id = Column(Integer, ForeignKey('cidadao.cidadao_id'), nullable=False)
    token = Column(String(500), nullable=False, unique=True)  # FCM Token
    platform = Column(String(20), nullable=False)  # 'android', 'ios', 'web'
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))


# ========== SISTEMA DE GAMIFICACAO ==========

class PontuacaoCidadao(Base):
    """
    Armazena a pontuacao total e nivel de cada cidadao no sistema de gamificacao.
    """
    __tablename__ = "pontuacao_cidadao"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cidadao_id = Column(Integer, ForeignKey('cidadao.cidadao_id'), nullable=False, unique=True)
    pontos_totais = Column(Integer, default=0)
    nivel = Column(Integer, default=1)
    data_atualizacao = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))


class Badge(Base):
    """
    Define os badges/conquistas disponiveis no sistema.
    """
    __tablename__ = "badge"

    badge_id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    descricao = Column(String(300), nullable=True)
    icone = Column(String(50), default='star')  # Nome do icone Material
    cor = Column(String(7), default='#FFD700')  # Cor hex do badge
    pontos_necessarios = Column(Integer, default=0)  # Pontos minimos para desbloquear
    criterio_tipo = Column(String(50), nullable=True)  # 'incidencias_total', 'incidencias_bairro', 'resolvidas', etc
    criterio_valor = Column(Integer, default=1)  # Quantidade necessaria para o criterio
    ativo = Column(Integer, default=1)


class CidadaoBadge(Base):
    """
    Relacao entre cidadaos e badges conquistados.
    """
    __tablename__ = "cidadao_badge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cidadao_id = Column(Integer, ForeignKey('cidadao.cidadao_id'), nullable=False)
    badge_id = Column(Integer, ForeignKey('badge.badge_id'), nullable=False)
    data_conquista = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))


class HistoricoPontos(Base):
    """
    Historico de todas as transacoes de pontos para auditoria.
    """
    __tablename__ = "historico_pontos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cidadao_id = Column(Integer, ForeignKey('cidadao.cidadao_id'), nullable=False)
    pontos = Column(Integer, nullable=False)  # Pode ser positivo ou negativo
    motivo = Column(String(100), nullable=False)  # 'incidencia_enviada', 'incidencia_resolvida', 'feedback'
    referencia_id = Column(Integer, nullable=True)  # ID da incidencia/feedback relacionado
    data_registro = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))


class ConfigStorage(Base):
    """
    Configuracao de armazenamento de fotos (MinIO/S3).
    Permite configurar servidor externo para armazenar fotos das incidencias.
    """
    __tablename__ = "config_storage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cliente_id = Column(Integer, nullable=False)
    minio_url = Column(String(500), nullable=True)  # URL do servidor MinIO/S3
    minio_bucket = Column(String(100), nullable=True)  # Nome do bucket
    minio_access_key = Column(String(255), nullable=True)  # Access Key (opcional)
    minio_secret_key = Column(Text, nullable=True)  # Secret Key (opcional)
    ativo = Column(Integer, default=1)  # 1 = Usar MinIO, 0 = Usar storage local
    created_at = Column(DateTime, default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(DateTime)


class ConfigNotificacoes(Base):
    """
    Configuracao de notificacoes por Email (SMTP) e SMS.
    Permite configurar servidores de envio e regras de notificacao.
    """
    __tablename__ = "config_notificacoes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cliente_id = Column(Integer, nullable=False)

    # Configuracao SMTP (Email)
    smtp_servidor = Column(String(255), nullable=True)
    smtp_porta = Column(Integer, default=587)
    smtp_usuario = Column(String(255), nullable=True)
    smtp_senha = Column(Text, nullable=True)
    smtp_email_remetente = Column(String(255), nullable=True)
    smtp_nome_remetente = Column(String(255), nullable=True)
    smtp_usar_tls = Column(Integer, default=1)  # 1 = Sim, 0 = Nao

    # Configuracao SMS
    sms_provedor = Column(String(50), nullable=True)  # twilio, aws_sns, nexmo, zenvia, outro
    sms_api_url = Column(String(500), nullable=True)
    sms_account_sid = Column(String(255), nullable=True)  # Account SID / API Key
    sms_auth_token = Column(Text, nullable=True)  # Auth Token / Secret
    sms_numero_remetente = Column(String(20), nullable=True)

    # Configuracoes de envio automatico
    email_ao_abrir = Column(Integer, default=0)  # 1 = Sim, 0 = Nao
    email_ao_mudar_status = Column(Integer, default=0)
    sms_ao_abrir = Column(Integer, default=0)
    sms_ao_mudar_status = Column(Integer, default=0)

    created_at = Column(DateTime, default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(DateTime)