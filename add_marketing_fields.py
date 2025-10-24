#!/usr/bin/env python3
"""
Script para adicionar campos de marketing na tabela companies
"""
import os
import sys
sys.path.append('/app')

from app.config.database import engine
from sqlalchemy import text

def add_marketing_fields():
    try:
        with engine.connect() as conn:
            # Verificar se as colunas já existem
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'companies' 
                AND column_name IN ('percentual_marketing', 'custo_adicional_por_pedido')
            """))
            
            existing_columns = [row[0] for row in result.fetchall()]
            
            if 'percentual_marketing' in existing_columns:
                print("✅ Coluna 'percentual_marketing' já existe na tabela 'companies'")
            else:
                # Adicionar coluna percentual_marketing
                conn.execute(text("""
                    ALTER TABLE companies 
                    ADD COLUMN percentual_marketing NUMERIC(5,2)
                """))
                print("✅ Coluna 'percentual_marketing' adicionada com sucesso!")
            
            if 'custo_adicional_por_pedido' in existing_columns:
                print("✅ Coluna 'custo_adicional_por_pedido' já existe na tabela 'companies'")
            else:
                # Adicionar coluna custo_adicional_por_pedido
                conn.execute(text("""
                    ALTER TABLE companies 
                    ADD COLUMN custo_adicional_por_pedido NUMERIC(10,2)
                """))
                print("✅ Coluna 'custo_adicional_por_pedido' adicionada com sucesso!")
            
            conn.commit()
            print("✅ Todas as colunas de marketing foram processadas!")
            
    except Exception as e:
        print(f"❌ Erro ao adicionar colunas: {e}")
        return False
    
    return True

if __name__ == "__main__":
    add_marketing_fields()
