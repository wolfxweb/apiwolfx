#!/usr/bin/env python3
"""
Script para testar a sincronização de pedidos com filtro de data
"""
import sys
import os
import requests
import json
from datetime import datetime, timedelta

# Adicionar o diretório do projeto ao path
sys.path.append('/Users/wolfx/Documents/wolfx/apiwolfx')

from app.config.database import get_db
from app.models.saas_models import MLAccount, MLAccountStatus, Token
from app.services.ml_orders_service import MLOrdersService
from sqlalchemy.orm import Session

def test_sync_with_date_filter():
    """Testa a sincronização com filtro de data"""
    
    print("=== TESTE DE SINCRONIZAÇÃO COM FILTRO DE DATA ===\n")
    
    # Conectar ao banco
    db = next(get_db())
    
    try:
        # Buscar primeira conta ML ativa
        account = db.query(MLAccount).filter(
            MLAccount.status == MLAccountStatus.ACTIVE
        ).first()
        
        if not account:
            print("❌ Nenhuma conta ML ativa encontrada")
            return
        
        print(f"✅ Testando conta: {account.nickname} (ID: {account.id})")
        
        # Buscar token ativo
        token = db.query(Token).filter(
            Token.ml_account_id == account.id,
            Token.is_active == True
        ).first()
        
        if not token:
            print(f"❌ Token ativo não encontrado para conta {account.nickname}")
            return
        
        print(f"✅ Token encontrado: {token.access_token[:20]}...")
        
        # Testar API com filtro de data
        headers = {"Authorization": f"Bearer {token.access_token}"}
        orders_url = "https://api.mercadolibre.com/orders/search"
        
        # Testar diferentes períodos
        test_periods = [
            {"days": 1, "name": "Últimas 24 horas"},
            {"days": 7, "name": "Últimos 7 dias"},
            {"days": 30, "name": "Últimos 30 dias"}
        ]
        
        for period in test_periods:
            print(f"\n--- {period['name']} ---")
            
            # Calcular data de início
            start_date = datetime.now() - timedelta(days=period['days'])
            start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.000-04:00")
            
            params = {
                "seller": account.ml_user_id,
                "limit": 10,
                "offset": 0,
                "sort": "date_desc",
                "order.date_created.from": start_date_str
            }
            
            print(f"📅 Data início: {start_date_str}")
            print(f"📋 Parâmetros: {params}")
            
            try:
                response = requests.get(orders_url, headers=headers, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    orders = data.get("results", [])
                    total = data.get("paging", {}).get("total", 0)
                    
                    print(f"✅ Encontrados {len(orders)} pedidos (total: {total})")
                    
                    if orders:
                        print("📦 Pedidos encontrados:")
                        for i, order in enumerate(orders[:3]):
                            order_id = order.get("id")
                            date_created = order.get("date_created")
                            status = order.get("status")
                            print(f"  {i+1}. ID: {order_id}, Data: {date_created}, Status: {status}")
                    else:
                        print("⚠️  Nenhum pedido encontrado neste período")
                        
                else:
                    print(f"❌ Erro na API: {response.status_code}")
                    print(f"📄 Resposta: {response.text[:200]}...")
                    
            except Exception as e:
                print(f"❌ Erro na requisição: {e}")
        
        # Testar sincronização real
        print(f"\n--- TESTE DE SINCRONIZAÇÃO REAL ---")
        service = MLOrdersService(db)
        
        result = service.sync_orders_from_api(
            ml_account_id=account.id,
            company_id=account.company_id,
            limit=10,
            is_full_import=False
        )
        
        print(f"📊 Resultado da sincronização:")
        print(f"  Sucesso: {result.get('success', False)}")
        if result.get('success'):
            print(f"  Pedidos criados: {result.get('saved_count', 0)}")
            print(f"  Pedidos atualizados: {result.get('updated_count', 0)}")
            print(f"  Total processados: {result.get('total_processed', 0)}")
        else:
            print(f"  Erro: {result.get('error', 'Erro desconhecido')}")
    
    except Exception as e:
        print(f"❌ Erro geral: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_sync_with_date_filter()
