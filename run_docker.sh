#!/bin/bash

# Script para executar a aplicação com Docker
echo "🚀 Iniciando API Mercado Livre com Docker..."

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não está instalado. Instale o Docker primeiro."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose não está instalado. Instale o Docker Compose primeiro."
    exit 1
fi

# Criar diretório de logs se não existir
mkdir -p logs

# Parar containers existentes
echo "🛑 Parando containers existentes..."
docker-compose down

# Construir e iniciar containers
echo "🔨 Construindo e iniciando containers..."
docker-compose up --build -d

# Aguardar aplicação inicializar
echo "⏳ Aguardando aplicação inicializar..."
sleep 5

# Nota: Usando PostgreSQL externo - não precisa inicializar banco local
echo "ℹ️  Usando PostgreSQL externo: pgadmin.wolfx.com.br"

echo ""
echo "✅ Aplicação iniciada com sucesso!"
echo ""
echo "🌐 URLs disponíveis:"
echo "   • API: http://localhost:8000"
echo "   • Documentação: http://localhost:8000/docs"
echo "   • Status: http://localhost:8000/health"
echo ""
echo "🔑 Banco de dados PostgreSQL:"
echo "   • Host: pgadmin.wolfx.com.br:5432"
echo "   • Usuário: postgres"
echo "   • Banco: comercial"
echo "   • Interface: https://pgadmin.wolfx.com.br/"
echo ""
echo "📊 Para ver logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Para parar:"
echo "   docker-compose down"
echo ""
