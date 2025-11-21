#!/bin/bash

# Script de Deploy para VPS em Produção
# Atualiza código do GitHub e faz deploy no Docker Swarm

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
STACK_NAME="celx_ml_api"

# Carregar variáveis de ambiente do portainer.env se existir
if [ -f "portainer.env" ]; then
    echo -e "${GREEN}✅ Carregando variáveis de ambiente de portainer.env${NC}"
    set -a
    source portainer.env
    set +a
else
    echo -e "${YELLOW}⚠️  Arquivo portainer.env não encontrado - usando variáveis do sistema${NC}"
fi

echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${GREEN}🚀 Deploy em Produção - Iniciando...${NC}"
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

# 4. Fazer deploy no Docker Swarm
echo -e "${YELLOW}🔨 Fazendo deploy no Docker Swarm...${NC}"
echo -e "${BLUE}⏳ Isso pode levar alguns minutos...${NC}"

# O docker stack deploy atualiza o stack se existir, ou cria se não existir
docker stack deploy -c "$COMPOSE_FILE" "$STACK_NAME"

# 4.1. Forçar atualização do serviço sem cache (força recriação dos containers)
echo -e "${YELLOW}🔄 Forçando atualização do serviço (sem cache)...${NC}"
docker service update --force "${STACK_NAME}_api" || true

# 5. Aguardar containers iniciarem
echo -e "${YELLOW}⏳ Aguardando containers iniciarem...${NC}"
sleep 15

# 6. Verificar status dos containers
echo -e "${YELLOW}📊 Status dos containers:${NC}"
docker service ps "${STACK_NAME}_api" || true

# 7. Mostrar logs recentes
echo -e "${YELLOW}📋 Últimos logs do container API:${NC}"
docker service logs "${STACK_NAME}_api" --tail=30 || true

# 8. Verificar se o serviço está acessível internamente
echo -e "${YELLOW}🔍 Verificando se o serviço está respondendo...${NC}"
SERVICE_CONTAINER=$(docker ps -q --filter "name=${STACK_NAME}_api" | head -1)
if [ -n "$SERVICE_CONTAINER" ]; then
    if docker exec "$SERVICE_CONTAINER" curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null | grep -q "200\|404\|301\|302"; then
        echo -e "${GREEN}✅ Serviço está respondendo na porta 8000${NC}"
    else
        echo -e "${YELLOW}⚠️  Serviço pode não estar totalmente iniciado ainda${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Container do serviço não encontrado ainda${NC}"
fi

# 9. Verificar se o Traefik detectou o serviço
echo -e "${YELLOW}🔍 Verificando se o Traefik detectou o serviço...${NC}"
TRAEFIK_CONTAINER=$(docker ps -q --filter "name=traefik" | head -1)
if [ -n "$TRAEFIK_CONTAINER" ]; then
    echo -e "${GREEN}✅ Traefik encontrado${NC}"
    echo -e "${YELLOW}💡 Reiniciando Traefik para forçar detecção do serviço...${NC}"
    docker service update --force traefik_traefik 2>/dev/null || docker service update --force traefik 2>/dev/null || echo -e "${YELLOW}⚠️  Não foi possível reiniciar o Traefik automaticamente${NC}"
    echo -e "${BLUE}⏳ Aguardando Traefik reiniciar...${NC}"
    sleep 10
else
    echo -e "${YELLOW}⚠️  Traefik não encontrado - verifique se está rodando${NC}"
fi

# 10. Verificar rede
echo -e "${YELLOW}🔍 Verificando rede 'server'...${NC}"
if docker network ls | grep -q "server"; then
    echo -e "${GREEN}✅ Rede 'server' existe${NC}"
    # Verificar se o serviço está na rede
    SERVICE_NETWORKS=$(docker service inspect "${STACK_NAME}_api" --format '{{range .Endpoint.Spec.Networks}}{{.Target}}{{end}}' 2>/dev/null || echo "")
    if echo "$SERVICE_NETWORKS" | grep -q "server"; then
        echo -e "${GREEN}✅ Serviço está na rede 'server'${NC}"
    else
        echo -e "${RED}❌ Serviço NÃO está na rede 'server'${NC}"
        echo -e "${YELLOW}💡 Isso pode causar 404. Verifique o docker-compose.prod.yml${NC}"
    fi
else
    echo -e "${RED}❌ Rede 'server' não encontrada!${NC}"
    echo -e "${YELLOW}💡 Criando rede 'server'...${NC}"
    docker network create --driver overlay --attachable server || true
fi

echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Deploy concluído!${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${YELLOW}💡 Próximos passos:${NC}"
echo -e "   1. Verifique os logs: docker service logs ${STACK_NAME}_api -f"
echo -e "   2. Teste a aplicação: curl http://localhost:8000"
echo -e "   3. Monitore os serviços: docker service ps ${STACK_NAME}_api"
echo -e "   4. Se ainda der 404, reinicie o Traefik: docker service update --force traefik_traefik"
echo -e "   5. Verifique logs do Traefik: docker service logs traefik_traefik --tail=50 | grep celx"
echo -e "${BLUE}════════════════════════════════════════${NC}"
