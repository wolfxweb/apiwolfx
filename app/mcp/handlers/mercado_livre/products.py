"""
Handlers MCP para produtos/anúncios do Mercado Livre
"""
from typing import Dict, Any
from app.mcp.handlers import register_tool


async def list_ml_products(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Lista anúncios do Mercado Livre"""
    session_token = args.get("session_token")
    if not session_token:
        raise ValueError("session_token is required")
    
    params = {
        "limit": args.get("limit", 50),
        "offset": args.get("offset", 0),
    }
    
    if args.get("status"):
        params["status"] = args["status"]
    if args.get("ml_account_id"):
        params["ml_account_id"] = args["ml_account_id"]
    if args.get("category_id"):
        params["category_id"] = args["category_id"]
    
    result = await api_client.get("/ml/products", session_token, params)
    return result


async def get_ml_product(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Obtém detalhes de um anúncio ML"""
    session_token = args.get("session_token")
    product_id = args.get("product_id")
    
    if not session_token:
        raise ValueError("session_token is required")
    if not product_id:
        raise ValueError("product_id is required")
    
    result = await api_client.get(f"/ml/products/{product_id}", session_token)
    return result


async def predict_ml_category(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Prediz categoria ML baseado no título do produto"""
    session_token = args.get("session_token")
    q = args.get("q")
    site_id = args.get("site_id", "MLB")
    
    if not session_token:
        raise ValueError("session_token is required")
    if not q:
        raise ValueError("q (título do produto) is required")
    
    params = {
        "q": q,
        "site_id": site_id,
        "limit": args.get("limit", 5)
    }
    
    result = await api_client.get("/ml/products/categories/predict", session_token, params)
    return result


async def get_ml_categories(api_client, args: Dict[str, Any]) -> Dict[str, Any]:
    """Lista categorias disponíveis no Mercado Livre"""
    session_token = args.get("session_token")
    site_id = args.get("site_id", "MLB")
    
    if not session_token:
        raise ValueError("session_token is required")
    
    params = {"site_id": site_id}
    result = await api_client.get("/ml/products/categories", session_token, params)
    return result


register_tool(
    name="list_ml_products",
    description="Lista anúncios/produtos do Mercado Livre com filtros opcionais",
    handler=list_ml_products,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "status": {"type": "string", "description": "Filtrar por status (active, paused, closed)"},
            "ml_account_id": {"type": "integer", "description": "ID da conta ML para filtrar"},
            "category_id": {"type": "string", "description": "ID da categoria para filtrar"},
            "limit": {"type": "integer", "description": "Limite de resultados", "default": 50},
            "offset": {"type": "integer", "description": "Offset para paginação", "default": 0}
        },
        "required": ["session_token"]
    }
)

register_tool(
    name="get_ml_product",
    description="Obtém detalhes de um anúncio/produto específico do Mercado Livre",
    handler=get_ml_product,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "product_id": {"type": "integer", "description": "ID do produto/anúncio ML"}
        },
        "required": ["session_token", "product_id"]
    }
)

register_tool(
    name="predict_ml_category",
    description="Prediz a categoria mais adequada no Mercado Livre baseado no título do produto",
    handler=predict_ml_category,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "q": {"type": "string", "description": "Título do produto para predição"},
            "site_id": {"type": "string", "description": "ID do site (MLB, MLA, etc)", "default": "MLB"},
            "limit": {"type": "integer", "description": "Número máximo de sugestões", "default": 5}
        },
        "required": ["session_token", "q"]
    }
)

register_tool(
    name="get_ml_categories",
    description="Lista categorias disponíveis no Mercado Livre",
    handler=get_ml_categories,
    input_schema={
        "type": "object",
        "properties": {
            "session_token": {"type": "string", "description": "Token de sessão para autenticação"},
            "site_id": {"type": "string", "description": "ID do site (MLB, MLA, etc)", "default": "MLB"}
        },
        "required": ["session_token"]
    }
)


