#!/usr/bin/env python3
"""
Script para testar a API de pedidos do Mercado Livre
"""
import sys
import os
import requests
import json
from datetime import datetime

# Adicionar o diretório do projeto ao path
sys.path.append('/Users/wolfx/Documents/wolfx/apiwolfx')

from app.config.database import get_db
from app.models.saas_models import MLAccount, MLAccountStatus, Token
from sqlalchemy.orm import Session

def test_orders_api():
    """Testa a API de pedidos do Mercado Livre"""
    
    print("=== TESTE DA API DE PEDIDOS DO MERCADO LIVRE ===\n")
    
    # Conectar ao banco
    db = next(get_db())
    
    try:
        # Buscar contas ML ativas
        accounts = db.query(MLAccount).filter(
            MLAccount.status == MLAccountStatus.ACTIVE
        ).all()
        
        if not accounts:
            print("❌ Nenhuma conta ML ativa encontrada")
            return
        
        print(f"✅ Encontradas {len(accounts)} contas ML ativas")
        
        for account in accounts:
            print(f"\n--- Testando conta: {account.nickname} (ID: {account.id}) ---")
            
            # Buscar token ativo
            token = db.query(Token).filter(
                Token.ml_account_id == account.id,
                Token.is_active == True
            ).first()
            
            if not token:
                print(f"❌ Token ativo não encontrado para conta {account.nickname}")
                continue
            
            print(f"✅ Token encontrado: {token.access_token[:20]}...")
            
            # Testar API de pedidos
            headers = {"Authorization": f"Bearer {token.access_token}"}
            orders_url = "https://api.mercadolibre.com/orders/search"
            params = {
                "seller": account.ml_user_id,
                "limit": 10,
                "offset": 0,
                "sort": "date_desc"
            }
            
            print(f"🔍 Buscando pedidos para seller_id: {account.ml_user_id}")
            print(f"📡 URL: {orders_url}")
            print(f"📋 Parâmetros: {params}")
            
            try:
                response = requests.get(orders_url, headers=headers, params=params, timeout=30)
                
                print(f"📊 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    orders = data.get("results", [])
                    total = data.get("paging", {}).get("total", 0)
                    
                    print(f"✅ Sucesso! Encontrados {len(orders)} pedidos (total: {total})")
                    
                    if orders:
                        print("\n📦 Primeiros pedidos encontrados:")
                        for i, order in enumerate(orders[:3]):
                            order_id = order.get("id")
                            date_created = order.get("date_created")
                            status = order.get("status")
                            print(f"  {i+1}. ID: {order_id}, Data: {date_created}, Status: {status}")
                    else:
                        print("⚠️  Nenhum pedido encontrado")
                        
                elif response.status_code == 401:
                    print("❌ Token expirado ou inválido")
                elif response.status_code == 403:
                    print("❌ Acesso negado - verificar permissões")
                else:
                    print(f"❌ Erro na API: {response.status_code}")
                    print(f"📄 Resposta: {response.text[:200]}...")
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ Erro na requisição: {e}")
            except Exception as e:
                print(f"❌ Erro inesperado: {e}")
    
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_orders_api()
