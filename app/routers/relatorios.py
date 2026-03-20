from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, extract
from datetime import datetime, timedelta
from typing import Optional
from .. import models  # Importando models do diretório pai
from ..database import get_db  # Importando database do diretório pai
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from fastapi import HTTPException, status

router = APIRouter()

load_dotenv()

# Configuração de segurança
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciais inválidas",
    headers={"WWW-Authenticate": "Bearer"},
)

# Configurações
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

# Relatório de Volume por Período
@router.get("/volume-periodo", response_model=None)
async def get_volume_periodo(token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    periodo: str = "month",  # Alterado para inglês
    data_inicio: str = None,
    data_fim: str = None,
    categoria_id: Optional[int] = None
):
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

    # Se foi passado um categoria_id específico, filtrar apenas se estiver nas permitidas
    if categoria_id is not None:
        if categoria_id in categorias_ids:
            categorias_ids = [categoria_id]
        else:
            return {"labels": [], "values": []}  # Categoria não permitida

    try:
        # Mapear períodos em português para inglês
        periodos = {
            "diario": "day",
            "semanal": "week",
            "mensal": "month",
            "anual": "year"
        }

        periodo_sql = periodos.get(periodo, "month")
        inicio = datetime.strptime(data_inicio, "%Y-%m-%d") if data_inicio else datetime.now() - timedelta(days=30)
        fim = datetime.strptime(data_fim, "%Y-%m-%d") if data_fim else datetime.now()

        query = db.query(
            func.date_trunc(periodo_sql, models.Incidencia.data_hora).label('periodo'),
            func.count(models.Incidencia.incidencia_id).label('total')
        ).filter(
            models.Incidencia.data_hora.between(inicio, fim)
        ).filter(models.Incidencia.categoria_id.in_(categorias_ids)
        ).group_by(
            'periodo'
        ).order_by(
            'periodo'
        )

        results = query.all()
        labels = [r.periodo.strftime("%d/%m/%Y") if r.periodo else '' for r in results]
        values = [r.total for r in results]

        return {"labels": labels, "values": values}

    except Exception as e:
        print(f"Erro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

# Relatório de Tendências por Categoria
@router.get("/tendencias-categoria", response_model=None)
async def get_tendencias_categoria(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    categoria_id: Optional[int] = None,
    data_inicio: str = None,
    data_fim: str = None
):

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

    # Se foi passado um categoria_id específico, filtrar apenas se estiver nas permitidas
    if categoria_id is not None:
        if categoria_id in categorias_ids:
            categorias_ids = [categoria_id]
        else:
            return {"categorias": [], "dados": []}  # Categoria não permitida

    try:
        # Adicionar prints para debug
        print("Iniciando consulta de categorias...")

        query = db.query(
            models.Categoria.nome,
            func.count(models.Incidencia.incidencia_id).label('total')
        ).outerjoin(
            models.Incidencia,
            models.Categoria.categoria_id == models.Incidencia.categoria_id
        ).filter(models.Incidencia.categoria_id.in_(categorias_ids))

        # Filtrar por data se fornecido
        if data_inicio:
            inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
            query = query.filter(models.Incidencia.data_hora >= inicio)
        if data_fim:
            fim = datetime.strptime(data_fim, "%Y-%m-%d")
            query = query.filter(models.Incidencia.data_hora <= fim)

        query = query.group_by(
            models.Categoria.nome
        ).order_by(
            models.Categoria.nome
        )

        results = query.all()
        print("Resultados encontrados:", results)  # Ver os resultados

        categorias = [r.nome for r in results]
        dados = [r.total for r in results]

        response_data = {
            "categorias": categorias,
            "dados": dados
        }
        print("Dados retornados:", response_data)  # Ver o formato final

        return response_data

    except Exception as e:
        print(f"Erro na consulta: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Relatório de Performance
@router.get("/performance", response_model=None)
async def get_performance(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    categoria_id: Optional[int] = None,
    data_inicio: str = None,
    data_fim: str = None
):

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

    # Se foi passado um categoria_id específico, filtrar apenas se estiver nas permitidas
    if categoria_id is not None:
        if categoria_id in categorias_ids:
            categorias_ids = [categoria_id]
        else:
            return {"tempo_medio_por_categoria": {}, "taxa_resolucao": 0}  # Categoria não permitida

    # Preparar filtros de data
    inicio = datetime.strptime(data_inicio, "%Y-%m-%d") if data_inicio else None
    fim = datetime.strptime(data_fim, "%Y-%m-%d") if data_fim else None

    try:
        # Tempo médio de resolução (apenas incidências resolvidas - status 3)
        tempo_query = db.query(
            models.Categoria.nome,
            func.avg(
                func.extract('epoch', models.Incidencia.data_ultimo_status - models.Incidencia.data_hora)
            ).label('tempo_medio')
        ).join(
            models.Categoria,
            models.Incidencia.categoria_id == models.Categoria.categoria_id
        ).filter(
            models.Incidencia.categoria_id.in_(categorias_ids),
            models.Incidencia.status == 3,  # Apenas resolvidas
            models.Incidencia.data_ultimo_status.isnot(None),
            models.Incidencia.data_hora.isnot(None)
        )

        # Aplicar filtros de data
        if inicio:
            tempo_query = tempo_query.filter(models.Incidencia.data_hora >= inicio)
        if fim:
            tempo_query = tempo_query.filter(models.Incidencia.data_hora <= fim)

        tempo_resolucao = tempo_query.group_by(
            models.Categoria.nome
        ).all()

        # Total de incidências
        total_query = db.query(func.count(models.Incidencia.incidencia_id)).filter(
            models.Incidencia.categoria_id.in_(categorias_ids)
        )
        if inicio:
            total_query = total_query.filter(models.Incidencia.data_hora >= inicio)
        if fim:
            total_query = total_query.filter(models.Incidencia.data_hora <= fim)
        total_incidencias = total_query.scalar() or 0

        # Total resolvidas
        resolvidas_query = db.query(
            func.count(models.Incidencia.incidencia_id)
        ).filter(
            models.Incidencia.categoria_id.in_(categorias_ids),
            models.Incidencia.status == 3  # Status 3 = Concluída/Resolvida
        )
        if inicio:
            resolvidas_query = resolvidas_query.filter(models.Incidencia.data_hora >= inicio)
        if fim:
            resolvidas_query = resolvidas_query.filter(models.Incidencia.data_hora <= fim)
        resolvidas = resolvidas_query.scalar() or 0

        # Formatar resposta
        result = {
            "tempo_medio_por_categoria": {
                r.nome: round(r.tempo_medio / 3600, 2) if r.tempo_medio else 0
                for r in tempo_resolucao
            } if tempo_resolucao else {},
            "taxa_resolucao": round((resolvidas / total_incidencias) * 100, 2) if total_incidencias > 0 else 0
        }

        print(f"Categorias permitidas: {categorias_ids}")
        try:
            print("Executando consulta de tempo médio...")
            # consulta tempo_resolucao
            print("Consulta de tempo médio concluída")

            print("Executando consulta de total de incidências...")
            # consulta total_incidencias
            print("Consulta de total concluída")

            print("Executando consulta de resolvidas...")
            # consulta resolvidas
            print("Consulta de resolvidas concluída")
        except Exception as e:
            print(f"Erro específico na consulta: {e}")
            print(f"Tipo de erro: {type(e)}")
            raise HTTPException(status_code=500, detail=str(e))

        return result

    except Exception as e:
        print(f"Erro no servidor (performance): {str(e)}")  # Debug
        raise HTTPException(status_code=500, detail=str(e))

# Relatório Geográfico
# No backend (relatorios.py)
@router.get("/geografico", response_model=None)
async def get_geografico(db: Session = Depends(get_db)):
    try:
        # Distribuição por estado
        por_estado = db.query(
            models.Incidencia.estado,
            func.count(models.Incidencia.incidencia_id).label('total')
        ).filter(
            models.Incidencia.estado.isnot(None)  # Filtrar estados nulos
        ).group_by(
            models.Incidencia.estado
        ).order_by(
            desc('total')  # Ordenar por total decrescente
        ).all()

        # Print para debug
        print("Dados geográficos:", por_estado)

        return {
            "por_estado": {r.estado: r.total for r in por_estado}
        }
    except Exception as e:
        print(f"Erro na rota geográfica: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
   
# Relatório de Status
@router.get("/status", response_model=None)
async def get_status(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    categoria_id: Optional[int] = None,
    data_inicio: str = None,
    data_fim: str = None
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id = payload.get("user_id")
    except JWTError:
        raise credentials_exception
    if not usuario_id:
        raise HTTPException(status_code=401, detail="Usuario nao identificado")

    # Pegamos as categorias permitidas para o usuario
    categorias_permitidas = db.query(
        models.UsuarioCategoria.categoria_id
    ).filter(
        models.UsuarioCategoria.usuario_id == usuario_id
    ).all()

    categorias_ids = [cat[0] for cat in categorias_permitidas]
    if not categorias_ids:
        return {"distribuicao": {}, "tempo_medio": {}}

    # Se foi passado um categoria_id especifico, filtrar apenas se estiver nas permitidas
    if categoria_id is not None:
        if categoria_id in categorias_ids:
            categorias_ids = [categoria_id]
        else:
            return {"distribuicao": {}, "tempo_medio": {}}

    # Preparar filtros de data
    inicio = datetime.strptime(data_inicio, "%Y-%m-%d") if data_inicio else None
    fim = datetime.strptime(data_fim, "%Y-%m-%d") if data_fim else None

    try:
        # Distribuicao atual
        dist_query = db.query(
            models.Status.nome,
            func.count(models.Incidencia.incidencia_id).label('total')
        ).join(
            models.Status
        ).filter(
            models.Incidencia.categoria_id.in_(categorias_ids)
        )

        if inicio:
            dist_query = dist_query.filter(models.Incidencia.data_hora >= inicio)
        if fim:
            dist_query = dist_query.filter(models.Incidencia.data_hora <= fim)

        distribuicao = dist_query.group_by(
            models.Status.nome
        ).all()

        # Tempo medio em cada status
        tempo_query = db.query(
            models.Status.nome,
            func.avg(
                func.extract('epoch', models.Incidencia.data_ultimo_status - models.Incidencia.data_hora)
            ).label('tempo_medio')
        ).join(
            models.Status
        ).filter(
            models.Incidencia.categoria_id.in_(categorias_ids)
        )

        if inicio:
            tempo_query = tempo_query.filter(models.Incidencia.data_hora >= inicio)
        if fim:
            tempo_query = tempo_query.filter(models.Incidencia.data_hora <= fim)

        tempo_medio = tempo_query.group_by(
            models.Status.nome
        ).all()

        return {
            "distribuicao": {r.nome: r.total for r in distribuicao},
            "tempo_medio": {r.nome: round(r.tempo_medio / 3600, 2) if r.tempo_medio else 0 for r in tempo_medio}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))