import logging
import json
from sqlalchemy import text
from app.config.database import get_db

logger = logging.getLogger(__name__)

TOOLS = [
    {
        "name": "get_product_core",
        "description": "Retorna dados essenciais do produto (preço, estoque, categoria, ML IDs)",
        "handler": "get_product_core",
        "schema": {
            "type": "object",
            "properties": {"product_id": {"type": "integer"}},
            "required": ["product_id"]
        }
    },
    {
        "name": "get_product_attributes",
        "description": "Retorna atributos, variações e configuração de envio do produto",
        "handler": "get_product_attributes",
        "schema": {
            "type": "object",
            "properties": {"product_id": {"type": "integer"}},
            "required": ["product_id"]
        }
    },
    {
        "name": "get_orders_by_item",
        "description": "Lista pedidos do item no período (campos mínimos para análise)",
        "handler": "get_orders_by_item",
        "schema": {
            "type": "object",
            "properties": {
                "ml_item_id": {"type": "string"},
                "days": {"type": "integer", "default": 30, "minimum": 1, "maximum": 365}
            },
            "required": ["ml_item_id"]
        }
    },
    {
        "name": "get_sales_aggregates",
        "description": "Agregados de vendas do item no período (receita, pedidos pagos, tickets)",
        "handler": "get_sales_aggregates",
        "schema": {
            "type": "object",
            "properties": {
                "ml_item_id": {"type": "string"},
                "days": {"type": "integer", "default": 30}
            },
            "required": ["ml_item_id"]
        }
    },
    {
        "name": "get_billing_breakdown",
        "description": "Quebra de faturamento: comissões, frete, descontos, líquido",
        "handler": "get_billing_breakdown",
        "schema": {
            "type": "object",
            "properties": {
                "ml_item_id": {"type": "string"},
                "days": {"type": "integer", "default": 30}
            },
            "required": ["ml_item_id"]
        }
    },
    {
        "name": "get_catalog_competitors_db",
        "description": "Concorrentes do mesmo catálogo (posição, vendedor, preço)",
        "handler": "get_catalog_competitors_db",
        "schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer"},
                "limit": {"type": "integer", "default": 50},
                "offset": {"type": "integer", "default": 0}
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "get_ads_metrics_by_item",
        "description": "Métricas de Product Ads do item (spend, ROAS/ACOS, orgânico vs ads)",
        "handler": "get_ads_metrics_by_item",
        "schema": {
            "type": "object",
            "properties": {
                "ml_item_id": {"type": "string"},
                "ml_account_id": {"type": "integer"},
                "days": {"type": "integer", "default": 30}
            },
            "required": ["ml_item_id", "ml_account_id"]
        }
    },
    {
        "name": "get_product_cost_config",
        "description": "Configuração de custos do produto (custo base, impostos, marketing)",
        "handler": "get_product_cost_config",
        "schema": {
            "type": "object",
            "properties": {"product_id": {"type": "integer"}},
            "required": ["product_id"]
        }
    },
    {
        "name": "compute_margin_db",
        "description": "Calcula margem usando inputs e médias do período no DB",
        "handler": "compute_margin_db",
        "schema": {
            "type": "object",
            "properties": {
                "sale_price": {"type": "number"},
                "product_cost": {"type": "number"},
                "taxes_percent": {"type": "number", "default": 0},
                "other_costs": {"type": "number", "default": 0},
                "marketing_percent": {"type": "number", "default": 0},
                "use_period_averages": {"type": "boolean", "default": True}
            },
            "required": ["sale_price", "product_cost"]
        }
    },
    {
        "name": "get_fee_preview_db",
        "description": "Prévia de comissão ML (por preço/listing/categoria)",
        "handler": "get_fee_preview_db",
        "schema": {
            "type": "object",
            "properties": {
                "price": {"type": "number"},
                "category_id": {"type": "string"},
                "listing_type_id": {"type": "string", "default": "gold_special"}
            },
            "required": ["price"]
        }
    },
    {
        "name": "simulate_price_candidates",
        "description": "Simula margem e competição para preços candidatos",
        "handler": "simulate_price_candidates",
        "schema": {
            "type": "object",
            "properties": {
                "candidates": {"type": "array", "items": {"type": "number"}},
                "product_cost": {"type": "number"},
                "taxes_percent": {"type": "number", "default": 0},
                "other_costs": {"type": "number", "default": 0},
                "marketing_percent": {"type": "number", "default": 0}
            },
            "required": ["candidates", "product_cost"]
        }
    },
    {
        "name": "get_required_attributes_db",
        "description": "Atributos obrigatórios/recomendados pela categoria",
        "handler": "get_required_attributes_db",
        "schema": {
            "type": "object",
            "properties": {"category_id": {"type": "string"}},
            "required": ["category_id"]
        }
    },
    {
        "name": "check_title_description_db",
        "description": "Valida título/descrição vs heurísticas de SEO (tamanho/keywords)",
        "handler": "check_title_description_db",
        "schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer"},
                "max_title_length": {"type": "integer", "default": 60}
            },
            "required": ["product_id"]
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
