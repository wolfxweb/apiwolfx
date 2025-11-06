#!/usr/bin/env python3
"""
Script para rodar a API MVC com ngrok
"""
import subprocess
import time
import requests
import json
import os
import sys

def get_ngrok_url():
    """Obtém a URL pública do ngrok"""
    try:
        response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
        data = response.json()
        for tunnel in data['tunnels']:
            if tunnel['proto'] == 'https':
                return tunnel['public_url']
        return None
    except Exception as e:
        print(f"Erro ao obter URL do ngrok: {e}")
        return None

def update_config_with_ngrok(ngrok_url):
    """Atualiza configuração com URL do ngrok"""
    config_content = f'''import os
from typing import Optional


class Settings:
    """Configurações da aplicação"""
    
    def __init__(self):
        # Mercado Livre API Configuration
        # IMPORTANTE: SEMPRE usar variáveis de ambiente (sem fallback hardcoded)
        self.ml_app_id = os.getenv("ML_APP_ID")
        self.ml_client_secret = os.getenv("ML_CLIENT_SECRET")
        
        # Validar se as credenciais foram definidas
        if not self.ml_app_id or not self.ml_client_secret:
            raise ValueError(
                "❌ ERRO: ML_APP_ID e ML_CLIENT_SECRET devem ser definidos nas variáveis de ambiente!"
            )
        self.ml_redirect_uri = "{ngrok_url}/api/callback"
        
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
'''
    
    with open('app/config/settings.py', 'w') as f:
        f.write(config_content)
    
    print(f"✅ Configuração MVC atualizada com URL: {ngrok_url}")

def main():
    print("🚀 Iniciando API Mercado Livre MVC com ngrok...")
    print("="*60)
    
    # Inicia ngrok em background
    print("🌐 Iniciando ngrok...")
    ngrok_process = subprocess.Popen(['ngrok', 'http', '8000'], 
                                    stdout=subprocess.DEVNULL, 
                                    stderr=subprocess.DEVNULL)
    
    # Aguarda ngrok inicializar
    print("⏳ Aguardando ngrok inicializar...")
    time.sleep(5)
    
    # Obtém URL do ngrok
    ngrok_url = get_ngrok_url()
    
    if not ngrok_url:
        print("❌ Erro: Não foi possível obter URL do ngrok")
        print("💡 Verifique se o ngrok está rodando: http://localhost:4040")
        ngrok_process.terminate()
        return
    
    print(f"✅ ngrok rodando em: {ngrok_url}")
    print()
    print("📋 CONFIGURAÇÃO NO MERCADO LIVRE:")
    print(f"   • URL de redirecionamento: {ngrok_url}/api/callback")
    print("   • Acesse: https://developers.mercadolibre.com/")
    print("   • Configure a URL acima no seu app")
    print()
    print("🌐 URLs IMPORTANTES:")
    print(f"   • API Pública: {ngrok_url}")
    print(f"   • Login: {ngrok_url}/login")
    print(f"   • Callback: {ngrok_url}/api/callback")
    print(f"   • Local: http://localhost:8000")
    print()
    print("🎯 PARA TESTAR:")
    print(f"   1. Acesse: {ngrok_url}")
    print("   2. Configure suas credenciais no Mercado Livre")
    print("   3. Clique em 'Fazer Login'")
    print("   4. Autorize a aplicação")
    print("   5. Receba seu token!")
    print()
    print("="*60)
    print("⚠️  IMPORTANTE: Mantenha este terminal aberto!")
    print("   Para parar: Ctrl+C")
    print("="*60)
    
    # Atualiza configuração
    update_config_with_ngrok(ngrok_url)
    
    # Inicia FastAPI MVC
    print("\n🚀 Iniciando servidor FastAPI MVC...")
    try:
        import uvicorn
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
    except KeyboardInterrupt:
        print("\n🛑 Parando servidor...")
        ngrok_process.terminate()
    except Exception as e:
        print(f"❌ Erro ao iniciar servidor: {e}")
        ngrok_process.terminate()

if __name__ == "__main__":
    main()
