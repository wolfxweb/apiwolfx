#!/bin/bash

# Script de Deploy para VPS
# Atualiza código do GitHub e faz deploy no Docker Swarm
# Uso: ./deploy.sh [homologation|production]

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Validar parâmetro obrigatório
if [ -z "$1" ]; then
    echo -e "${RED}❌ Erro: Ambiente não especificado!${NC}"
    echo -e "${YELLOW}Uso: ./deploy.sh [homologation|production]${NC}"
    echo ""
    echo -e "${YELLOW}Exemplos:${NC}"
    echo -e "  ${GREEN}./deploy.sh homologation${NC}  - Deploy em homologação (celx.com.br)"
    echo -e "  ${GREEN}./deploy.sh production${NC}   - Deploy em produção (www.selvez.com.br)"
    exit 1
fi

ENVIRONMENT="$1"
if [ "$ENVIRONMENT" != "homologation" ] && [ "$ENVIRONMENT" != "production" ]; then
    echo -e "${RED}❌ Erro: Ambiente inválido!${NC}"
    echo -e "${YELLOW}Use: homologation ou production${NC}"
    exit 1
fi

# Configurar arquivos baseado no ambiente
if [ "$ENVIRONMENT" = "homologation" ]; then
    ENV_FILE="hdeploy.env"
    COMPOSE_FILE="docker-compose.homologation.yml"
    STACK_NAME="celx_ml_api"
    ENV_DISPLAY="Homologação (celx.com.br)"
else
    ENV_FILE="pdeploy.env"
    COMPOSE_FILE="docker-compose.production.yml"
    STACK_NAME="selvez_ml_api"
    ENV_DISPLAY="Produção (www.selvez.com.br)"
fi

# Diretório do projeto (será detectado automaticamente ou usar padrão)
if [ -d "/root/apiwolfx" ]; then
    PROJECT_DIR="/root/apiwolfx"
else
    # Tentar detectar diretório atual se não estiver no servidor
    PROJECT_DIR=$(pwd)
fi

# Carregar variáveis de ambiente do arquivo correto
if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}✅ Carregando variáveis de ambiente de ${ENV_FILE}${NC}"
    set -a
    source "$ENV_FILE"
    set +a
    
    # Verificar se OPENAI_API_KEY foi carregada
    if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "" ]; then
        echo -e "${RED}❌ ERRO: OPENAI_API_KEY não está definida ou está vazia no ${ENV_FILE}${NC}"
        echo -e "${YELLOW}💡 Adicione a chave no arquivo ${ENV_FILE} antes de fazer deploy${NC}"
        echo -e "${YELLOW}   Exemplo: OPENAI_API_KEY=sk-proj-sua-chave-aqui${NC}"
        read -p "Deseja continuar mesmo assim? (s/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Ss]$ ]]; then
            echo -e "${YELLOW}⏸️  Deploy cancelado pelo usuário${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✅ OPENAI_API_KEY carregada (${#OPENAI_API_KEY} caracteres)${NC}"
        # Garantir que a variável está exportada para o Docker Swarm
        export OPENAI_API_KEY
    fi
else
    echo -e "${RED}❌ ERRO: Arquivo ${ENV_FILE} não encontrado!${NC}"
    echo -e "${YELLOW}💡 Certifique-se de que o arquivo existe antes de fazer deploy${NC}"
    exit 1
fi

echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${GREEN}🚀 Deploy em ${ENV_DISPLAY} - Iniciando...${NC}"
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
# Exportar variáveis explicitamente para garantir que o Docker Swarm as veja
export OPENAI_API_KEY
export ASAAS_API_KEY
export ASAAS_WEBHOOK_TOKEN

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
        echo -e "${YELLOW}💡 Adicionando serviço à rede 'server'...${NC}"
        if docker service update --network-add server "${STACK_NAME}_api" 2>/dev/null; then
            echo -e "${GREEN}✅ Serviço adicionado à rede 'server'${NC}"
            echo -e "${BLUE}⏳ Aguardando atualização do serviço...${NC}"
            sleep 5
        else
            echo -e "${YELLOW}⚠️  Não foi possível adicionar à rede automaticamente. Verifique o ${COMPOSE_FILE}${NC}"
        fi
    fi
