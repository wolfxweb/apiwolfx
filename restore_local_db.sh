#!/bin/bash

# Script para restaurar backup do banco de dados local (comercial)
# Uso: ./restore_local_db.sh <arquivo_backup.sql.gz>

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar se o arquivo foi fornecido
if [ -z "$1" ]; then
    echo -e "${RED}❌ Erro: Arquivo de backup não fornecido!${NC}"
    echo -e "${YELLOW}💡 Uso: ./restore_local_db.sh <arquivo_backup.sql.gz>${NC}"
    echo ""
    echo -e "${YELLOW}📁 Backups disponíveis:${NC}"
    if [ -d "./backups" ]; then
        ls -lh ./backups/*.sql.gz 2>/dev/null | awk '{print "   " $9 " (" $5 ")"}'
    else
        echo -e "   ${YELLOW}Nenhum backup encontrado${NC}"
    fi
    exit 1
fi

BACKUP_FILE="$1"

# Verificar se o arquivo existe
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}❌ Erro: Arquivo não encontrado: ${BACKUP_FILE}${NC}"
    exit 1
fi

# Configurações do banco de dados local
DB_HOST="pgadmin.wolfx.com.br"
DB_PORT="5432"
DB_NAME="comercial"
DB_USER="postgres"
DB_PASSWORD="97452c28f62db6d77be083917b698660"

echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}🔄 Restauração do Banco de Dados Local${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo -e "📋 Configurações:"
echo -e "   Host: ${YELLOW}${DB_HOST}${NC}"
echo -e "   Port: ${YELLOW}${DB_PORT}${NC}"
echo -e "   Database: ${YELLOW}${DB_NAME}${NC}"
echo -e "   User: ${YELLOW}${DB_USER}${NC}"
echo -e "   Backup: ${YELLOW}${BACKUP_FILE}${NC}"
echo ""

# Verificar se psql está instalado
if ! command -v psql &> /dev/null; then
    echo -e "${RED}❌ Erro: psql não está instalado!${NC}"
    echo -e "${YELLOW}💡 Instale o PostgreSQL client:${NC}"
    echo -e "   macOS: ${YELLOW}brew install postgresql${NC}"
    echo -e "   Linux: ${YELLOW}sudo apt-get install postgresql-client${NC}"
    exit 1
fi

# Confirmar ação
echo -e "${RED}⚠️  ATENÇÃO: Esta operação irá ${NC}${RED}SUBSTITUIR${NC}${RED} todos os dados do banco!${NC}"
echo -e "${YELLOW}Deseja continuar? (digite 'sim' para confirmar):${NC} "
read -r CONFIRM

if [ "$CONFIRM" != "sim" ]; then
    echo -e "${YELLOW}❌ Operação cancelada${NC}"
    exit 0
fi

# Exportar variável de ambiente para senha
export PGPASSWORD="$DB_PASSWORD"

# Descomprimir se necessário
TEMP_FILE=""
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo -e "${GREEN}🗜️  Descomprimindo backup...${NC}"
    TEMP_FILE="${BACKUP_FILE%.gz}"
    if ! gunzip -c "$BACKUP_FILE" > "$TEMP_FILE"; then
        echo -e "${RED}❌ Erro ao descomprimir backup!${NC}"
        unset PGPASSWORD
        exit 1
    fi
    BACKUP_FILE="$TEMP_FILE"
fi

echo -e "${GREEN}🔄 Restaurando backup...${NC}"

# Restaurar backup
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE" 2>&1; then
    echo -e "${GREEN}✅ Backup restaurado com sucesso!${NC}"
    
    # Limpar arquivo temporário se foi criado
    if [ -n "$TEMP_FILE" ] && [ -f "$TEMP_FILE" ]; then
        rm "$TEMP_FILE"
    fi
    
    # Limpar variável de ambiente
    unset PGPASSWORD
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Restauração concluída com sucesso!${NC}"
    echo -e "${GREEN}════════════════════════════════════════${NC}"
    echo ""
    
    exit 0
else
    echo -e "${RED}❌ Erro ao restaurar backup!${NC}"
    
    # Limpar arquivo temporário se foi criado
    if [ -n "$TEMP_FILE" ] && [ -f "$TEMP_FILE" ]; then
        rm "$TEMP_FILE"
    fi
    
    unset PGPASSWORD
    exit 1
fi

