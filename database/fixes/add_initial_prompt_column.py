#!/usr/bin/env python3
"""
Script para adicionar coluna initial_prompt à tabela openai_assistants
Execute este script para adicionar a coluna de prompt inicial com template

Uso:
    python database/fixes/add_initial_prompt_column.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config.database import engine, SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_initial_prompt_column():
    """Adiciona coluna initial_prompt à tabela openai_assistants"""
    
    sql = """
    -- Adicionar initial_prompt à tabela openai_assistants se não existir
    DO $$ 
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'openai_assistants' AND column_name = 'initial_prompt'
        ) THEN
            ALTER TABLE openai_assistants 
            ADD COLUMN initial_prompt TEXT;
            logger.info("✅ Coluna initial_prompt adicionada à tabela openai_assistants");
        ELSE
            logger.info("ℹ️ Coluna initial_prompt já existe em openai_assistants");
        END IF;
    END $$;
    """
    
    db = SessionLocal()
    try:
        logger.info("🚀 Adicionando coluna initial_prompt à tabela openai_assistants...")
        
        # Executar SQL
        with db.begin():
            db.execute(text(sql))
        
        logger.info("✅ Coluna initial_prompt adicionada com sucesso!")
        
        # Verificar se a coluna foi adicionada
        check_sql = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'openai_assistants' 
            AND column_name = 'initial_prompt'
        """)
        result = db.execute(check_sql).fetchall()
        
        if result:
            logger.info(f"✅ Verificação: Coluna initial_prompt encontrada")
        else:
            logger.warning("⚠️ Coluna initial_prompt não encontrada")
        
    except Exception as e:
        logger.error(f"❌ Erro ao adicionar coluna initial_prompt: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    add_initial_prompt_column()

