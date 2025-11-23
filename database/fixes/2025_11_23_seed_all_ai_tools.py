"""
Script para registrar todas as ferramentas do agente IA no banco de dados.
Este script deve ser executado durante o startup da aplicação.
"""
import logging
import json
from sqlalchemy import text
from app.config.database import get_db

logger = logging.getLogger(__name__)

# Lista completa de todas as ferramentas do agente IA
ALL_TOOLS = [
    # ========== Produtos ML ==========
    {
        "name": "get_product_core",
        "description": "Obtém dados básicos de um produto do Mercado Livre (ID, preço, estoque, categoria, SKU)",
        "handler": "get_product_core",
        "schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "ID interno do produto no sistema"}
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "get_product_attributes",
        "description": "Obtém atributos detalhados do produto, incluindo variações, configurações de envio, tags e status de saúde",
        "handler": "get_product_attributes",
        "schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "ID interno do produto no sistema"}
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "search_products_by_name",
        "description": "Busca produtos por nome ou SKU, permitindo encontrar produtos de forma flexível",
        "handler": "search_products_by_name",
        "schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Termo de busca (nome ou SKU)"},
                "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 100},
                "include_sku": {"type": "boolean", "default": True, "description": "Se deve buscar também por SKU"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "resolve_product_by_code",
        "description": "Resolve um produto a partir de diferentes tipos de código (ID interno, SKU, ml_item_id), com detecção automática do tipo",
        "handler": "resolve_product_by_code",
        "schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Código do produto (ID, SKU ou ml_item_id)"},
                "code_type": {"type": "string", "enum": ["id", "seller_sku", "ml_item_id"], "description": "Tipo do código (opcional - auto-detecção se não informado)"}
            },
            "required": ["code"]
        }
    },
    {
        "name": "check_title_description_db",
        "description": "Valida o título e descrição do produto, verificando se atendem aos critérios de qualidade",
        "handler": "check_title_description_db",
        "schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "ID interno do produto no sistema"},
                "max_title_length": {"type": "integer", "default": 60, "description": "Tamanho máximo permitido para o título"}
            },
            "required": ["product_id"]
        }
    },
    
    # ========== Pedidos e Vendas ==========
    {
        "name": "get_orders",
        "description": "Seleciona pedidos do Mercado Livre com múltiplos filtros opcionais (período, status, produto, comprador)",
        "handler": "get_orders",
        "schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Data inicial no formato YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "Data final no formato YYYY-MM-DD"},
                "status": {"oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]},
                "ml_item_id": {"type": "string"},
                "product_name": {"type": "string"},
                "seller_sku": {"type": "string"},
                "is_catalog": {"type": "boolean"},
                "buyer_nickname": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 500},
                "offset": {"type": "integer", "default": 0, "minimum": 0}
            }
        }
    },
    {
        "name": "get_product_sales",
        "description": "Lista vendas de um produto específico, incluindo quantidade vendida em cada pedido",
        "handler": "get_product_sales",
        "schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer"},
                "ml_item_id": {"type": "string"},
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                "status": {"oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]},
                "limit": {"type": "integer", "default": 50, "minimum": 1, "maximum": 500},
                "offset": {"type": "integer", "default": 0, "minimum": 0}
            }
        }
    },
    {
        "name": "get_orders_by_item",
        "description": "Busca pedidos que contêm um item específico do Mercado Livre, retornando informações resumidas dos pedidos",
        "handler": "get_orders_by_item",
        "schema": {
            "type": "object",
            "properties": {
                "ml_item_id": {"type": "string", "description": "ID do item no Mercado Livre"},
                "days": {"type": "integer", "default": 30, "description": "Número de dias para trás a partir de hoje"}
            },
            "required": ["ml_item_id"]
        }
    },
    {
        "name": "get_sales_aggregates",
        "description": "Calcula agregações de vendas de um produto (receita total, quantidade vendida, ticket médio, preço médio)",
        "handler": "get_sales_aggregates",
        "schema": {
            "type": "object",
            "properties": {
                "ml_item_id": {"type": "string", "description": "ID do item no Mercado Livre"},
                "days": {"type": "integer", "default": 30, "description": "Número de dias para trás a partir de hoje"}
            },
            "required": ["ml_item_id"]
        }
    },
    {
        "name": "get_billing_breakdown",
        "description": "Calcula breakdown detalhado de faturamento de um produto (receita, comissões, frete, descontos)",
        "handler": "get_billing_breakdown",
        "schema": {
            "type": "object",
            "properties": {
                "ml_item_id": {"type": "string", "description": "ID do item no Mercado Livre"},
                "days": {"type": "integer", "default": 30, "description": "Número de dias para trás a partir de hoje"}
            },
            "required": ["ml_item_id"]
        }
    },
    {
        "name": "get_order_details",
        "description": "Obtém detalhes completos de um pedido específico, incluindo todos os itens, comprador, envio, pagamentos e taxas",
        "handler": "get_order_details",
        "schema": {
            "type": "object",
            "properties": {
                "order_id": {"oneOf": [{"type": "string"}, {"type": "integer"}], "description": "ID do pedido (ml_order_id, order_id ou id interno)"},
                "include_items": {"type": "boolean", "default": True},
                "include_shipping": {"type": "boolean", "default": True},
                "include_payments": {"type": "boolean", "default": True},
                "include_billing": {"type": "boolean", "default": True}
            },
            "required": ["order_id"]
        }
    },
    
    # ========== Estoque ==========
    {
        "name": "get_stock_by_product",
        "description": "Consulta estoque de um produto, incluindo quantidade disponível e reservada por depósito",
        "handler": "get_stock_by_product",
        "schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer"},
                "internal_product_id": {"type": "integer"},
                "ml_item_id": {"type": "string"},
                "warehouse_id": {"type": "integer"}
            }
        }
    },
    {
        "name": "get_stock_movements",
        "description": "Lista movimentações de estoque de um produto, permitindo rastrear histórico de entradas e saídas",
        "handler": "get_stock_movements",
        "schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer"},
                "internal_product_id": {"type": "integer"},
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                "movement_type": {"type": "string"},
                "limit": {"type": "integer", "default": 50, "minimum": 1, "maximum": 500},
                "offset": {"type": "integer", "default": 0, "minimum": 0}
            }
        }
    },
    {
        "name": "update_stock_quantity",
        "description": "Atualiza a quantidade de estoque de um produto, permitindo ajustes manuais ou automáticos",
        "handler": "update_stock_quantity",
        "schema": {
            "type": "object",
            "properties": {
                "internal_product_id": {"type": "integer", "description": "ID do produto interno"},
                "warehouse_id": {"type": "integer", "description": "ID do depósito (opcional)"},
                "quantity": {"type": "number", "description": "Quantidade a adicionar/subtrair (pode ser negativo)"},
                "notes": {"type": "string", "description": "Observações sobre a movimentação"},
                "movement_type": {"type": "string", "default": "adjustment"}
            },
            "required": ["internal_product_id", "quantity"]
        }
    },
    {
        "name": "sync_stock_to_ml",
        "description": "Sincroniza o estoque interno com os anúncios do Mercado Livre, atualizando a quantidade disponível em todos os anúncios associados ao SKU",
        "handler": "sync_stock_to_ml",
        "schema": {
            "type": "object",
            "properties": {
                "internal_product_id": {"type": "integer", "description": "ID do produto interno"},
                "ml_account_id": {"type": "integer", "description": "ID da conta ML (opcional - se não informado, sincroniza todas)"}
            },
            "required": ["internal_product_id"]
        }
    },
    
    # ========== Catálogo ==========
    {
        "name": "get_catalog_competitors_db",
        "description": "Lista concorrentes de um produto no catálogo compartilhado do Mercado Livre, incluindo informações sobre preços, vendedores e posição na Buy Box",
        "handler": "get_catalog_competitors_db",
        "schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "ID interno do produto no sistema"},
                "limit": {"type": "integer", "default": 50, "minimum": 1, "maximum": 500},
                "offset": {"type": "integer", "default": 0, "minimum": 0}
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "get_catalog_monitoring_status",
        "description": "Obtém informações sobre o status do monitoramento de catálogo de um produto, incluindo se está ativo, última verificação, histórico recente e estatísticas",
        "handler": "get_catalog_monitoring_status",
        "schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "ID interno do produto"},
                "include_latest_history": {"type": "boolean", "default": True},
                "include_statistics": {"type": "boolean", "default": True}
            },
            "required": ["product_id"]
        }
    },
    
    # ========== Publicidade ==========
    {
        "name": "get_ads_metrics_by_item",
        "description": "Obtém métricas de publicidade (Product Ads) para um item específico do Mercado Livre, incluindo investimento, cliques, conversões e ROAS",
        "handler": "get_ads_metrics_by_item",
        "schema": {
            "type": "object",
            "properties": {
                "ml_item_id": {"type": "string", "description": "ID do item no Mercado Livre"},
                "ml_account_id": {"type": "integer", "description": "ID da conta ML"},
                "days": {"type": "integer", "default": 30, "description": "Número de dias para trás a partir de hoje"}
            },
            "required": ["ml_item_id", "ml_account_id"]
        }
    },
    
    # ========== Análises ==========
    {
        "name": "compute_margin_db",
        "description": "Calcula a margem de lucro de um produto com base no preço de venda, custos e percentuais de impostos e marketing",
        "handler": "compute_margin_db",
        "schema": {
            "type": "object",
            "properties": {
                "sale_price": {"type": "number", "description": "Preço de venda do produto"},
                "product_cost": {"type": "number", "description": "Custo do produto"},
                "taxes_percent": {"type": "number", "default": 0, "description": "Percentual de impostos sobre o preço de venda"},
                "other_costs": {"type": "number", "default": 0, "description": "Outros custos fixos"},
                "marketing_percent": {"type": "number", "default": 0, "description": "Percentual de marketing sobre o preço de venda"},
                "use_period_averages": {"type": "boolean", "default": True}
            },
            "required": ["sale_price", "product_cost"]
        }
    },
    {
        "name": "simulate_price_candidates",
        "description": "Simula diferentes preços candidatos e calcula a margem de lucro para cada um, permitindo análise de estratégia de preços",
        "handler": "simulate_price_candidates",
        "schema": {
            "type": "object",
            "properties": {
                "candidates": {"type": "array", "items": {"type": "number"}, "description": "Lista de preços candidatos para simular"},
                "product_cost": {"type": "number", "description": "Custo do produto"},
                "taxes_percent": {"type": "number", "default": 0},
                "other_costs": {"type": "number", "default": 0},
                "marketing_percent": {"type": "number", "default": 0}
            },
            "required": ["candidates", "product_cost"]
        }
    },
    {
        "name": "calculate",
        "description": "Realiza cálculos matemáticos de forma segura (operações básicas, funções matemáticas, percentuais)",
        "handler": "calculate",
        "schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Expressão matemática a ser calculada (ex: '100 * 1.15 + 25')"},
                "precision": {"type": "integer", "default": 2, "description": "Número de casas decimais no resultado"}
            },
            "required": ["expression"]
        }
    },
    {
        "name": "get_product_cost_config",
        "description": "Obtém configuração de custos de um produto, incluindo custo do produto, impostos e percentual de marketing (placeholder)",
        "handler": "get_product_cost_config",
        "schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer"},
                "internal_product_id": {"type": "integer"}
            }
        }
    },
    {
        "name": "get_fee_preview_db",
        "description": "Obtém preview de taxas do Mercado Livre para um preço específico, estimando comissões e taxas (placeholder)",
        "handler": "get_fee_preview_db",
        "schema": {
            "type": "object",
            "properties": {
                "price": {"type": "number", "description": "Preço do produto"},
                "category_id": {"type": "string"},
                "listing_type_id": {"type": "string"}
            },
            "required": ["price"]
        }
    },
    {
        "name": "get_required_attributes_db",
        "description": "Obtém lista de atributos obrigatórios e recomendados para uma categoria do Mercado Livre (placeholder)",
        "handler": "get_required_attributes_db",
        "schema": {
            "type": "object",
            "properties": {
                "category_id": {"type": "string", "description": "ID da categoria ML"}
            },
            "required": ["category_id"]
        }
    },
    {
        "name": "check_title_description_db",
        "description": "Valida o título e descrição do produto, verificando se atendem aos critérios de qualidade",
        "handler": "check_title_description_db",
        "schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer", "description": "ID interno do produto no sistema"},
                "max_title_length": {"type": "integer", "default": 60, "description": "Tamanho máximo permitido para o título"}
            },
            "required": ["product_id"]
        }
    }
]


