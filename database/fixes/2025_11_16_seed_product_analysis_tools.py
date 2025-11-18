import logging
import json
from sqlalchemy import text
from app.config.database import get_db

logger = logging.getLogger(__name__)

TOOLS = [
    {
        "name": "get_orders",
        "description": "Seleciona pedidos (ml_ordens) com filtros de período, status, item e comprador",
        "handler": "get_orders",
        "schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                "status": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}}
                    ]
                },
                "ml_item_id": {"type": "string"},
                "buyer_nickname": {"type": "string"},
                "limit": {"type": "integer", "default": 50, "minimum": 1, "maximum": 500},
                "offset": {"type": "integer", "default": 0, "minimum": 0}
            }
        }
    },
    {
        "name": "get_product_sales",
        "description": "Lista vendas de um produto (por product_id ou ml_item_id) no período",
        "handler": "get_product_sales",
        "schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer"},
                "ml_item_id": {"type": "string"},
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                "status": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}}
                    ]
                },
                "limit": {"type": "integer", "default": 50, "minimum": 1, "maximum": 500},
                "offset": {"type": "integer", "default": 0, "minimum": 0}
            }
        }
    }
]


def run(db=None):
    try:
        if db is None:
            db = next(get_db())
        # Upsert tools and handlers
        for t in TOOLS:
            tool_row = db.execute(
                text(
                    """
                    INSERT INTO openai_tools (name, description, json_schema, is_active)
                    VALUES (:name, :description, CAST(:schema AS JSONB), TRUE)
                    ON CONFLICT (name) DO UPDATE SET description=EXCLUDED.description, json_schema=EXCLUDED.json_schema, is_active=TRUE
                    RETURNING id
                    """
                ), {"name": t["name"], "description": t["description"], "schema": json.dumps(t["schema"]) }
            ).fetchone()
            tool_id = tool_row[0]
            # Upsert handler
            db.execute(
                text(
                    """
                    INSERT INTO openai_tool_handlers (tool_id, handler_name, python_module, python_function, is_active)
                    VALUES (:tool_id, :handler_name, NULL, NULL, TRUE)
                    ON CONFLICT (tool_id, handler_name) DO UPDATE SET is_active=TRUE
                    """
                ), {"tool_id": tool_id, "handler_name": t["handler"]}
            )
        # Associar ao agente 'Analise produto' se existir
        agent = db.execute(text("SELECT id FROM openai_assistants WHERE LOWER(name) LIKE LOWER('%analise%produto%') LIMIT 1")).fetchone()
        if agent:
            agent_id = agent[0]
            tool_ids = db.execute(text("SELECT id FROM openai_tools WHERE is_active=TRUE")).fetchall()
            for (tid,) in tool_ids:
                db.execute(
                    text(
                        """
                        INSERT INTO openai_agent_tools (agent_id, tool_id, config)
                        VALUES (:agent_id, :tool_id, NULL)
                        ON CONFLICT (agent_id, tool_id) DO NOTHING
                        """
                    ), {"agent_id": agent_id, "tool_id": tid}
                )
        db.commit()
        logger.info("✅ Ferramentas de análise de produto seedadas com sucesso")
        return {"success": True}
    except Exception as e:
        logger.error(f"❌ Erro ao seedar ferramentas: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return {"success": False, "error": str(e)}
