import os
from typing import Optional


class Settings:
    """Configurações da aplicação"""
    
    def __init__(self):
        # Mercado Livre API Configuration
        self.ml_app_id = os.getenv("ML_APP_ID", "6987936494418444")
        self.ml_client_secret = os.getenv("ML_CLIENT_SECRET", "puvG9Z7XBgICZg5yK3t0PAXAmnco18Tl")
        self.ml_redirect_uri = os.getenv("ML_REDIRECT_URI", "https://15a45cfe4ee8.ngrok-free.app/api/callback")
        
        # API Configuration
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))
        self.debug = os.getenv("DEBUG", "True").lower() == "true"
        
        # Mercado Livre API URLs (Brasil)
        self.ml_auth_url = "https://auth.mercadolivre.com.br/authorization"
        self.ml_token_url = "https://api.mercadolibre.com/oauth/token"
        self.ml_api_base_url = "https://api.mercadolibre.com"
        
        # Mercado Pago Configuration - PRODUÇÃO com usuários de teste
        # IMPORTANTE: Mercado Pago NÃO tem sandbox separado!
        # Usa usuários de teste em ambiente de produção
        self.mp_access_token = os.getenv("MP_ACCESS_TOKEN", "APP_USR-6252941991597570-101508-8d44441cc0d386eee063ba11e1ea5a18-1979794691")
        self.mp_public_key = os.getenv("MP_PUBLIC_KEY", "APP_USR-4549749e-5420-4118-95fe-ab17831df6bb")
        self.mp_webhook_secret = os.getenv("MP_WEBHOOK_SECRET", "a85db9f8e932e94707bb0b23413e3b8e4abdb60e19ad81caa1e80b8459a87fe9")
        self.mp_base_url = "https://api.mercadopago.com"
        self.mp_sandbox = False  # Sempre produção - Mercado Pago não tem sandbox
        
        # URLs para pagamentos (configuráveis via ambiente)
        self.mp_success_url = os.getenv("MP_SUCCESS_URL", "https://15a45cfe4ee8.ngrok-free.app/payment/success")
        self.mp_failure_url = os.getenv("MP_FAILURE_URL", "https://15a45cfe4ee8.ngrok-free.app/payment/failure")
        self.mp_pending_url = os.getenv("MP_PENDING_URL", "https://15a45cfe4ee8.ngrok-free.app/payment/pending")
        self.mp_webhook_url = os.getenv("MP_WEBHOOK_URL", "https://15a45cfe4ee8.ngrok-free.app/api/payments/webhooks/mercadopago")
    
    def update_redirect_uri(self, new_uri: str):
        """Atualiza a URL de redirecionamento"""
        self.ml_redirect_uri = new_uri


# Instância global das configurações
settings = Settings()
