#!/bin/bash

# Script de Deploy em Produção - celx.com.br
# Uso: ./deploy-production.sh

set -e  # Parar em caso de erro

echo "🚀 Deploy em Produção - celx.com.br"
echo "===================================="
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar se está executando como root
if [ "$EUID" -ne 0 ]; then 
   echo -e "${RED}❌ Este script deve ser executado como root${NC}"
   exit 1
fi

# Verificar se o docker-compose.prod.yml existe localmente ou baixar do repositório
if [ -f "docker-compose.prod.yml" ]; then
    echo "📁 Arquivo docker-compose.prod.yml encontrado localmente, copiando..."
    cp docker-compose.prod.yml /root/docker-compose.prod.yml
elif [ -f "/root/docker-compose.prod.yml" ]; then
    echo "📁 Usando arquivo existente em /root/docker-compose.prod.yml"
else
    echo "📥 Baixando docker-compose.prod.yml do repositório..."
    
    # Tentar baixar usando git clone (com token se disponível)
    if [ -n "$GITHUB_TOKEN" ]; then
        echo "🔑 Usando token do GitHub..."
        rm -rf /tmp/apiwolfx-clone
        git clone https://${GITHUB_TOKEN}@github.com/wolfxweb/apiwolfx.git /tmp/apiwolfx-clone
        cp /tmp/apiwolfx-clone/docker-compose.prod.yml /root/docker-compose.prod.yml
        rm -rf /tmp/apiwolfx-clone
    else
        echo "⚠️  GITHUB_TOKEN não definido, tentando repositório público..."
        curl -s https://raw.githubusercontent.com/wolfxweb/apiwolfx/main/docker-compose.prod.yml \
            -o /root/docker-compose.prod.yml
        
        if [ $? -ne 0 ] || [ ! -s /root/docker-compose.prod.yml ]; then
            echo -e "${RED}❌ Erro ao baixar arquivo. Verifique se o repositório é público ou configure GITHUB_TOKEN${NC}"
            exit 1
        fi
    fi
fi

# Verificar se o arquivo existe e não está vazio
if [ ! -f "/root/docker-compose.prod.yml" ] || [ ! -s "/root/docker-compose.prod.yml" ]; then
    echo -e "${RED}❌ Arquivo docker-compose.prod.yml não encontrado ou vazio${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Arquivo docker-compose.prod.yml pronto${NC}"
echo ""

echo "🔍 Verificando arquivo..."
head -5 /root/docker-compose.prod.yml
echo ""

# Atualizar o stack
echo "📦 Atualizando stack Docker Swarm..."
docker stack deploy -c /root/docker-compose.prod.yml celx_ml_api

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Erro ao atualizar stack${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Stack atualizado${NC}"
echo ""

# Aguardar serviço iniciar
echo "⏳ Aguardando serviço iniciar (15 segundos)..."
sleep 15

# Verificar status
echo ""
echo "📊 Status do serviço:"
docker service ps celx_ml_api_api

echo ""
echo "📝 Últimos logs do serviço:"
docker service logs celx_ml_api_api --tail 20 | tail -10

echo ""
echo "🔍 Verificando se uvicorn iniciou:"
docker service logs celx_ml_api_api --tail 30 | grep -i "uvicorn running" || echo -e "${YELLOW}⚠️  Uvicorn ainda não iniciou (aguarde alguns segundos)${NC}"

echo ""
echo "🔄 Reiniciando Traefik para detectar mudanças..."
docker service update --force traefik_traefik > /dev/null 2>&1

echo "⏳ Aguardando Traefik reiniciar (10 segundos)..."
sleep 10

echo ""
echo "🧪 Testando acesso:"
echo "HTTP (deve redirecionar):"
curl -I http://celx.com.br/ 2>&1 | head -3 || echo -e "${YELLOW}⚠️  Não foi possível testar HTTP${NC}"

echo ""
echo "HTTPS:"
curl -k -I https://celx.com.br/ 2>&1 | head -3 || echo -e "${YELLOW}⚠️  Não foi possível testar HTTPS${NC}"

echo ""
echo -e "${GREEN}✅ Deploy concluído!${NC}"
echo ""
echo "📋 Comandos úteis:"
echo "  - Ver logs: docker service logs -f celx_ml_api_api"
echo "  - Ver status: docker service ps celx_ml_api_api"
echo "  - Ver logs do Traefik: docker service logs -f traefik_traefik"
echo ""
echo "🌐 Acesse: https://celx.com.br"
echo ""
