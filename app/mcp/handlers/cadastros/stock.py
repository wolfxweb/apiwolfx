"""
Handlers MCP para estoque
"""
from typing import Dict, Any
from app.mcp.handlers import register_tool


async def get_stock(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Consulta estoque de produtos"""
    session_token = args.get("session_token")
    if not session_token:
        raise ValueError("session_token is required")
    
    params = {}
    if args.get("warehouse_id"):
        params["warehouse_id"] = args["warehouse_id"]
    if args.get("internal_product_id"):
        params["internal_product_id"] = args["internal_product_id"]
    
    result = await api_client.get("/api/stock/stocks", session_token, params)
    return result


async def update_stock(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Atualiza quantidade em estoque"""
    session_token = args.get("session_token")
    product_stock_id = args.get("product_stock_id")
    quantity = args.get("quantity")
    
    if not session_token:
        raise ValueError("session_token is required")
    if not product_stock_id:
        raise ValueError("product_stock_id is required")
    if quantity is None:
        raise ValueError("quantity is required")
    
    stock_data = {"quantity": quantity}
    result = await api_client.put(f"/api/stock/stocks/{product_stock_id}/quantity", session_token, json_data=stock_data)
    return result


async def get_stock_projections(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Obtém projeções de estoque"""
    session_token = args.get("session_token")
    if not session_token:
        raise ValueError("session_token is required")
    
    params = {}
    if args.get("internal_product_id"):
        params["internal_product_id"] = args["internal_product_id"]
    if args.get("warehouse_id"):
        params["warehouse_id"] = args["warehouse_id"]
    
    result = await api_client.get("/api/stock/projections", session_token, params)
    return result


async def get_reorder_recommendations(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Obtém recomendações de reposição de estoque"""
    session_token = args.get("session_token")
    if not session_token:
        raise ValueError("session_token is required")
    
    params = {}
    if args.get("warehouse_id"):
        params["warehouse_id"] = args["warehouse_id"]
    if args.get("limit"):
        params["limit"] = args["limit"]
    
    result = await api_client.get("/api/stock/projections/reorder-recommendations", session_token, params)
    return result


register_tool(
    name="get_stock",
    description="Consulta estoque de produtos, com filtros opcionais por depósito e produto",
    handler=get_stock,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "warehouse_id": {"type": "integer", "description": "ID do depósito para filtrar"},
            "internal_product_id": {"type": "integer", "description": "ID do produto interno para filtrar"}
        },
        "required": ["session_token"]
    }
)

register_tool(
    name="update_stock",
    description="Atualiza quantidade de estoque usando o ID do stock",
    handler=update_stock,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "product_stock_id": {"type": "integer", "description": "ID do registro de estoque (product_stock_id)"},
            "quantity": {"type": "integer", "description": "Nova quantidade em estoque"}
        },
        "required": ["session_token", "product_stock_id", "quantity"]
    }
)

register_tool(
    name="get_stock_projections",
    description="Obtém projeções de estoque futuro baseado em histórico de vendas",
    handler=get_stock_projections,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "internal_product_id": {"type": "integer", "description": "ID do produto interno para filtrar"},
            "warehouse_id": {"type": "integer", "description": "ID do depósito para filtrar"}
        },
        "required": ["session_token"]
    }
)

register_tool(
    name="get_reorder_recommendations",
    description="Obtém recomendações de produtos que precisam ser recomprados",
    handler=get_reorder_recommendations,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "warehouse_id": {"type": "integer", "description": "ID do depósito para filtrar"},
            "limit": {"type": "integer", "description": "Limite de resultados", "default": 50}
        },
        "required": ["session_token"]
    }
)

