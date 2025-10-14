#!/bin/bash

echo "🔨 Build da Imagem para Produção"
echo "================================="
echo ""

# Verificar se o docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não está instalado"
    exit 1
fi

echo "✅ Docker encontrado"
echo ""

# Fazer build da imagem
echo "🔨 Fazendo build da imagem apiwolfx-api:latest..."
docker build -t apiwolfx-api:latest .

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Imagem criada com sucesso!"
    echo ""
    echo "📦 Detalhes da imagem:"
    docker images apiwolfx-api:latest
    echo ""
    echo "🚀 Próximos passos:"
    echo "1. Se estiver no servidor de produção, use o docker-compose.prod.yml no Portainer"
    echo "2. Se estiver em outra máquina, envie a imagem para um registry:"
    echo "   docker tag apiwolfx-api:latest seu-registry/apiwolfx-api:latest"
    echo "   docker push seu-registry/apiwolfx-api:latest"
    echo ""
else
    echo ""
    echo "❌ Erro ao fazer build da imagem"
    exit 1
fi

