#!/bin/bash

# Script de Diagnóstico para Erro 404 em Produção

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

STACK_NAME="celx_ml_api"
SERVICE_NAME="${STACK_NAME}_api"

echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${GREEN}🔍 Diagnóstico de Erro 404${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"

# 1. Verificar se o serviço está rodando
echo -e "\n${YELLOW}1. Verificando status do serviço...${NC}"
if docker service ps "$SERVICE_NAME" &>/dev/null; then
    echo -e "${GREEN}✅ Serviço encontrado${NC}"
    docker service ps "$SERVICE_NAME" --no-trunc | head -3
else
    echo -e "${RED}❌ Serviço não encontrado!${NC}"
    exit 1
fi

# 2. Verificar se o serviço está na rede 'server'
echo -e "\n${YELLOW}2. Verificando rede do serviço...${NC}"
SERVICE_NETWORKS=$(docker service inspect "$SERVICE_NAME" --format '{{range .Endpoint.Spec.Networks}}{{.Target}} {{end}}' 2>/dev/null)
if echo "$SERVICE_NETWORKS" | grep -q "server"; then
    echo -e "${GREEN}✅ Serviço está na rede 'server'${NC}"
    echo -e "   Redes: $SERVICE_NETWORKS"
else
    echo -e "${RED}❌ Serviço NÃO está na rede 'server'!${NC}"
    echo -e "   Redes atuais: $SERVICE_NETWORKS"
    echo -e "${YELLOW}💡 Execute: docker service update --network-add server $SERVICE_NAME${NC}"
fi

# 3. Verificar se a rede 'server' existe
echo -e "\n${YELLOW}3. Verificando se a rede 'server' existe...${NC}"
if docker network ls | grep -q "server"; then
    echo -e "${GREEN}✅ Rede 'server' existe${NC}"
    docker network ls | grep server
else
    echo -e "${RED}❌ Rede 'server' não encontrada!${NC}"
    echo -e "${YELLOW}💡 Execute: docker network create --driver overlay --attachable server${NC}"
fi

# 4. Verificar labels do Traefik
echo -e "\n${YELLOW}4. Verificando labels do Traefik...${NC}"
TRAEFIK_LABELS=$(docker service inspect "$SERVICE_NAME" --format '{{range $k, $v := .Spec.Labels}}{{printf "%s=%s\n" $k $v}}{{end}}' | grep traefik)
if [ -n "$TRAEFIK_LABELS" ]; then
    echo -e "${GREEN}✅ Labels do Traefik encontradas:${NC}"
    echo "$TRAEFIK_LABELS" | while read -r label; do
        echo -e "   $label"
    done
else
    echo -e "${RED}❌ Nenhuma label do Traefik encontrada!${NC}"
fi

# 5. Verificar se o Traefik está rodando
echo -e "\n${YELLOW}5. Verificando Traefik...${NC}"
TRAEFIK_SERVICE=$(docker service ls | grep -i traefik | awk '{print $1}' | head -1)
if [ -n "$TRAEFIK_SERVICE" ]; then
    echo -e "${GREEN}✅ Traefik encontrado: $TRAEFIK_SERVICE${NC}"
    docker service ps "$TRAEFIK_SERVICE" --no-trunc | head -2
else
    echo -e "${RED}❌ Traefik não encontrado!${NC}"
fi

# 6. Verificar se o serviço está respondendo na porta 8000
echo -e "\n${YELLOW}6. Verificando se o serviço responde na porta 8000...${NC}"
SERVICE_CONTAINER=$(docker ps -q --filter "name=${SERVICE_NAME}" | head -1)
if [ -n "$SERVICE_CONTAINER" ]; then
    HTTP_CODE=$(docker exec "$SERVICE_CONTAINER" curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" != "000" ]; then
        echo -e "${GREEN}✅ Serviço está respondendo (HTTP $HTTP_CODE)${NC}"
    else
        echo -e "${RED}❌ Serviço não está respondendo na porta 8000${NC}"
        echo -e "${YELLOW}💡 Verifique os logs: docker service logs $SERVICE_NAME --tail=50${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Container do serviço não encontrado ainda${NC}"
fi

# 7. Verificar logs do Traefik para ver se detectou o serviço
echo -e "\n${YELLOW}7. Verificando logs do Traefik...${NC}"
if [ -n "$TRAEFIK_SERVICE" ]; then
    TRAEFIK_LOGS=$(docker service logs "$TRAEFIK_SERVICE" --tail=50 2>&1 | grep -i "celx\|${SERVICE_NAME}" | tail -5)
    if [ -n "$TRAEFIK_LOGS" ]; then
        echo -e "${GREEN}✅ Logs do Traefik relacionados ao serviço:${NC}"
        echo "$TRAEFIK_LOGS"
    else
        echo -e "${YELLOW}⚠️  Nenhum log relacionado encontrado${NC}"
        echo -e "${YELLOW}💡 Isso pode indicar que o Traefik não detectou o serviço${NC}"
    fi
fi

# 8. Testar acesso direto ao serviço
echo -e "\n${YELLOW}8. Testando acesso direto ao serviço...${NC}"
if [ -n "$SERVICE_CONTAINER" ]; then
    echo -e "${BLUE}   Testando http://localhost:8000/...${NC}"
    RESPONSE=$(docker exec "$SERVICE_CONTAINER" curl -s http://localhost:8000/ 2>/dev/null | head -20)
    if [ -n "$RESPONSE" ]; then
        echo -e "${GREEN}✅ Serviço está respondendo:${NC}"
        echo "$RESPONSE" | head -5
    else
        echo -e "${RED}❌ Serviço não está respondendo${NC}"
    fi
fi

# 9. Recomendações
echo -e "\n${BLUE}════════════════════════════════════════${NC}"
echo -e "${YELLOW}💡 Recomendações:${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"

# Verificar se precisa reiniciar Traefik
if [ -n "$TRAEFIK_SERVICE" ]; then
    echo -e "1. Reiniciar Traefik para forçar detecção:"
    echo -e "   ${GREEN}docker service update --force $TRAEFIK_SERVICE${NC}"
fi

# Verificar se precisa adicionar rede
if ! echo "$SERVICE_NETWORKS" | grep -q "server"; then
    echo -e "2. Adicionar serviço à rede 'server':"
    echo -e "   ${GREEN}docker service update --network-add server $SERVICE_NAME${NC}"
fi

echo -e "3. Ver logs do serviço:"
echo -e "   ${GREEN}docker service logs $SERVICE_NAME -f${NC}"

echo -e "4. Ver logs do Traefik:"
if [ -n "$TRAEFIK_SERVICE" ]; then
    echo -e "   ${GREEN}docker service logs $TRAEFIK_SERVICE -f | grep celx${NC}"
fi

echo -e "5. Verificar se o serviço está acessível externamente:"
echo -e "   ${GREEN}curl -I https://celx.com.br${NC}"

echo -e "\n${BLUE}════════════════════════════════════════${NC}"

