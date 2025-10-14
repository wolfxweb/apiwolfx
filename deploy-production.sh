#!/bin/bash

echo "🚀 Deploy em Produção - wolfx.com.br"
echo "===================================="
echo ""

# Verificar se o docker-compose está instalado
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose não está instalado"
    exit 1
fi

echo "✅ Docker Compose encontrado"
echo ""

# Parar containers antigos
echo "🛑 Parando containers antigos..."
docker-compose -f docker-compose.prod.yml down

# Fazer build da nova imagem
echo "🔨 Fazendo build da aplicação..."
docker-compose -f docker-compose.prod.yml build --no-cache

# Criar diretório para certificados SSL
echo "📁 Criando diretórios necessários..."
mkdir -p letsencrypt
mkdir -p logs
chmod 600 letsencrypt

# Subir os containers
echo "🚀 Iniciando containers..."
docker-compose -f docker-compose.prod.yml up -d

# Aguardar containers iniciarem
echo "⏳ Aguardando containers iniciarem..."
sleep 5

# Verificar status
echo ""
echo "📊 Status dos containers:"
docker-compose -f docker-compose.prod.yml ps

# Verificar logs
echo ""
echo "📝 Últimos logs da API:"
docker-compose -f docker-compose.prod.yml logs --tail=20 api

echo ""
echo "✅ Deploy concluído!"
echo ""
echo "🌐 Acesse: https://wolfx.com.br"
echo "📊 Dashboard Traefik: http://seu-ip:8080"
echo ""
echo "Para ver os logs em tempo real:"
echo "  docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "⚠️  IMPORTANTE:"
echo "1. Configure o DNS para apontar wolfx.com.br para o IP deste servidor"
echo "2. Abra as portas 80 e 443 no firewall"
echo "3. Configure o webhook no Mercado Pago: https://wolfx.com.br/payment/webhooks/mercadopago"
echo ""

