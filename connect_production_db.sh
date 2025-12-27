#!/bin/bash

# Script para conectar ao banco de produção do selvez no localhost
# Uso: ./connect_production_db.sh

echo "🔄 Configurando conexão com banco de produção do selvez..."

# Backup do .env atual
if [ -f .env ]; then
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ Backup do .env criado"
fi

# Atualizar DATABASE_URL
if grep -q "DATABASE_URL=" .env 2>/dev/null; then
    # Atualizar linha existente
    sed -i '' 's|DATABASE_URL=.*|DATABASE_URL=postgresql://api_user:%40Wolfx20202025@207.231.108.38:5432/selvez|g' .env
else
    # Adicionar nova linha
    echo "DATABASE_URL=postgresql://api_user:%40Wolfx20202025@207.231.108.38:5432/selvez" >> .env
fi

# Atualizar ENVIRONMENT
if grep -q "ENVIRONMENT=" .env 2>/dev/null; then
    sed -i '' 's|ENVIRONMENT=.*|ENVIRONMENT=production|g' .env
else
    echo "ENVIRONMENT=production" >> .env
fi

echo ""
echo "✅ Configuração atualizada!"
echo ""
echo "📋 Configurações aplicadas:"
grep -E "DATABASE_URL|ENVIRONMENT" .env
echo ""
echo "⚠️  ATENÇÃO: Você está conectando ao banco de PRODUÇÃO!"
echo "   Tenha cuidado com alterações nos dados."
echo ""
echo "🔄 Para aplicar as mudanças, reinicie o container:"
echo "   docker-compose restart api"
echo ""
echo "🔍 Para verificar a conexão:"
echo "   docker logs apiwolfx-api --tail=50 | grep -i 'database\\|connection'"
echo ""
echo "💾 Backup salvo em: .env.backup.*"

