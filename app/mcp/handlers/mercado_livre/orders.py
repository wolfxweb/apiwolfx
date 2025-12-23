"""
Handlers MCP para pedidos do Mercado Livre
"""
from typing import Dict, Any
from app.mcp.handlers import register_tool


async def list_ml_orders(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Lista pedidos do Mercado Livre"""
    session_token = args.get("session_token")
    if not session_token:
        raise ValueError("session_token is required")
    
    params = {
        "limit": args.get("limit", 50),
        "offset": args.get("offset", 0),
    }
    
    if args.get("ml_account_id"):
        params["ml_account_id"] = args["ml_account_id"]
    if args.get("shipping_status_filter"):
        params["shipping_status_filter"] = args["shipping_status_filter"]
    if args.get("internal_status_filter"):
        params["internal_status_filter"] = args["internal_status_filter"]
    if args.get("date_from"):
        params["date_from"] = args["date_from"]
    if args.get("date_to"):
        params["date_to"] = args["date_to"]
    if args.get("search_query"):
        params["search_query"] = args["search_query"]
    
    result = await api_client.get("/ml/api/orders", session_token, params)
    return result


async def get_ml_order(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Obtém detalhes de um pedido ML"""
    session_token = args.get("session_token")
    order_id = args.get("order_id")
    
    if not session_token:
        raise ValueError("session_token is required")
    if not order_id:
        raise ValueError("order_id is required")
    
    result = await api_client.get(f"/ml/api/orders/{order_id}", session_token)
    return result


async def update_order_internal_status(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Atualiza status interno de um pedido"""
    session_token = args.get("session_token")
    order_id = args.get("order_id")
    internal_status = args.get("internal_status")
    
    if not session_token:
        raise ValueError("session_token is required")
    if not order_id:
        raise ValueError("order_id is required")
    if not internal_status:
        raise ValueError("internal_status is required")
    
    status_data = {"internal_status": internal_status}
    result = await api_client.post(f"/ml/api/orders/{order_id}/internal-status", session_token, json_data=status_data)
    return result


async def sync_ml_orders(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Sincroniza pedidos do Mercado Livre"""
    session_token = args.get("session_token")
    if not session_token:
        raise ValueError("session_token is required")
    
    params = {}
    if args.get("ml_account_id"):
        params["ml_account_id"] = args["ml_account_id"]
    
    result = await api_client.get("/ml/api/orders/sync", session_token, params)
    return result


register_tool(
    name="list_ml_orders",
    description="Lista pedidos do Mercado Livre com filtros opcionais",
    handler=list_ml_orders,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "ml_account_id": {"type": "integer", "description": "ID da conta ML para filtrar"},
            "shipping_status_filter": {"type": "string", "description": "Filtrar por status de envio"},
            "internal_status_filter": {"type": "string", "description": "Filtrar por status interno"},
            "date_from": {"type": "string", "description": "Data inicial (YYYY-MM-DD)"},
            "date_to": {"type": "string", "description": "Data final (YYYY-MM-DD)"},
            "search_query": {"type": "string", "description": "Buscar por texto"},
            "limit": {"type": "integer", "description": "Limite de resultados", "default": 50},
            "offset": {"type": "integer", "description": "Offset para paginação", "default": 0}
        },
        "required": ["session_token"]
    }
)

register_tool(
    name="get_ml_order",
    description="Obtém detalhes de um pedido específico do Mercado Livre",
    handler=get_ml_order,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "order_id": {"type": "string", "description": "ID do pedido ML"}
        },
        "required": ["session_token", "order_id"]
    }
)

register_tool(
    name="update_order_internal_status",
    description="Atualiza o status interno de um pedido (ex: separação, expedição, enviado)",
    handler=update_order_internal_status,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "order_id": {"type": "string", "description": "ID do pedido ML"},
            "internal_status": {"type": "string", "description": "Novo status interno"}
        },
        "required": ["session_token", "order_id", "internal_status"]
    }
)

register_tool(
    name="sync_ml_orders",
    description="Sincroniza pedidos do Mercado Livre (busca atualizações da API ML)",
    handler=sync_ml_orders,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "ml_account_id": {"type": "integer", "description": "ID da conta ML para sincronizar (opcional)"}
        },
        "required": ["session_token"]
    }
)


