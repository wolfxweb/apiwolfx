#!/bin/bash

# Script de Deploy para VPS em Produção
# Atualiza código do GitHub e reconstrói containers sem cache

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Diretório do projeto
PROJECT_DIR="/root/apiwolfx"
COMPOSE_FILE="docker-compose.prod.yml"

# Detectar qual comando docker compose está disponível
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    echo -e "${RED}❌ Erro: docker-compose ou docker compose não encontrado${NC}"
    echo -e "${YELLOW}💡 Instale docker-compose ou atualize o Docker para versão com compose integrado${NC}"
    exit 1
fi

echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${GREEN}🚀 Deploy em Produção - Iniciando...${NC}"
echo -e "${GREEN}✅ Usando comando: $DOCKER_COMPOSE${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"

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
echo -e "${YELLOW}📋 Verificando atualizações no GitHub...${NC}"
git fetch origin

LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})
BASE=$(git merge-base @ @{u})

if [ "$LOCAL" = "$REMOTE" ]; then
    echo -e "${GREEN}✅ Código já está atualizado (sem novas alterações)${NC}"
    read -p "Deseja continuar mesmo assim? (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo -e "${YELLOW}⏸️  Deploy cancelado pelo usuário${NC}"
        exit 0
    fi
else
    echo -e "${YELLOW}📥 Atualizando código do GitHub...${NC}"
    git pull origin main
    echo -e "${GREEN}✅ Código atualizado${NC}"
fi

# 3. Mostrar último commit
echo -e "${YELLOW}📝 Último commit:${NC}"
git log -1 --oneline --decorate

# 4. Parar containers atuais
echo -e "${YELLOW}🛑 Parando containers...${NC}"
$DOCKER_COMPOSE -f "$COMPOSE_FILE" down || true

# 5. Limpar imagens antigas (opcional, para economizar espaço)
echo -e "${YELLOW}🧹 Limpando imagens antigas...${NC}"
docker system prune -f || true

# 6. Reconstruir containers SEM CACHE
echo -e "${YELLOW}🔨 Reconstruindo containers (sem cache)...${NC}"
echo -e "${BLUE}⏳ Isso pode levar alguns minutos...${NC}"
$DOCKER_COMPOSE -f "$COMPOSE_FILE" build --no-cache --pull

# 7. Subir containers
echo -e "${YELLOW}⬆️  Subindo containers...${NC}"
$DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d

# 8. Aguardar containers iniciarem
echo -e "${YELLOW}⏳ Aguardando containers iniciarem...${NC}"
sleep 5

# 9. Verificar status dos containers
echo -e "${YELLOW}📊 Status dos containers:${NC}"
$DOCKER_COMPOSE -f "$COMPOSE_FILE" ps

# 10. Verificar saúde dos containers
echo -e "${YELLOW}🏥 Verificando saúde dos containers...${NC}"
CONTAINERS=$($DOCKER_COMPOSE -f "$COMPOSE_FILE" ps -q)
for container in $CONTAINERS; do
    if [ -n "$container" ]; then
        STATUS=$(docker inspect --format='{{.State.Status}}' "$container")
        if [ "$STATUS" = "running" ]; then
            echo -e "${GREEN}✅ Container $container está rodando${NC}"
        else
            echo -e "${RED}❌ Container $container está com status: $STATUS${NC}"
        fi
    fi
done

# 11. Mostrar logs recentes
echo -e "${YELLOW}📋 Últimos logs do container API:${NC}"
$DOCKER_COMPOSE -f "$COMPOSE_FILE" logs --tail=30 api

echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Deploy concluído com sucesso!${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${YELLOW}💡 Próximos passos:${NC}"
echo -e "   1. Verifique os logs: $DOCKER_COMPOSE -f $COMPOSE_FILE logs -f api"
echo -e "   2. Teste a aplicação: curl http://localhost:8000"
echo -e "   3. Monitore os containers: $DOCKER_COMPOSE -f $COMPOSE_FILE ps"
echo -e "${BLUE}════════════════════════════════════════${NC}"

