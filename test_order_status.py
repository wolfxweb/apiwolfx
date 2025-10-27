#!/usr/bin/env python3
"""
Script para verificar o status de um pedido na API do Mercado Livre
"""
import sys
import os
import json
sys.path.insert(0, os.path.abspath('.'))

from app.config.database import SessionLocal
from app.models.saas_models import Token, MLAccount
import requests

def test_order_status(order_id):
    """Verifica o status real de um pedido na API do ML"""
    
    db = SessionLocal()
    
    try:
        # Buscar token
        account = db.query(MLAccount).filter(MLAccount.company_id == 15).first()
        token = db.query(Token).filter(
            Token.ml_account_id == account.id,
            Token.is_active == True
        ).first()
        
        if not token:
            print("❌ Token não encontrado")
            return
        
        access_token = token.access_token
        
        # Buscar dados do pedido
        order_url = f'https://api.mercadolibre.com/orders/{order_id}'
        headers = {'Authorization': f'Bearer {access_token}'}
        
        print(f"\n{'='*80}")
        print(f"Buscando dados do pedido: {order_id}")
        print(f"{'='*80}")
        print(f"URL: {order_url}")
        
        response = requests.get(order_url, headers=headers, timeout=30)
        
        print(f"Status Code: {response.status_code}\n")
        
        if response.status_code == 200:
            data = response.json()
            
            print("📋 DADOS DO PEDIDO:")
            print(f"  ID: {data.get('id')}")
            print(f"  Status: {data.get('status')}")
            print(f"  Status Detail: {data.get('status_detail')}")
            
            # Verificar shipping
            shipping = data.get('shipping', {})
            if shipping:
                print(f"\n📦 SHIPPING:")
                print(f"  ID: {shipping.get('id')}")
                print(f"  Status: {shipping.get('status')}")
                print(f"  Substatus: {shipping.get('substatus')}")
            
            # Verificar tags (pode ter informação de mediação)
            tags = data.get('tags', [])
            if tags:
                print(f"\n🏷️  TAGS:")
                for tag in tags:
                    print(f"  - {tag}")
            
            # Verificar se tem disputes (reclamações/mediações)
            disputes = data.get('disputes', [])
            if disputes:
                print(f"\n⚠️  DISPUTES (Mediações/Reclamações):")
                for dispute in disputes:
                    print(f"  - ID: {dispute.get('id')}")
                    print(f"    Status: {dispute.get('status')}")
                    print(f"    Type: {dispute.get('type')}")
            
            # Verificar claim_id
            claim_id = data.get('claim_id')
            if claim_id:
                print(f"\n🔴 CLAIM ID (Reclamação): {claim_id}")
            
            # Mostrar JSON completo para análise
            print(f"\n{'='*80}")
            print("JSON COMPLETO:")
            print(f"{'='*80}")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
        else:
            print(f"❌ Erro: {response.status_code}")
            print(response.text[:500])
            
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == '__main__':
    # Testar o pedido mais recente pendente
    test_order_status('2000012697159846')
