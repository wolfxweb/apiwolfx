#!/usr/bin/env python3
"""
Script para adicionar colunas memory_enabled e memory_data às tabelas OpenAI
Execute este script para adicionar as colunas de memória persistente

Uso:
    python database/fixes/add_memory_columns_to_openai_assistants.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config.database import engine, SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_memory_columns():
    """Adiciona colunas memory_enabled e memory_data às tabelas OpenAI"""
    
    sql = """
    -- Adicionar memory_enabled e memory_data à tabela openai_assistants se não existirem
    DO $$ 
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'openai_assistants' AND column_name = 'memory_enabled'
        ) THEN
            ALTER TABLE openai_assistants 
            ADD COLUMN memory_enabled BOOLEAN DEFAULT TRUE NOT NULL;
            logger.info("✅ Coluna memory_enabled adicionada à tabela openai_assistants");
        ELSE
            logger.info("ℹ️ Coluna memory_enabled já existe em openai_assistants");
        END IF;
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'openai_assistants' AND column_name = 'memory_data'
        ) THEN
            ALTER TABLE openai_assistants 
            ADD COLUMN memory_data JSONB;
            logger.info("✅ Coluna memory_data adicionada à tabela openai_assistants");
        ELSE
            logger.info("ℹ️ Coluna memory_data já existe em openai_assistants");
        END IF;
    END $$;

    -- Adicionar memory_data à tabela openai_assistant_threads se não existir
    DO $$ 
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'openai_assistant_threads' AND column_name = 'memory_data'
        ) THEN
            ALTER TABLE openai_assistant_threads 
            ADD COLUMN memory_data JSONB;
            logger.info("✅ Coluna memory_data adicionada à tabela openai_assistant_threads");
        ELSE
            logger.info("ℹ️ Coluna memory_data já existe em openai_assistant_threads");
        END IF;
    END $$;
    """
    
    db = SessionLocal()
    try:
        logger.info("🚀 Adicionando colunas de memória às tabelas OpenAI...")
        
        # Executar SQL
        with db.begin():
            db.execute(text(sql))
        
        logger.info("✅ Colunas de memória adicionadas com sucesso!")
        
        # Verificar se as colunas foram adicionadas
        check_sql = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'openai_assistants' 
            AND column_name IN ('memory_enabled', 'memory_data')
        """)
        result = db.execute(check_sql).fetchall()
        
        if result:
            logger.info(f"✅ Verificação: Colunas encontradas: {[r[0] for r in result]}")
        else:
            logger.warning("⚠️ Nenhuma coluna de memória encontrada")
        
    except Exception as e:
        logger.error(f"❌ Erro ao adicionar colunas de memória: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    add_memory_columns()

