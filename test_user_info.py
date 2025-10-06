#!/usr/bin/env python3
"""
Teste para verificar se as informações do usuário estão sendo retornadas corretamente
"""
import requests
import sys
sys.path.append('/Users/wolfx/Documents/wolfx/apiwolfx')

def test_user_info():
    """Testa se as informações do usuário estão sendo retornadas"""
    
    print("=== TESTE DE INFORMAÇÕES DO USUÁRIO ===\n")
    
    # URL base
    base_url = "https://7d4bb0f3ee33.ngrok-free.app"
    
    # Dados de login
    login_data = {
        "email": "teste@teste.com",
        "password": "123456",
        "remember": "on"
    }
    
    try:
        # Fazer login
        print("🔐 Fazendo login...")
        response = requests.post(f"{base_url}/auth/login", data=login_data, allow_redirects=False)
        
        if response.status_code != 302:
            print(f"❌ Erro no login: {response.status_code}")
            return
            
        # Pegar o cookie
        cookies = response.cookies
        if 'session_token' not in cookies:
            print("❌ Session token não encontrado")
            return
            
        session_token = cookies['session_token']
        print(f"✅ Session token: {session_token[:20]}...")
        
        # Testar acesso à API de produtos internos
        print("\n🔍 Testando API de produtos internos...")
        headers = {'Cookie': f'session_token={session_token}'}
        response = requests.get(f"{base_url}/api/internal-products?session_token={session_token}")
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ API acessada com sucesso!")
            print(f"Response: {response.text[:200]}...")
        else:
            print(f"❌ Erro na API: {response.text}")
            
        # Testar busca de produtos base
        print("\n🔍 Testando busca de produtos base...")
        response = requests.get(f"{base_url}/api/internal-products/base-products/search?session_token={session_token}")
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Busca de produtos base funcionando!")
            data = response.json()
            print(f"Produtos base encontrados: {len(data.get('base_products', []))}")
        else:
            print(f"❌ Erro na busca: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro no teste: {e}")

if __name__ == "__main__":
    test_user_info()
