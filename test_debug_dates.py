#!/usr/bin/env python3
"""
Debug das datas no dashboard
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from datetime import datetime, timedelta

def test_debug_dates():
    """Debug das datas no dashboard"""
    print("🔍 Debug das Datas no Dashboard")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        controller = AnalyticsController(db)
        
        # Simular a lógica do get_sales_dashboard
        period_days = 31
        end_date = datetime.now()
        
        print(f"📅 end_date: {end_date}")
        print(f"📅 end_date.year: {end_date.year}")
        print(f"📅 end_date.month: {end_date.month}")
        print(f"📅 period_days: {period_days}")
        
        # Verificar condição
        condition = end_date.year == 2025 and end_date.month == 10
        print(f"🔍 Condição (end_date.year == 2025 and end_date.month == 10): {condition}")
        
        if condition:
            start_date = datetime(2025, 10, 1)
            end_date = datetime(2025, 10, 31, 23, 59, 59)
            print(f"🎯 Usando datas específicas de Outubro: {start_date} a {end_date}")
        else:
            start_date = end_date - timedelta(days=period_days)
            print(f"📅 Usando últimos {period_days} dias: {start_date} a {end_date}")
        
        # Testar _get_billing_data com as datas calculadas
        billing_data = controller._get_billing_data(company_id, start_date, end_date)
        
        print(f"\n📊 Dados de billing com datas calculadas:")
        if billing_data:
            print(f"   🎯 Marketing: R$ {billing_data.get('total_advertising_cost', 0):.2f}")
            print(f"   💳 Sale Fees: R$ {billing_data.get('total_sale_fees', 0):.2f}")
            print(f"   🚚 Shipping: R$ {billing_data.get('total_shipping_fees', 0):.2f}")
            print(f"   📅 Períodos: {billing_data.get('periods_count', 0)}")
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
    print("🔍 Debug das Datas no Dashboard")
    print("=" * 60)
    print()
    
    success = test_debug_dates()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE CONCLUÍDO!")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
