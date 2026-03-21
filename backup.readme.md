# 📦 Sistema de Backup - Projeto + PostgreSQL

Sistema completo de backup e restauração para projetos de desenvolvimento com suporte a múltiplos bancos de dados PostgreSQL.

---

## 📁 Arquivos do Sistema

| Arquivo | Descrição |
|---------|-----------|
| `backup.sh` | Script principal para criar backups |
| `backup_restore.sh` | Script para restaurar backups com menu interativo |
| `.env.backup` | Arquivo de configuração |

---

## 🚀 Instalação

### 1. Copie os arquivos para a raiz do seu projeto

```bash
cp backup.sh /caminho/do/seu/projeto/
cp backup_restore.sh /caminho/do/seu/projeto/
cp .env.backup /caminho/do/seu/projeto/
```

### 2. Dê permissão de execução

```bash
chmod +x backup.sh backup_restore.sh
```

### 3. Configure o arquivo `.env.backup`

Edite o arquivo com suas configurações (veja seção de configuração abaixo).

---

## ⚙️ Configuração do `.env.backup`

```bash
# ============================================
# CONFIGURAÇÃO BÁSICA
# ============================================

# Nome do projeto (usado no nome do arquivo de backup)
PROJECT_NAME="meu_projeto"

# Diretório onde os backups serão salvos
BACKUP_DIR="/caminho/para/backups"

# ============================================
# BANCO DE DADOS POSTGRESQL
# ============================================

# Formato da connection string:
# postgresql://USUARIO:SENHA@HOST:PORTA/NOME_BANCO

# Um único banco:
DATABASES="postgresql://postgres:senha123@localhost:5432/meu_banco"

# Múltiplos bancos (separados por ";"):
DATABASES="postgresql://user:pass@host:5432/banco1;postgresql://user:pass@host:5432/banco2;postgresql://user:pass@host:5432/banco3"

# ============================================
# EXCLUSÕES
# ============================================

# Diretórios a ignorar (separados por vírgula)
IGNORE_DIRS=".git,node_modules,__pycache__,.venv,venv,.claude,.cache,logs"

# Arquivos a ignorar (separados por vírgula, suporta wildcards)
IGNORE_FILES="*.log,*.pyc,*.tmp,.DS_Store"

# ============================================
# OPÇÕES ADICIONAIS
# ============================================

# Quantidade de backups antigos a manter (0 = manter todos)
KEEP_BACKUPS=10

# Fazer backup do banco de dados? (true/false)
BACKUP_DATABASE=true

# Nível de compressão ZIP (1-9, onde 9 é máximo)
COMPRESSION_LEVEL=6
```

---

## 📋 Uso

### Criar Backup

```bash
cd /caminho/do/seu/projeto
./backup.sh
```

**Saída esperada:**

```
========================================
        INICIANDO BACKUP
========================================

[INFO] Projeto: meu_projeto
[INFO] Diretório do projeto: /caminho/do/seu/projeto
[INFO] Destino: /caminho/para/backups
[INFO] Nome do backup: meu_projeto_04-12-2025-14-30-45.zip

>> Backup dos Arquivos do Projeto
[INFO] Copiando arquivos...
[OK] Arquivos do projeto copiados!

>> Backup dos Bancos de Dados
[INFO] Encontrados 2 banco(s) de dados para backup
[OK] [1] banco1: 2.5M
[OK] [2] banco2: 1.8M

>> Compactando Backup
[OK] Backup compactado!

========================================
      BACKUP CONCLUÍDO COM SUCESSO!
========================================

[INFO] Arquivo: /caminho/para/backups/meu_projeto_04-12-2025-14-30-45.zip
[INFO] Tamanho: 5.2M
```

---

### Restaurar Backup

```bash
cd /caminho/do/seu/projeto
./backup_restore.sh
```

**Menu interativo:**

```
========================================
     BACKUPS DISPONÍVEIS
========================================

Nº   ARQUIVO                                  DATA/HORA            TAMANHO
---  ---------------------------------------- -------------------- ----------
[1]  meu_projeto_04-12-2025-14-30-45.zip     04/12/2025 14:30:45  5.2M
[2]  meu_projeto_03-12-2025-22-15-10.zip     03/12/2025 22:15:10  4.8M
[3]  meu_projeto_02-12-2025-18-00-00.zip     02/12/2025 18:00:00  4.5M

[0]  Cancelar e sair

Selecione o backup para restaurar [0-3]: 
```

**Opções de restauração:**

```
========================================
     OPÇÕES DE RESTAURAÇÃO
========================================

[1] Apenas arquivos do projeto
[2] Apenas banco(s) de dados
[3] Tudo (arquivos + banco de dados)
[0] Cancelar
```

---

## 📂 Estrutura do Backup

O arquivo ZIP gerado contém:

```
meu_projeto_04-12-2025-14-30-45/
├── projeto/                    # Arquivos do projeto
│   ├── app/
│   ├── templates/
│   ├── static/
│   ├── requirements.txt
│   ├── docker-compose.yml
│   └── ...
├── databases/                  # Dumps dos bancos de dados
│   ├── banco1_04-12-2025-14-30-45.sql
│   └── banco2_04-12-2025-14-30-45.sql
└── backup_info.txt             # Informações do backup
```

---

## 🗄️ Backup do Banco de Dados

### O que é incluído (Backup FULL)

