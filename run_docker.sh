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

# Aguardar banco de dados inicializar
echo "⏳ Aguardando banco de dados inicializar..."
sleep 10

# Inicializar banco de dados
echo "🗄️ Inicializando banco de dados..."
docker-compose exec api python scripts/init_db.py

echo ""
echo "✅ Aplicação iniciada com sucesso!"
echo ""
echo "🌐 URLs disponíveis:"
echo "   • API: http://localhost:8000"
echo "   • Documentação: http://localhost:8000/docs"
echo "   • phpMyAdmin: http://localhost:8080"
echo "   • Status: http://localhost:8000/health"
echo ""
echo "🔑 Credenciais do banco:"
echo "   • Host: localhost:3306"
echo "   • Usuário: root"
echo "   • Senha: password"
echo "   • Banco: apiwolfx"
echo ""
echo "📊 Para ver logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Para parar:"
echo "   docker-compose down"
echo ""
