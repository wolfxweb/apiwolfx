#!/usr/bin/env python3
"""
Script para debugar configuração do Mercado Livre
"""
import requests
import json
from app.config.settings import settings

def test_mercadolibre_config():
    """Testa a configuração do Mercado Livre"""
    print("🔍 Debugando configuração do Mercado Livre...")
    print("="*60)
    
    # 1. Verificar credenciais
    print("📋 Credenciais configuradas:")
    print(f"   • App ID: {settings.ml_app_id}")
    print(f"   • Client Secret: {settings.ml_client_secret[:10]}...")
    print(f"   • Redirect URI: {settings.ml_redirect_uri}")
    print()
    
    # 2. Testar URL de autorização
    print("🌐 Testando URL de autorização...")
    auth_url = f"{settings.ml_auth_url}?response_type=code&client_id={settings.ml_app_id}&redirect_uri={settings.ml_redirect_uri}"
    print(f"   • URL: {auth_url}")
    print()
    
    # 3. Mostrar estrutura de rotas
    print("🛣️ Estrutura de rotas da API:")
    print("   • Página inicial: /")
    print("   • Login: /login")
    print("   • Callback: /callback (compatibilidade)")
    print("   • API Callback: /api/callback")
    print("   • Autenticação: /api/")
    print("   • Produtos: /api/products/")
    print("   • Usuários: /api/users/")
    print("   • Categorias: /api/categories/")
    print("   • Health: /health")
    print("   • Docs: /docs")
    print()
    
    # 3. Verificar se a URL é acessível
    print("🔗 Testando conectividade...")
    try:
        response = requests.get(settings.ml_api_base_url, timeout=10)
        print(f"   • API Base: {response.status_code} - {'✅ OK' if response.status_code == 200 else '❌ Erro'}")
    except Exception as e:
        print(f"   • API Base: ❌ Erro - {e}")
    
    try:
        response = requests.get(settings.ml_auth_url, timeout=10)
        print(f"   • Auth URL: {response.status_code} - {'✅ OK' if response.status_code == 200 else '❌ Erro'}")
    except Exception as e:
        print(f"   • Auth URL: ❌ Erro - {e}")
    
    print()
    
    # 4. Verificar configuração do aplicativo
    print("🔧 Verificações necessárias:")
    print("   1. ✅ URL de callback deve ser HTTPS")
    print("   2. ✅ URL de callback deve estar registrada no Mercado Livre")
    print("   3. ✅ App ID e Client Secret devem estar corretos")
    print("   4. ✅ Aplicativo deve estar ativo no Mercado Livre")
    print()
    
    # 5. URLs para verificar no Mercado Livre
    print("🌐 URLs para verificar no painel do Mercado Livre:")
    print(f"   • Painel: https://developers.mercadolibre.com/")
    print(f"   • URL de callback: {settings.ml_redirect_uri}")
    print()
    
    # 6. Possíveis soluções
    print("💡 Possíveis soluções:")
    print("   1. Verificar se o aplicativo está ativo")
    print("   2. Confirmar se a URL de callback está correta")
    print("   3. Verificar se as credenciais estão corretas")
    print("   4. Testar com uma conta diferente")
    print("   5. Verificar se o aplicativo está configurado para o país correto")
    print()
    
    # 7. Teste de token (se possível)
    print("🧪 Teste de token (opcional):")
    print("   • Para testar, acesse a URL de autorização acima")
    print("   • Faça login com sua conta do Mercado Livre")
    print("   • Verifique se o callback é chamado corretamente")
    print()
    
    return {
        "app_id": settings.ml_app_id,
        "redirect_uri": settings.ml_redirect_uri,
        "auth_url": auth_url
    }

def generate_correct_urls():
    """Gera URLs corretas para configuração"""
    print("🔗 URLs corretas para configuração:")
    print("="*40)
    
    # URL de autorização correta
    auth_url = f"{settings.ml_auth_url}?response_type=code&client_id={settings.ml_app_id}&redirect_uri={settings.ml_redirect_uri}"
    
    print(f"📱 URL de Autorização:")
    print(f"   {auth_url}")
    print()
    
    print(f"🔗 URL de Callback:")
    print(f"   {settings.ml_redirect_uri}")
    print()
    
    print("📋 Para configurar no Mercado Livre:")
    print("   1. Acesse: https://developers.mercadolibre.com/")
    print("   2. Vá em 'Minhas Aplicações'")
    print("   3. Edite sua aplicação")
    print("   4. Configure a URL de redirecionamento:")
    print(f"      {settings.ml_redirect_uri}")
    print("   5. Salve as alterações")
    print()

if __name__ == "__main__":
    test_mercadolibre_config()
    print()
    generate_correct_urls()
