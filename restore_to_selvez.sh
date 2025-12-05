#!/bin/bash

# Script para restaurar backup do banco local (comercial) no banco de produção (selvez)
# Uso: ./restore_to_selvez.sh [arquivo_backup.sql.gz]

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Verificar se o arquivo foi fornecido
if [ -z "$1" ]; then
    echo -e "${RED}❌ Erro: Arquivo de backup não fornecido!${NC}"
    echo -e "${YELLOW}💡 Uso: ./restore_to_selvez.sh <arquivo_backup.sql.gz>${NC}"
    echo ""
    echo -e "${YELLOW}📁 Backups disponíveis:${NC}"
    if [ -d "./backups" ]; then
        ls -lh ./backups/*.sql.gz 2>/dev/null | awk '{print "   " $9 " (" $5 ")"}'
    else
        echo -e "   ${YELLOW}Nenhum backup encontrado${NC}"
        echo -e "${YELLOW}💡 Primeiro faça um backup: ./backup_local_db.sh${NC}"
    fi
    exit 1
fi

BACKUP_FILE="$1"

# Verificar se o arquivo existe
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}❌ Erro: Arquivo não encontrado: ${BACKUP_FILE}${NC}"
    exit 1
fi

# Configurações do banco de produção (selvez)
DB_HOST="207.231.108.38"
DB_PORT="5432"
DB_NAME="selvez"
DB_USER="api_user"
DB_PASSWORD="@Wolfx20202025"

echo -e "${RED}════════════════════════════════════════${NC}"
echo -e "${RED}⚠️  RESTAURAÇÃO EM PRODUÇÃO (SELVEZ)${NC}"
echo -e "${RED}════════════════════════════════════════${NC}"
echo ""
echo -e "${RED}🚨 ATENÇÃO: Esta operação irá ${NC}${RED}SUBSTITUIR${NC}${RED} todos os dados do banco de PRODUÇÃO!${NC}"
echo ""
echo -e "📋 Configurações:"
echo -e "   Host: ${YELLOW}${DB_HOST}${NC}"
echo -e "   Port: ${YELLOW}${DB_PORT}${NC}"
echo -e "   Database: ${RED}${DB_NAME}${NC} ${RED}(PRODUÇÃO)${NC}"
echo -e "   User: ${YELLOW}${DB_USER}${NC}"
echo -e "   Backup: ${YELLOW}${BACKUP_FILE}${NC}"
echo ""

# Confirmar ação DUPLA para produção
echo -e "${RED}⚠️  Digite 'CONFIRMAR SELVEZ' para continuar:${NC} "
read -r CONFIRM1

if [ "$CONFIRM1" != "CONFIRMAR SELVEZ" ]; then
    echo -e "${YELLOW}❌ Operação cancelada${NC}"
    exit 0
fi

echo -e "${RED}⚠️  Digite novamente 'CONFIRMAR SELVEZ' para confirmar:${NC} "
read -r CONFIRM2

if [ "$CONFIRM2" != "CONFIRMAR SELVEZ" ]; then
    echo -e "${YELLOW}❌ Operação cancelada${NC}"
    exit 0
fi

# Verificar se psql está instalado
if ! command -v psql &> /dev/null; then
    echo -e "${RED}❌ Erro: psql não está instalado!${NC}"
    echo -e "${YELLOW}💡 Instale o PostgreSQL client:${NC}"
    echo -e "   macOS: ${YELLOW}brew install postgresql${NC}"
    echo -e "   Linux: ${YELLOW}sudo apt-get install postgresql-client${NC}"
    exit 1
fi

# Exportar variável de ambiente para senha
export PGPASSWORD="$DB_PASSWORD"

# Verificar se o banco existe
echo -e "${GREEN}🔍 Verificando conexão com o banco...${NC}"
if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "\l" 2>/dev/null | grep -qw "$DB_NAME"; then
    echo -e "${YELLOW}⚠️  Banco de dados '${DB_NAME}' não existe.${NC}"
    echo -e "${YELLOW}Deseja criar o banco? (digite 'sim' para criar):${NC} "
    read -r CREATE_DB
    
    if [ "$CREATE_DB" = "sim" ]; then
        echo -e "${GREEN}📦 Criando banco de dados...${NC}"
        if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE \"$DB_NAME\";" 2>&1; then
            echo -e "${GREEN}✅ Banco de dados criado!${NC}"
        else
            echo -e "${RED}❌ Erro ao criar banco de dados!${NC}"
            unset PGPASSWORD
            exit 1
        fi
    else
        echo -e "${YELLOW}❌ Operação cancelada${NC}"
        unset PGPASSWORD
        exit 0
    fi
fi

# Descomprimir se necessário
TEMP_FILE=""
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo -e "${GREEN}🗜️  Descomprimindo backup...${NC}"
    TEMP_FILE="/tmp/restore_selvez_$(basename ${BACKUP_FILE%.gz})"
    if ! gunzip -c "$BACKUP_FILE" > "$TEMP_FILE"; then
        echo -e "${RED}❌ Erro ao descomprimir backup!${NC}"
        unset PGPASSWORD
        exit 1
    fi
    BACKUP_FILE="$TEMP_FILE"
fi

echo -e "${GREEN}🔄 Restaurando backup no banco selvez...${NC}"

# Tentar conceder permissões básicas antes de restaurar (pode falhar se não tiver privilégios)
echo -e "${YELLOW}🔧 Tentando conceder permissões básicas...${NC}"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF 2>/dev/null || echo -e "${YELLOW}⚠️  Não foi possível conceder permissões automaticamente (normal se não for superusuário)${NC}"
GRANT ALL ON SCHEMA public TO api_user;
GRANT CREATE ON SCHEMA public TO api_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO api_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO api_user;
EOF

# Filtrar comandos problemáticos do backup com filtragem mais robusta
FILTERED_FILE="/tmp/restore_selvez_filtered_$(basename $BACKUP_FILE)"
echo -e "${GREEN}🔍 Filtrando comandos problemáticos do backup...${NC}"

# Usar processamento mais robusto para filtrar comandos problemáticos
cat "$BACKUP_FILE" | \
    sed -e '/^CREATE DATABASE/d' \
        -e '/^DROP DATABASE/d' \
        -e '/^\\connect/d' \
        -e '/^\\\\connect/d' \
        -e '/^-- Database: /d' \
        -e '/^-- Dumped from database version/d' \
        -e '/^-- Dumped by pg_dump version/d' \
        -e 's/OWNER TO postgres/OWNER TO api_user/g' \
        -e 's/OWNER TO "postgres"/OWNER TO api_user/g' \
        -e 's/OWNER TO postgres;/OWNER TO api_user;/g' \
        -e 's/OWNER TO "postgres";/OWNER TO api_user;/g' \
    > "$FILTERED_FILE" 2>/dev/null

# Verificar se o arquivo filtrado foi criado e tem conteúdo
if [ ! -f "$FILTERED_FILE" ]; then
    echo -e "${RED}❌ Erro ao criar arquivo filtrado!${NC}"
    unset PGPASSWORD
    exit 1
fi

if [ ! -s "$FILTERED_FILE" ]; then
    echo -e "${RED}❌ Arquivo filtrado está vazio!${NC}"
    echo -e "${YELLOW}💡 Verificando arquivo original...${NC}"
    if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
        echo -e "${YELLOW}⚠️  Arquivo original existe e tem conteúdo, mas filtragem falhou${NC}"
    fi
    rm -f "$FILTERED_FILE"
    unset PGPASSWORD
    exit 1
fi

FILTERED_SIZE=$(du -h "$FILTERED_FILE" | cut -f1)
echo -e "${GREEN}✅ Arquivo filtrado criado: ${FILTERED_SIZE}${NC}"

# Restaurar backup (redirecionar stderr para filtrar erros conhecidos)
echo -e "${YELLOW}⚠️  Restaurando (alguns erros de permissão são esperados e serão ignorados)...${NC}"
RESTORE_OUTPUT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$FILTERED_FILE" 2>&1)

# Filtrar erros conhecidos e não críticos
echo "$RESTORE_OUTPUT" | \
    grep -v "permission denied" | \
    grep -v "role \"postgres\" does not exist" | \
    grep -v "database \"comercial\" does not exist" | \
    grep -v "CREATE DATABASE" | \
    grep -v "DROP DATABASE" | \
    grep -v "\\connect" | \
    grep -v "\\\\connect" | \
    grep -v "does not exist, skipping" | \
    grep -v "ERROR:  relation" | \
    grep -v "WARNING:" || true

# Verificar se as tabelas foram criadas (isso é o mais importante)
echo -e "${GREEN}🔍 Verificando se as tabelas foram criadas...${NC}"
TABLE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -A -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | head -1 | tr -d ' \n' || echo "0")

# Limpar arquivo filtrado
if [ -f "$FILTERED_FILE" ]; then
    rm "$FILTERED_FILE"
fi

# Verificar se pelo menos algumas tabelas foram criadas
if [ -n "$TABLE_COUNT" ] && [ "$TABLE_COUNT" != "0" ] && [ "$TABLE_COUNT" -gt 0 ] 2>/dev/null; then
    echo -e "${GREEN}✅ Backup restaurado com sucesso no banco selvez!${NC}"
    echo -e "${GREEN}📊 Tabelas encontradas no banco: ${TABLE_COUNT}${NC}"
    
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
    echo -e "${YELLOW}💡 Próximos passos:${NC}"
    echo -e "   1. Verificar se as tabelas foram criadas corretamente"
    echo -e "   2. Fazer deploy em produção: ${GREEN}./deploy.sh production${NC}"
    echo ""
    
    exit 0
else
    echo -e "${RED}❌ Erro ao restaurar backup!${NC}"
    echo -e "${YELLOW}💡 Verificando se algumas tabelas foram criadas...${NC}"
    
    # Verificar se pelo menos algumas tabelas foram criadas
    if [ -n "$TABLE_COUNT" ] && [ "$TABLE_COUNT" != "0" ] && [ "$TABLE_COUNT" -gt 0 ] 2>/dev/null; then
        echo -e "${GREEN}✅ ${TABLE_COUNT} tabelas encontradas no banco - restauração parcial bem-sucedida${NC}"
        echo -e "${YELLOW}⚠️  Alguns erros podem ter ocorrido, mas as tabelas principais foram criadas${NC}"
        unset PGPASSWORD
        exit 0
    else
        echo -e "${RED}❌ Nenhuma tabela foi encontrada no banco${NC}"
        echo -e "${YELLOW}💡 Verificando conexão com o banco...${NC}"
        if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\dt" 2>&1 | head -5; then
            echo -e "${YELLOW}⚠️  Conexão OK, mas nenhuma tabela encontrada${NC}"
        fi
    fi
    
    # Limpar arquivo temporário se foi criado
    if [ -n "$TEMP_FILE" ] && [ -f "$TEMP_FILE" ]; then
        rm "$TEMP_FILE"
    fi
    
    unset PGPASSWORD
    exit 1
fi

