#!/usr/bin/env python3
"""
Script para otimizar consultas do dashboard criando índices necessários
"""
import sys
import os

# Adicionar o diretório do projeto ao path
sys.path.append('/Users/wolfx/Documents/wolfx/apiwolfx')

from app.config.database import engine
from sqlalchemy import text

def optimize_dashboard_queries():
    """Cria índices para otimizar consultas do dashboard"""
    
    print("=== OTIMIZANDO CONSULTAS DO DASHBOARD ===\n")
    
    try:
        with engine.connect() as conn:
            # Lista de índices para otimizar consultas do dashboard
            indexes = [
                # Índices para ml_orders (tabela principal do dashboard)
                {
                    "name": "idx_ml_orders_company_date_closed",
                    "sql": "CREATE INDEX IF NOT EXISTS idx_ml_orders_company_date_closed ON ml_orders (company_id, date_closed) WHERE date_closed IS NOT NULL",
                    "description": "Otimiza consultas por empresa e data de fechamento"
                },
                {
                    "name": "idx_ml_orders_company_status_date",
                    "sql": "CREATE INDEX IF NOT EXISTS idx_ml_orders_company_status_date ON ml_orders (company_id, status, date_closed)",
                    "description": "Otimiza consultas por empresa, status e data"
                },
                {
                    "name": "idx_ml_orders_company_account_date",
                    "sql": "CREATE INDEX IF NOT EXISTS idx_ml_orders_company_account_date ON ml_orders (company_id, ml_account_id, date_closed)",
                    "description": "Otimiza consultas por empresa, conta ML e data"
                },
                {
                    "name": "idx_ml_orders_cancelled_delivered",
                    "sql": "CREATE INDEX IF NOT EXISTS idx_ml_orders_cancelled_delivered ON ml_orders (company_id, status, date_closed) WHERE status = 'CANCELLED'",
                    "description": "Otimiza consultas de pedidos cancelados"
                },
                {
                    "name": "idx_ml_orders_refunded",
                    "sql": "CREATE INDEX IF NOT EXISTS idx_ml_orders_refunded ON ml_orders (company_id, status, date_closed) WHERE status = 'REFUNDED'",
                    "description": "Otimiza consultas de pedidos devolvidos"
                },
                
                # Índices para ml_accounts
                {
                    "name": "idx_ml_accounts_company",
                    "sql": "CREATE INDEX IF NOT EXISTS idx_ml_accounts_company ON ml_accounts (company_id)",
                    "description": "Otimiza consultas de contas por empresa"
                },
                
                # Índices para users
                {
                    "name": "idx_users_company_active",
                    "sql": "CREATE INDEX IF NOT EXISTS idx_users_company_active ON users (company_id, is_active) WHERE is_active = true",
                    "description": "Otimiza consultas de usuários ativos por empresa"
                },
                
                # Índices para tokens
                {
                    "name": "idx_tokens_user_active",
                    "sql": "CREATE INDEX IF NOT EXISTS idx_tokens_user_active ON tokens (user_id, is_active, expires_at) WHERE is_active = true",
                    "description": "Otimiza consultas de tokens válidos"
                },
                
                # Índices para ml_products
                {
                    "name": "idx_ml_products_company_status",
                    "sql": "CREATE INDEX IF NOT EXISTS idx_ml_products_company_status ON ml_products (company_id, status)",
                    "description": "Otimiza consultas de produtos por empresa e status"
                },
                {
                    "name": "idx_ml_products_company_updated",
                    "sql": "CREATE INDEX IF NOT EXISTS idx_ml_products_company_updated ON ml_products (company_id, updated_at)",
                    "description": "Otimiza consultas de produtos por data de atualização"
                }
            ]
            
            print("🔧 Criando índices para otimização...")
            
            for index in indexes:
                try:
                    print(f"   📊 {index['name']}: {index['description']}")
                    conn.execute(text(index['sql']))
                    conn.commit()
                    print(f"   ✅ Criado com sucesso")
                except Exception as e:
                    print(f"   ⚠️ Aviso ao criar {index['name']}: {e}")
            
            print("\n🔍 Verificando índices criados...")
            
            # Verificar índices criados
            result = conn.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes 
                WHERE indexname LIKE 'idx_%' 
                AND schemaname = 'public'
                ORDER BY tablename, indexname
            """)).fetchall()
            
            print(f"\n📋 Índices criados ({len(result)} total):")
            for row in result:
                print(f"   • {row[1]}.{row[2]}")
            
            print("\n🎉 Otimização de consultas concluída!")
            print("\n💡 Próximos passos:")
            print("   1. Reiniciar o container para aplicar os índices")
            print("   2. Monitorar performance das consultas")
            print("   3. Considerar implementar cache Redis")
            
    except Exception as e:
        print(f"❌ Erro ao otimizar consultas: {e}")

if __name__ == "__main__":
    optimize_dashboard_queries()
