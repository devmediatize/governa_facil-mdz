from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, cast, Date, desc
from sqlalchemy.sql import text
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from starlette.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import calendar

# Importações dos seus módulos
from app.database import get_db
import app.models as models
from app.schemas import *

# Configuração das templates
templates = Jinja2Templates(directory="templates")

# Criar um router para o dashboard público
dashboard_public_router = APIRouter(
    prefix="/api/dashboard/public",
    tags=["dashboard público"],
)

# Função auxiliar para processar o parâmetro de categorias
def parse_categorias(categorias_str: Optional[str] = None):
    if not categorias_str:
        return None
    try:
        # Converter string "1,2,34" para lista [1, 2, 34]
        return [int(cat.strip()) for cat in categorias_str.split(',') if cat.strip().isdigit()]
    except Exception:
        return None

# Rota para renderizar a página do dashboard público
@dashboard_public_router.get("/", response_class=HTMLResponse)
async def get_public_dashboard(request: Request, categorias: Optional[str] = None):
    # Passar os parâmetros para o template
    return templates.TemplateResponse(
        "projetor.html",
        {"request": request, "categorias_filtro": categorias}
    )

# Rota para estatísticas gerais
@dashboard_public_router.get("/statistics")
async def get_statistics(db: Session = Depends(get_db)):
    try:
        # Total de incidências
        total_incidencias = db.query(func.count(models.Incidencia.incidencia_id)).scalar() or 0
        
        # Incidências em andamento
        em_andamento = db.query(func.count(models.Incidencia.incidencia_id)).filter(
            models.Incidencia.status == 2  # Status 2 = Em Andamento
        ).scalar() or 0
        
        # Incidências resolvidas
        resolvidas = db.query(func.count(models.Incidencia.incidencia_id)).filter(
            models.Incidencia.status == 3  # Status 4 = Resolvido
        ).scalar() or 0
        
        # Incidências pendentes (novas)
        pendentes = db.query(func.count(models.Incidencia.incidencia_id)).filter(
            models.Incidencia.status == 1  # Status 1 = Novo
        ).scalar() or 0
        
        # Tempo médio de resolução
        tempo_medio_query = db.query(
            func.avg(
                func.extract('epoch', models.Incidencia.data_ultimo_status - models.Incidencia.data_hora) / 86400
            )
        ).filter(
            models.Incidencia.status == 3  # Status 4 = Resolvido
        )
        tempo_medio_resolucao = round(tempo_medio_query.scalar() or 0, 1)
        
        # Taxa de resolução
        taxa_resolucao = round((resolvidas / total_incidencias * 100) if total_incidencias > 0 else 0, 1)
        
        # Satisfação média (exemplo - se você tiver uma tabela de avaliações)
        satisfacao_media = 4.7  # Valor de exemplo - substitua por uma consulta real se tiver os dados
        
        return {
            "total_incidencias": total_incidencias,
            "em_andamento": em_andamento,
            "resolvidas": resolvidas,
            "pendentes": pendentes,
            "tempo_medio_resolucao": tempo_medio_resolucao,
            "taxa_resolucao": taxa_resolucao,
            "satisfacao_media": satisfacao_media
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar estatísticas: {str(e)}")

# Rota para incidências por mês
@dashboard_public_router.get("/incidencias-por-mes")
async def get_incidencias_por_mes(db: Session = Depends(get_db)):
    try:
        # Obtendo os meses para os últimos 12 meses
        data_atual = datetime.now()
        
        # Preparando o retorno
        labels = []
        registradas = []
        resolvidas = []
        
        # Percorrer os últimos 12 meses
        for i in range(12):
            data = data_atual - timedelta(days=30 * i)
            mes = data.month
            ano = data.year
            
            # Nome do mês em português
            # nome_mes = calendar.month_name[mes][:3]
            nomes_meses_pt = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
            mes_indice = data.month - 1  # Os índices começam em 0
            nome_mes = nomes_meses_pt[mes_indice]
            
            # Adicionar ao início para manter a ordem cronológica
            labels.insert(0, nome_mes)
            
            # Contar incidências registradas no mês
            registradas_mes = db.query(func.count(models.Incidencia.incidencia_id)).filter(
                extract('month', models.Incidencia.data_hora) == mes,
                extract('year', models.Incidencia.data_hora) == ano
            ).scalar() or 0
            
            registradas.insert(0, registradas_mes)
            
            # Contar incidências resolvidas no mês
            resolvidas_mes = db.query(func.count(models.Incidencia.incidencia_id)).filter(
                extract('month', models.Incidencia.data_ultimo_status) == mes,
                extract('year', models.Incidencia.data_ultimo_status) == ano,
                models.Incidencia.status == 3  # Status 4 = Resolvido
            ).scalar() or 0
            
            resolvidas.insert(0, resolvidas_mes)
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Incidências Registradas",
                    "data": registradas,
                    "backgroundColor": 'rgba(54, 162, 235, 0.2)',
                    "borderColor": 'rgba(54, 162, 235, 1)',
                    "borderWidth": 2,
                    "tension": 0.4
                },
                {
                    "label": "Incidências Resolvidas",
                    "data": resolvidas,
                    "backgroundColor": 'rgba(75, 192, 192, 0.2)',
                    "borderColor": 'rgba(75, 192, 192, 1)',
                    "borderWidth": 2,
                    "tension": 0.4
                }
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar incidências por mês: {str(e)}")

