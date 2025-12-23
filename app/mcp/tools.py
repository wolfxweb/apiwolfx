"""
Definições de ferramentas MCP disponíveis
"""
from typing import List, Dict, Any
from app.mcp.handlers import get_all_tool_handlers

# Forçar importação dos módulos de handlers para registro
import app.mcp.handlers.cadastros.products  # noqa: F401
import app.mcp.handlers.cadastros.stock  # noqa: F401
import app.mcp.handlers.cadastros.fornecedores  # noqa: F401
import app.mcp.handlers.cadastros.ordem_compra  # noqa: F401
import app.mcp.handlers.mercado_livre.products  # noqa: F401
import app.mcp.handlers.mercado_livre.orders  # noqa: F401


def get_tool_definitions() -> List[Dict[str, Any]]:
    """
    Retorna lista de definições de ferramentas disponíveis
    Cada ferramenta tem:
    - name: Nome da ferramenta
    - description: Descrição do que a ferramenta faz
    - inputSchema: JSON Schema dos parâmetros de entrada
    """
    handlers = get_all_tool_handlers()
    
    tools = []
    for handler_name, handler_info in handlers.items():
        tools.append({
            "name": handler_name,
            "description": handler_info.get("description", ""),
            "inputSchema": handler_info.get("inputSchema", {
                "type": "object",
                "properties": {
                    "session_token": {
                        "type": "string",
                        "description": "Token de sessão para autenticação"
                    }
                },
                "required": ["session_token"]
            })
        })
    
    return tools

