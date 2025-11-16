from sqlalchemy import text
from app.config.database import get_db
import logging

logger = logging.getLogger(__name__)

"""
Cria índices para acelerar listagem de conversas e carregamento de mensagens
- Threads: filtros por company_id, user_id, is_active e ordenação por last_message_at/created_at
- Messages: busca por thread_id e ordenação por created_at
"""

def run(db=None):
    try:
        if db is None:
            db = next(get_db())
        
        statements = [
            # Threads
            """
            CREATE INDEX IF NOT EXISTS ix_openai_assistant_threads_company
            ON openai_assistant_threads (company_id);
            """,
            """
            CREATE INDEX IF NOT EXISTS ix_openai_assistant_threads_user
            ON openai_assistant_threads (user_id);
            """,
            """
            CREATE INDEX IF NOT EXISTS ix_openai_assistant_threads_assistant
            ON openai_assistant_threads (assistant_id);
            """,
            """
            CREATE INDEX IF NOT EXISTS ix_openai_assistant_threads_active
            ON openai_assistant_threads (is_active);
            """,
            """
            CREATE INDEX IF NOT EXISTS ix_openai_assistant_threads_last_message
            ON openai_assistant_threads (last_message_at DESC);
            """,
            """
            CREATE INDEX IF NOT EXISTS ix_openai_assistant_threads_created
            ON openai_assistant_threads (created_at DESC);
            """,
            # Índice composto mais usado no filtro/ordenação
            """
            CREATE INDEX IF NOT EXISTS ix_openai_assistant_threads_company_user_active_last
            ON openai_assistant_threads (company_id, user_id, is_active, last_message_at DESC, created_at DESC);
            """,
            
            # Messages
            """
            CREATE INDEX IF NOT EXISTS ix_openai_assistant_messages_thread
            ON openai_assistant_messages (thread_id);
            """,
            """
            CREATE INDEX IF NOT EXISTS ix_openai_assistant_messages_created
            ON openai_assistant_messages (created_at DESC);
            """,
            # Índice composto para carregar histórico ordenado por data
            """
            CREATE INDEX IF NOT EXISTS ix_openai_assistant_messages_thread_created
            ON openai_assistant_messages (thread_id, created_at DESC);
            """,
        ]
        
        for stmt in statements:
            db.execute(text(stmt))
        db.commit()
        logger.info("✅ Índices para chat (OpenAI) criados/garantidos com sucesso")
        return {"success": True}
    except Exception as e:
        logger.error(f"❌ Erro ao criar índices do chat: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return {"success": False, "error": str(e)}
