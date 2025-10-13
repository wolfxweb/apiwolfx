#!/usr/bin/env python3
"""
Script para testar o fluxo completo do Mercado Livre
"""
import requests
import json

# URL base
BASE_URL = "http://localhost:8000"

def test_ml_flow():
    print("🧪 Testando fluxo completo do Mercado Livre...")
    
    # 1. Fazer login
    print("\n1️⃣ Fazendo login...")
    login_data = {
        "email": "wolfxweb@gmail.com",
        "password": "Wolfx2020"
    }
    
    login_response = requests.post(f"{BASE_URL}/auth/login", data=login_data, allow_redirects=False)
    print(f"Status: {login_response.status_code}")
    
    if login_response.status_code == 302:
        # Extrair session_token do cookie
        cookies = login_response.cookies
        session_token = cookies.get('session_token')
        print(f"✅ Login realizado! Session token: {session_token[:20]}...")
        
        # 2. Acessar página de contas ML
        print("\n2️⃣ Acessando página de contas ML...")
        headers = {"Cookie": f"session_token={session_token}"}
        accounts_response = requests.get(f"{BASE_URL}/ml/accounts", headers=headers)
        print(f"Status: {accounts_response.status_code}")
        
        if accounts_response.status_code == 200:
            print("✅ Página de contas acessada com sucesso!")
            
            # 3. Testar rota de conexão
            print("\n3️⃣ Testando rota de conexão...")
            connect_response = requests.get(f"{BASE_URL}/ml/connect", headers=headers, allow_redirects=False)
            print(f"Status: {connect_response.status_code}")
            
            if connect_response.status_code == 302:
                auth_url = connect_response.headers.get('location')
                print(f"✅ URL de autorização: {auth_url}")
                
                # 4. Simular callback (com code inválido para teste)
                print("\n4️⃣ Testando callback...")
                callback_response = requests.get(
                    f"{BASE_URL}/api/callback?code=test_code&state=test_state",
                    headers=headers,
                    allow_redirects=False
                )
                print(f"Status: {callback_response.status_code}")
                
                if callback_response.status_code == 302:
                    redirect_url = callback_response.headers.get('location')
                    print(f"✅ Redirecionamento: {redirect_url}")
                else:
                    print(f"❌ Erro no callback: {callback_response.text}")
            else:
                print(f"❌ Erro na rota de conexão: {connect_response.text}")
        else:
            print(f"❌ Erro ao acessar contas: {accounts_response.text}")
    else:
        print(f"❌ Erro no login: {login_response.text}")

if __name__ == "__main__":
    test_ml_flow()