def run(db=None):
    """Registra todas as ferramentas no banco de dados"""
    try:
        if db is None:
            db = next(get_db())
        
        # Primeiro, remover/desativar ferramentas antigas
        try:
            import importlib.util
            import os
            cleanup_path = os.path.join(
                os.path.dirname(__file__),
                '2025_11_23_remove_deprecated_tools.py'
            )
            if os.path.exists(cleanup_path):
                spec_cleanup = importlib.util.spec_from_file_location("remove_deprecated_tools", cleanup_path)
                cleanup_module = importlib.util.module_from_spec(spec_cleanup)
                spec_cleanup.loader.exec_module(cleanup_module)
                cleanup_module.run(db)
                logger.info("✅ Ferramentas antigas removidas/desativadas")
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível remover ferramentas antigas: {e}")
        
        logger.info(f"📋 Registrando {len(ALL_TOOLS)} ferramentas do agente IA...")
        
        # Upsert tools and handlers
        for t in ALL_TOOLS:
            try:
                tool_row = db.execute(
                    text(
                        """
                        INSERT INTO openai_tools (name, description, json_schema, is_active)
                        VALUES (:name, :description, CAST(:schema AS JSONB), TRUE)
                        ON CONFLICT (name) DO UPDATE SET 
                            description=EXCLUDED.description, 
                            json_schema=EXCLUDED.json_schema, 
                            is_active=TRUE
                        RETURNING id
                        """
                    ), {
                        "name": t["name"], 
                        "description": t["description"], 
                        "schema": json.dumps(t["schema"])
                    }
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
                    ), {
                        "tool_id": tool_id, 
                        "handler_name": t["handler"]
                    }
                )
                
                logger.debug(f"✅ Ferramenta '{t['name']}' registrada (ID: {tool_id})")
                
            except Exception as e:
                logger.error(f"❌ Erro ao registrar ferramenta '{t.get('name', 'unknown')}': {e}", exc_info=True)
                # Continuar com as outras ferramentas mesmo se uma falhar
                continue
        
        # Associar todas as ferramentas ativas ao agente 'Analise produto' se existir
        try:
            agent = db.execute(
                text("SELECT id FROM openai_assistants WHERE LOWER(name) LIKE LOWER('%analise%produto%') OR LOWER(name) LIKE LOWER('%chat%') LIMIT 1")
            ).fetchone()
            
            if agent:
                agent_id = agent[0]
                tool_ids = db.execute(
                    text("SELECT id FROM openai_tools WHERE is_active=TRUE")
                ).fetchall()
                
                for (tid,) in tool_ids:
                    db.execute(
                        text(
                            """
                            INSERT INTO openai_agent_tools (agent_id, tool_id, config)
                            VALUES (:agent_id, :tool_id, NULL)
                            ON CONFLICT (agent_id, tool_id) DO NOTHING
                            """
                        ), {
                            "agent_id": agent_id, 
                            "tool_id": tid
                        }
                    )
                
                logger.info(f"✅ {len(tool_ids)} ferramentas associadas ao agente ID {agent_id}")
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível associar ferramentas ao agente: {e}")
        
        db.commit()
        logger.info(f"✅ {len(ALL_TOOLS)} ferramentas do agente IA registradas com sucesso")
        return {"success": True, "tools_registered": len(ALL_TOOLS)}
        
    except Exception as e:
        logger.error(f"❌ Erro ao registrar ferramentas: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return {"success": False, "error": str(e)}

