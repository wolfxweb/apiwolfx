#!/usr/bin/env python3
"""
Script para adicionar a coluna sku à tabela products
"""
import sys
sys.path.append('/Users/wolfx/Documents/wolfx/apiwolfx')

from app.config.database import engine
from sqlalchemy import text

def fix_products_table():
    """Adiciona a coluna sku à tabela products"""
    
    print("=== CORRIGINDO TABELA PRODUCTS ===\n")
    
    try:
        with engine.connect() as conn:
            # Verificar se a coluna sku já existe
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'products' 
                AND column_name = 'sku'
            """)
            
            result = conn.execute(check_query).fetchone()
            
            if result:
                print("✅ Coluna 'sku' já existe na tabela 'products'")
                return
            
            print("🔧 Adicionando coluna 'sku' à tabela 'products'...")
            
            # Adicionar a coluna sku
            alter_query = text("""
                ALTER TABLE products 
                ADD COLUMN sku VARCHAR(100)
            """)
            
            conn.execute(alter_query)
            conn.commit()
            
            print("✅ Coluna 'sku' adicionada com sucesso!")
            
            # Criar índice na coluna sku
            print("🔧 Criando índice na coluna 'sku'...")
            try:
                index_query = text("""
                    CREATE INDEX ix_products_sku ON products (sku)
                """)
                conn.execute(index_query)
                conn.commit()
                print("✅ Índice criado com sucesso!")
            except Exception as e:
                print(f"⚠️ Aviso ao criar índice: {e}")
        
        print("\n🎉 Tabela 'products' corrigida com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao corrigir tabela: {e}")

if __name__ == "__main__":
    fix_products_table()
