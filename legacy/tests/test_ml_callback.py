#!/usr/bin/env python3
"""
Script para testar o callback do ML com dados simulados
"""
import requests
import json

def test_ml_callback():
    print("🧪 Testando callback do ML...")
    
    # Simular dados do ML (baseado no que recebemos)
    mock_user_info = {
        "id": 1979794691,  # Este é o ID que está causando problema
        "nickname": "TEST_USER_123",
        "email": "test@mercadolivre.com",
        "first_name": "Teste",
        "last_name": "Usuario",
        "country_id": "BR",
        "site_id": "MLB",
        "permalink": "http://perfil.mercadolivre.com.br/TEST_USER_123"
    }
    
    print(f"Mock user_info: {mock_user_info}")
    print(f"ID tipo: {type(mock_user_info['id'])}")
    print(f"ID como string: {str(mock_user_info['id'])}")
    
    # Testar a conversão que estamos usando
    ml_user_id = str(mock_user_info['id'])
    print(f"ml_user_id final: {ml_user_id} (tipo: {type(ml_user_id)})")
    
    # Simular token data
    mock_token_data = {
        "access_token": "APP_USR_1234567890abcdef",
        "token_type": "bearer",
        "expires_in": 21600,
        "scope": "read write",
        "user_id": 1979794691,
        "refresh_token": "TG_1234567890abcdef"
    }
    
    print(f"\nMock token_data: {mock_token_data}")
    
    # Testar se conseguimos fazer uma requisição para o callback
    print("\n🌐 Testando callback real...")
    
    # Usar o code real que recebemos
    real_code = "TG-68e055b76bd60d0001ed10c7-1979794691"
    real_state = "CNR9M1mLcDKrBlTNO3EHU0Ol7tEXDgrR"
    
    try:
        response = requests.get(
            f"http://localhost:8000/api/callback",
            params={
                "code": real_code,
                "state": real_state
            },
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 302:
            redirect_url = response.headers.get('location')
            print(f"Redirecionamento: {redirect_url}")
        else:
            print(f"Resposta: {response.text[:500]}...")
            
    except Exception as e:
        print(f"Erro na requisição: {e}")

if __name__ == "__main__":
    test_ml_callback()
