import httpx
from typing import Optional, Dict, Any, List
from app.config.settings import settings
from app.models.mercadolibre_models import MLToken, MLUser, MLItem, MLSearchResponse, MLCategory, MLError


class MercadoLivreService:
    """Serviço para integração com a API do Mercado Livre"""
    
    def __init__(self):
        self.base_url = settings.ml_api_base_url
        self.auth_url = settings.ml_auth_url
        self.token_url = settings.ml_token_url
        self.app_id = settings.ml_app_id
        self.client_secret = settings.ml_client_secret
        self.redirect_uri = settings.ml_redirect_uri
        
    def get_auth_url(self, state: str = None) -> str:
        """Gera URL de autorização do Mercado Livre seguindo documentação oficial"""
        params = {
            "response_type": "code",
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri
        }
        
        # Adicionar state para segurança (recomendado pela documentação)
        if state:
            params["state"] = state
            
        return f"{self.auth_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    
    async def exchange_code_for_token(self, code: str, redirect_uri: str = None) -> Optional[MLToken]:
        """Troca código de autorização por token de acesso seguindo documentação oficial"""
        async with httpx.AsyncClient() as client:
            # Usar redirect_uri fornecido ou o padrão
            redirect_uri = redirect_uri or self.redirect_uri
            
            data = {
                "grant_type": "authorization_code",
                "client_id": self.app_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": redirect_uri
            }
            
            headers = {
                "accept": "application/json",
                "content-type": "application/x-www-form-urlencoded"
            }
            
            try:
                response = await client.post(self.token_url, data=data, headers=headers)
                response.raise_for_status()
                return MLToken(**response.json())
            except httpx.HTTPStatusError as e:
                print(f"Erro ao trocar código por token: {e}")
                if e.response.status_code == 400:
                    error_data = e.response.json()
                    print(f"Detalhes do erro: {error_data}")
                return None
    
    async def refresh_token(self, refresh_token: str) -> Optional[MLToken]:
        """Renova token de acesso usando refresh token seguindo documentação oficial"""
        async with httpx.AsyncClient() as client:
            data = {
                "grant_type": "refresh_token",
                "client_id": self.app_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token
            }
            
            headers = {
                "accept": "application/json",
                "content-type": "application/x-www-form-urlencoded"
            }
            
            try:
                response = await client.post(self.token_url, data=data, headers=headers)
                response.raise_for_status()
                return MLToken(**response.json())
            except httpx.HTTPStatusError as e:
                print(f"Erro ao renovar token: {e}")
                if e.response.status_code == 400:
                    error_data = e.response.json()
                    print(f"Detalhes do erro: {error_data}")
                return None
    
    async def get_user_info(self, access_token: str) -> Optional[MLUser]:
        """Obtém informações do usuário"""
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            try:
                response = await client.get(f"{self.base_url}/users/me", headers=headers)
                response.raise_for_status()
                return MLUser(**response.json())
            except httpx.HTTPStatusError as e:
                print(f"Erro ao obter informações do usuário: {e}")
                return None
    
    async def search_items(self, query: str, access_token: Optional[str] = None, 
                          site_id: str = "MLB", limit: int = 50) -> Optional[MLSearchResponse]:
        """Busca itens no Mercado Livre"""
        async with httpx.AsyncClient() as client:
            headers = {}
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
            
            params = {
                "q": query,
                "limit": limit,
                "site_id": site_id
            }
            
            try:
                response = await client.get(
                    f"{self.base_url}/sites/{site_id}/search",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                return MLSearchResponse(**response.json())
            except httpx.HTTPStatusError as e:
                print(f"Erro ao buscar itens: {e}")
                return None
    
    async def get_item(self, item_id: str, access_token: Optional[str] = None) -> Optional[MLItem]:
        """Obtém detalhes de um item específico"""
        async with httpx.AsyncClient() as client:
            headers = {}
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
            
            try:
                response = await client.get(
                    f"{self.base_url}/items/{item_id}",
                    headers=headers
                )
                response.raise_for_status()
                return MLItem(**response.json())
            except httpx.HTTPStatusError as e:
                print(f"Erro ao obter item: {e}")
                return None
    
    async def get_categories(self, site_id: str = "MLB") -> Optional[List[MLCategory]]:
        """Obtém categorias do site"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/sites/{site_id}/categories")
                response.raise_for_status()
                return [MLCategory(**cat) for cat in response.json()]
            except httpx.HTTPStatusError as e:
                print(f"Erro ao obter categorias: {e}")
                return None
    
    async def get_category(self, category_id: str) -> Optional[MLCategory]:
        """Obtém detalhes de uma categoria específica"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/categories/{category_id}")
                response.raise_for_status()
                return MLCategory(**response.json())
            except httpx.HTTPStatusError as e:
                print(f"Erro ao obter categoria: {e}")
                return None
    
    async def get_user_items(self, user_id: int, access_token: str, 
                           status: str = "active", limit: int = 50) -> Optional[List[MLItem]]:
        """Obtém itens de um usuário específico"""
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            params = {
                "status": status,
                "limit": limit
            }
            
            try:
                response = await client.get(
                    f"{self.base_url}/users/{user_id}/items/search",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                return [MLItem(**item) for item in data.get("results", [])]
            except httpx.HTTPStatusError as e:
                print(f"Erro ao obter itens do usuário: {e}")
                return None