| Componente | Incluído |
|------------|:--------:|
| Estrutura das tabelas (CREATE TABLE) | ✅ |
| Todos os dados (INSERT) | ✅ |
| Índices | ✅ |
| Sequences (auto-increment) | ✅ |
| Views | ✅ |
| Functions / Stored Procedures | ✅ |
| Triggers | ✅ |
| Constraints (PK, FK, Unique, Check) | ✅ |
| Types customizados | ✅ |
| Extensions | ✅ |

### Comando utilizado

```bash
pg_dump -h HOST -p PORTA -U USUARIO -d BANCO \
        --no-owner --no-acl -F p > dump.sql
```

| Parâmetro | Descrição |
|-----------|-----------|
| `--no-owner` | Não inclui comandos de ownership |
| `--no-acl` | Não inclui permissões (evita erros de roles) |
| `-F p` | Formato plain text (SQL legível) |

---

## 🔄 Restauração do Banco de Dados

A restauração é **FULL** - executa todo o SQL do dump:

```bash
psql -h HOST -p PORTA -U USUARIO -d BANCO < dump.sql
```

### ⚠️ Atenção

- A restauração **sobrescreve** dados existentes
- Podem ocorrer conflitos se houver dados duplicados
- Recomenda-se fazer backup antes de restaurar

---

## 📅 Rotação de Backups

O sistema mantém automaticamente apenas os últimos N backups (configurável via `KEEP_BACKUPS`).

```bash
# Manter últimos 10 backups
KEEP_BACKUPS=10

# Manter todos os backups (sem rotação)
KEEP_BACKUPS=0
```

Backups mais antigos são removidos automaticamente após cada novo backup.

---

## 🔧 Requisitos

### Sistema

- Linux (Ubuntu/Debian recomendado)
- Bash 4.0+
- rsync
- zip / unzip

### PostgreSQL

- postgresql-client (para `pg_dump` e `psql`)

**Instalação do cliente PostgreSQL:**

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql-client

# CentOS/RHEL
sudo yum install postgresql

# Alpine
apk add postgresql-client
```

---

## 📝 Formato do Nome do Backup

```
{PROJECT_NAME}_{DD}-{MM}-{YYYY}-{HH}-{MM}-{SS}.zip
```

**Exemplo:**

```
meu_projeto_04-12-2025-14-30-45.zip
│            │  │  │    │  │  │
│            │  │  │    │  │  └── Segundo (45)
│            │  │  │    │  └───── Minuto (30)
│            │  │  │    └──────── Hora (14)
│            │  │  └───────────── Ano (2025)
│            │  └──────────────── Mês (12)
│            └─────────────────── Dia (04)
└──────────────────────────────── Nome do projeto
```

---

## 🛠️ Solução de Problemas

### Erro: "pg_dump não encontrado"

```bash
sudo apt-get install postgresql-client
```

### Erro: "Conexão recusada ao banco"

Verifique:
1. Host e porta estão corretos
2. Usuário e senha estão corretos
3. Banco de dados existe
4. Firewall permite conexão na porta

### Erro: "Permissão negada"

```bash
chmod +x backup.sh backup_restore.sh
```

### Backup muito grande

Aumente o nível de compressão:

```bash
COMPRESSION_LEVEL=9
```

Ou adicione mais diretórios ao `IGNORE_DIRS`.

---

## 📌 Exemplos de Configuração

### Projeto Python/Flask

```bash
PROJECT_NAME="minha_api"
BACKUP_DIR="/backups/api"
DATABASES="postgresql://api_user:senha@localhost:5432/api_db"
IGNORE_DIRS=".git,__pycache__,.venv,venv,.pytest_cache,htmlcov"
IGNORE_FILES="*.log,*.pyc,*.pyo,.coverage,*.egg-info"
KEEP_BACKUPS=15
BACKUP_DATABASE=true
COMPRESSION_LEVEL=6
```

### Projeto Node.js

```bash
PROJECT_NAME="minha_app_node"
BACKUP_DIR="/backups/node"
DATABASES="postgresql://node_user:senha@db.servidor.com:5432/app_db"
IGNORE_DIRS=".git,node_modules,dist,build,.next,coverage"
IGNORE_FILES="*.log,.env.local,npm-debug.log"
KEEP_BACKUPS=10
BACKUP_DATABASE=true
COMPRESSION_LEVEL=6
```

### Múltiplos Bancos

```bash
PROJECT_NAME="sistema_completo"
BACKUP_DIR="/nvme/backups"
DATABASES="postgresql://admin:senha@db.empresa.com:5432/sistema_principal;postgresql://admin:senha@db.empresa.com:5432/sistema_logs;postgresql://admin:senha@db.empresa.com:5432/sistema_cache"
IGNORE_DIRS=".git,node_modules,__pycache__,.venv"
IGNORE_FILES="*.log,*.tmp"
KEEP_BACKUPS=20
BACKUP_DATABASE=true
COMPRESSION_LEVEL=7
```

---

## 📜 Licença

Este script é fornecido "como está", sem garantias. Use por sua conta e risco.

---

## 🤝 Suporte

Em caso de dúvidas ou problemas, verifique:

1. Se o arquivo `.env.backup` está configurado corretamente
2. Se as permissões dos scripts estão corretas (`chmod +x`)
3. Se o `postgresql-client` está instalado
4. Se as credenciais do banco estão corretas

---

**Última atualização:** 04/12/2025
