#!/usr/bin/env python3
"""
Script para adicionar suporte a múltiplos providers de IA na tabela openai_assistants
Execute este script para adicionar campos provider e api_config

Uso:
    python database/fixes/add_provider_support_to_agents.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config.database import engine, SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_provider_support():
    """Adiciona campos provider e api_config às tabelas de agentes"""
    
    db = SessionLocal()
    try:
        logger.info("🔄 Adicionando suporte a múltiplos providers de IA...")
        
        # Adicionar campo provider na tabela openai_assistants
        try:
            check_provider = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'openai_assistants' AND column_name = 'provider'
            """)
            result = db.execute(check_provider).fetchone()
            
            if not result:
                logger.info("📝 Adicionando campo 'provider' à tabela openai_assistants...")
                add_provider = text("""
                    ALTER TABLE openai_assistants 
                    ADD COLUMN provider VARCHAR(50) DEFAULT 'openai' NOT NULL
                """)
                db.execute(add_provider)
                
                # Criar índice
                create_idx = text("""
                    CREATE INDEX IF NOT EXISTS ix_openai_assistants_provider 
                    ON openai_assistants(provider)
                """)
                db.execute(create_idx)
                db.commit()
                logger.info("✅ Campo 'provider' adicionado à tabela openai_assistants")
            else:
                logger.info("ℹ️ Campo 'provider' já existe na tabela openai_assistants")
        except Exception as e:
            db.rollback()
            if 'already exists' not in str(e).lower() and 'duplicate' not in str(e).lower():
                logger.warning(f"⚠️ Aviso ao adicionar campo provider: {e}")
        
        # Adicionar campo api_config na tabela openai_assistants
        try:
            check_api_config = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'openai_assistants' AND column_name = 'api_config'
            """)
            result = db.execute(check_api_config).fetchone()
            
            if not result:
                logger.info("📝 Adicionando campo 'api_config' à tabela openai_assistants...")
                add_api_config = text("""
                    ALTER TABLE openai_assistants 
                    ADD COLUMN api_config JSONB
                """)
                db.execute(add_api_config)
                db.commit()
                logger.info("✅ Campo 'api_config' adicionado à tabela openai_assistants")
            else:
                logger.info("ℹ️ Campo 'api_config' já existe na tabela openai_assistants")
        except Exception as e:
            db.rollback()
            if 'already exists' not in str(e).lower() and 'duplicate' not in str(e).lower():
                logger.warning(f"⚠️ Aviso ao adicionar campo api_config: {e}")
        
        # Adicionar campo provider na tabela openai_assistant_usage
        try:
            check_usage_provider = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'openai_assistant_usage' AND column_name = 'provider'
            """)
            result = db.execute(check_usage_provider).fetchone()
            
            if not result:
                logger.info("📝 Adicionando campo 'provider' à tabela openai_assistant_usage...")
                add_usage_provider = text("""
                    ALTER TABLE openai_assistant_usage 
                    ADD COLUMN provider VARCHAR(50) DEFAULT 'openai'
                """)
                db.execute(add_usage_provider)
                
                # Criar índice
                create_usage_idx = text("""
                    CREATE INDEX IF NOT EXISTS ix_openai_assistant_usage_provider 
                    ON openai_assistant_usage(provider)
                """)
                db.execute(create_usage_idx)
                db.commit()
                logger.info("✅ Campo 'provider' adicionado à tabela openai_assistant_usage")
            else:
                logger.info("ℹ️ Campo 'provider' já existe na tabela openai_assistant_usage")
        except Exception as e:
            db.rollback()
            if 'already exists' not in str(e).lower() and 'duplicate' not in str(e).lower():
                logger.warning(f"⚠️ Aviso ao adicionar campo provider em usage: {e}")
        
        # Atualizar registros existentes para ter provider = 'openai'
        try:
            update_assistants = text("""
                UPDATE openai_assistants 
                SET provider = 'openai' 
                WHERE provider IS NULL OR provider = ''
            """)
            db.execute(update_assistants)
            
            update_usage = text("""
                UPDATE openai_assistant_usage 
                SET provider = 'openai' 
                WHERE provider IS NULL OR provider = ''
            """)
            db.execute(update_usage)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f"⚠️ Aviso ao atualizar providers existentes: {e}")
        
        logger.info("✅ Suporte a múltiplos providers adicionado com sucesso!")
        return {"success": True, "message": "Campos provider e api_config adicionados com sucesso"}
        
    except Exception as e:
        logger.error(f"❌ Erro ao adicionar suporte a providers: {e}", exc_info=True)
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()

if __name__ == "__main__":
    result = add_provider_support()
    if result.get("success"):
        print("✅ Migração concluída com sucesso!")
        sys.exit(0)
    else:
        print(f"❌ Erro na migração: {result.get('error')}")
        sys.exit(1)

