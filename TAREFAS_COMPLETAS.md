# TAREFAS GOVERNA FÁCIL - CHECKLIST COMPLETO

Data: 2026-03-17

---

## 1. LAYOUT E DESIGN

| # | Tarefa | Status | Observação |
|---|--------|--------|------------|
| 1.1 | Sidebar lateral escura (estilo mdz_patrimonio) | FEITO | base.html atualizado |
| 1.2 | Logos maiores (120px sidebar, 100px cliente) | FEITO | CSS em base.html |
| 1.3 | Acentos corrigidos em menus e textos | FEITO | Todos os templates |
| 1.4 | Cores das abas de configuração legíveis | FEITO | configuracao.html |
| 1.5 | Nome e foto usuário juntos no canto direito header | FEITO | base.html |
| 1.6 | Botão Assistente IA centralizado no header | FEITO | header-center div |
| 1.7 | Header do assistente com cores parametrizadas | FEITO | assistente-ia.css |
| 1.8 | Botão do assistente com cores do sidebar | FEITO | assistente-ia.css |
| 1.9 | Menu com contraste (texto branco fundo escuro) | FEITO | nav-link rgba(255,255,255,0.85) |

---

## 2. MAPA

| # | Tarefa | Status | Observação |
|---|--------|--------|------------|
| 2.1 | Link para mapa ampliado no dashboard | FEITO | Botão fullscreen |
| 2.2 | Página de mapa em tela cheia (/mapa) | FEITO | templates/mapa.html criado |
| 2.3 | Menu "Mapa" no sidebar | FEITO | base.html |
| 2.4 | Filtro por bairro no dashboard | FEITO | select + JS |
| 2.5 | Filtro por bairro/status/categoria na página mapa | FEITO | mapa.html |
| 2.6 | Correção contador vs marcadores (lat/lng válidos) | FEITO | main.py endpoint corrigido |

---

## 3. PERFIL DO USUÁRIO

| # | Tarefa | Status | Observação |
|---|--------|--------|------------|
| 3.1 | Endpoint /api/usuario/perfil para atualizar dados | FEITO | main.py |
| 3.2 | Endpoint /dados-usuarios retorna email, celular, foto | FEITO | main.py |
| 3.3 | Campo email no perfil somente leitura | FEITO | readonly + style |
| 3.4 | Endpoint /api/usuario/foto para upload | FEITO | main.py |
| 3.5 | Campo 'foto' no modelo Usuario | FEITO | models.py |
| 3.6 | Upload de foto funcional no modal | FEITO | base.html JS |
| 3.7 | Foto exibida no avatar do header | FEITO | carregarDadosUsuario() |
| 3.8 | Modal de perfil carrega dados do usuário | FEITO | window.currentUser |

---

## 4. CONFIGURAÇÃO DE IA

| # | Tarefa | Status | Observação |
|---|--------|--------|------------|
| 4.1 | Campo Provedor (OpenRouter, OpenAI, etc) | FEITO | select aiProvider |
| 4.2 | Campo URL da API | FEITO | input aiApiUrl |
| 4.3 | Campo API Key | FEITO | input aiApiKey |
| 4.4 | Campo Modelo LLM (input texto livre) | FEITO | input aiModel |
| 4.5 | Campo Embedding Provider | FEITO | select embeddingProvider |
| 4.6 | Campo Embedding Model | FEITO | input embeddingModel |
| 4.7 | Campo Embedding API URL | FEITO | input embeddingApiUrl |
| 4.8 | Campo Embedding API Key | FEITO | input embeddingApiKey |
| 4.9 | Campo Retry Attempts | FEITO | input aiRetryAttempts |
| 4.10 | Campos Temperatura, Max Tokens, Context Window, Timeout | FEITO | inputs numéricos |
| 4.11 | JavaScript envia todos campos de embedding | FEITO | btnSalvarIA |
| 4.12 | JavaScript carrega todos campos de embedding | FEITO | carregarConfiguracaoIA |
| 4.13 | Prompt do assistente para gráficos/relatórios | PENDENTE | Melhorar system_prompt |

---

## 5. DASHBOARD INTELIGENTE

