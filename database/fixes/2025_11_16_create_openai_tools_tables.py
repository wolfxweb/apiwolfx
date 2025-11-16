from sqlalchemy import text
from app.config.database import get_db
import logging

logger = logging.getLogger(__name__)

"""
Cria estrutura de ferramentas reutilizáveis e associação a agentes:
- openai_tools
- openai_tool_handlers
- openai_agent_tools (pivot N:N)
"""

def run(db=None):
    try:
        if db is None:
            db = next(get_db())
        
        statements = [
            # Tabela de ferramentas
            """
            CREATE TABLE IF NOT EXISTS openai_tools (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                description TEXT,
                json_schema JSONB NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """,
            # Índices ferramentas
            """
            CREATE INDEX IF NOT EXISTS ix_openai_tools_active ON openai_tools (is_active);
            """,
            
            # Handlers (resolução local do nome -> função python ou entrypoint)
            """
            CREATE TABLE IF NOT EXISTS openai_tool_handlers (
                id SERIAL PRIMARY KEY,
                tool_id INTEGER NOT NULL REFERENCES openai_tools(id) ON DELETE CASCADE,
                handler_name VARCHAR(150) NOT NULL,
                python_module VARCHAR(255),
                python_function VARCHAR(255),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_tool_handler_name ON openai_tool_handlers (tool_id, handler_name);
            """,
            
            # Pivot agente<->ferramenta
            """
            CREATE TABLE IF NOT EXISTS openai_agent_tools (
                agent_id INTEGER NOT NULL REFERENCES openai_assistants(id) ON DELETE CASCADE,
                tool_id INTEGER NOT NULL REFERENCES openai_tools(id) ON DELETE CASCADE,
                config JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(agent_id, tool_id)
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS ix_openai_agent_tools_agent ON openai_agent_tools (agent_id);
            """,
            """
            CREATE INDEX IF NOT EXISTS ix_openai_agent_tools_tool ON openai_agent_tools (tool_id);
            """,
        ]
        
        for stmt in statements:
            db.execute(text(stmt))
        db.commit()
        logger.info("✅ Tabelas/índices de ferramentas criados/garantidos com sucesso")
        return {"success": True}
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas de ferramentas: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return {"success": False, "error": str(e)}
