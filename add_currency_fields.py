#!/usr/bin/env python3
"""
Script para adicionar campos de moeda à tabela ordem_compra
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Configuração do banco
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://apiwolfx:apiwolfx@localhost:5432/apiwolfx")

def add_currency_fields():
    """Adicionar campos de moeda à tabela ordem_compra"""
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Adicionar coluna moeda
            conn.execute(text("""
                ALTER TABLE ordem_compra 
                ADD COLUMN IF NOT EXISTS moeda VARCHAR(10) DEFAULT 'BRL' NOT NULL;
            """))
            
            # Adicionar coluna cotacao_moeda
            conn.execute(text("""
                ALTER TABLE ordem_compra 
                ADD COLUMN IF NOT EXISTS cotacao_moeda NUMERIC(10,4) DEFAULT 1.0;
            """))
            
            conn.commit()
            print("✅ Campos de moeda adicionados com sucesso!")
            
    except SQLAlchemyError as e:
        print(f"❌ Erro ao adicionar campos de moeda: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🔧 Adicionando campos de moeda à tabela ordem_compra...")
    add_currency_fields()
    print("✅ Processo concluído!")
