#!/usr/bin/env python3
"""
Script para testar sincronização direta de pedido
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.config.database import get_db
from app.services.shipment_service import ShipmentService
from app.services.token_manager import TokenManager
from app.models.saas_models import User

def test_sync_order():
    order_id = "2000008568258421"
    company_id = 15
    
    print(f"🔍 Testando sincronização do pedido: {order_id}")
    print(f"   Company ID: {company_id}")
    print("="*80)
    
    db = next(get_db())
    
    try:
        # Buscar usuário e token
        user_db = db.query(User).filter(
            User.company_id == company_id,
            User.is_active == True
        ).first()
        
        if not user_db:
            print(f"❌ Usuário não encontrado para company_id {company_id}")
            return
        
        token_manager = TokenManager(db)
        access_token = token_manager.get_valid_token(user_db.id)
        
        if not access_token:
            print(f"❌ Token de acesso não encontrado")
            return
        
        print(f"✅ Token obtido: {access_token[:20]}...")
        
        # Criar serviço
        service = ShipmentService(db)
        
        # Sincronizar
        print(f"\n🔄 Iniciando sincronização...")
        result = service.sync_single_order_invoice(order_id, company_id, access_token)
        
        print(f"\n📊 Resultado:")
        print(f"   Success: {result.get('success')}")
        print(f"   Message: {result.get('message')}")
        print(f"   Error: {result.get('error')}")
        print(f"   Status Updated: {result.get('status_updated')}")
        print(f"   Invoice Updated: {result.get('invoice_updated')}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_sync_order()

