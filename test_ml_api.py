#!/usr/bin/env python3
"""
Script para testar requisição na API do Mercado Livre
"""
import requests
import sys
import os
sys.path.append('/app')

from app.config.database import get_db
from app.services.token_manager import TokenManager

def test_ml_api():
    """Testa requisição na API do ML"""
    print("🔍 Testando API do Mercado Livre...")
    
    # Obter sessão do banco
    db = next(get_db())
    
    # Criar TokenManager
    token_manager = TokenManager(db)
    
    # Buscar token válido para company_id 15
    # Vou tentar diferentes user_ids para encontrar um que tenha token
    user_ids_to_try = [8, 2, 1, 3, 4, 5]
    token = None
    
    for user_id in user_ids_to_try:
        print(f"📋 Tentando buscar token para user_id={user_id}...")
        token = token_manager.get_valid_token(user_id)
        if token:
            print(f"✅ Token encontrado para user_id={user_id}")
            break
        else:
            print(f"❌ Nenhum token válido para user_id={user_id}")
    
    if not token:
        print("❌ Nenhum token válido encontrado para nenhum user_id testado")
        return
    
    if not token:
        print("❌ Nenhum token válido encontrado")
        return
    
    print(f"✅ Token encontrado: {token[:20]}...")
    
    # Testar requisição na API do ML
    item_id = "MLB5069302578"
    url = f"https://api.mercadolibre.com/items/{item_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"🌐 Fazendo requisição para: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Requisição bem-sucedida!")
            print(f"📦 Produto: {data.get('title', 'N/A')}")
            print(f"💰 Preço: R$ {data.get('price', 'N/A')}")
            print(f"📈 Quantidade disponível: {data.get('available_quantity', 'N/A')}")
            print(f"📊 Quantidade vendida: {data.get('sold_quantity', 'N/A')}")
            print(f"🔄 Status: {data.get('status', 'N/A')}")
            print(f"🏷️ SKU: {data.get('seller_sku', 'N/A')}")
            
            # Verificar se tem preço promocional
            if 'promotions' in data and data['promotions']:
                for promotion in data['promotions']:
                    if promotion.get('status') == 'active':
                        print(f"🎯 Preço promocional: R$ {promotion.get('price', 'N/A')}")
                        break
            else:
                print("ℹ️ Nenhuma promoção ativa encontrada")
                
        else:
            print(f"❌ Erro na requisição: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {str(e)}")
    
    finally:
        db.close()

if __name__ == "__main__":
    test_ml_api()
