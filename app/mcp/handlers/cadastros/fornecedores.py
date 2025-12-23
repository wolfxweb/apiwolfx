"""
Handlers MCP para fornecedores
"""
from typing import Dict, Any
from app.mcp.handlers import register_tool


async def list_fornecedores(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Lista fornecedores"""
    session_token = args.get("session_token")
    if not session_token:
        raise ValueError("session_token is required")
    
    params = {}
    if args.get("ativo") is not None:
        params["ativo"] = args["ativo"]
    
    result = await api_client.get("/api/fornecedores", session_token, params)
    return result


async def get_fornecedor(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Obtém detalhes de um fornecedor"""
    session_token = args.get("session_token")
    fornecedor_id = args.get("fornecedor_id")
    
    if not session_token:
        raise ValueError("session_token is required")
    if not fornecedor_id:
        raise ValueError("fornecedor_id is required")
    
    result = await api_client.get(f"/api/fornecedores/{fornecedor_id}", session_token)
    return result


async def create_fornecedor(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Cria novo fornecedor"""
    session_token = args.get("session_token")
    if not session_token:
        raise ValueError("session_token is required")
    
    fornecedor_data = {
        "nome": args.get("nome"),
        "nome_fantasia": args.get("nome_fantasia"),
        "cnpj": args.get("cnpj"),
        "email": args.get("email"),
        "telefone": args.get("telefone"),
        "endereco": args.get("endereco"),
        "ativo": args.get("ativo", True)
    }
    
    # Remover None values
    fornecedor_data = {k: v for k, v in fornecedor_data.items() if v is not None}
    
    result = await api_client.post("/api/fornecedores", session_token, json_data=fornecedor_data)
    return result


async def update_fornecedor(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Atualiza fornecedor"""
    session_token = args.get("session_token")
    fornecedor_id = args.get("fornecedor_id")
    
    if not session_token:
        raise ValueError("session_token is required")
    if not fornecedor_id:
        raise ValueError("fornecedor_id is required")
    
    update_data = {}
    for key in ["nome", "nome_fantasia", "cnpj", "email", "telefone", "endereco", "ativo"]:
        if key in args:
            update_data[key] = args[key]
    
    result = await api_client.put(f"/api/fornecedores/{fornecedor_id}", session_token, json_data=update_data)
    return result


async def delete_fornecedor(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Remove fornecedor"""
    session_token = args.get("session_token")
    fornecedor_id = args.get("fornecedor_id")
    
    if not session_token:
        raise ValueError("session_token is required")
    if not fornecedor_id:
        raise ValueError("fornecedor_id is required")
    
    result = await api_client.delete(f"/api/fornecedores/{fornecedor_id}", session_token)
    return result


async def search_fornecedores(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Busca fornecedores com autocomplete"""
    session_token = args.get("session_token")
    if not session_token:
        raise ValueError("session_token is required")
    
    params = {
        "q": args.get("q", ""),
        "limit": args.get("limit", 10)
    }
    
    result = await api_client.get("/api/fornecedores/search", session_token, params)
    return result


async def toggle_fornecedor_status(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Ativa/desativa fornecedor"""
    session_token = args.get("session_token")
    fornecedor_id = args.get("fornecedor_id")
    
    if not session_token:
        raise ValueError("session_token is required")
    if not fornecedor_id:
        raise ValueError("fornecedor_id is required")
    
    result = await api_client.patch(f"/api/fornecedores/{fornecedor_id}/toggle-status", session_token)
    return result


register_tool(
    name="list_fornecedores",
    description="Lista fornecedores da empresa, com filtro opcional por status ativo/inativo",
    handler=list_fornecedores,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "ativo": {"type": "boolean", "description": "Filtrar por status ativo (true/false)"}
        },
        "required": ["session_token"]
    }
)

register_tool(
    name="get_fornecedor",
    description="Obtém detalhes de um fornecedor específico por ID",
    handler=get_fornecedor,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "fornecedor_id": {"type": "integer", "description": "ID do fornecedor"}
        },
        "required": ["session_token", "fornecedor_id"]
    }
)

register_tool(
    name="create_fornecedor",
    description="Cria um novo fornecedor na empresa",
    handler=create_fornecedor,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "nome": {"type": "string", "description": "Nome completo do fornecedor"},
            "nome_fantasia": {"type": "string", "description": "Nome fantasia"},
            "cnpj": {"type": "string", "description": "CNPJ do fornecedor"},
            "email": {"type": "string", "description": "Email de contato"},
            "telefone": {"type": "string", "description": "Telefone de contato"},
            "endereco": {"type": "string", "description": "Endereço completo"},
            "ativo": {"type": "boolean", "description": "Status ativo (padrão: true)"}
        },
        "required": ["session_token", "nome"]
    }
)

register_tool(
    name="update_fornecedor",
    description="Atualiza dados de um fornecedor existente",
    handler=update_fornecedor,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "fornecedor_id": {"type": "integer", "description": "ID do fornecedor a atualizar"},
            "nome": {"type": "string", "description": "Nome completo do fornecedor"},
            "nome_fantasia": {"type": "string", "description": "Nome fantasia"},
            "email": {"type": "string", "description": "Email de contato"},
            "telefone": {"type": "string", "description": "Telefone de contato"},
            "ativo": {"type": "boolean", "description": "Status ativo"}
        },
        "required": ["session_token", "fornecedor_id"]
    }
)

register_tool(
    name="delete_fornecedor",
    description="Remove um fornecedor",
    handler=delete_fornecedor,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "fornecedor_id": {"type": "integer", "description": "ID do fornecedor a remover"}
        },
        "required": ["session_token", "fornecedor_id"]
    }
)

register_tool(
    name="search_fornecedores",
    description="Busca fornecedores por nome ou nome fantasia (autocomplete)",
    handler=search_fornecedores,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "q": {"type": "string", "description": "Termo de busca"},
            "limit": {"type": "integer", "description": "Limite de resultados", "default": 10}
        },
        "required": ["session_token"]
    }
)

register_tool(
    name="toggle_fornecedor_status",
    description="Alterna status ativo/inativo de um fornecedor",
    handler=toggle_fornecedor_status,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "fornecedor_id": {"type": "integer", "description": "ID do fornecedor"}
        },
        "required": ["session_token", "fornecedor_id"]
    }
)


