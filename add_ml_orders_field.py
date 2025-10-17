#!/usr/bin/env python3
"""
Script para adicionar campo ml_orders_as_revenue na tabela companies
"""
import os
import sys
sys.path.append('/app')

from app.config.database import engine
from sqlalchemy import text

def add_ml_orders_field():
    try:
        with engine.connect() as conn:
            # Verificar se a coluna já existe
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'companies' 
                AND column_name = 'ml_orders_as_revenue'
            """))
            
            if result.fetchone():
                print("✅ Coluna 'ml_orders_as_revenue' já existe na tabela 'companies'")
                return
            
            # Adicionar coluna
            conn.execute(text("""
                ALTER TABLE companies 
                ADD COLUMN ml_orders_as_revenue BOOLEAN DEFAULT true
            """))
            conn.commit()
            print("✅ Coluna 'ml_orders_as_revenue' adicionada com sucesso!")
            
    except Exception as e:
        print(f"❌ Erro ao adicionar coluna: {e}")
        return False
    
    return True

if __name__ == "__main__":
    add_ml_orders_field()
