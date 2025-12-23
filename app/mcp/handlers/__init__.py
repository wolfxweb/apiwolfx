"""
Handlers para ferramentas MCP
"""
from typing import Dict, Any, Callable
import importlib
import sys
from pathlib import Path

# Registrar todos os handlers
_handlers: Dict[str, Dict[str, Any]] = {}


def register_tool(
    name: str,
    description: str,
    handler: Callable,
    input_schema: Dict[str, Any]
):
    """Registra uma ferramenta MCP"""
    _handlers[name] = {
        "description": description,
        "handler": handler,
        "inputSchema": input_schema
    }


def get_tool_handler(name: str) -> Callable:
    """Obtém o handler de uma ferramenta"""
    if name not in _handlers:
        raise ValueError(f"Tool '{name}' not found")
    return _handlers[name]["handler"]


def get_all_tool_handlers() -> Dict[str, Dict[str, Any]]:
    """Retorna todos os handlers registrados"""
    return _handlers


# Importar todos os módulos de handlers para registro automático
def _load_handlers():
    """Carrega todos os handlers dos módulos"""
    handlers_dir = Path(__file__).parent
    
    # Importar handlers de cadastros
    try:
        from app.mcp.handlers.cadastros import products as cadastros_products
    except ImportError as e:
        pass  # Módulo ainda não criado
    
    # Importar handlers de produtos (força o registro)
    try:
        import app.mcp.handlers.cadastros.products
    except ImportError:
        pass
    
    try:
        from app.mcp.handlers.cadastros import stock as cadastros_stock
    except ImportError:
        pass
    
    try:
        from app.mcp.handlers.cadastros import fornecedores as cadastros_fornecedores
    except ImportError:
        pass
    
    try:
        from app.mcp.handlers.cadastros import ordem_compra as cadastros_ordem_compra
    except ImportError:
        pass
    
    try:
        from app.mcp.handlers.mercado_livre import products as ml_products
    except ImportError:
        pass
    
    try:
        from app.mcp.handlers.mercado_livre import orders as ml_orders
    except ImportError:
        pass


# Carregar handlers na importação
_load_handlers()

