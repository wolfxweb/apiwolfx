"""
Migration: Adicionar campos de tokens de IA na tabela companies
- ai_tokens_monthly: Tokens mensais do plano (adicionados a cada pagamento mensal)
- ai_tokens_purchased: Tokens comprados avulsos
"""
import sys
import os
from pathlib import Path

# Adicionar o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from app.config.database import SessionLocal
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def add_ai_tokens_to_companies():
    """Adiciona campos de tokens de IA na tabela companies"""
    db = SessionLocal()
    try:
        logger.info("🔧 Adicionando campos de tokens de IA na tabela companies...")
        
        # Verificar se as colunas já existem
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'companies' 
            AND column_name IN ('ai_tokens_monthly', 'ai_tokens_purchased')
        """)
        existing_columns = [row[0] for row in db.execute(check_query).fetchall()]
        
        if 'ai_tokens_monthly' not in existing_columns:
            db.execute(text("ALTER TABLE companies ADD COLUMN ai_tokens_monthly INTEGER DEFAULT 0"))
            logger.info("✅ Coluna ai_tokens_monthly adicionada")
        else:
            logger.info("ℹ️ Coluna ai_tokens_monthly já existe")
        
        if 'ai_tokens_purchased' not in existing_columns:
            db.execute(text("ALTER TABLE companies ADD COLUMN ai_tokens_purchased INTEGER DEFAULT 0"))
            logger.info("✅ Coluna ai_tokens_purchased adicionada")
        else:
            logger.info("ℹ️ Coluna ai_tokens_purchased já existe")
        
        # Criar índices para melhor performance
        try:
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_companies_ai_tokens_monthly ON companies(ai_tokens_monthly)"))
            logger.info("✅ Índice em ai_tokens_monthly criado")
        except Exception as e:
            logger.warning(f"⚠️ Índice já existe ou erro ao criar: {e}")
        
        try:
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_companies_ai_tokens_purchased ON companies(ai_tokens_purchased)"))
            logger.info("✅ Índice em ai_tokens_purchased criado")
        except Exception as e:
            logger.warning(f"⚠️ Índice já existe ou erro ao criar: {e}")
        
        db.commit()
        logger.info("✅ Campos de tokens de IA adicionados com sucesso!")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro ao adicionar campos de tokens de IA: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    add_ai_tokens_to_companies()

