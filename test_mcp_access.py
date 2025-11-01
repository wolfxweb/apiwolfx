#!/usr/bin/env python3
"""
Script para testar acesso ao MCP do Mercado Livre
"""
import requests
import json

# Configuração do MCP
MCP_URL = "https://mcp.mercadolibre.com/mcp"
TOKEN = "APP_USR-6987936494418444-110108-2244ed391e6a524f95d176777c8cb71b-1979794691"
COMPANY_ID = "15"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "X-Company-ID": COMPANY_ID,
    "Content-Type": "application/json"
}

def test_mcp_access():
    """Testa acesso ao MCP do Mercado Livre"""
    print("🔍 Testando acesso ao MCP do Mercado Livre...")
    print(f"📍 URL: {MCP_URL}")
    print(f"🔑 Token: {TOKEN[:30]}...")
    print(f"🏢 Company ID: {COMPANY_ID}\n")
    
    # Teste 1: Verificar se o servidor responde
    try:
        print("📡 Teste 1: Verificando se o servidor está acessível...")
        response = requests.get(MCP_URL, headers=headers, timeout=10)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        print(f"   Response Body (primeiros 500 chars): {response.text[:500]}\n")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Erro ao acessar MCP: {e}\n")
        return
    
    # Teste 2: Tentar uma chamada de documentação
    try:
        print("📚 Teste 2: Tentando acessar documentação...")
        # Tentar diferentes endpoints comuns
        endpoints_to_test = [
            "/docs",
            "/documentation",
            "/api/docs",
            "/",
        ]
        
        for endpoint in endpoints_to_test:
            test_url = f"{MCP_URL.rstrip('/')}{endpoint}"
            try:
                print(f"   Testando: {test_url}")
                response = requests.get(test_url, headers=headers, timeout=10)
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    print(f"   ✅ Sucesso! Resposta: {response.text[:200]}...")
                else:
                    print(f"   ⚠️ Status {response.status_code}: {response.text[:200]}...")
            except Exception as e:
                print(f"   ❌ Erro: {e}")
            print()
    except Exception as e:
        print(f"   ❌ Erro ao testar documentação: {e}\n")
    
    # Teste 3: Verificar token (se for um endpoint de validação)
    try:
        print("🔐 Teste 3: Verificando validade do token...")
        # Tentar usar o token na API normal do ML para verificar se está válido
        ml_api_url = "https://api.mercadolibre.com/users/me"
        ml_headers = {
            "Authorization": f"Bearer {TOKEN}"
        }
        
        response = requests.get(ml_api_url, headers=ml_headers, timeout=10)
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            user_data = response.json()
            print(f"   ✅ Token válido! User ID: {user_data.get('id')}, Nickname: {user_data.get('nickname')}")
        elif response.status_code == 401:
            print(f"   ❌ Token inválido ou expirado")
        else:
            print(f"   ⚠️ Status {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Erro ao verificar token: {e}")

if __name__ == "__main__":
    test_mcp_access()

