#!/bin/bash

# Script de backup do banco de dados local (comercial)
# Uso: ./backup_local_db.sh

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configurações do banco de dados local
DB_HOST="pgadmin.wolfx.com.br"
DB_PORT="5432"
DB_NAME="comercial"
DB_USER="postgres"
DB_PASSWORD="97452c28f62db6d77be083917b698660"

# Diretório para salvar backups
BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/comercial_backup_${TIMESTAMP}.sql"
BACKUP_FILE_COMPRESSED="${BACKUP_FILE}.gz"

# Criar diretório de backups se não existir
mkdir -p "$BACKUP_DIR"

echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}🗄️  Backup do Banco de Dados Local${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo -e "📋 Configurações:"
echo -e "   Host: ${YELLOW}${DB_HOST}${NC}"
echo -e "   Port: ${YELLOW}${DB_PORT}${NC}"
echo -e "   Database: ${YELLOW}${DB_NAME}${NC}"
echo -e "   User: ${YELLOW}${DB_USER}${NC}"
echo -e "   Backup: ${YELLOW}${BACKUP_FILE}${NC}"
echo ""

# Verificar se pg_dump está instalado
if ! command -v pg_dump &> /dev/null; then
    echo -e "${RED}❌ Erro: pg_dump não está instalado!${NC}"
    echo -e "${YELLOW}💡 Instale o PostgreSQL client:${NC}"
    echo -e "   macOS: ${YELLOW}brew install postgresql${NC}"
    echo -e "   Linux: ${YELLOW}sudo apt-get install postgresql-client${NC}"
    exit 1
fi

# Exportar variável de ambiente para senha
export PGPASSWORD="$DB_PASSWORD"

echo -e "${GREEN}🔄 Iniciando backup...${NC}"

# Fazer backup usando pg_dump
if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --verbose \
    --clean \
    --if-exists \
    --create \
    --format=plain \
    --file="$BACKUP_FILE" 2>&1; then
    
    echo -e "${GREEN}✅ Backup criado com sucesso!${NC}"
    
    # Comprimir o backup
    echo -e "${GREEN}🗜️  Comprimindo backup...${NC}"
    if gzip "$BACKUP_FILE"; then
        BACKUP_SIZE=$(du -h "$BACKUP_FILE_COMPRESSED" | cut -f1)
        echo -e "${GREEN}✅ Backup comprimido: ${BACKUP_FILE_COMPRESSED}${NC}"
        echo -e "${GREEN}📦 Tamanho: ${BACKUP_SIZE}${NC}"
    else
        echo -e "${YELLOW}⚠️  Aviso: Não foi possível comprimir o backup${NC}"
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        echo -e "${GREEN}📦 Tamanho: ${BACKUP_SIZE}${NC}"
    fi
    
    # Limpar variável de ambiente
    unset PGPASSWORD
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Backup concluído com sucesso!${NC}"
    echo -e "${GREEN}════════════════════════════════════════${NC}"
    echo ""
    echo -e "📁 Arquivo: ${YELLOW}${BACKUP_FILE_COMPRESSED}${NC}"
    echo ""
    echo -e "${YELLOW}💡 Para restaurar o backup:${NC}"
    echo -e "   ${YELLOW}gunzip ${BACKUP_FILE_COMPRESSED}${NC}"
    echo -e "   ${YELLOW}psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} < ${BACKUP_FILE}${NC}"
    echo ""
    
    exit 0
else
    echo -e "${RED}❌ Erro ao criar backup!${NC}"
    unset PGPASSWORD
    exit 1
fi

