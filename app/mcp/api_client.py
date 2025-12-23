"""
Cliente HTTP para fazer requisições aos endpoints da API interna
"""
import httpx
import json
import logging
from typing import Dict, Any, Optional
from app.mcp.config import mcp_config

logger = logging.getLogger(__name__)


class APIClient:
    """Cliente HTTP para fazer requisições aos endpoints da API"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or mcp_config.API_BASE_URL
        self.timeout = mcp_config.HTTP_TIMEOUT
        self.max_retries = mcp_config.HTTP_MAX_RETRIES
    
    async def request(
        self,
        method: str,
        endpoint: str,
        session_token: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Faz uma requisição HTTP para o endpoint da API
        
        Args:
            method: Método HTTP (GET, POST, PUT, DELETE, etc)
            endpoint: Endpoint relativo (ex: '/api/internal-products/list')
            session_token: Token de sessão para autenticação
            params: Parâmetros de query string
            json_data: Dados JSON para o body (para POST/PUT)
            headers: Headers adicionais
            
        Returns:
            Dict com a resposta da API
            
        Raises:
            Exception: Se a requisição falhar
        """
        url = f"{self.base_url}{endpoint}"
        
        # Headers padrão
        request_headers = {
            "Content-Type": "application/json",
        }
        
        # Adicionar session_token como Cookie para POST/PUT/PATCH (padrão da API)
        if session_token and method.upper() in ["POST", "PUT", "PATCH"]:
            request_headers["Cookie"] = f"session_token={session_token}"
        
        if headers:
            request_headers.update(headers)
        
        # Adicionar session_token como query param também (para compatibilidade)
        # Alguns endpoints esperam como query param, outros como cookie
        if session_token:
            if params is None:
                params = {}
            if "session_token" not in params:
                params["session_token"] = session_token
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Fazer requisição com retry
                last_error = None
                for attempt in range(self.max_retries):
                    try:
                        if mcp_config.ENABLE_VERBOSE_LOGGING:
                            logger.debug(f"MCP API Request: {method} {url} (attempt {attempt + 1})")
                        
                        response = await client.request(
                            method=method,
                            url=url,
                            params=params,
                            json=json_data if json_data else None,
                            headers=request_headers,
                            follow_redirects=True
                        )
                        
                        # Tentar parsear JSON
                        try:
                            result = response.json()
                        except json.JSONDecodeError:
                            result = {"text": response.text, "status_code": response.status_code}
                        
                        # Verificar status code
                        if response.status_code >= 400:
                            error_msg = result.get("error", result.get("detail", f"HTTP {response.status_code}"))
                            logger.error(f"MCP API Error: {method} {url} -> {response.status_code}: {error_msg}")
                            raise Exception(f"API Error: {error_msg} (status: {response.status_code})")
                        
                        if mcp_config.ENABLE_VERBOSE_LOGGING:
                            logger.debug(f"MCP API Response: {method} {url} -> {response.status_code}")
                        
                        return result
                        
                    except httpx.HTTPError as e:
                        last_error = e
                        if attempt < self.max_retries - 1:
                            logger.warning(f"MCP API request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                            continue
                        else:
                            raise
                
                # Se chegou aqui, todas as tentativas falharam
                if last_error:
                    raise last_error
                    
        except Exception as e:
            logger.error(f"MCP API Client Error: {method} {url} -> {str(e)}")
            raise Exception(f"Failed to call API: {str(e)}")
    
    async def get(
        self,
        endpoint: str,
        session_token: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Faz requisição GET"""
        return await self.request("GET", endpoint, session_token, params=params)
    
    async def post(
        self,
        endpoint: str,
        session_token: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Faz requisição POST"""
        return await self.request("POST", endpoint, session_token, json_data=json_data, params=params)
    
    async def put(
        self,
        endpoint: str,
        session_token: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Faz requisição PUT"""
        return await self.request("PUT", endpoint, session_token, json_data=json_data, params=params)
    
    async def delete(
        self,
        endpoint: str,
        session_token: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Faz requisição DELETE"""
        return await self.request("DELETE", endpoint, session_token, params=params)
    
    async def patch(
        self,
        endpoint: str,
        session_token: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Faz requisição PATCH"""
        return await self.request("PATCH", endpoint, session_token, json_data=json_data, params=params)

