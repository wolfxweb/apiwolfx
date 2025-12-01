"""
Script para atualizar o max_tokens do agente "Analise cadastro produto" para o máximo (8000)
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def run(db=None):
    """
    Atualiza o max_tokens do agente "Analise cadastro produto" para 16000 (máximo do gpt-5).
    """
    try:
        if db is None:
            from app.config.database import get_db
            db = next(get_db())
        
        # Buscar o agente
        check_query = text("""
            SELECT id, name, max_tokens 
            FROM openai_assistants 
            WHERE LOWER(name) LIKE LOWER('%analise%cadastro%produto%')
            LIMIT 1
        """)
        result = db.execute(check_query).fetchone()
        
        if not result:
            logger.warning("⚠️ Agente 'Analise cadastro produto' não encontrado.")
            return {"success": False, "error": "Agente não encontrado"}
        
        agent_id, agent_name, current_max_tokens = result
        
        if current_max_tokens == 16000:
            logger.info(f"ℹ️ Agente '{agent_name}' já está com max_tokens=16000. Nada a fazer.")
            return {"success": True, "message": "Agente já está com max_tokens=16000"}
        
        # Atualizar max_tokens para 16000 (máximo do gpt-5)
        update_query = text("""
            UPDATE openai_assistants 
            SET max_tokens = 16000,
                updated_at = NOW()
            WHERE id = :agent_id
        """)
        
        db.execute(update_query, {"agent_id": agent_id})
        db.commit()
        
        logger.info(f"✅ Agente '{agent_name}' (ID: {agent_id}) atualizado: max_tokens {current_max_tokens} → 16000")
        return {"success": True, "agent_id": agent_id, "old_max_tokens": current_max_tokens, "new_max_tokens": 16000}
        
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar agente: {e}", exc_info=True)
        if db:
            db.rollback()
        return {"success": False, "error": str(e)}

