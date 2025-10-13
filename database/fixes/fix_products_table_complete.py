#!/usr/bin/env python3
"""
Script para adicionar todas as colunas faltantes à tabela products
"""
import sys
sys.path.append('/Users/wolfx/Documents/wolfx/apiwolfx')

from app.config.database import engine
from sqlalchemy import text

def fix_products_table_complete():
    """Adiciona todas as colunas faltantes à tabela products"""
    
    print("=== CORRIGINDO TABELA PRODUCTS COMPLETAMENTE ===\n")
    
    # Colunas que precisam ser adicionadas
    columns_to_add = [
        ("cost_price", "VARCHAR(20)"),
        ("tax_rate", "VARCHAR(10)"),
        ("marketing_cost", "VARCHAR(20)"),
        ("other_costs", "VARCHAR(20)"),
        ("notes", "TEXT")
    ]
    
    try:
        with engine.connect() as conn:
            for column_name, column_type in columns_to_add:
                # Verificar se a coluna já existe
                check_query = text(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'products' 
                    AND column_name = '{column_name}'
                """)
                
                result = conn.execute(check_query).fetchone()
                
                if result:
                    print(f"✅ Coluna '{column_name}' já existe")
                else:
                    print(f"🔧 Adicionando coluna '{column_name}'...")
                    
                    # Adicionar a coluna
                    alter_query = text(f"""
                        ALTER TABLE products 
                        ADD COLUMN {column_name} {column_type}
                    """)
                    
                    conn.execute(alter_query)
                    conn.commit()
                    
                    print(f"✅ Coluna '{column_name}' adicionada com sucesso!")
        
        print("\n🎉 Tabela 'products' corrigida completamente!")
        
    except Exception as e:
        print(f"❌ Erro ao corrigir tabela: {e}")

if __name__ == "__main__":
    fix_products_table_complete()
