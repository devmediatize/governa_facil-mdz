# TAREFAS GOVERNA FÁCIL - CHECKLIST

## CONCLUÍDO

### Layout e Design
- [x] Sidebar lateral escura (estilo mdz_patrimonio)
- [x] Logos maiores (120px sidebar, 100px cliente)
- [x] Acentos corrigidos em todos os menus e textos
- [x] Cores das abas de configuração corrigidas (fundo branco/texto escuro)
- [x] Nome e foto do usuário juntos no canto direito do header
- [x] Botão Assistente IA centralizado no header
- [x] Header do assistente com cores parametrizadas do sidebar
- [x] Botão do assistente com cores parametrizadas do sidebar

### Mapa
- [x] Link para mapa ampliado no dashboard
- [x] Página de mapa em tela cheia (/mapa)
- [x] Menu "Mapa" no sidebar
- [x] Filtro por bairro no dashboard
- [x] Filtro por bairro/status/categoria na página de mapa
- [x] Correção do contador vs marcadores (só mostra incidências com lat/lng válidos)

### Perfil do Usuário
- [x] Endpoint /api/usuario/perfil para atualizar dados
- [x] Endpoint /dados-usuarios agora retorna email, celular, foto
- [x] Campo email no perfil é somente leitura
- [x] Endpoint /api/usuario/foto para upload de foto
- [x] Campo 'foto' adicionado no modelo Usuario
- [x] Upload de foto funcional no modal de perfil
- [x] Foto exibida no avatar do header

### Configuração de IA
- [x] Campo de Provedor (OpenRouter, OpenAI, Anthropic, etc)
- [x] Campo de URL da API
- [x] Campo de API Key
- [x] Campo de Modelo LLM (input texto livre)
- [x] Campos de Embedding (provedor, modelo, url, api_key)
- [x] Campo Retry Attempts
- [x] Temperatura, Max Tokens, Context Window, Timeout

---

## PENDENTE

### Dashboard Inteligente (FALTA FAZER)
- [ ] Previsão de tendências (ex: "Incidências devem aumentar 15% na próxima semana")
- [ ] Alertas automáticos (ex: "Bairro X tem 3x mais incidências que a média")
- [ ] Comparativo com período anterior (semana/mês passado)
- [ ] Tempo médio de resolução por categoria
- [ ] Taxa de resolução (% resolvidas vs total)
- [ ] Ranking de bairros mais problemáticos
- [ ] Gráfico de evolução temporal (linha do tempo)
- [ ] Heatmap de horários com mais incidências
- [ ] Análise de sazonalidade

### Categorias (FALTA FAZER)
- [ ] Menu de categorias no sidebar (Administração)
- [ ] CRUD completo de categorias
- [ ] Seletor de ícone para cada categoria (Bootstrap Icons)
- [ ] Preview do ícone ao selecionar
- [ ] Campo de cor para cada categoria

### GitHub (AGUARDANDO AUTORIZAÇÃO)
- [ ] Remover venv/ do rastreamento git
- [ ] Commitar alterações pendentes
- [ ] Mudar remote para governa_facil-mdz
- [ ] Push para novo repositório
- IMPORTANTE: NÃO substituir .env local

### Outras Pendências
- [ ] Prompt do assistente IA melhorado para gerar gráficos/relatórios
- [ ] Verificar se modelo no banco tem todos campos de embedding
- [ ] Criar endpoint para salvar configuração de IA com campos de embedding

---

## DADOS DO GITHUB (para sincronização)

```
Repositório: https://github.com/devmediatize/governa_facil-mdz.git
Token: [REMOVIDO POR SEGURANÇA]
URL com Token: [REMOVIDO POR SEGURANÇA]
```

### Passos para sincronizar:
1. `git rm -r --cached venv/` (remover venv do git)
2. `git add .` (adicionar alterações)
3. `git commit -m "Atualizações Governa Fácil"`
4. `git remote set-url origin https://ghp_...@github.com/devmediatize/governa_facil-mdz.git`
5. `git push -u origin main`

---

## ESTRUTURA DE IA DO MDZ_PREV (REFERÊNCIA)

Campos da tabela de configuração:
- id
- provider
- model_name
- embedding_model
- api_url
- api_key
- temperature
- max_tokens
- timeout
- retry_attempts
- context_window
- is_active
- created_at
- updated_at
- system_prompt
- embedding_provider
- embedding_api_url
- embedding_api_key
- chat_habilitado

---

Última atualização: 2026-03-17
