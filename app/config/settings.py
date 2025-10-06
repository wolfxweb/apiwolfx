import os
from typing import Optional


class Settings:
    """Configurações da aplicação"""
    
    def __init__(self):
        # Mercado Livre API Configuration
        self.ml_app_id = os.getenv("ML_APP_ID", "6987936494418444")
        self.ml_client_secret = os.getenv("ML_CLIENT_SECRET", "puvG9Z7XBgICZg5yK3t0PAXAmnco18Tl")
        self.ml_redirect_uri = "https://7b8e8fed970d.ngrok-free.app/api/callback"
        
        # API Configuration
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))
        self.debug = os.getenv("DEBUG", "True").lower() == "true"
        
        # Mercado Livre API URLs (Brasil)
        self.ml_auth_url = "https://auth.mercadolivre.com.br/authorization"
        self.ml_token_url = "https://api.mercadolibre.com/oauth/token"
        self.ml_api_base_url = "https://api.mercadolibre.com"
    
    def update_redirect_uri(self, new_uri: str):
        """Atualiza a URL de redirecionamento"""
        self.ml_redirect_uri = new_uri


# Instância global das configurações
settings = Settings()
