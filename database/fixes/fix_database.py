#!/usr/bin/env python3
"""
Script para corrigir o banco de dados - adicionar campo has_catalog_products
"""
import sys
import os

# Adicionar o diretório do projeto ao path
sys.path.append('/Users/wolfx/Documents/wolfx/apiwolfx')

from app.config.database import engine
from sqlalchemy import text

def fix_database():
    """Adiciona o campo has_catalog_products à tabela ml_orders"""
    
    print("=== CORRIGINDO BANCO DE DADOS ===\n")
    
    try:
        with engine.connect() as conn:
            # Verificar se a coluna já existe
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'ml_orders' 
                AND column_name = 'has_catalog_products'
            """)
            
            result = conn.execute(check_query).fetchone()
            
            if result:
                print("✅ Coluna 'has_catalog_products' já existe")
            else:
                print("🔧 Adicionando coluna 'has_catalog_products'...")
                
                # Adicionar a coluna
                alter_query = text("""
                    ALTER TABLE ml_orders 
                    ADD COLUMN has_catalog_products BOOLEAN DEFAULT FALSE
                """)
                
                conn.execute(alter_query)
                conn.commit()
                
                print("✅ Coluna 'has_catalog_products' adicionada com sucesso!")
                
                # Criar índice
                print("🔧 Criando índice...")
                index_query = text("""
                    CREATE INDEX IF NOT EXISTS ix_ml_orders_has_catalog_products 
                    ON ml_orders (has_catalog_products)
                """)
                
                conn.execute(index_query)
                conn.commit()
                
                print("✅ Índice criado com sucesso!")
            
            # Verificar se a coluna catalog_products_count já existe
            check_query2 = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'ml_orders' 
                AND column_name = 'catalog_products_count'
            """)
            
            result2 = conn.execute(check_query2).fetchone()
            
            if result2:
                print("✅ Coluna 'catalog_products_count' já existe")
            else:
                print("🔧 Adicionando coluna 'catalog_products_count'...")
                
                # Adicionar a coluna
                alter_query2 = text("""
                    ALTER TABLE ml_orders 
                    ADD COLUMN catalog_products_count INTEGER DEFAULT 0
                """)
                
                conn.execute(alter_query2)
                conn.commit()
                
                print("✅ Coluna 'catalog_products_count' adicionada com sucesso!")
            
            # Verificar se a coluna catalog_products já existe
            check_query3 = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'ml_orders' 
                AND column_name = 'catalog_products'
            """)
            
            result3 = conn.execute(check_query3).fetchone()
            
            if result3:
                print("✅ Coluna 'catalog_products' já existe")
            else:
                print("🔧 Adicionando coluna 'catalog_products'...")
                
                # Adicionar a coluna
                alter_query3 = text("""
                    ALTER TABLE ml_orders 
                    ADD COLUMN catalog_products JSON
                """)
                
                conn.execute(alter_query3)
                conn.commit()
                
                print("✅ Coluna 'catalog_products' adicionada com sucesso!")
        
        print("\n🎉 Banco de dados corrigido com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao corrigir banco de dados: {e}")

if __name__ == "__main__":
    fix_database()
