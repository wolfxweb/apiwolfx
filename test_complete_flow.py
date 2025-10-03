#!/usr/bin/env python3
"""
Script para testar o fluxo completo: login + callback ML
"""
import requests
import json

def test_complete_flow():
    print("🧪 Testando fluxo completo...")
    
    # 1. Fazer login
    print("\n1️⃣ Fazendo login...")
    login_data = {
        "email": "wolfxweb@gmail.com",
        "password": "Wolfx2020"
    }
    
    session = requests.Session()
    login_response = session.post("http://localhost:8000/auth/login", data=login_data, allow_redirects=False)
    print(f"Status: {login_response.status_code}")
    
    if login_response.status_code == 302:
        print("✅ Login realizado!")
        
        # 2. Acessar página de contas ML
        print("\n2️⃣ Acessando página de contas ML...")
        accounts_response = session.get("http://localhost:8000/ml/accounts")
        print(f"Status: {accounts_response.status_code}")
        
        if accounts_response.status_code == 200:
            print("✅ Página de contas acessada!")
            
            # 3. Testar rota de conexão
            print("\n3️⃣ Testando rota de conexão...")
            connect_response = session.get("http://localhost:8000/ml/connect", allow_redirects=False)
            print(f"Status: {connect_response.status_code}")
            
            if connect_response.status_code == 302:
                auth_url = connect_response.headers.get('location')
                print(f"✅ URL de autorização: {auth_url}")
                
                # 4. Simular callback com dados fictícios
                print("\n4️⃣ Testando callback com dados fictícios...")
                
                # Simular dados que o ML retornaria
                mock_token_data = {
                    "access_token": "APP_USR_1234567890abcdef",
                    "token_type": "bearer",
                    "expires_in": 21600,
                    "scope": "read write",
                    "user_id": 1979794691,
                    "refresh_token": "TG_1234567890abcdef"
                }
                
                mock_user_info = {
                    "id": 1979794691,
                    "nickname": "TEST_USER_123",
                    "email": "test@mercadolivre.com",
                    "first_name": "Teste",
                    "last_name": "Usuario",
                    "country_id": "BR",
                    "site_id": "MLB",
                    "permalink": "http://perfil.mercadolivre.com.br/TEST_USER_123"
                }
                
                print(f"Mock token_data: {mock_token_data}")
                print(f"Mock user_info: {mock_user_info}")
                
                # Testar callback
                callback_response = session.get(
                    "http://localhost:8000/api/callback",
                    params={
                        "code": "TG-TEST_CODE_123456789",
                        "state": "TEST_STATE_123456789"
                    },
                    allow_redirects=False
                )
                
                print(f"Status: {callback_response.status_code}")
                if callback_response.status_code == 302:
                    redirect_url = callback_response.headers.get('location')
                    print(f"✅ Redirecionamento: {redirect_url}")
                else:
                    print(f"❌ Erro no callback: {callback_response.text[:200]}...")
            else:
                print(f"❌ Erro na rota de conexão: {connect_response.text[:200]}...")
        else:
            print(f"❌ Erro ao acessar contas: {accounts_response.text[:200]}...")
    else:
        print(f"❌ Erro no login: {login_response.text[:200]}...")

if __name__ == "__main__":
    test_complete_flow()
