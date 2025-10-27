#!/usr/bin/env python3
"""
Script de teste para sincronização de notas fiscais
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.config.database import SessionLocal
from app.models.saas_models import Token, MLAccount, MLOrder
from app.services.shipment_service import ShipmentService
import requests

def test_invoice_sync():
    """Testa a sincronização de nota fiscal para um pedido específico"""
    
    db = SessionLocal()
    
    try:
        # Buscar pedido
        order_id = '2000013542959906'
        order = db.query(MLOrder).filter(MLOrder.ml_order_id == order_id).first()
        
        if not order:
            print(f"❌ Pedido {order_id} não encontrado")
            return
        
        print(f"\n{'='*80}")
        print(f"PEDIDO: {order_id}")
        print(f"{'='*80}")
        print(f"Company ID: {order.company_id}")
        print(f"Pack ID: {order.pack_id}")
        print(f"Shipping ID: {order.shipping_id}")
        print(f"Status: {order.status}")
        print(f"Invoice Emitted: {order.invoice_emitted}")
        
        # Buscar token
        account = db.query(MLAccount).filter(MLAccount.company_id == order.company_id).first()
        if not account:
            print("❌ Account não encontrada")
            return
        
        token = db.query(Token).filter(
            Token.ml_account_id == account.id,
            Token.is_active == True
        ).first()
        
        if not token:
            print("❌ Token não encontrado")
            return
        
        access_token = token.access_token
        
        print(f"\n🔑 Token obtido: {access_token[:30]}...")
        
        # TESTE 1: Verificar se a API do ML retorna a nota fiscal
        print(f"\n{'='*80}")
        print("TESTE 1: Verificar API do Mercado Livre")
        print(f"{'='*80}")
        
        seller_id = '1979794691'
        invoice_url = f'https://api.mercadolibre.com/users/{seller_id}/invoices/orders/{order_id}'
        headers = {'Authorization': f'Bearer {access_token}'}
        
        print(f"GET {invoice_url}")
        response = requests.get(invoice_url, headers=headers, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ NF encontrada na API do ML!")
            print(f"   Status: {data.get('status')}")
            print(f"   Invoice Number: {data.get('invoice_number')}")
            print(f"   Invoice Series: {data.get('invoice_series')}")
            
            attributes = data.get('attributes', {})
            print(f"   Key: {attributes.get('invoice_key')}")
        else:
            print(f"❌ Erro ao buscar NF na API: {response.text[:200]}")
            return
        
        # TESTE 2: Sincronizar usando o serviço
        print(f"\n{'='*80}")
        print("TESTE 2: Sincronizar usando ShipmentService")
        print(f"{'='*80}")
        
        service = ShipmentService(db)
        result = service.sync_single_order_invoice(order_id, order.company_id, access_token)
        
        print(f"\nResultado:")
        print(f"  Success: {result.get('success')}")
        print(f"  Message: {result.get('message')}")
        print(f"  Status Updated: {result.get('status_updated')}")
        print(f"  Invoice Updated: {result.get('invoice_updated')}")
        
        # Verificar se foi atualizado no banco
        db.refresh(order)
        print(f"\n{'='*80}")
        print("DADOS ATUALIZADOS NO BANCO:")
        print(f"{'='*80}")
        print(f"Invoice Emitted: {order.invoice_emitted}")
        print(f"Invoice Number: {order.invoice_number}")
        print(f"Invoice Series: {order.invoice_series}")
        print(f"Invoice Key: {order.invoice_key}")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == '__main__':
    test_invoice_sync()
