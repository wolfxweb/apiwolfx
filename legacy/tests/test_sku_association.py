#!/usr/bin/env python3
"""
Teste de associação de múltiplos anúncios ao mesmo SKU
"""
import sys
sys.path.append('/Users/wolfx/Documents/wolfx/apiwolfx')

from app.config.database import get_db
from app.services.sku_management_service import SKUManagementService

def test_sku_association():
    """Testa associação de múltiplos anúncios ao mesmo SKU"""
    
    print("=== TESTE DE ASSOCIAÇÃO DE SKUs ===\n")
    
    db = next(get_db())
    try:
        service = SKUManagementService(db)
        company_id = 13  # ID da empresa de teste
        
        # Simular cenário: 2 anúncios ML com mesmo SKU
        sku = "IPHONE15-128GB"
        
        print(f"🔍 Testando SKU: {sku}")
        print(f"🏢 Empresa ID: {company_id}")
        
        # Primeiro anúncio
        print("\n1️⃣ Registrando primeiro anúncio...")
        result1 = service.register_sku(
            sku=sku,
            platform="mercadolivre",
            platform_item_id="MLB4166851761",
            company_id=company_id,
            product_id=1
        )
        
        print(f"Resultado: {result1.get('action', 'unknown')}")
        print(f"Mensagem: {result1.get('message', 'N/A')}")
        
        # Segundo anúncio (mesmo SKU)
        print("\n2️⃣ Registrando segundo anúncio (mesmo SKU)...")
        result2 = service.register_sku(
            sku=sku,
            platform="mercadolivre", 
            platform_item_id="MLB5598362090",
            company_id=company_id,
            product_id=2
        )
        
        print(f"Resultado: {result2.get('action', 'unknown')}")
        print(f"Mensagem: {result2.get('message', 'N/A')}")
        
        # Verificar histórico
        print("\n📋 Histórico do SKU:")
        history = service.get_sku_history(sku, company_id)
        
        if history.get("success"):
            print(f"SKU: {history['sku']}")
            print(f"Total de anúncios: {history['total_announcements']}")
            
            for i, announcement in enumerate(history['announcements'], 1):
                print(f"\n  Anúncio {i}:")
                print(f"    ID: {announcement['id']}")
                print(f"    Platform Item ID: {announcement['platform_item_id']}")
                print(f"    Status: {announcement['status']}")
                print(f"    Criado em: {announcement['created_at']}")
        else:
            print(f"❌ Erro: {history.get('error')}")
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_sku_association()

