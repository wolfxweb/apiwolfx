"""
Handlers MCP para ordens de compra
"""
from typing import Dict, Any
from app.mcp.handlers import register_tool


async def list_ordem_compra(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Lista ordens de compra"""
    session_token = args.get("session_token")
    if not session_token:
        raise ValueError("session_token is required")
    
    params = {}
    if args.get("status"):
        params["status"] = args["status"]
    if args.get("search"):
        params["search"] = args["search"]
    if args.get("date_from"):
        params["date_from"] = args["date_from"]
    if args.get("date_to"):
        params["date_to"] = args["date_to"]
    
    result = await api_client.get("/api/ordem-compra", session_token, params)
    return result


async def get_ordem_compra(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Obtém detalhes de uma ordem de compra"""
    session_token = args.get("session_token")
    ordem_id = args.get("ordem_id")
    
    if not session_token:
        raise ValueError("session_token is required")
    if not ordem_id:
        raise ValueError("ordem_id is required")
    
    result = await api_client.get(f"/api/ordem-compra/{ordem_id}", session_token)
    return result


async def create_ordem_compra(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Cria nova ordem de compra"""
    session_token = args.get("session_token")
    if not session_token:
        raise ValueError("session_token is required")
    
    ordem_data = {
        "numero_ordem": args.get("numero_ordem"),
        "fornecedor_id": args.get("fornecedor_id"),
        "data_ordem": args.get("data_ordem"),
        "data_entrega_prevista": args.get("data_entrega_prevista"),
        "status": args.get("status", "pendente"),
        "itens": args.get("itens", []),
        "valor_total": args.get("valor_total"),
        "desconto": args.get("desconto"),
        "observacoes": args.get("observacoes")
    }
    
    # Remover None values
    ordem_data = {k: v for k, v in ordem_data.items() if v is not None}
    
    result = await api_client.post("/api/ordem-compra", session_token, json_data=ordem_data)
    return result


async def update_ordem_compra(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Atualiza ordem de compra"""
    session_token = args.get("session_token")
    ordem_id = args.get("ordem_id")
    
    if not session_token:
        raise ValueError("session_token is required")
    if not ordem_id:
        raise ValueError("ordem_id is required")
    
    update_data = {}
    for key in ["numero_ordem", "fornecedor_id", "data_entrega_prevista", "status", 
                "itens", "valor_total", "desconto", "observacoes"]:
        if key in args:
            update_data[key] = args[key]
    
    result = await api_client.put(f"/api/ordem-compra/{ordem_id}", session_token, json_data=update_data)
    return result


async def delete_ordem_compra(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Remove ordem de compra"""
    session_token = args.get("session_token")
    ordem_id = args.get("ordem_id")
    
    if not session_token:
        raise ValueError("session_token is required")
    if not ordem_id:
        raise ValueError("ordem_id is required")
    
    result = await api_client.delete(f"/api/ordem-compra/{ordem_id}", session_token)
    return result


async def receive_ordem_compra(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Registra recebimento de ordem de compra"""
    session_token = args.get("session_token")
    ordem_id = args.get("ordem_id")
    
    if not session_token:
        raise ValueError("session_token is required")
    if not ordem_id:
        raise ValueError("ordem_id is required")
    
    receive_data = {
        "data_recebimento": args.get("data_recebimento"),
        "itens_recebidos": args.get("itens_recebidos", [])
    }
    
    result = await api_client.post(f"/api/ordem-compra/{ordem_id}/receive", session_token, json_data=receive_data)
    return result


register_tool(
    name="list_ordem_compra",
    description="Lista ordens de compra da empresa com filtros opcionais",
    handler=list_ordem_compra,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "status": {"type": "string", "description": "Filtrar por status"},
            "search": {"type": "string", "description": "Buscar por texto"},
            "date_from": {"type": "string", "description": "Data inicial (YYYY-MM-DD)"},
            "date_to": {"type": "string", "description": "Data final (YYYY-MM-DD)"}
        },
        "required": ["session_token"]
    }
)

register_tool(
    name="get_ordem_compra",
    description="Obtém detalhes de uma ordem de compra específica por ID",
    handler=get_ordem_compra,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "ordem_id": {"type": "integer", "description": "ID da ordem de compra"}
        },
        "required": ["session_token", "ordem_id"]
    }
)

register_tool(
    name="create_ordem_compra",
    description="Cria uma nova ordem de compra",
    handler=create_ordem_compra,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "numero_ordem": {"type": "string", "description": "Número da ordem"},
            "fornecedor_id": {"type": "integer", "description": "ID do fornecedor"},
            "data_ordem": {"type": "string", "description": "Data da ordem (YYYY-MM-DD)"},
            "data_entrega_prevista": {"type": "string", "description": "Data prevista de entrega (YYYY-MM-DD)"},
            "status": {"type": "string", "description": "Status da ordem"},
            "itens": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Lista de itens da ordem"
            },
            "valor_total": {"type": "number", "description": "Valor total da ordem"},
            "desconto": {"type": "number", "description": "Desconto aplicado"},
            "observacoes": {"type": "string", "description": "Observações"}
        },
        "required": ["session_token", "fornecedor_id"]
    }
)

register_tool(
    name="update_ordem_compra",
    description="Atualiza uma ordem de compra existente",
    handler=update_ordem_compra,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "ordem_id": {"type": "integer", "description": "ID da ordem a atualizar"},
            "status": {"type": "string", "description": "Novo status"},
            "data_entrega_prevista": {"type": "string", "description": "Nova data prevista"},
            "itens": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Itens atualizados"
            }
        },
        "required": ["session_token", "ordem_id"]
    }
)

register_tool(
    name="delete_ordem_compra",
    description="Remove uma ordem de compra",
    handler=delete_ordem_compra,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "ordem_id": {"type": "integer", "description": "ID da ordem a remover"}
        },
        "required": ["session_token", "ordem_id"]
    }
)

register_tool(
    name="receive_ordem_compra",
    description="Registra recebimento de uma ordem de compra",
    handler=receive_ordem_compra,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "ordem_id": {"type": "integer", "description": "ID da ordem recebida"},
            "data_recebimento": {"type": "string", "description": "Data do recebimento (YYYY-MM-DD)"},
            "itens_recebidos": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Itens recebidos"
            }
        },
        "required": ["session_token", "ordem_id"]
    }
)


