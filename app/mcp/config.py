"""
Configurações do servidor MCP
"""
import os
from typing import Optional
from app.config.settings import settings


class MCPConfig:
    """Configurações para o servidor MCP"""
    
    # URL base da API interna
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")
    
    # Nome do servidor MCP
    SERVER_NAME: str = "selvez-api"
    
    # Versão do servidor
    SERVER_VERSION: str = "1.0.0"
    
    # Timeout para requisições HTTP (em segundos)
    HTTP_TIMEOUT: int = int(os.getenv("MCP_HTTP_TIMEOUT", "30"))
    
    # Número máximo de retries para requisições HTTP
    HTTP_MAX_RETRIES: int = int(os.getenv("MCP_HTTP_MAX_RETRIES", "3"))
    
    # Habilitar logging detalhado
    ENABLE_VERBOSE_LOGGING: bool = os.getenv("MCP_VERBOSE_LOGGING", "false").lower() == "true"


# Instância global de configuração
mcp_config = MCPConfig()