# Rota para distribuição por categoria
@dashboard_public_router.get("/categorias")
async def get_categorias(db: Session = Depends(get_db)):
    try:
        # Buscar todas as categorias e contar incidências
        categorias_query = db.query(
            models.Categoria.nome,
            func.count(models.Incidencia.incidencia_id).label('total')
        ).outerjoin(
            models.Incidencia,
            models.Incidencia.categoria_id == models.Categoria.categoria_id
        ).group_by(
            models.Categoria.nome
        ).order_by(
            desc('total')
        ).limit(10)
        
        resultados = categorias_query.all()
        
        # Extrair nomes e totais
        nomes = [r.nome for r in resultados]
        totais = [r.total for r in resultados]
        
        # Cores para o gráfico
        cores_background = [
            'rgba(255, 99, 132, 0.7)',
            'rgba(54, 162, 235, 0.7)',
            'rgba(255, 206, 86, 0.7)',
            'rgba(75, 192, 192, 0.7)',
            'rgba(153, 102, 255, 0.7)',
            'rgba(255, 159, 64, 0.7)',
            'rgba(199, 199, 199, 0.7)',
            'rgba(83, 102, 255, 0.7)',
            'rgba(40, 167, 69, 0.7)',
            'rgba(220, 53, 69, 0.7)'
        ]
        
        cores_borda = [
            'rgba(255, 99, 132, 1)',
            'rgba(54, 162, 235, 1)',
            'rgba(255, 206, 86, 1)',
            'rgba(75, 192, 192, 1)',
            'rgba(153, 102, 255, 1)',
            'rgba(255, 159, 64, 1)',
            'rgba(199, 199, 199, 1)',
            'rgba(83, 102, 255, 1)',
            'rgba(40, 167, 69, 1)',
            'rgba(220, 53, 69, 1)'
        ]
        
        return {
            "labels": nomes,
            "datasets": [{
                "data": totais,
                "backgroundColor": cores_background[:len(nomes)],
                "borderColor": cores_borda[:len(nomes)],
                "borderWidth": 1
            }]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar categorias: {str(e)}")

# Rota para tempo médio por categoria
@dashboard_public_router.get("/tempo-por-categoria")
async def get_tempo_por_categoria(db: Session = Depends(get_db)):
    try:
        # Consultar tempo médio de resolução por categoria
        tempo_medio_query = db.query(
            models.Categoria.nome,
            func.avg(
                func.extract('epoch', models.Incidencia.data_ultimo_status - models.Incidencia.data_hora) / 86400
            ).label('tempo_medio')
        ).join(
            models.Incidencia,
            models.Incidencia.categoria_id == models.Categoria.categoria_id
        ).filter(
            models.Incidencia.status == 3  # Status 4 = Resolvido
        ).group_by(
            models.Categoria.nome
        ).order_by(
            desc('tempo_medio')
        ).all()
        
        # Extrair nomes e tempos médios
        nomes = [r.nome for r in tempo_medio_query]
        tempos = [round(r.tempo_medio, 1) if r.tempo_medio else 0 for r in tempo_medio_query]
        
        return {
            "labels": nomes,
            "datasets": [{
                "label": "Tempo Médio (dias)",
                "data": tempos,
                "backgroundColor": 'rgba(54, 162, 235, 0.7)',
                "borderColor": 'rgba(54, 162, 235, 1)',
                "borderWidth": 1
            }]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar tempo por categoria: {str(e)}")

# Rota para desempenho mensal
@dashboard_public_router.get("/desempenho-mensal")
async def get_desempenho_mensal(db: Session = Depends(get_db)):
    try:
        # Obtendo os meses para os últimos 12 meses
        data_atual = datetime.now()
        
        # Preparando o retorno
        labels = []
        taxas_resolucao = []
        tempos_medios = []
        
        # Percorrer os últimos 12 meses
        for i in range(12):
            data = data_atual - timedelta(days=30 * i)
            mes = data.month
            ano = data.year
            
            # Nome do mês em português
            #nome_mes = calendar.month_name[mes][:3]
            nomes_meses_pt = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
            mes_indice = data.month - 1  # Os índices começam em 0
            nome_mes = nomes_meses_pt[mes_indice]
            
            # Adicionar ao início para manter a ordem cronológica
            labels.insert(0, nome_mes)
            
            # Total de incidências no mês
            total_mes = db.query(func.count(models.Incidencia.incidencia_id)).filter(
                extract('month', models.Incidencia.data_hora) == mes,
                extract('year', models.Incidencia.data_hora) == ano
            ).scalar() or 0
            
            # Incidências resolvidas no mês
            resolvidas_mes = db.query(func.count(models.Incidencia.incidencia_id)).filter(
                extract('month', models.Incidencia.data_ultimo_status) == mes,
                extract('year', models.Incidencia.data_ultimo_status) == ano,
                models.Incidencia.status == 3  # Status 4 = Resolvido
            ).scalar() or 0
            
            # Taxa de resolução
            taxa = round((resolvidas_mes / total_mes * 100) if total_mes > 0 else 0, 1)
            taxas_resolucao.insert(0, taxa)
            
            # Tempo médio de resolução no mês
            tempo_medio_query = db.query(
                func.avg(
                    func.extract('epoch', models.Incidencia.data_ultimo_status - models.Incidencia.data_hora) / 86400
                )
            ).filter(
                extract('month', models.Incidencia.data_ultimo_status) == mes,
                extract('year', models.Incidencia.data_ultimo_status) == ano,
                models.Incidencia.status == 3  # Status 4 = Resolvido
            )
            
            tempo_medio = round(tempo_medio_query.scalar() or 0, 1)
            tempos_medios.insert(0, tempo_medio)
        
        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Taxa de Resolução (%)",
                    "data": taxas_resolucao,
                    "backgroundColor": 'rgba(255, 159, 64, 0.2)',
                    "borderColor": 'rgba(255, 159, 64, 1)',
                    "borderWidth": 2,
                    "yAxisID": 'y'
                },
                {
                    "label": "Tempo Médio (dias)",
                    "data": tempos_medios,
                    "backgroundColor": 'rgba(153, 102, 255, 0.2)',
                    "borderColor": 'rgba(153, 102, 255, 1)',
                    "borderWidth": 2,
                    "type": 'line',
                    "yAxisID": 'y1'
                }
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar desempenho mensal: {str(e)}")

# Rota para incidências por bairro
@dashboard_public_router.get("/incidencias-por-bairro")
async def get_incidencias_por_bairro(db: Session = Depends(get_db)):
    try:
        # Consultar incidências por bairro
        bairros_query = db.query(
            models.Incidencia.bairro,
            func.count(models.Incidencia.incidencia_id).label('total')
        ).group_by(
            models.Incidencia.bairro
        ).order_by(
            desc('total')
        ).limit(10)
        
        resultados = bairros_query.all()
        
        # Extrair bairros e totais
        bairros = [r.bairro for r in resultados if r.bairro]  # Filtrar valores nulos
        totais = [r.total for r in resultados if r.bairro]
        
        return {
            "labels": bairros,
            "datasets": [{
                "label": "Número de Incidências",
                "data": totais,
                "backgroundColor": 'rgba(75, 192, 192, 0.7)',
                "borderColor": 'rgba(75, 192, 192, 1)',
                "borderWidth": 1
            }]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar incidências por bairro: {str(e)}")

# Rota para tipos por região
@dashboard_public_router.get("/tipos-por-regiao")
async def get_tipos_por_regiao(db: Session = Depends(get_db)):
    try:
        # Determinar regiões - adaptado para usar o campo bairro para simplificar
        # Em uma implementação real, você precisaria de um mapeamento de bairros para regiões
        # Aqui, vamos supor que os primeiros caracteres do bairro indicam a região
        # Por exemplo, bairros começando com A-E são Zona Norte, F-J são Zona Sul, etc.
        
        # Primeiro, buscar as categorias
        categorias = db.query(models.Categoria).all()
        categoria_ids = {cat.categoria_id: cat.nome for cat in categorias}
        
        # Definir regiões para exemplo
        regioes = ["Zona Norte", "Zona Sul", "Zona Leste", "Zona Oeste", "Centro"]
        
        # Criar dados de exemplo - em uma implementação real, você faria uma consulta complexa
        # para agrupar por região e categoria
        datasets = []
        
        # Para cada categoria, criar um dataset
        for cat_id, cat_nome in categoria_ids.items():
            dados_regiao = []
            
            # Para cada região, contar incidências desta categoria
            for regiao in regioes:
                # Em uma implementação real, fazer uma consulta adequada
                # Aqui usamos dados fictícios para demonstração
                if regiao == "Zona Norte":
                    total = db.query(func.count(models.Incidencia.incidencia_id)).filter(
                        models.Incidencia.categoria_id == cat_id,
                        models.Incidencia.bairro.ilike('A%') | models.Incidencia.bairro.ilike('B%')
                    ).scalar() or 0
                elif regiao == "Zona Sul":
                    total = db.query(func.count(models.Incidencia.incidencia_id)).filter(
                        models.Incidencia.categoria_id == cat_id,
                        models.Incidencia.bairro.ilike('C%') | models.Incidencia.bairro.ilike('D%')
                    ).scalar() or 0
                elif regiao == "Zona Leste":
                    total = db.query(func.count(models.Incidencia.incidencia_id)).filter(
                        models.Incidencia.categoria_id == cat_id,
                        models.Incidencia.bairro.ilike('E%') | models.Incidencia.bairro.ilike('F%')
                    ).scalar() or 0
                elif regiao == "Zona Oeste":
                    total = db.query(func.count(models.Incidencia.incidencia_id)).filter(
                        models.Incidencia.categoria_id == cat_id,
                        models.Incidencia.bairro.ilike('G%') | models.Incidencia.bairro.ilike('H%')
                    ).scalar() or 0
                else:  # Centro
                    total = db.query(func.count(models.Incidencia.incidencia_id)).filter(
                        models.Incidencia.categoria_id == cat_id,
                        models.Incidencia.bairro.ilike('Centro%')
                    ).scalar() or 0
                
                dados_regiao.append(total)
            
            # Adicionar dataset para esta categoria
            datasets.append({
                "label": cat_nome,
                "data": dados_regiao,
                "backgroundColor": f'rgba({50 + cat_id * 40}, {100 + cat_id * 20}, {150 + cat_id * 10}, 0.7)'
            })
        
        return {
            "labels": regioes,
            "datasets": datasets
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar tipos por região: {str(e)}")

# Rota para taxa de resolução por bairro
@dashboard_public_router.get("/resolucao-por-bairro")
async def get_resolucao_por_bairro(db: Session = Depends(get_db)):
    try:
        # Buscar os 5 bairros com mais incidências
        top_bairros_query = db.query(
            models.Incidencia.bairro,
            func.count(models.Incidencia.incidencia_id).label('total')
        ).filter(
            models.Incidencia.bairro.isnot(None)
        ).group_by(
            models.Incidencia.bairro
        ).order_by(
            desc('total')
        ).limit(5)
        
        top_bairros = [r.bairro for r in top_bairros_query.all()]
        
        # Calcular taxa de resolução para cada bairro
        taxas_resolucao = []
        
        for bairro in top_bairros:
            # Total de incidências no bairro
            total_bairro = db.query(func.count(models.Incidencia.incidencia_id)).filter(
                models.Incidencia.bairro == bairro
            ).scalar() or 0
            
            # Incidências resolvidas no bairro
            resolvidas_bairro = db.query(func.count(models.Incidencia.incidencia_id)).filter(
                models.Incidencia.bairro == bairro,
                models.Incidencia.status == 4  # Status 4 = Resolvido
            ).scalar() or 0
            
            # Taxa de resolução
            taxa = round((resolvidas_bairro / total_bairro * 100) if total_bairro > 0 else 0, 1)
            taxas_resolucao.append(taxa)
        
        return {
            "labels": top_bairros,
            "datasets": [{
                "label": "Taxa de Resolução (%)",
                "data": taxas_resolucao,
                "backgroundColor": 'rgba(75, 192, 192, 0.7)',
                "borderColor": 'rgba(75, 192, 192, 1)',
                "borderWidth": 1
            }]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar resolução por bairro: {str(e)}")

# Adicione esta rota ao seu app.py ou main.py
# app.include_router(dashboard_public_router)


@dashboard_public_router.get("/data")
async def get_heatmap_data(db: Session = Depends(get_db)):
    try:
        # Buscar todas as incidências com coordenadas válidas
        incidencias = db.query(
            models.Incidencia.lat,
            models.Incidencia.long,
            models.Incidencia.categoria_id,
            models.Categoria.nome.label('categoria_nome')
        ).join(
            models.Categoria,
            models.Incidencia.categoria_id == models.Categoria.categoria_id
        ).filter(
            models.Incidencia.lat.isnot(None),
            models.Incidencia.long.isnot(None)
        ).all()
        
        # Extrair coordenadas e metadados
        pontos = []
        for inc in incidencias:
            if inc.lat and inc.long:
                pontos.append({
                    "lat": float(inc.lat),
                    "lng": float(inc.long),
                    "categoria_id": inc.categoria_id,
                    "categoria_nome": inc.categoria_nome
                })
        
        # Calcular o centro do mapa (média das coordenadas)
        if pontos:
            centro_lat = sum(p["lat"] for p in pontos) / len(pontos)
            centro_lng = sum(p["lng"] for p in pontos) / len(pontos)
        else:
            # Coordenadas padrão caso não haja pontos
            centro_lat = -15.793889
            centro_lng = -47.882778  # Coordenadas de Brasília como exemplo
        
        return {
            "pontos": pontos,
            "centro": {
                "lat": centro_lat,
                "lng": centro_lng
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar dados do mapa: {str(e)}")