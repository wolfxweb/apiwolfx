#!/usr/bin/env python3
"""
Debug do cookie e sessão
"""
import requests
import sys
sys.path.append('/Users/wolfx/Documents/wolfx/apiwolfx')

def debug_cookie():
    """Debug do cookie"""
    
    print("=== DEBUG DO COOKIE ===\n")
    
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
        
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        # Verificar cookies
        cookies = response.cookies
        print(f"Cookies recebidos: {dict(cookies)}")
        
        if 'session_token' in cookies:
            session_token = cookies['session_token']
            print(f"✅ Session token: {session_token}")
            
            # Testar API com cookie
            print("\n🔍 Testando API com cookie...")
            response = requests.get(f"{base_url}/api/internal-products", cookies=cookies)
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Response (primeiros 200 chars): {response.text[:200]}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✅ JSON válido: {data}")
                except:
                    print("❌ Resposta não é JSON válido")
            else:
                print(f"❌ Erro: {response.text}")
                
        else:
            print("❌ Session token não encontrado")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    debug_cookie()
