#!/bin/bash

# Script para configurar permissões no banco selvez
# Este script precisa ser executado por um usuário com privilégios de superusuário

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configurações do banco de produção (selvez)
DB_HOST="207.231.108.38"
DB_PORT="5432"
DB_NAME="selvez"
DB_USER="api_user"
DB_PASSWORD="@Wolfx20202025"

echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}🔧 Configuração de Permissões - SELVEZ${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}⚠️  Este script precisa ser executado por um usuário com privilégios de superusuário${NC}"
echo -e "${YELLOW}💡 Se você não tem acesso de superusuário, peça ao DBA para executar os comandos abaixo${NC}"
echo ""

# Tentar conceder permissões
echo -e "${GREEN}🔧 Tentando conceder permissões...${NC}"

export PGPASSWORD="$DB_PASSWORD"

# Comandos SQL para conceder permissões
SQL_COMMANDS="
-- Conceder permissões no schema public
GRANT ALL ON SCHEMA public TO api_user;
GRANT CREATE ON SCHEMA public TO api_user;
GRANT USAGE ON SCHEMA public TO api_user;

-- Conceder permissões em tabelas existentes
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO api_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO api_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO api_user;

-- Conceder permissões em objetos futuros
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO api_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO api_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO api_user;

-- Tornar api_user o dono do schema public (se possível)
ALTER SCHEMA public OWNER TO api_user;

-- Garantir que api_user pode criar extensões (se necessário)
ALTER USER api_user CREATEDB;
"

if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$SQL_COMMANDS" 2>&1; then
    echo -e "${GREEN}✅ Permissões concedidas com sucesso!${NC}"
else
    echo -e "${RED}❌ Erro ao conceder permissões${NC}"
    echo -e "${YELLOW}💡 Você precisa de privilégios de superusuário ou pedir ao DBA para executar:${NC}"
    echo ""
    echo -e "${YELLOW}Comandos SQL para o DBA executar:${NC}"
    echo "---"
    echo "$SQL_COMMANDS"
    echo "---"
    echo ""
    echo -e "${YELLOW}Ou conecte como superusuário e execute:${NC}"
    echo -e "${GREEN}psql -h $DB_HOST -p $DB_PORT -U postgres -d $DB_NAME${NC}"
    echo ""
    exit 1
fi

unset PGPASSWORD

echo ""
echo -e "${GREEN}✅ Configuração concluída!${NC}"
echo -e "${YELLOW}💡 Agora você pode restaurar o backup:${NC}"
echo -e "${GREEN}   ./restore_to_selvez.sh backups/comercial_backup_20251204_183730.sql.gz${NC}"

