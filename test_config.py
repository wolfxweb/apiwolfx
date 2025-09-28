#!/usr/bin/env python3
"""
Teste da configuração do Mercado Livre
"""

from app.config.settings import settings
from app.services.mercadolibre_service import MercadoLivreService

def test_config():
    print("🔍 VERIFICAÇÃO DA CONFIGURAÇÃO:")
    print("=" * 50)
    
    print(f"Auth URL: {settings.ml_auth_url}")
    print(f"Token URL: {settings.ml_token_url}")
    print(f"API Base: {settings.ml_api_base_url}")
    print(f"App ID: {settings.ml_app_id}")
    print(f"Client Secret: {settings.ml_client_secret[:10]}...")
    print(f"Redirect URI: {settings.ml_redirect_uri}")
    print()
    
    service = MercadoLivreService()
    print("URL de autorização gerada:")
    print(service.get_auth_url())
    print()
    
    # Verificar se está correto
    if "mercadolivre.com.br" in service.auth_url:
        print("✅ URL de autorização CORRETA (Brasil)")
    else:
        print("❌ URL de autorização INCORRETA")
    
    if "api/callback" in service.redirect_uri:
        print("✅ URL de callback CORRETA (/api/callback)")
    else:
        print("❌ URL de callback INCORRETA")

if __name__ == "__main__":
    test_config()
