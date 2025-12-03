"""
Script para tornar company_id nullable na tabela openai_assistant_threads
Permite que superadmin execute agentes sem company_id
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def run(db):
    """
    Executa a migração para tornar company_id nullable
    
    Args:
        db: Sessão do banco de dados
    """
    try:
        logger.info("🔄 Tornando company_id nullable em openai_assistant_threads...")
        
        # Verificar se a coluna já é nullable
        check_query = text("""
            SELECT is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'openai_assistant_threads' 
            AND column_name = 'company_id'
        """)
        result = db.execute(check_query).fetchone()
        
        if result and result[0] == 'YES':
            logger.info("ℹ️ company_id já é nullable em openai_assistant_threads")
            return
        
        # SQL para tornar company_id nullable
        sql = text("""
        ALTER TABLE openai_assistant_threads 
        ALTER COLUMN company_id DROP NOT NULL;
        """)
        
        db.execute(sql)
        
        # Remover foreign key constraint de user_id para permitir IDs de superadmin
        # (superadmin não está na tabela users)
        try:
            # Verificar se a constraint existe
            check_fk = text("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'openai_assistant_threads' 
                AND constraint_type = 'FOREIGN KEY'
                AND constraint_name LIKE '%user_id%'
            """)
            fk_result = db.execute(check_fk).fetchone()
            
            if fk_result:
                fk_name = fk_result[0]
                drop_fk_sql = text(f"ALTER TABLE openai_assistant_threads DROP CONSTRAINT IF EXISTS {fk_name};")
                db.execute(drop_fk_sql)
                logger.info(f"✅ Foreign key constraint {fk_name} removida de user_id")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao remover foreign key de user_id (pode não existir): {e}")
        
        db.commit()
        
        logger.info("✅ company_id agora é nullable em openai_assistant_threads")
        
    except Exception as e:
        logger.error(f"❌ Erro ao tornar company_id nullable: {e}", exc_info=True)
        db.rollback()
        raise

