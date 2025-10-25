#!/usr/bin/env python3
"""
Testar Outubro específico
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from datetime import datetime

def test_october_specific():
    """Testar Outubro específico"""
    print("🔍 Testando Outubro Específico")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        controller = AnalyticsController(db)
        
        # Testar com datas específicas de Outubro
        october_start = datetime(2025, 10, 1)
        october_end = datetime(2025, 10, 31, 23, 59, 59)
        
        print(f"📅 Período: {october_start.strftime('%d/%m/%Y')} a {october_end.strftime('%d/%m/%Y')}")
        
        # Testar _get_billing_data com datas específicas
        billing_data = controller._get_billing_data(company_id, october_start, october_end)
        
        print(f"\n📊 Dados de billing para Outubro:")
        if billing_data:
            print(f"   🎯 Marketing: R$ {billing_data.get('total_advertising_cost', 0):.2f}")
            print(f"   💳 Sale Fees: R$ {billing_data.get('total_sale_fees', 0):.2f}")
            print(f"   🚚 Shipping: R$ {billing_data.get('total_shipping_fees', 0):.2f}")
            print(f"   📅 Períodos: {billing_data.get('periods_count', 0)}")
        else:
            print(f"   ❌ Nenhum dado retornado")
        
        # Testar _calculate_costs_with_taxes com datas específicas
        costs_data = controller._calculate_costs_with_taxes(company_id, 27000, 446, october_start, october_end)
        
        print(f"\n💰 Custos calculados para Outubro:")
        print(f"   🎯 Marketing: R$ {costs_data.get('marketing_cost', 0):.2f}")
        print(f"   💳 Sale Fees: R$ {costs_data.get('ml_fees', 0):.2f}")
        print(f"   🚚 Shipping: R$ {costs_data.get('shipping_fees', 0):.2f}")
        print(f"   💰 Total Custos: R$ {costs_data.get('total_costs', 0):.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def main():
    """Função principal"""
    print("🔍 Testando Outubro Específico")
    print("=" * 60)
    print()
    
    success = test_october_specific()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE CONCLUÍDO!")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
