#!/usr/bin/env python3
"""
Debug da configuração seguindo documentação oficial do Mercado Livre
Última atualização: 11/09/2025
"""

import requests
from app.config.settings import settings

def debug_mercadolibre_oficial():
    """Debug seguindo documentação oficial do Mercado Livre"""
    
    print("🔍 Debugando configuração seguindo documentação oficial...")
    print("=" * 60)
    
    # 1. Verificar credenciais
    print("📋 Credenciais configuradas:")
    print(f"   • App ID: {settings.ml_app_id}")
    print(f"   • Client Secret: {settings.ml_client_secret[:10]}...")
    print(f"   • Redirect URI: {settings.ml_redirect_uri}")
    print()
    
    # 2. URL de autorização seguindo documentação oficial
    print("🌐 URL de autorização (documentação oficial):")
    auth_url = f"{settings.ml_auth_url}?response_type=code&client_id={settings.ml_app_id}&redirect_uri={settings.ml_redirect_uri}"
    print(f"   • URL: {auth_url}")
    print()
    
    # 3. Exemplo com state (recomendado para segurança)
    print("🔒 URL com state (recomendado para segurança):")
    state_example = "ABC1234"
    auth_url_with_state = f"{settings.ml_auth_url}?response_type=code&client_id={settings.ml_app_id}&redirect_uri={settings.ml_redirect_uri}&state={state_example}"
    print(f"   • URL: {auth_url_with_state}")
    print()
    
    # 4. Estrutura de rotas da API
    print("🛣️ Estrutura de rotas da API:")
    print("   • Página inicial: /")
    print("   • Login: /login")
    print("   • Login com state: /login?state=ABC1234")
    print("   • Callback: /callback")
    print("   • API Callback: /api/callback")
    print("   • Autenticação: /api/")
    print("   • Produtos: /api/products/")
    print("   • Usuários: /api/users/")
    print("   • Categorias: /api/categories/")
    print("   • Health: /health")
    print("   • Docs: /docs")
    print()
    
    # 5. Testar conectividade
    print("🔗 Testando conectividade...")
    try:
        response = requests.get(settings.ml_api_base_url, timeout=10)
        print(f"   • API Base: {response.status_code} - {'✅ OK' if response.status_code == 200 else '❌ Erro'}")
    except Exception as e:
        print(f"   • API Base: Erro - {e}")
    
    try:
        response = requests.get(settings.ml_auth_url, timeout=10)
        print(f"   • Auth URL: {response.status_code} - {'✅ OK' if response.status_code == 200 else '❌ Erro'}")
    except Exception as e:
        print(f"   • Auth URL: Erro - {e}")
    
    print()
    
    # 6. Verificações necessárias
    print("🔧 Verificações necessárias:")
    print("   1. ✅ URL de callback deve ser HTTPS")
    print("   2. ✅ URL de callback deve estar registrada no Mercado Livre")
    print("   3. ✅ App ID e Client Secret devem estar corretos")
    print("   4. ✅ Aplicativo deve estar ativo no Mercado Livre")
    print("   5. ✅ Usuário deve ser administrador (não operador/colaborador)")
    print()
    
    # 7. URLs para verificar no painel do Mercado Livre
    print("🌐 URLs para verificar no painel do Mercado Livre:")
    print("   • Painel: https://developers.mercadolibre.com/")
    print("   • URL de callback: https://c7198784b3cb.ngrok-free.app/api/callback")
    print()
    
    # 8. Possíveis soluções
    print("💡 Possíveis soluções:")
    print("   1. Verificar se o aplicativo está ativo")
    print("   2. Confirmar se a URL de callback está correta")
    print("   3. Verificar se as credenciais estão corretas")
    print("   4. Testar com uma conta diferente")
    print("   5. Verificar se o aplicativo está configurado para o país correto")
    print("   6. Verificar se o usuário é administrador")
    print()
    
    # 9. Teste de token (opcional)
    print("🧪 Teste de token (opcional):")
    print("   • Para testar, acesse a URL de autorização acima")
    print("   • Faça login com sua conta do Mercado Livre")
    print("   • Verifique se o callback é chamado corretamente")
    print()
    
    # 10. URLs corretas para configuração
    print("🔗 URLs corretas para configuração:")
    print("=" * 40)
    print("📱 URL de Autorização:")
    print(f"   {auth_url}")
    print()
    print("🔗 URL de Callback:")
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
    
    # 11. Códigos de erro da documentação oficial
    print("🚨 Códigos de erro da documentação oficial:")
    print("   1. invalid_client: client_id e/ou client_secret inválidos")
    print("   2. invalid_grant: authorization_code ou refresh_token inválidos")
    print("   3. invalid_scope: alcance solicitado é inválido")
    print("   4. invalid_request: parâmetro obrigatório ausente")
    print("   5. unsupported_grant_type: grant_type inválido")
    print("   6. forbidden (403): acesso não autorizado")
    print("   7. local_rate_limited (429): muitas requisições")
    print("   8. unauthorized_client: aplicação sem grant")
    print("   9. unauthorized_application: aplicação bloqueada")
    print()

if __name__ == "__main__":
    debug_mercadolibre_oficial()
