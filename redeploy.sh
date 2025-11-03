#!/bin/bash

# Script simples para redeploy - celx.com.br
# Uso: ./redeploy.sh

echo "🚀 Redeploy em Produção"
echo "======================"
echo ""

# Atualizar o stack (o docker-compose.prod.yml já faz git clone automaticamente)
echo "📦 Atualizando stack..."
docker stack deploy -c /root/docker-compose.prod.yml celx_ml_api

echo "✅ Stack atualizado!"
echo ""
echo "⏳ Aguardando serviço reiniciar (20 segundos)..."
sleep 20

echo ""
echo "📊 Status:"
docker service ps celx_ml_api_api --no-trunc | head -3

echo ""
echo "📝 Logs:"
docker service logs celx_ml_api_api --tail 10 | grep -i "uvicorn\|error\|started" || docker service logs celx_ml_api_api --tail 5

echo ""
echo "✅ Pronto! Acesse: https://celx.com.br"

