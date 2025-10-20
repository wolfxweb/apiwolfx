#!/usr/bin/env python3
"""
Script para criar a tabela internal_products
"""
import sys
sys.path.append('/Users/wolfx/Documents/wolfx/apiwolfx')

from app.config.database import engine
from sqlalchemy import text

def create_internal_products_table():
    """Cria a tabela internal_products"""
    
    print("=== CRIANDO TABELA INTERNAL_PRODUCTS ===\n")
    
    try:
        with engine.connect() as conn:
            # Verificar se a tabela já existe
            check_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'internal_products'
            """)
            
            result = conn.execute(check_query).fetchone()
            
            if result:
                print("✅ Tabela 'internal_products' já existe")
                return
            
            print("🔧 Criando tabela 'internal_products'...")
            
            # Criar tabela
            create_query = text("""
                CREATE TABLE internal_products (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL,
                    base_product_id INTEGER,
                    name VARCHAR(500) NOT NULL,
                    description TEXT,
                    internal_sku VARCHAR(100) NOT NULL,
                    barcode VARCHAR(100),
                    cost_price NUMERIC(10, 2),
                    selling_price NUMERIC(10, 2),
                    tax_rate NUMERIC(5, 2) DEFAULT 0.0,
                    marketing_cost NUMERIC(10, 2) DEFAULT 0.0,
                    other_costs NUMERIC(10, 2) DEFAULT 0.0,
                    category VARCHAR(100),
                    brand VARCHAR(100),
                    model VARCHAR(100),
                    supplier VARCHAR(200),
                    status VARCHAR(50) DEFAULT 'active',
                    is_featured BOOLEAN DEFAULT FALSE,
                    min_stock INTEGER DEFAULT 0,
                    current_stock INTEGER DEFAULT 0,
                    main_image VARCHAR(1000),
                    additional_images JSON,
                    notes TEXT,
                    internal_notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            conn.execute(create_query)
            conn.commit()
            
            print("✅ Tabela 'internal_products' criada com sucesso!")
            
            # Criar índices
            print("🔧 Criando índices...")
            
            indexes = [
                "CREATE INDEX ix_internal_products_company ON internal_products (company_id)",
                "CREATE INDEX ix_internal_products_base ON internal_products (base_product_id)",
                "CREATE INDEX ix_internal_products_sku ON internal_products (internal_sku)",
                "CREATE INDEX ix_internal_products_status ON internal_products (status)",
                "CREATE INDEX ix_internal_products_category ON internal_products (category)",
                "CREATE INDEX ix_internal_products_created ON internal_products (created_at)"
            ]
            
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    conn.commit()
                except Exception as e:
                    print(f"⚠️ Aviso ao criar índice: {e}")
            
            print("✅ Índices criados com sucesso!")
        
        print("\n🎉 Tabela 'internal_products' criada com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao criar tabela: {e}")

if __name__ == "__main__":
    create_internal_products_table()
