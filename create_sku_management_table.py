#!/usr/bin/env python3
"""
Script para criar tabela de gerenciamento de SKUs
"""
import sys
sys.path.append('/Users/wolfx/Documents/wolfx/apiwolfx')

from app.config.database import engine
from sqlalchemy import text

def create_sku_management_table():
    """Cria tabela para gerenciar SKUs e evitar duplicação"""
    
    print("=== CRIANDO TABELA DE GERENCIAMENTO DE SKUs ===\n")
    
    try:
        with engine.connect() as conn:
            # Verificar se a tabela já existe
            check_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'sku_management'
            """)
            
            result = conn.execute(check_query).fetchone()
            
            if result:
                print("✅ Tabela 'sku_management' já existe")
                return
            
            print("🔧 Criando tabela 'sku_management'...")
            
            # Criar tabela
            create_query = text("""
                CREATE TABLE sku_management (
                    id SERIAL PRIMARY KEY,
                    sku VARCHAR(100) NOT NULL UNIQUE,
                    platform VARCHAR(50) NOT NULL DEFAULT 'mercadolivre',
                    platform_item_id VARCHAR(100) NOT NULL,
                    product_id INTEGER,
                    internal_product_id INTEGER,
                    company_id INTEGER NOT NULL,
                    status VARCHAR(50) DEFAULT 'active',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            conn.execute(create_query)
            conn.commit()
            
            print("✅ Tabela 'sku_management' criada com sucesso!")
            
            # Criar índices
            print("🔧 Criando índices...")
            
            indexes = [
                "CREATE INDEX ix_sku_management_sku ON sku_management (sku)",
                "CREATE INDEX ix_sku_management_platform ON sku_management (platform)",
                "CREATE INDEX ix_sku_management_platform_item ON sku_management (platform_item_id)",
                "CREATE INDEX ix_sku_management_company ON sku_management (company_id)",
                "CREATE INDEX ix_sku_management_status ON sku_management (status)",
                "CREATE UNIQUE INDEX ix_sku_management_unique ON sku_management (sku, company_id)"
            ]
            
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    conn.commit()
                    print(f"✅ Índice criado: {index_sql.split()[-1]}")
                except Exception as e:
                    print(f"⚠️ Aviso ao criar índice: {e}")
            
            print("✅ Índices criados com sucesso!")
        
        print("\n🎉 Tabela 'sku_management' criada com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao criar tabela: {e}")

if __name__ == "__main__":
    create_sku_management_table()