else
    echo -e "${RED}❌ Rede 'server' não encontrada!${NC}"
    echo -e "${YELLOW}💡 Criando rede 'server'...${NC}"
    docker network create --driver overlay --attachable server || true
fi

echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Deploy concluído!${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"

# Configurar MCP no Cursor (apenas se executado localmente, não no servidor)
# Detectar se estamos em ambiente local (Mac/Windows com Cursor) ou servidor
IS_LOCAL=false
if [ -d "$HOME/.cursor" ] && [ "$USER" != "root" ]; then
    IS_LOCAL=true
elif [ -d "$HOME/.cursor" ]; then
    # Mesmo sendo root, se tem .cursor pode ser local
    IS_LOCAL=true
fi

if [ "$IS_LOCAL" = true ]; then
    echo -e "${YELLOW}🔧 Configurando MCP no Cursor...${NC}"
    
    # Obter diretório do script deploy.sh
    SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
    MCP_SCRIPT="$SCRIPT_DIR/add_mcp_to_cursor.py"
    
    # Verificar se o script existe
    if [ -f "$MCP_SCRIPT" ]; then
        # Executar script de configuração do MCP no diretório do script
        if command -v python3 &> /dev/null; then
            echo -e "${BLUE}⏳ Configurando MCP para ambiente: ${ENVIRONMENT}...${NC}"
            (cd "$SCRIPT_DIR" && python3 add_mcp_to_cursor.py "$ENVIRONMENT" 2>/dev/null)
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✅ MCP configurado no Cursor para ambiente: ${ENVIRONMENT}${NC}"
                echo -e "${GREEN}   Reinicie o Cursor para aplicar as mudanças${NC}"
            else
                echo -e "${YELLOW}⚠️  Não foi possível configurar o MCP automaticamente${NC}"
                echo -e "${YELLOW}💡 Execute manualmente: cd $(dirname "$SCRIPT_DIR") && python3 add_mcp_to_cursor.py ${ENVIRONMENT}${NC}"
            fi
        else
            echo -e "${YELLOW}⚠️  Python3 não encontrado - pulando configuração do MCP${NC}"
            echo -e "${YELLOW}💡 Execute manualmente: python3 add_mcp_to_cursor.py ${ENVIRONMENT}${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Script add_mcp_to_cursor.py não encontrado em ${SCRIPT_DIR}${NC}"
        echo -e "${YELLOW}💡 Execute manualmente: python3 add_mcp_to_cursor.py ${ENVIRONMENT}${NC}"
    fi
else
    echo -e "${YELLOW}💡 Para configurar MCP no Cursor localmente, execute:${NC}"
    echo -e "   ${GREEN}python3 add_mcp_to_cursor.py ${ENVIRONMENT}${NC}"
fi

echo -e "${YELLOW}💡 Próximos passos:${NC}"
echo -e "   1. Verifique os logs: docker service logs ${STACK_NAME}_api -f"
echo -e "   2. Teste a aplicação: curl http://localhost:8000"
echo -e "   3. Monitore os serviços: docker service ps ${STACK_NAME}_api"
echo -e "   4. Se ainda der 404, reinicie o Traefik: docker service update --force traefik_traefik"
    if [ "$ENVIRONMENT" = "homologation" ]; then
        echo -e "   5. Verifique logs do Traefik: docker service logs traefik_traefik --tail=50 | grep celx"
        echo -e "   6. Configure MCP: python3 add_mcp_to_cursor.py homologation"
        echo -e "      URL da API: https://celx.com.br"
    else
        echo -e "   5. Verifique logs do Traefik: docker service logs traefik_traefik --tail=50 | grep selvez"
        echo -e "   6. Configure MCP: python3 add_mcp_to_cursor.py production"
        echo -e "      URL da API: https://www.selvez.com.br"
    fi
echo -e "${BLUE}════════════════════════════════════════${NC}"
