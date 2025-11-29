"""
Script para atualizar o enum userrole adicionando o valor 'analyst'
"""
import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from app.config.database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_userrole_enum():
    """Adiciona o valor 'analyst' ao enum userrole se não existir"""
    try:
        with engine.connect() as conn:
            # Verificar se o enum existe
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = 'userrole'
                );
            """))
            enum_exists = result.scalar()
            
            if not enum_exists:
                logger.info("Criando enum userrole...")
                conn.execute(text("""
                    CREATE TYPE userrole AS ENUM ('super_admin', 'company_admin', 'manager', 'analyst', 'viewer');
                """))
                conn.commit()
                logger.info("✅ Enum userrole criado com todos os valores")
            else:
                # Verificar se 'analyst' já existe
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_enum 
                        WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'userrole')
                        AND enumlabel = 'analyst'
                    );
                """))
                analyst_exists = result.scalar()
                
                if not analyst_exists:
                    logger.info("Adicionando valor 'analyst' ao enum userrole...")
                    # PostgreSQL não permite adicionar valores no meio do enum facilmente
                    # Vamos tentar adicionar no final
                    try:
                        conn.execute(text("""
                            ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'analyst';
                        """))
                        conn.commit()
                        logger.info("✅ Valor 'analyst' adicionado ao enum userrole")
                    except Exception as e:
                        logger.warning(f"⚠️ Não foi possível adicionar 'analyst' ao enum: {e}")
                        logger.info("💡 Pode ser necessário recriar o enum ou usar uma migração Alembic")
                else:
                    logger.info("✅ Valor 'analyst' já existe no enum userrole")
            
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar enum userrole: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    update_userrole_enum()

