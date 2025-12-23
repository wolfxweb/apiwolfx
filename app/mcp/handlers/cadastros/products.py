"""
Handlers MCP para produtos internos
"""
from typing import Dict, Any
from app.mcp.handlers import register_tool

# Este módulo será importado automaticamente para registrar as ferramentas


async def list_internal_products(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Lista produtos internos"""
    session_token = args.get("session_token")
    if not session_token:
        raise ValueError("session_token is required")
    
    params = {
        "limit": args.get("limit", 20),
        "offset": args.get("offset", 0),
    }
    
    if args.get("status"):
        params["status"] = args["status"]
    if args.get("category"):
        params["category"] = args["category"]
    if args.get("search"):
        params["search"] = args["search"]
    
    result = await api_client.get("/api/internal-products/list", session_token, params)
    return result


async def get_internal_product(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Obtém detalhes de um produto interno"""
    session_token = args.get("session_token")
    product_id = args.get("product_id")
    
    if not session_token:
        raise ValueError("session_token is required")
    if not product_id:
        raise ValueError("product_id is required")
    
    params = {"session_token": session_token}
    result = await api_client.get(f"/api/internal-products/{product_id}", session_token, params)
    return result


async def create_internal_product(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Cria novo produto interno"""
    session_token = args.get("session_token")
    if not session_token:
        raise ValueError("session_token is required")
    
    # Construir dados do produto
    product_data = {
        "name": args.get("name"),
        "internal_sku": args.get("internal_sku"),
        "description": args.get("description"),
        "cost_price": args.get("cost_price"),
        "selling_price": args.get("selling_price"),
        "category": args.get("category"),
        "brand": args.get("brand"),
        "supplier": args.get("supplier"),
        "barcode": args.get("barcode"),
        "tax_rate": args.get("tax_rate"),
        "marketing_cost": args.get("marketing_cost"),
        "other_costs": args.get("other_costs"),
        "min_stock": args.get("min_stock"),
        "current_stock": args.get("current_stock"),
        "notes": args.get("notes"),
    }
    
    # Remover None values
    product_data = {k: v for k, v in product_data.items() if v is not None}
    
    params = {"session_token": session_token}
    result = await api_client.post("/api/internal-products/", session_token, json_data=product_data, params=params)
    return result


async def update_internal_product(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Atualiza produto interno"""
    session_token = args.get("session_token")
    product_id = args.get("product_id")
    
    if not session_token:
        raise ValueError("session_token is required")
    if not product_id:
        raise ValueError("product_id is required")
    
    # Dados de atualização
    update_data = {}
    for key in ["name", "description", "cost_price", "selling_price", "category", "brand", 
                "supplier", "barcode", "tax_rate", "marketing_cost", "other_costs", 
                "min_stock", "current_stock", "notes", "status"]:
        if key in args:
            update_data[key] = args[key]
    
    result = await api_client.put(f"/api/internal-products/{product_id}", session_token, json_data=update_data)
    return result


async def delete_internal_product(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Remove produto interno"""
    session_token = args.get("session_token")
    product_id = args.get("product_id")
    
    if not session_token:
        raise ValueError("session_token is required")
    if not product_id:
        raise ValueError("product_id is required")
    
    params = {"session_token": session_token}
    result = await api_client.delete(f"/api/internal-products/{product_id}", session_token, params)
    return result


# Registrar ferramentas
register_tool(
    name="list_internal_products",
    description="Lista produtos internos da empresa com filtros opcionais (status, categoria, busca)",
    handler=list_internal_products,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "status": {"type": "string", "description": "Filtrar por status (active, inactive, discontinued)"},
            "category": {"type": "string", "description": "Filtrar por categoria"},
            "search": {"type": "string", "description": "Buscar por nome, SKU ou descrição"},
            "limit": {"type": "integer", "description": "Limite de resultados", "default": 20},
            "offset": {"type": "integer", "description": "Offset para paginação", "default": 0}
        },
        "required": ["session_token"]
    }
)

register_tool(
    name="get_internal_product",
    description="Obtém detalhes de um produto interno específico por ID",
    handler=get_internal_product,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "product_id": {"type": "integer", "description": "ID do produto interno"}
        },
        "required": ["session_token", "product_id"]
    }
)

register_tool(
    name="create_internal_product",
    description="Cria um novo produto interno na empresa",
    handler=create_internal_product,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "name": {"type": "string", "description": "Nome do produto"},
            "internal_sku": {"type": "string", "description": "SKU interno único"},
            "description": {"type": "string", "description": "Descrição do produto"},
            "cost_price": {"type": "number", "description": "Preço de custo"},
            "selling_price": {"type": "number", "description": "Preço de venda"},
            "category": {"type": "string", "description": "Categoria"},
            "brand": {"type": "string", "description": "Marca"},
            "supplier": {"type": "string", "description": "Fornecedor"},
            "barcode": {"type": "string", "description": "Código de barras"},
            "tax_rate": {"type": "number", "description": "Taxa de imposto (%)"},
            "marketing_cost": {"type": "number", "description": "Custo de marketing"},
            "other_costs": {"type": "number", "description": "Outros custos"},
            "min_stock": {"type": "integer", "description": "Estoque mínimo"},
            "current_stock": {"type": "integer", "description": "Estoque atual"},
            "notes": {"type": "string", "description": "Observações"}
        },
        "required": ["session_token", "name", "internal_sku"]
    }
)

register_tool(
    name="update_internal_product",
    description="Atualiza um produto interno existente",
    handler=update_internal_product,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "product_id": {"type": "integer", "description": "ID do produto a atualizar"},
            "name": {"type": "string", "description": "Nome do produto"},
            "description": {"type": "string", "description": "Descrição do produto"},
            "cost_price": {"type": "number", "description": "Preço de custo"},
            "selling_price": {"type": "number", "description": "Preço de venda"},
            "category": {"type": "string", "description": "Categoria"},
            "brand": {"type": "string", "description": "Marca"},
            "status": {"type": "string", "description": "Status (active, inactive, discontinued)"}
        },
        "required": ["session_token", "product_id"]
    }
)

register_tool(
    name="delete_internal_product",
    description="Remove um produto interno",
    handler=delete_internal_product,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "product_id": {"type": "integer", "description": "ID do produto a remover"}
        },
        "required": ["session_token", "product_id"]
    }
)


async def bulk_update_internal_products(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Atualização em massa de produtos internos"""
    session_token = args.get("session_token")
    if not session_token:
        raise ValueError("session_token is required")
    
    update_data = {}
    if "cost_price" in args:
        update_data["cost_price"] = args["cost_price"]
    if "tax_rate" in args:
        update_data["tax_rate"] = args["tax_rate"]
    if "marketing_cost" in args:
        update_data["marketing_cost"] = args["marketing_cost"]
    if "other_costs" in args:
        update_data["other_costs"] = args["other_costs"]
    
    result = await api_client.post("/api/internal-products/bulk-update", session_token, json_data=update_data)
    return result


async def bulk_delete_internal_products(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Exclusão em massa de produtos internos"""
    session_token = args.get("session_token")
    product_ids = args.get("product_ids")
    
    if not session_token:
        raise ValueError("session_token is required")
    if not product_ids or not isinstance(product_ids, list):
        raise ValueError("product_ids must be a list of integers")
    
    delete_data = {"product_ids": product_ids}
    result = await api_client.post("/api/internal-products/bulk-delete", session_token, json_data=delete_data)
    return result


async def get_product_announcements(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Obtém anúncios ML associados a um produto interno"""
    session_token = args.get("session_token")
    product_id = args.get("product_id")
    
    if not session_token:
        raise ValueError("session_token is required")
    if not product_id:
        raise ValueError("product_id is required")
    
    result = await api_client.get(f"/api/internal-products/{product_id}/announcements", session_token)
    return result


register_tool(
    name="bulk_update_internal_products",
    description="Atualiza valores em massa em todos os produtos internos (cost_price, tax_rate, marketing_cost, other_costs)",
    handler=bulk_update_internal_products,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "cost_price": {"type": "number", "description": "Novo preço de custo para aplicar"},
            "tax_rate": {"type": "number", "description": "Nova taxa de imposto (%) para aplicar"},
            "marketing_cost": {"type": "number", "description": "Novo custo de marketing para aplicar"},
            "other_costs": {"type": "number", "description": "Novos outros custos para aplicar"}
        },
        "required": ["session_token"]
    }
)

register_tool(
    name="bulk_delete_internal_products",
    description="Exclui múltiplos produtos internos de uma vez",
    handler=bulk_delete_internal_products,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "product_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Lista de IDs dos produtos a excluir"
            }
        },
        "required": ["session_token", "product_ids"]
    }
)

register_tool(
    name="get_product_announcements",
    description="Obtém anúncios do Mercado Livre associados a um produto interno",
    handler=get_product_announcements,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "product_id": {"type": "integer", "description": "ID do produto interno"}
        },
        "required": ["session_token", "product_id"]
    }
)