| # | Tarefa | Status | Observação |
|---|--------|--------|------------|
| 5.1 | Cards de estatísticas (Total, Novos, Andamento, Resolvidos) | FEITO | stats-grid |
| 5.2 | Insights básicos (Hoje, Bairro, Categoria) | FEITO | insights-grid |
| 5.3 | Taxa de Resolução (% resolvidas) | FEITO | advanced-insights-grid |
| 5.4 | Tempo Médio de Resolução (dias) | FEITO | advanced-insights-grid |
| 5.5 | Comparativo Semanal (+X% ou -X%) | FEITO | advanced-insights-grid |
| 5.6 | Bairro Crítico (mais pendências) | FEITO | advanced-insights-grid |
| 5.7 | Categoria em Alta (mais cresceu) | FEITO | advanced-insights-grid |
| 5.8 | Cores dinâmicas (verde/amarelo/vermelho) | FEITO | renderEstatisticasAvancadas() |
| 5.9 | Endpoint /api/dashboard/estatisticas-avancadas | FEITO | main.py |
| 5.10 | Gráfico de evolução temporal (linha do tempo) | PENDENTE | |
| 5.11 | Heatmap de horários | PENDENTE | |

---

## 6. CATEGORIAS

| # | Tarefa | Status | Observação |
|---|--------|--------|------------|
| 6.1 | Menu Categorias no sidebar (Administração) | FEITO | base.html |
| 6.2 | Página de listagem de categorias | FEITO | categorias.html |
| 6.3 | Modal adicionar/editar categoria | FEITO | categorias.html |
| 6.4 | Campo nome | FEITO | input |
| 6.5 | Seletor de ícone visual (Bootstrap Icons) | FEITO | grid 80+ ícones |
| 6.6 | Campo cor (color picker) | FEITO | input type=color |
| 6.7 | Preview do ícone ao selecionar | FEITO | JS |
| 6.8 | Campos icone e cor no modelo Categoria | FEITO | models.py |
| 6.9 | Endpoints GET/POST/PUT/DELETE categorias | FEITO | main.py |
| 6.10 | Script SQL para adicionar colunas | FEITO | scripts/add_categoria_fields.sql |

---

## 7. MODAL PERMISSÕES CATEGORIAS (USUÁRIOS)

| # | Tarefa | Status | Observação |
|---|--------|--------|------------|
| 7.1 | Modal muito estreito cortando categorias | PENDENTE | Precisa aumentar largura |

---

## 8. GITHUB

| # | Tarefa | Status | Observação |
|---|--------|--------|------------|
| 8.1 | Remover venv/ do rastreamento git | PENDENTE | git rm -r --cached venv/ |
| 8.2 | Commitar alterações pendentes | PENDENTE | |
| 8.3 | Mudar remote para governa_facil-mdz | PENDENTE | |
| 8.4 | Push para novo repositório | PENDENTE | Aguardando autorização |
| 8.5 | NÃO substituir .env local | OK | .gitignore protege |

**Dados GitHub:**
- Repositório: https://github.com/devmediatize/governa_facil-mdz.git
- Token: [REMOVIDO POR SEGURANÇA]
- URL com Token: [REMOVIDO POR SEGURANÇA]

---

## 9. OUTRAS PENDÊNCIAS

| # | Tarefa | Status | Observação |
|---|--------|--------|------------|
| 9.1 | Verificar modelo banco tem campos embedding | PENDENTE | |
| 9.2 | Endpoint salvar config IA com campos embedding | PENDENTE | Verificar se já existe |
| 9.3 | Status de incidências (CRUD) | VERIFICAR | Existe templates/status.html? |

---

## ARQUIVOS MODIFICADOS/CRIADOS

### Templates:
- templates/base.html - Layout principal, sidebar, header, modal perfil
- templates/dashboard.html - Dashboard com estatísticas avançadas
- templates/mapa.html - NOVO - Mapa em tela cheia
- templates/categorias.html - CRUD categorias com ícones
- templates/configuracao.html - Abas corrigidas, IA com embedding

### CSS:
- static/css/assistente-ia.css - Cores parametrizadas
- static/css/style.css - Estilos gerais

### JavaScript:
- static/js/assistente-ia.js - Chat assistente

### Backend:
- app/main.py - Novos endpoints (mapa, perfil, foto, estatísticas avançadas, categorias)
- app/models.py - Campos foto (Usuario), icone/cor (Categoria)

### Outros:
- scripts/add_categoria_fields.sql - NOVO - Script SQL
- fotos/usuarios/ - NOVO - Diretório para fotos de perfil
- TAREFAS_COMPLETAS.md - Este arquivo

---

## RESUMO

| Categoria | Total | Feitas | Pendentes |
|-----------|-------|--------|-----------|
| Layout/Design | 9 | 9 | 0 |
| Mapa | 6 | 6 | 0 |
| Perfil Usuário | 8 | 8 | 0 |
| Config IA | 13 | 12 | 1 |
| Dashboard | 11 | 9 | 2 |
| Categorias | 10 | 10 | 0 |
| Modal Permissões | 1 | 0 | 1 |
| GitHub | 5 | 1 | 4 |
| Outras | 3 | 0 | 3 |
| **TOTAL** | **66** | **55** | **11** |

---

Última atualização: 2026-03-17
