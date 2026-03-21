#!/bin/bash

# ============================================
# SCRIPT DE RESTAURAÇÃO - PROJETO + POSTGRESQL
# Com listagem e seleção de backups
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

# Diretório do projeto
PROJECT_DIR="$(pwd)"
ENV_FILE="${PROJECT_DIR}/.env.backup"

# Função para parsear connection string PostgreSQL
parse_connection_string() {
    local conn_string="$1"
    
    local without_prefix="${conn_string#postgresql://}"
    local user_pass="${without_prefix%%@*}"
    local host_port_db="${without_prefix#*@}"
    
    DB_USER="${user_pass%%:*}"
    DB_PASSWORD="${user_pass#*:}"
    
    local host_port="${host_port_db%%/*}"
    DB_NAME="${host_port_db#*/}"
    
    DB_HOST="${host_port%%:*}"
    DB_PORT="${host_port#*:}"
    
    if [[ -z "$DB_USER" || -z "$DB_HOST" || -z "$DB_PORT" || -z "$DB_NAME" ]]; then
        return 1
    fi
    
    return 0
}

# Função para listar backups disponíveis
list_backups() {
    local backup_dir="$1"
    local project_name="$2"
    local -n backup_array=$3
    
    backup_array=()
    
    if [[ ! -d "$backup_dir" ]]; then
        return 1
    fi
    
    # Buscar arquivos de backup ordenados por data (mais recente primeiro)
    while IFS= read -r file; do
        if [[ -n "$file" ]]; then
            backup_array+=("$file")
        fi
    done < <(ls -1t "${backup_dir}/${project_name}_"*.zip 2>/dev/null)
    
    if [[ ${#backup_array[@]} -eq 0 ]]; then
        return 1
    fi
    
    return 0
}

# Função para extrair informações do nome do backup
parse_backup_name() {
    local filename="$1"
    local basename=$(basename "$filename" .zip)
    
    # Formato: NomeProjeto_DD-MM-YYYY-HH-MM-SS
    if [[ $basename =~ ^(.+)_([0-9]{2})-([0-9]{2})-([0-9]{4})-([0-9]{2})-([0-9]{2})-([0-9]{2})$ ]]; then
        BACKUP_PROJECT="${BASH_REMATCH[1]}"
        BACKUP_DAY="${BASH_REMATCH[2]}"
        BACKUP_MONTH="${BASH_REMATCH[3]}"
        BACKUP_YEAR="${BASH_REMATCH[4]}"
        BACKUP_HOUR="${BASH_REMATCH[5]}"
        BACKUP_MIN="${BASH_REMATCH[6]}"
        BACKUP_SEC="${BASH_REMATCH[7]}"
        return 0
    fi
    return 1
}

# Função para mostrar menu de seleção
show_backup_menu() {
    local -n backups=$1
    local selected=0
    local total=${#backups[@]}
    
    echo ""
    log_header "========================================"
    log_header "     BACKUPS DISPONÍVEIS"
    log_header "========================================"
    echo ""
    
    printf "%-4s %-40s %-20s %-10s\n" "Nº" "ARQUIVO" "DATA/HORA" "TAMANHO"
    printf "%-4s %-40s %-20s %-10s\n" "---" "----------------------------------------" "--------------------" "----------"
    
    local i=1
    for backup in "${backups[@]}"; do
        local filename=$(basename "$backup")
        local filesize=$(du -h "$backup" | cut -f1)
        local datetime=""
        
        if parse_backup_name "$filename"; then
            datetime="${BACKUP_DAY}/${BACKUP_MONTH}/${BACKUP_YEAR} ${BACKUP_HOUR}:${BACKUP_MIN}:${BACKUP_SEC}"
        else
            datetime="N/A"
        fi
        
        # Truncar nome se muito longo
        if [[ ${#filename} -gt 38 ]]; then
            filename="${filename:0:35}..."
        fi
        
        printf "${GREEN}%-4s${NC} %-40s %-20s %-10s\n" "[$i]" "$filename" "$datetime" "$filesize"
        
        ((i++))
    done
    
    echo ""
    printf "${YELLOW}[0]${NC} Cancelar e sair\n"
    echo ""
    
    while true; do
        read -p "Selecione o backup para restaurar [0-${total}]: " choice
        
        if [[ "$choice" =~ ^[0-9]+$ ]]; then
            if [[ "$choice" -eq 0 ]]; then
                log_info "Operação cancelada pelo usuário."
                exit 0
            elif [[ "$choice" -ge 1 && "$choice" -le "$total" ]]; then
                selected=$((choice - 1))
                SELECTED_BACKUP="${backups[$selected]}"
                return 0
            fi
        fi
        
        log_warning "Opção inválida. Digite um número entre 0 e ${total}."
    done
}

# Função para mostrar informações do backup
show_backup_info() {
    local backup_file="$1"
    local temp_dir=$(mktemp -d)
    
    log_info "Extraindo informações do backup..."
    
    # Extrair apenas o arquivo de info
    unzip -q "$backup_file" -d "$temp_dir"
    
    local extracted_dir=$(ls -d "${temp_dir}"/*/ 2>/dev/null | head -1)
    
    if [[ -f "${extracted_dir}/backup_info.txt" ]]; then
        echo ""
        log_header "========================================"
        log_header "     INFORMAÇÕES DO BACKUP"
        log_header "========================================"
        cat "${extracted_dir}/backup_info.txt"
    fi
    
    # Guardar caminho para uso posterior
    TEMP_EXTRACT_DIR="$temp_dir"
    EXTRACTED_BACKUP_DIR="$extracted_dir"
}

# Função principal de restauração
restore_backup() {
    local backup_file="$1"
    local restore_dir="$2"
    
    echo ""
    log_header "========================================"
    log_header "     OPÇÕES DE RESTAURAÇÃO"
    log_header "========================================"
    echo ""
    
    echo "Selecione o que deseja restaurar:"
    echo ""
    printf "${GREEN}[1]${NC} Apenas arquivos do projeto\n"
    printf "${GREEN}[2]${NC} Apenas banco(s) de dados\n"
    printf "${GREEN}[3]${NC} Tudo (arquivos + banco de dados)\n"
    printf "${YELLOW}[0]${NC} Cancelar\n"
    echo ""
    
    read -p "Opção: " restore_option
    
    case $restore_option in
        0)
            log_info "Operação cancelada."
            rm -rf "$TEMP_EXTRACT_DIR"
            exit 0
            ;;
        1)
            restore_files "$restore_dir"
            ;;
        2)
            restore_databases
            ;;
        3)
            restore_files "$restore_dir"
            restore_databases
            ;;
        *)
            log_warning "Opção inválida."
            rm -rf "$TEMP_EXTRACT_DIR"
            exit 1
            ;;
    esac
}

# Função para restaurar arquivos
restore_files() {
    local restore_dir="$1"
    
    echo ""
    log_header ">> Restauração de Arquivos"
    
    if [[ ! -d "${EXTRACTED_BACKUP_DIR}/projeto" ]]; then
        log_error "Pasta 'projeto' não encontrada no backup."
        return 1
    fi
    
    echo ""
    log_warning "ATENÇÃO: Isso irá sobrescrever arquivos em:"
    log_info "${restore_dir}"
    echo ""
    read -p "Confirma a restauração dos arquivos? (s/N): " confirm
    
    if [[ ! "$confirm" =~ ^[Ss]$ ]]; then
        log_info "Restauração de arquivos cancelada."
        return 0
    fi
    
    log_info "Restaurando arquivos..."
    mkdir -p "$restore_dir"
    
    rsync -av --progress "${EXTRACTED_BACKUP_DIR}/projeto/" "$restore_dir/"
    
    log_success "Arquivos restaurados com sucesso!"
}

# Função para restaurar bancos de dados
restore_databases() {
    echo ""
    log_header ">> Restauração de Banco(s) de Dados"
    
    # Verificar se há arquivos SQL no backup
    local sql_files=()
    while IFS= read -r file; do
        if [[ -n "$file" ]]; then
            sql_files+=("$file")
        fi
    done < <(find "${EXTRACTED_BACKUP_DIR}/databases" -name "*.sql" 2>/dev/null)
    
    if [[ ${#sql_files[@]} -eq 0 ]]; then
        log_warning "Nenhum backup de banco de dados encontrado."
        return 0
    fi
    
    echo ""
    log_info "Bancos de dados encontrados no backup:"
    echo ""
    
    local i=1
    for sql_file in "${sql_files[@]}"; do
        local sql_name=$(basename "$sql_file" .sql)
        local sql_size=$(du -h "$sql_file" | cut -f1)
        printf "${GREEN}[%d]${NC} %s (%s)\n" "$i" "$sql_name" "$sql_size"
        ((i++))
    done
    
    echo ""
    
    # Verificar se tem .env.backup com conexões
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "Arquivo .env.backup não encontrado em ${PROJECT_DIR}"
        log_info "Configure o .env.backup com as conexões dos bancos de dados."
        return 1
    fi
    
    source "$ENV_FILE"
    
    if [[ -z "$DATABASES" ]]; then
        log_error "Nenhuma conexão de banco de dados configurada no .env.backup"
        return 1
    fi
    
    echo ""
    log_info "Conexões configuradas no .env.backup:"
    
    IFS=';' read -ra DB_CONNECTIONS <<< "$DATABASES"
    
    local conn_i=1
    for conn in "${DB_CONNECTIONS[@]}"; do
        conn=$(echo "$conn" | xargs)
        if parse_connection_string "$conn"; then
            printf "${CYAN}[%d]${NC} %s@%s:%s\n" "$conn_i" "$DB_NAME" "$DB_HOST" "$DB_PORT"
        fi
        ((conn_i++))
    done
    
    echo ""
    log_warning "ATENÇÃO: A restauração irá SOBRESCREVER os dados existentes nos bancos!"
    echo ""
    read -p "Deseja continuar com a restauração dos bancos? (s/N): " confirm_db
    
    if [[ ! "$confirm_db" =~ ^[Ss]$ ]]; then
        log_info "Restauração de bancos cancelada."
        return 0
    fi
    
    # Restaurar cada banco
    for sql_file in "${sql_files[@]}"; do
        local sql_basename=$(basename "$sql_file" .sql)
        # Extrair nome do banco do arquivo (formato: banco_timestamp.sql)
        local db_name_from_file="${sql_basename%_*}"
        # Remover possível timestamp adicional
        db_name_from_file="${db_name_from_file%_[0-9]*}"
        
        log_info "Procurando conexão para banco: ${db_name_from_file}"
        
        local found=false
        for conn in "${DB_CONNECTIONS[@]}"; do
            conn=$(echo "$conn" | xargs)
            if parse_connection_string "$conn"; then
                if [[ "$DB_NAME" == "$db_name_from_file" ]]; then
                    found=true
                    log_info "Restaurando ${DB_NAME}..."
                    
                    export PGPASSWORD="$DB_PASSWORD"
                    
                    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$sql_file" 2>/dev/null; then
                        log_success "${DB_NAME} restaurado com sucesso!"
                    else
                        log_error "Falha ao restaurar ${DB_NAME}"
                    fi
                    
                    unset PGPASSWORD
                    break
                fi
            fi
        done
        
        if [[ "$found" == false ]]; then
            log_warning "Conexão não encontrada para: ${db_name_from_file}"
            log_info "Configure a conexão no .env.backup para restaurar este banco."
        fi
    done
}

# ============================================
# INÍCIO DO SCRIPT
# ============================================

clear
echo ""
log_header "========================================"
log_header "     RESTAURAÇÃO DE BACKUP"
log_header "========================================"
echo ""

# Verificar se .env.backup existe
if [[ ! -f "$ENV_FILE" ]]; then
    log_error "Arquivo .env.backup não encontrado!"
    log_info "O arquivo .env.backup é necessário para identificar o diretório de backup."
    exit 1
fi

source "$ENV_FILE"

# Validar configurações
if [[ -z "$PROJECT_NAME" || -z "$BACKUP_DIR" ]]; then
    log_error "PROJECT_NAME e BACKUP_DIR devem estar definidos no .env.backup"
    exit 1
fi

log_info "Projeto: ${PROJECT_NAME}"
log_info "Diretório de backup: ${BACKUP_DIR}"

# Listar backups disponíveis
declare -a BACKUPS
if ! list_backups "$BACKUP_DIR" "$PROJECT_NAME" BACKUPS; then
    log_error "Nenhum backup encontrado em ${BACKUP_DIR}"
    log_info "Procurando por: ${PROJECT_NAME}_*.zip"
    exit 1
fi

log_success "Encontrados ${#BACKUPS[@]} backup(s)"

# Mostrar menu de seleção
SELECTED_BACKUP=""
show_backup_menu BACKUPS

if [[ -z "$SELECTED_BACKUP" ]]; then
    log_error "Nenhum backup selecionado."
    exit 1
fi

log_info "Backup selecionado: $(basename "$SELECTED_BACKUP")"

# Mostrar informações do backup
TEMP_EXTRACT_DIR=""
EXTRACTED_BACKUP_DIR=""
show_backup_info "$SELECTED_BACKUP"

# Perguntar diretório de restauração
echo ""
log_info "Diretório atual: ${PROJECT_DIR}"
read -p "Restaurar arquivos neste diretório? (S/n): " use_current_dir

if [[ "$use_current_dir" =~ ^[Nn]$ ]]; then
    read -p "Digite o diretório de destino: " RESTORE_DIR
    if [[ -z "$RESTORE_DIR" ]]; then
        RESTORE_DIR="$PROJECT_DIR"
    fi
else
    RESTORE_DIR="$PROJECT_DIR"
fi

# Executar restauração
restore_backup "$SELECTED_BACKUP" "$RESTORE_DIR"

# Limpeza final
log_info "Limpando arquivos temporários..."
rm -rf "$TEMP_EXTRACT_DIR"

echo ""
log_header "========================================"
log_header "     RESTAURAÇÃO CONCLUÍDA!"
log_header "========================================"
echo ""

exit 0
