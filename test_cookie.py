#!/usr/bin/env python3
"""
Teste para verificar se o cookie está sendo definido corretamente
"""
import requests
import sys
sys.path.append('/Users/wolfx/Documents/wolfx/apiwolfx')

def test_login_and_cookie():
    """Testa o login e verifica se o cookie é definido"""
    
    print("=== TESTE DE LOGIN E COOKIE ===\n")
    
    # URL base
    base_url = "https://7d4bb0f3ee33.ngrok-free.app"
    
    # Dados de login (usando um usuário existente)
    login_data = {
        "email": "teste@teste.com",
        "password": "123456",  # Senha padrão
        "remember": "on"
    }
    
    try:
        # Fazer login
        print("🔐 Fazendo login...")
        response = requests.post(f"{base_url}/auth/login", data=login_data, allow_redirects=False)
        
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        # Verificar se há cookie
        cookies = response.cookies
        print(f"Cookies recebidos: {dict(cookies)}")
        
        if 'session_token' in cookies:
            session_token = cookies['session_token']
            print(f"✅ Session token encontrado: {session_token[:20]}...")
            
            # Testar acesso à página de produtos internos
            print("\n🔍 Testando acesso à página de produtos internos...")
            headers = {'Cookie': f'session_token={session_token}'}
            response = requests.get(f"{base_url}/api/internal-products", headers=headers)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Página acessada com sucesso!")
            else:
                print(f"❌ Erro ao acessar página: {response.text[:200]}")
                
        else:
            print("❌ Session token não encontrado nos cookies")
            
    except Exception as e:
        print(f"❌ Erro no teste: {e}")

if __name__ == "__main__":
    test_login_and_cookie()
