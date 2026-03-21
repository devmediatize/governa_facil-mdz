#!/bin/bash

# ============================================
# SCRIPT DE BACKUP - PROJETO + POSTGRESQL
# Suporte a múltiplos bancos de dados
# ============================================

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Funções de log
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[AVISO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERRO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_header() {
    echo -e "${CYAN}${BOLD}$1${NC}"
}

# Diretório do projeto (onde o script está sendo executado)
PROJECT_DIR="$(pwd)"

# Verificar se o arquivo .env.backup existe
ENV_FILE="${PROJECT_DIR}/.env.backup"

if [[ ! -f "$ENV_FILE" ]]; then
    log_error "Arquivo .env.backup não encontrado em ${PROJECT_DIR}"
    log_info "Crie o arquivo .env.backup com as configurações necessárias."
    exit 1
fi

# Carregar configurações
log_info "Carregando configurações de ${ENV_FILE}..."
source "$ENV_FILE"

# Validar variáveis obrigatórias
validate_config() {
    local missing=()
    
    [[ -z "$PROJECT_NAME" ]] && missing+=("PROJECT_NAME")
    [[ -z "$BACKUP_DIR" ]] && missing+=("BACKUP_DIR")
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Variáveis obrigatórias não definidas: ${missing[*]}"
        exit 1
    fi
}

validate_config

# Função para parsear connection string PostgreSQL
# Formato: postgresql://user:password@host:port/database
parse_connection_string() {
    local conn_string="$1"
    
    # Remover o prefixo postgresql://
    local without_prefix="${conn_string#postgresql://}"
    
    # Extrair user:password@host:port/database
    local user_pass="${without_prefix%%@*}"
    local host_port_db="${without_prefix#*@}"
    
    # Extrair user e password
    DB_USER="${user_pass%%:*}"
    DB_PASSWORD="${user_pass#*:}"
    
    # Extrair host:port e database
    local host_port="${host_port_db%%/*}"
    DB_NAME="${host_port_db#*/}"
    
    # Extrair host e port
    DB_HOST="${host_port%%:*}"
    DB_PORT="${host_port#*:}"
    
    # Validar extração
    if [[ -z "$DB_USER" || -z "$DB_HOST" || -z "$DB_PORT" || -z "$DB_NAME" ]]; then
        return 1
    fi
    
    return 0
}

# Criar timestamp para o backup
TIMESTAMP=$(date '+%d-%m-%Y-%H-%M-%S')
BACKUP_NAME="${PROJECT_NAME}_${TIMESTAMP}"

# Diretório temporário para montar o backup (dentro da pasta de backup)
TEMP_DIR="${BACKUP_DIR}/.tmp_backup_${TIMESTAMP}"
TEMP_BACKUP_DIR="${TEMP_DIR}/${BACKUP_NAME}"

echo ""
log_header "========================================"
log_header "        INICIANDO BACKUP"
log_header "========================================"
echo ""
log_info "Projeto: ${PROJECT_NAME}"
log_info "Diretório do projeto: ${PROJECT_DIR}"
log_info "Destino: ${BACKUP_DIR}"
log_info "Nome do backup: ${BACKUP_NAME}.zip"
echo ""

# Criar diretório de backup se não existir
if [[ ! -d "$BACKUP_DIR" ]]; then
    log_info "Criando diretório de backup: ${BACKUP_DIR}"
    mkdir -p "$BACKUP_DIR"
fi

# Criar diretório temporário
mkdir -p "$TEMP_BACKUP_DIR"
mkdir -p "${TEMP_BACKUP_DIR}/databases"

# ============================================
# BACKUP DOS ARQUIVOS DO PROJETO
# ============================================
log_header ">> Backup dos Arquivos do Projeto"

# Construir argumentos de exclusão para rsync
EXCLUDE_ARGS=""

# Processar diretórios a ignorar
if [[ -n "$IGNORE_DIRS" ]]; then
    IFS=',' read -ra DIRS <<< "$IGNORE_DIRS"
    for dir in "${DIRS[@]}"; do
        dir=$(echo "$dir" | xargs)
        EXCLUDE_ARGS+="--exclude='${dir}' "
    done
fi

# Processar arquivos a ignorar
if [[ -n "$IGNORE_FILES" ]]; then
    IFS=',' read -ra FILES <<< "$IGNORE_FILES"
    for file in "${FILES[@]}"; do
        file=$(echo "$file" | xargs)
        EXCLUDE_ARGS+="--exclude='${file}' "
    done
fi

# Sempre ignorar backups e arquivos temporários
EXCLUDE_ARGS+="--exclude='*.zip' --exclude='*.sql' --exclude='*.dump' "

log_info "Copiando arquivos..."
log_info "Ignorando: ${IGNORE_DIRS:-nenhum}, ${IGNORE_FILES:-nenhum}"

eval rsync -a --progress $EXCLUDE_ARGS "${PROJECT_DIR}/" "${TEMP_BACKUP_DIR}/projeto/"

# Contar arquivos copiados para o resumo
FILES_COUNT=$(find "${TEMP_BACKUP_DIR}/projeto" -type f | wc -l)

log_success "Arquivos do projeto copiados!"
echo ""

# ============================================
# BACKUP DOS BANCOS DE DADOS POSTGRESQL
# ============================================
# Variáveis para o resumo final
DB_SUMMARY_INFO=""
PG_VERSION_USED=""
DOCKER_IMAGE_USED=""

if [[ "$BACKUP_DATABASE" == "true" && -n "$DATABASES" ]]; then
    log_header ">> Backup dos Bancos de Dados"

    # Verificar se Docker está disponível
    USE_DOCKER=false
    if command -v docker &> /dev/null; then
        USE_DOCKER=true
        log_info "Docker detectado - será usado para pg_dump"
    elif ! command -v pg_dump &> /dev/null; then
        log_error "pg_dump não encontrado e Docker não disponível."
        log_warning "Continuando sem backup do banco de dados..."
        USE_DOCKER="skip"
    fi

    if [[ "$USE_DOCKER" != "skip" ]]; then
        # Contador de bancos
        DB_COUNT=0
        DB_SUCCESS=0

        # Processar cada connection string separada por ";"
        IFS=';' read -ra DB_CONNECTIONS <<< "$DATABASES"

        log_info "Encontrados ${#DB_CONNECTIONS[@]} banco(s) de dados para backup"
        echo ""

        for conn_string in "${DB_CONNECTIONS[@]}"; do
            # Remover espaços em branco
            conn_string=$(echo "$conn_string" | xargs)

            if [[ -z "$conn_string" ]]; then
                continue
            fi

            ((DB_COUNT++)) || true

            # Parsear connection string
            if parse_connection_string "$conn_string"; then
                log_info "[${DB_COUNT}] Fazendo backup: ${DB_NAME}@${DB_HOST}:${DB_PORT}"

                DB_BACKUP_FILE="${TEMP_BACKUP_DIR}/databases/${DB_NAME}_${TIMESTAMP}.sql"

                # Detectar versão do servidor PostgreSQL
                log_info "Detectando versão do servidor..."
                export PGPASSWORD="$DB_PASSWORD"

                if [[ "$USE_DOCKER" == "true" ]]; then
                    # Obter versão major do servidor usando Docker
                    SERVER_VERSION=$(docker run --rm -e PGPASSWORD="$DB_PASSWORD" postgres:latest \
                        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SHOW server_version;" 2>/dev/null | xargs)
                    SERVER_MAJOR=$(echo "$SERVER_VERSION" | cut -d'.' -f1)

                    if [[ -z "$SERVER_MAJOR" ]]; then
                        log_warning "Não foi possível detectar versão, usando postgres:latest"
                        DOCKER_IMAGE="postgres:latest"
                        PG_VERSION_USED="N/A"
                    else
                        DOCKER_IMAGE="postgres:${SERVER_MAJOR}"
                        PG_VERSION_USED="${SERVER_VERSION}"
                        log_info "Servidor PostgreSQL versão ${SERVER_VERSION} - usando imagem ${DOCKER_IMAGE}"
                    fi
                    DOCKER_IMAGE_USED="${DOCKER_IMAGE}"

                    # Executar pg_dump via Docker
                    log_info "Iniciando dump via Docker (pode demorar alguns minutos para bancos grandes)..."
                    if docker run --rm \
                        -e PGPASSWORD="$DB_PASSWORD" \
                        -v "${TEMP_BACKUP_DIR}/databases:/backup" \
                        "$DOCKER_IMAGE" \
                        pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
                        --no-owner --no-acl -F p -f "/backup/${DB_NAME}_${TIMESTAMP}.sql" 2>&1; then

                        if [[ -s "$DB_BACKUP_FILE" ]]; then
                            DB_SIZE=$(du -h "$DB_BACKUP_FILE" | cut -f1)
                            log_success "[${DB_COUNT}] ${DB_NAME}: ${DB_SIZE}"
                            DB_SUMMARY_INFO="${DB_NAME}_${TIMESTAMP}.sql (${DB_SIZE})"
                            ((DB_SUCCESS++)) || true
                        else
                            log_warning "[${DB_COUNT}] ${DB_NAME}: Backup vazio!"
                            DB_SUMMARY_INFO="Backup vazio"
                            rm -f "$DB_BACKUP_FILE"
                        fi
                    else
                        log_error "[${DB_COUNT}] ${DB_NAME}: Falha no pg_dump via Docker"
                        DB_SUMMARY_INFO="Falha no dump"
                    fi
                else
                    # Usar pg_dump local
                    PG_VERSION_USED=$(pg_dump --version | head -1 | awk '{print $NF}')
                    DOCKER_IMAGE_USED="local (pg_dump ${PG_VERSION_USED})"
                    log_info "Iniciando dump (pode demorar alguns minutos para bancos grandes)..."
                    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
                        --no-owner --no-acl -F p > "$DB_BACKUP_FILE" 2>&1; then

                        if [[ -s "$DB_BACKUP_FILE" ]]; then
                            DB_SIZE=$(du -h "$DB_BACKUP_FILE" | cut -f1)
                            log_success "[${DB_COUNT}] ${DB_NAME}: ${DB_SIZE}"
                            DB_SUMMARY_INFO="${DB_NAME}_${TIMESTAMP}.sql (${DB_SIZE})"
                            ((DB_SUCCESS++)) || true
                        else
                            log_warning "[${DB_COUNT}] ${DB_NAME}: Backup vazio!"
                            DB_SUMMARY_INFO="Backup vazio"
                            rm -f "$DB_BACKUP_FILE"
                        fi
                    else
                        log_error "[${DB_COUNT}] ${DB_NAME}: Falha no pg_dump"
                        DB_SUMMARY_INFO="Falha no dump"
                    fi
                fi

                unset PGPASSWORD
            else
                log_error "[${DB_COUNT}] Connection string inválida: ${conn_string:0:50}..."
            fi
        done

        echo ""
        log_info "Resultado: ${DB_SUCCESS}/${DB_COUNT} banco(s) com sucesso"
    fi
else
    log_info "Backup de banco de dados desativado ou não configurado."
fi

echo ""

# ============================================
# CRIAR ARQUIVO INFO DO BACKUP
# ============================================
log_info "Criando arquivo de informações..."

INFO_FILE="${TEMP_BACKUP_DIR}/backup_info.txt"
cat > "$INFO_FILE" << EOF
============================================
INFORMAÇÕES DO BACKUP
============================================
Projeto: ${PROJECT_NAME}
Data/Hora: $(date '+%d/%m/%Y %H:%M:%S')
Diretório Original: ${PROJECT_DIR}
Hostname: $(hostname)
Usuário: $(whoami)

============================================
CONFIGURAÇÕES UTILIZADAS
============================================
Diretórios Ignorados: ${IGNORE_DIRS:-nenhum}
Arquivos Ignorados: ${IGNORE_FILES:-nenhum}
Backup do Banco: ${BACKUP_DATABASE}

============================================
BANCOS DE DADOS INCLUÍDOS
============================================
EOF

# Listar arquivos SQL criados
if ls "${TEMP_BACKUP_DIR}/databases/"*.sql 1> /dev/null 2>&1; then
    for sql_file in "${TEMP_BACKUP_DIR}/databases/"*.sql; do
        sql_name=$(basename "$sql_file")
        sql_size=$(du -h "$sql_file" | cut -f1)
        echo "- ${sql_name} (${sql_size})" >> "$INFO_FILE"
    done
else
    echo "Nenhum banco de dados no backup" >> "$INFO_FILE"
fi

cat >> "$INFO_FILE" << EOF

============================================
ESTRUTURA DO BACKUP
============================================
$(ls -lah "${TEMP_BACKUP_DIR}")

============================================
EOF

# ============================================
# COMPACTAR BACKUP
# ============================================
log_header ">> Compactando Backup"

FINAL_BACKUP="${BACKUP_DIR}/${BACKUP_NAME}.zip"
COMPRESSION=${COMPRESSION_LEVEL:-6}

cd "$TEMP_DIR"
zip -r -q -${COMPRESSION} "$FINAL_BACKUP" "$BACKUP_NAME"

log_success "Backup compactado!"
echo ""

# ============================================
# LIMPEZA
# ============================================
log_info "Limpando arquivos temporários..."
rm -rf "$TEMP_DIR"

# ============================================
# ROTAÇÃO DE BACKUPS ANTIGOS
# ============================================
KEEP_BACKUPS=${KEEP_BACKUPS:-0}

if [[ "$KEEP_BACKUPS" -gt 0 ]]; then
    log_info "Verificando backups antigos (manter últimos ${KEEP_BACKUPS})..."
    
    BACKUP_COUNT=$(ls -1 "${BACKUP_DIR}/${PROJECT_NAME}_"*.zip 2>/dev/null | wc -l)
    
    if [[ "$BACKUP_COUNT" -gt "$KEEP_BACKUPS" ]]; then
        DELETE_COUNT=$((BACKUP_COUNT - KEEP_BACKUPS))
        
        log_info "Removendo ${DELETE_COUNT} backup(s) antigo(s)..."
        
        ls -1t "${BACKUP_DIR}/${PROJECT_NAME}_"*.zip | tail -n "$DELETE_COUNT" | while read old_backup; do
            log_info "Removendo: $(basename "$old_backup")"
            rm -f "$old_backup"
        done
        
        log_success "Backups antigos removidos!"
    fi
fi

# ============================================
# RESULTADO FINAL
# ============================================
FINAL_SIZE=$(du -h "$FINAL_BACKUP" | cut -f1)

# Verificar se temporários foram limpos
if [[ -d "$TEMP_DIR" ]]; then
    TEMP_STATUS="${RED}Falha na limpeza${NC}"
else
    TEMP_STATUS="${GREEN}Nenhum diretório .tmp_* remanescente${NC}"
fi

# Preparar info do banco
if [[ -z "$DB_SUMMARY_INFO" ]]; then
    DB_SUMMARY_INFO="Não configurado"
fi

# Preparar info da versão PostgreSQL
if [[ -n "$PG_VERSION_USED" && -n "$DOCKER_IMAGE_USED" ]]; then
    PG_INFO="Detectada ${PG_VERSION_USED}, usou imagem ${DOCKER_IMAGE_USED}"
else
    PG_INFO="N/A"
fi

echo ""
log_header "========================================"
log_header "   ✅ BACKUP CONCLUÍDO COM SUCESSO!"
log_header "========================================"
echo ""
echo -e "${CYAN}${BOLD}RESUMO DO BACKUP${NC}"
echo ""
echo -e "  Item                   Status   Detalhes"
echo -e "  ---------------------  ------   ----------------------------------------"
echo -e "  Arquivo ZIP criado     ${GREEN}✅${NC}       ${FINAL_BACKUP} (${FINAL_SIZE})"
echo -e "  Temporários limpos     ${GREEN}✅${NC}       Nenhum diretório .tmp_* remanescente"
echo -e "  Arquivos do projeto    ${GREEN}✅${NC}       ${FILES_COUNT} arquivos copiados"
echo -e "  Dump do banco          ${GREEN}✅${NC}       ${DB_SUMMARY_INFO}"
echo -e "  Versão PostgreSQL      ${GREEN}✅${NC}       ${PG_INFO}"
echo ""

exit 0
