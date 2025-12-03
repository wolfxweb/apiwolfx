#!/usr/bin/env python3
"""
Script para tornar company_id nullable na tabela content_briefings
Execute este script para permitir que superadmin crie briefings sem company_id

Uso:
    python database/fixes/make_company_id_nullable_in_briefings.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config.database import engine, SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def make_company_id_nullable():
    """Torna company_id nullable na tabela content_briefings"""
    
    db = SessionLocal()
    try:
        logger.info("🔄 Tornando company_id nullable na tabela content_briefings...")
        
        # Verificar se a coluna já é nullable
        check_nullable = text("""
            SELECT is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'content_briefings' AND column_name = 'company_id'
        """)
        result = db.execute(check_nullable).fetchone()
        
        if result and result[0] == 'YES':
            logger.info("ℹ️ Campo 'company_id' já é nullable na tabela content_briefings")
            return {"success": True, "message": "Campo já é nullable"}
        
        # Tornar company_id nullable
        logger.info("📝 Tornando campo 'company_id' nullable...")
        alter_table = text("""
            ALTER TABLE content_briefings 
            ALTER COLUMN company_id DROP NOT NULL
        """)
        db.execute(alter_table)
        db.commit()
        
        logger.info("✅ Campo 'company_id' agora é nullable na tabela content_briefings")
        return {"success": True, "message": "Campo company_id agora é nullable"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro ao tornar company_id nullable: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        db.close()

if __name__ == "__main__":
    result = make_company_id_nullable()
    if result.get("success"):
        print("✅ Migração concluída com sucesso!")
        sys.exit(0)
    else:
        print(f"❌ Erro na migração: {result.get('error')}")
        sys.exit(1)

