#!/usr/bin/env python3
"""
Testar método _get_billing_data diretamente
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from datetime import datetime

def test_get_billing_data():
    """Testar método _get_billing_data diretamente"""
    print("🔍 Testando Método _get_billing_data")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        controller = AnalyticsController(db)
        
        # Período de Outubro de 2025
        october_start = datetime(2025, 10, 1)
        october_end = datetime(2025, 10, 31, 23, 59, 59)
        
        print(f"📅 Período: {october_start.strftime('%d/%m/%Y')} a {october_end.strftime('%d/%m/%Y')}")
        
        # Testar método _get_billing_data diretamente
        billing_data = controller._get_billing_data(company_id, october_start, october_end)
        
        print(f"\n📊 Resultado do _get_billing_data:")
        if billing_data:
            print(f"   🎯 Marketing: R$ {billing_data.get('total_advertising_cost', 0):.2f}")
            print(f"   💳 Sale Fees: R$ {billing_data.get('total_sale_fees', 0):.2f}")
            print(f"   🚚 Shipping: R$ {billing_data.get('total_shipping_fees', 0):.2f}")
            print(f"   📅 Períodos: {billing_data.get('periods_count', 0)}")
        else:
            print(f"   ❌ Nenhum dado retornado")
        
        # Testar com período mais amplo
        print(f"\n📊 Testando com período mais amplo (últimos 30 dias):")
        from datetime import timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        billing_data_30d = controller._get_billing_data(company_id, start_date, end_date)
        
        if billing_data_30d:
            print(f"   🎯 Marketing: R$ {billing_data_30d.get('total_advertising_cost', 0):.2f}")
            print(f"   💳 Sale Fees: R$ {billing_data_30d.get('total_sale_fees', 0):.2f}")
            print(f"   🚚 Shipping: R$ {billing_data_30d.get('total_shipping_fees', 0):.2f}")
            print(f"   📅 Períodos: {billing_data_30d.get('periods_count', 0)}")
        else:
            print(f"   ❌ Nenhum dado retornado")
        
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
    print("🔍 Testando Método _get_billing_data")
    print("=" * 60)
    print()
    
    success = test_get_billing_data()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE CONCLUÍDO!")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
