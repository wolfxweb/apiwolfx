#!/usr/bin/env python3
"""
Teste da busca de SKU com company_id específico
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from app.services.internal_product_service import InternalProductService
from app.controllers.pricing_analysis_controller import PricingAnalysisController

def test_sku_search(sku: str, company_id: int):
    """Testa a busca de SKU com company_id"""
    db = SessionLocal()
    
    try:
        print(f"🔍 Testando busca para SKU: '{sku}', Company ID: {company_id}\n")
        
        # Testar o serviço diretamente
        service = InternalProductService(db)
        result = service.get_pricing_data_by_sku(sku, company_id)
        
        print("📊 Resultado do serviço:")
        if result.get("success"):
            print(f"   ✅ Sucesso!")
            pricing_data = result.get("pricing_data", {})
            print(f"   Product ID: {pricing_data.get('product_id')}")
            print(f"   Name: {pricing_data.get('name')}")
            print(f"   Internal SKU: {pricing_data.get('internal_sku')}")
            print(f"   Cost Price: {pricing_data.get('cost_price')}")
        else:
            print(f"   ❌ Erro: {result.get('error')}")
        
        # Testar o controller
        print("\n📊 Resultado do controller:")
        controller = PricingAnalysisController(db)
        result2 = controller.get_pricing_analysis_by_sku(sku, company_id)
        
        if result2.get("success"):
            print(f"   ✅ Sucesso!")
            analysis = result2.get("analysis", {})
            internal_product = analysis.get("internal_product", {})
            print(f"   Product ID: {internal_product.get('product_id')}")
            print(f"   Name: {internal_product.get('name')}")
            print(f"   Internal SKU: {internal_product.get('internal_sku')}")
        else:
            print(f"   ❌ Erro: {result2.get('error')}")
        
        # Verificar se há produtos com company_id diferente
        print(f"\n🔍 Verificando produtos com SKU '{sku}' em outras empresas:")
        from app.models.saas_models import InternalProduct
        all_products = db.query(InternalProduct).filter(
            InternalProduct.internal_sku == sku
        ).all()
        
        for p in all_products:
            match = "✅" if p.company_id == company_id else "⚠️"
            print(f"   {match} ID={p.id}, Company={p.company_id}, Status={p.status}, SKU='{p.internal_sku}'")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    sku = "M24fb-610a"
    company_id = 27  # Company ID do produto encontrado
    
    if len(sys.argv) > 1:
        sku = sys.argv[1]
    if len(sys.argv) > 2:
        company_id = int(sys.argv[2])
    
    test_sku_search(sku, company_id)

