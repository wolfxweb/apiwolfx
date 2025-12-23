"""
Servidor MCP principal
Implementa o protocolo Model Context Protocol (MCP) via stdio
"""
import sys
import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from app.mcp.config import mcp_config
from app.mcp.tools import get_tool_definitions
from app.mcp.handlers import get_tool_handler
from app.mcp.api_client import APIClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # Logs vão para stderr para não interferir no stdio
)
logger = logging.getLogger(__name__)


class MCPServer:
    """Servidor MCP que expõe ferramentas da API SELVEZ"""
    
    def __init__(self):
        self.api_client = APIClient()
        self.tools = get_tool_definitions()
        logger.info(f"MCP Server initialized with {len(self.tools)} tools")
    
    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Processa uma requisição MCP
        
        Args:
            request: Requisição JSON-RPC
            
        Returns:
            Resposta JSON-RPC ou None se não houver resposta
        """
        try:
            method = request.get("method")
            request_id = request.get("id")
            params = request.get("params", {})
            
            if method == "initialize":
                return self._handle_initialize(request_id, params)
            elif method == "tools/list":
                return self._handle_list_tools(request_id)
            elif method == "tools/call":
                return await self._handle_call_tool(request_id, params)
            elif method == "ping":
                return {"jsonrpc": "2.0", "id": request_id, "result": {}}
            else:
                logger.warning(f"Unknown method: {method}")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    def _handle_initialize(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler para initialize"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": mcp_config.SERVER_NAME,
                    "version": mcp_config.SERVER_VERSION
                }
            }
        }
    
    def _handle_list_tools(self, request_id: Any) -> Dict[str, Any]:
        """Handler para listar ferramentas"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": self.tools
            }
        }
    
    async def _handle_call_tool(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler para chamar uma ferramenta"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": "Missing required parameter: name"
                }
            }
        
        try:
            # Obter handler da ferramenta
            handler = get_tool_handler(tool_name)
            
            # Executar handler
            result = await handler(self.api_client, arguments)
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2, ensure_ascii=False)
                        }
                    ]
                }
            }
        except ValueError as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": str(e)
                }
            }
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Error executing tool: {str(e)}"
                }
            }
    
    async def run(self):
        """Executa o servidor MCP lendo de stdin e escrevendo em stdout"""
        logger.info("MCP Server starting (stdio mode)")
        
        try:
            # Ler linha por linha do stdin (bloqueante, mas OK para MCP)
            loop = asyncio.get_event_loop()
            
            while True:
                # Ler linha do stdin de forma assíncrona
                def read_stdin():
                    try:
                        return sys.stdin.readline()
                    except Exception:
                        return None
                
                line = await loop.run_in_executor(None, read_stdin)
                
                if not line:
                    # EOF - encerrar servidor
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # Parsear requisição JSON
                    request = json.loads(line)
                    
                    # Processar requisição
                    response = await self.handle_request(request)
                    
                    # Enviar resposta
                    if response:
                        print(json.dumps(response), flush=True)
                
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {line}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": f"Parse error: {str(e)}"
                        }
                    }
                    print(json.dumps(error_response), flush=True)
                
        except KeyboardInterrupt:
            logger.info("MCP Server stopped by user")
        except Exception as e:
            logger.error(f"MCP Server error: {e}", exc_info=True)


async def main():
    """Função principal para executar o servidor"""
    server = MCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())

