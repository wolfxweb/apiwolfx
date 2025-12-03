import os
from typing import Optional


class Settings:
    """Configurações da aplicação"""
    
    def __init__(self):
        # Detecta ambiente (produção ou desenvolvimento)
        self.environment = os.getenv("ENVIRONMENT", "development").lower()
        self.is_production = self.environment == "production"
        
        # Define domínio base conforme ambiente
        if self.is_production:
            # Produção: usa domínio real
            default_domain = os.getenv("DOMAIN", "celx.com.br")
            default_base_url = f"https://{default_domain}"
            self.ml_app_id = os.getenv("ML_APP_ID")
            self.ml_client_secret = os.getenv("ML_CLIENT_SECRET")
        else:
            # Desenvolvimento: usa URL exposta via ngrok (fallback)
            default_base_url = os.getenv("LOCAL_BASE_URL", "https://963b5189936e.ngrok-free.app")
            # Credenciais padrão de desenvolvimento (ID do aplicativo local)
            self.ml_app_id = os.getenv("ML_APP_ID", "3821568023399477")
            self.ml_client_secret = os.getenv("ML_CLIENT_SECRET", "3gDZs9aLX9jmm64MCXPmdSIaCf7rBRHa")
        
        self.base_url = default_base_url
        
        # Validar se as credenciais foram definidas
        if not self.ml_app_id or not self.ml_client_secret:
            raise ValueError(
                "❌ ERRO CRÍTICO: ML_APP_ID e ML_CLIENT_SECRET devem ser definidos nas variáveis de ambiente! "
                f"ML_APP_ID: {'✅' if self.ml_app_id else '❌ FALTANDO'}, "
                f"ML_CLIENT_SECRET: {'✅' if self.ml_client_secret else '❌ FALTANDO'}"
            )
        
        # ML Redirect URI - usa variável de ambiente ou padrão baseado no ambiente
        self.ml_redirect_uri = os.getenv(
            "ML_REDIRECT_URI",
            f"{default_base_url}/api/callback"
        )
        
        # ML Notification URL - usa variável de ambiente ou padrão baseado no ambiente
        self.ml_notification_url = os.getenv(
            "ML_NOTIFICATION_URL",
            f"{default_base_url}/api/notifications"
        )
        
        # API Configuration
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))
        self.debug = os.getenv("DEBUG", str(not self.is_production)).lower() == "true"
        
        # Mercado Livre API URLs (Brasil)
        self.ml_auth_url = "https://auth.mercadolivre.com.br/authorization"
        self.ml_token_url = "https://api.mercadolibre.com/oauth/token"
        self.ml_api_base_url = "https://api.mercadolibre.com"
        
        # Mercado Pago Configuration
        # IMPORTANTE: Mercado Pago NÃO tem sandbox separado!
        # Em produção, usa credenciais de produção
        # Em desenvolvimento, pode usar credenciais de teste
        if self.is_production:
            # Produção - credenciais de produção
            self.mp_access_token = os.getenv(
                "MP_ACCESS_TOKEN",
                "APP_USR-6987936494418444-101415-df063090488cd09fd99bb0e75ba91dc5-534913383560219"
            )
            self.mp_public_key = os.getenv(
                "MP_PUBLIC_KEY",
                "APP_USR-a77d3ee7-7c94-443e-b910-d4e0c3e41e63"
            )
            self.mp_webhook_secret = os.getenv(
                "MP_WEBHOOK_SECRET",
                "7c315606ea2ebac4cb8410755f6bd42af5f8d7d5af0e5bcdcb1d4b5440068bb2"
            )
        else:
            # Desenvolvimento - credenciais de teste
            self.mp_access_token = os.getenv(
                "MP_ACCESS_TOKEN",
                "APP_USR-6252941991597570-101508-8d44441cc0d386eee063ba11e1ea5a18-1979794691"
            )
            self.mp_public_key = os.getenv(
                "MP_PUBLIC_KEY",
                "APP_USR-4549749e-5420-4118-95fe-ab17831df6bb"
            )
            self.mp_webhook_secret = os.getenv(
                "MP_WEBHOOK_SECRET",
                "a85db9f8e932e94707bb0b23413e3b8e4abdb60e19ad81caa1e80b8459a87fe9"
            )
        
        self.mp_base_url = "https://api.mercadopago.com"
        self.mp_sandbox = False  # Sempre produção - Mercado Pago não tem sandbox
        
        # URLs para pagamentos (configuráveis via ambiente ou padrão baseado no ambiente)
        self.mp_success_url = os.getenv(
            "MP_SUCCESS_URL",
            f"{default_base_url}/payment/success"
        )
        self.mp_failure_url = os.getenv(
            "MP_FAILURE_URL",
            f"{default_base_url}/payment/failure"
        )
        self.mp_pending_url = os.getenv(
            "MP_PENDING_URL",
            f"{default_base_url}/payment/pending"
        )
        self.mp_webhook_url = os.getenv(
            "MP_WEBHOOK_URL",
            f"{default_base_url}/api/payments/webhooks/mercadopago"
        )
        
        # Asaas Configuration
        # IMPORTANTE: Usar chave de sandbox para desenvolvimento e produção para produção
        if self.is_production:
            # Produção: usa ASAAS_API_KEY (chave de produção)
            self.asaas_api_key = os.getenv("ASAAS_API_KEY", "")
        else:
            # Desenvolvimento: usa ASAAS_API_KEY_SANDBOX se disponível, senão ASAAS_API_KEY
            # Isso permite usar chave de sandbox em desenvolvimento
            self.asaas_api_key = os.getenv("ASAAS_API_KEY_SANDBOX") or os.getenv("ASAAS_API_KEY", "")
        
        self.asaas_webhook_token = os.getenv("ASAAS_WEBHOOK_TOKEN", "")
        self.asaas_webhook_url = os.getenv(
            "ASAAS_WEBHOOK_URL",
            f"{default_base_url}/api/asaas/webhooks"
        )
        
        # Validar credenciais Asaas
        if not self.asaas_api_key:
            import logging
            env_name = "ASAAS_API_KEY" if self.is_production else "ASAAS_API_KEY_SANDBOX (ou ASAAS_API_KEY)"
            logging.warning(
                f"⚠️ AVISO: {env_name} deve ser definido! "
                f"ASAAS_API_KEY: {'✅' if self.asaas_api_key else '❌ FALTANDO'}"
            )

        # Supabase Storage (para imagens ML)
        self.supabase_url = os.getenv("SUPABASE_URL", "https://supabase.wolfx.com.br").rstrip("/")
        self.supabase_service_key = os.getenv(
            "SUPABASE_SERVICE_KEY",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ewogICJyb2xlIjogInNlcnZpY2Vfcm9sZSIsCiAgImlzcyI6ICJzdXBhYmFzZSIsCiAgImlhdCI6IDE3MTUwNTA4MDAsCiAgImV4cCI6IDE4NzI4MTcyMDAKfQ.JkkevDN7zY6HpQ54lc9iETFihaZ5F1-aXhE46byNQ64"
        )
        self.supabase_bucket = os.getenv("SUPABASE_BUCKET", "ml-product-images")
        
        # API Keys para múltiplos providers de IA
        # Perplexity API Key (pesquisa de conteúdo)
        self.perplexity_api_key = os.getenv("VITE_PERPLEXITY_API_KEY") or os.getenv("PERPLEXITY_API_KEY", "")
        
        # Anthropic API Key (Claude - criação de texto)
        self.anthropic_api_key = os.getenv("VITE_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "")
        
        # Google API Key (Gemini, Imagen, VEO - texto, imagem, vídeo)
        self.google_api_key = os.getenv("VITE_GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    
    def update_redirect_uri(self, new_uri: str):
        """Atualiza a URL de redirecionamento"""
        self.ml_redirect_uri = new_uri


# Instância global das configurações
settings = Settings()
