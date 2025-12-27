#!/bin/bash

# Script para testar a conexão com o banco de produção
# Uso: ./test_production_db_connection.sh

echo "🔍 Testando conexão com banco de produção do selvez..."
echo ""

# Verificar se o container está rodando
if ! docker ps | grep -q apiwolfx-api; then
    echo "⚠️  Container 'apiwolfx-api' não está rodando."
    echo "   Inicie o container primeiro: docker-compose up -d"
    exit 1
fi

echo "📋 Executando teste de conexão no container..."
echo ""

docker exec apiwolfx-api python3 -c "
import sys
import os
sys.path.insert(0, '/app')

try:
    from app.config.database import engine, DATABASE_URL
    from sqlalchemy import text
    
    print('✅ Módulo database importado com sucesso')
    print(f'📊 DATABASE_URL configurada: {DATABASE_URL[:50]}...')
    print('')
    
    # Testar conexão
    print('🔄 Testando conexão...')
    with engine.connect() as conn:
        result = conn.execute(text('SELECT current_database(), current_user, version()'))
        db_info = result.fetchone()
        print('')
        print('✅ Conexão estabelecida com sucesso!')
        print(f'   Database: {db_info[0]}')
        print(f'   User: {db_info[1]}')
        print(f'   PostgreSQL Version: {db_info[2][:50]}...')
        print('')
        
        # Contar tabelas
        result = conn.execute(text(\"\"\"
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        \"\"\"))
        table_count = result.scalar()
        print(f'📊 Tabelas encontradas: {table_count}')
        
except Exception as e:
    print(f'❌ Erro ao conectar: {e}')
    sys.exit(1)
" 2>&1

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Teste concluído com sucesso!"
else
    echo ""
    echo "❌ Falha no teste de conexão"
    echo "   Verifique os logs: docker logs apiwolfx-api --tail=50"
fi

