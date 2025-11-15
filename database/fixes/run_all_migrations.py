#!/usr/bin/env python3
"""
Script para executar todas as migrações de banco de dados relacionadas ao OpenAI
Execute este script em produção após fazer deploy

Uso:
    python database/fixes/run_all_migrations.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config.database import engine, SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_all_migrations():
    """Executa todas as migrações necessárias"""
    
    db = SessionLocal()
    try:
        logger.info("🚀 Iniciando migrações de banco de dados...")
        
        # 1. Criar tabelas OpenAI Assistants (se não existirem)
        logger.info("📋 1/3: Verificando tabelas OpenAI Assistants...")
        # Importar e executar o script de criação de tabelas
        import importlib.util
        script_path = os.path.join(os.path.dirname(__file__), 'create_openai_assistants_tables.py')
        spec = importlib.util.spec_from_file_location("create_openai_assistants_tables", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        try:
            module.create_openai_assistants_tables()
            logger.info("✅ Tabelas OpenAI Assistants verificadas/criadas")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao criar tabelas (podem já existir): {e}")
        
        # 2. Adicionar colunas de memória (se não existirem)
        logger.info("📋 2/3: Verificando colunas de memória...")
        sql_memory = """
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'openai_assistants' AND column_name = 'memory_enabled'
            ) THEN
                ALTER TABLE openai_assistants 
                ADD COLUMN memory_enabled BOOLEAN DEFAULT TRUE NOT NULL;
            END IF;
            
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'openai_assistants' AND column_name = 'memory_data'
            ) THEN
                ALTER TABLE openai_assistants 
                ADD COLUMN memory_data JSONB;
            END IF;
            
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'openai_assistant_threads' AND column_name = 'memory_data'
            ) THEN
                ALTER TABLE openai_assistant_threads 
                ADD COLUMN memory_data JSONB;
            END IF;
        END $$;
        """
        
        with db.begin():
            db.execute(text(sql_memory))
        logger.info("✅ Colunas de memória verificadas/adicionadas")
        
        # 3. Adicionar coluna initial_prompt (se não existir)
        logger.info("📋 3/3: Verificando coluna initial_prompt...")
        sql_initial_prompt = """
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'openai_assistants' AND column_name = 'initial_prompt'
            ) THEN
                ALTER TABLE openai_assistants 
                ADD COLUMN initial_prompt TEXT;
            END IF;
        END $$;
        """
        
        with db.begin():
            db.execute(text(sql_initial_prompt))
        logger.info("✅ Coluna initial_prompt verificada/adicionada")
        
        logger.info("✅ Todas as migrações concluídas com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro ao executar migrações: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_all_migrations()

