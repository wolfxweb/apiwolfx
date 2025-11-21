#!/bin/bash

# Script de Deploy para VPS em Produção
# Atualiza código do GitHub e reconstrói containers sem cache

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Diretório do projeto
PROJECT_DIR="/root/apiwolfx"
COMPOSE_FILE="docker-compose.prod.yml"

echo -e "${GREEN}🚀 Iniciando deploy em produção...${NC}"

# Verificar se está no diretório correto
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}❌ Erro: Arquivo $COMPOSE_FILE não encontrado${NC}"
    echo -e "${YELLOW}💡 Certifique-se de estar no diretório do projeto${NC}"
    exit 1
fi

# 1. Entrar no diretório do projeto
cd "$PROJECT_DIR" || exit 1
echo -e "${GREEN}✅ Diretório: $(pwd)${NC}"

# 2. Verificar status do Git
echo -e "${YELLOW}📋 Verificando status do Git...${NC}"
git fetch origin
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})

if [ "$LOCAL" = "$REMOTE" ]; then
    echo -e "${GREEN}✅ Código já está atualizado${NC}"
else
    echo -e "${YELLOW}📥 Atualizando código do GitHub...${NC}"
    git pull origin main
    echo -e "${GREEN}✅ Código atualizado${NC}"
fi

# 3. Mostrar último commit
echo -e "${YELLOW}📝 Último commit:${NC}"
git log -1 --oneline

# 4. Parar containers atuais
echo -e "${YELLOW}🛑 Parando containers...${NC}"
docker-compose -f "$COMPOSE_FILE" down

# 5. Reconstruir containers SEM CACHE
echo -e "${YELLOW}🔨 Reconstruindo containers (sem cache)...${NC}"
docker-compose -f "$COMPOSE_FILE" build --no-cache

# 6. Subir containers
echo -e "${YELLOW}⬆️  Subindo containers...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d

# 7. Verificar status dos containers
echo -e "${YELLOW}📊 Verificando status dos containers...${NC}"
sleep 3
docker-compose -f "$COMPOSE_FILE" ps

# 8. Mostrar logs recentes
echo -e "${YELLOW}📋 Últimos logs do container API:${NC}"
docker-compose -f "$COMPOSE_FILE" logs --tail=20 api

echo -e "${GREEN}✅ Deploy concluído com sucesso!${NC}"
echo -e "${GREEN}🌐 Verifique se a aplicação está funcionando corretamente${NC}"

