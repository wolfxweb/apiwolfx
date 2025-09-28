#!/bin/bash

# Script para executar em modo desenvolvimento
echo "🚀 Iniciando API Mercado Livre - Modo Desenvolvimento..."

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não está instalado. Instale o Docker primeiro."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose não está instalado. Instale o Docker Compose primeiro."
    exit 1
fi

# Criar diretórios necessários
mkdir -p logs
mkdir -p database

# Parar containers existentes
echo "🛑 Parando containers existentes..."
docker-compose -f docker-compose.dev.yml down

# Construir e iniciar containers
echo "🔨 Construindo e iniciando containers de desenvolvimento..."
docker-compose -f docker-compose.dev.yml up --build -d

# Aguardar banco de dados inicializar
echo "⏳ Aguardando banco de dados inicializar..."
sleep 15

# Inicializar banco de dados
echo "🗄️ Inicializando banco de dados..."
docker-compose -f docker-compose.dev.yml exec api python scripts/init_db.py

echo ""
echo "✅ Aplicação de desenvolvimento iniciada com sucesso!"
echo ""
echo "🌐 URLs disponíveis:"
echo "   • API: http://localhost:8000"
echo "   • Documentação: http://localhost:8000/docs"
echo "   • phpMyAdmin: http://localhost:8080"
echo "   • Redis: http://localhost:6379"
echo "   • MailHog: http://localhost:8025"
echo "   • Status: http://localhost:8000/health"
echo ""
echo "🔑 Credenciais do banco:"
echo "   • Host: localhost:3306"
echo "   • Usuário: root"
echo "   • Senha: password"
echo "   • Banco: apiwolfx"
echo ""
echo "📊 Para ver logs:"
echo "   docker-compose -f docker-compose.dev.yml logs -f"
echo ""
echo "🛑 Para parar:"
echo "   docker-compose -f docker-compose.dev.yml down"
echo ""
echo "🔄 Para reiniciar:"
echo "   docker-compose -f docker-compose.dev.yml restart api"
echo ""
