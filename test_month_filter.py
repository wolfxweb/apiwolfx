#!/usr/bin/env python3
"""
Testar filtro de mês específico
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from datetime import datetime

def test_month_filter():
    """Testar filtro de mês específico"""
    print("🔍 Testando Filtro de Mês Específico")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        controller = AnalyticsController(db)
        
        # Testar diferentes meses
        test_months = [
            ("Outubro 2025", 31),
            ("Setembro 2025", 30),
            ("Agosto 2025", 31),
            ("Julho 2025", 31)
        ]
        
        for month_name, days in test_months:
            print(f"\n📅 {month_name} ({days} dias):")
            print("-" * 40)
            
            # Buscar dados do dashboard
            dashboard_data = controller.get_sales_dashboard(company_id, days)
            
            if dashboard_data and dashboard_data.get('success'):
                # KPIs
                kpis = dashboard_data.get('kpis', {})
                print(f"   💰 Receita: R$ {kpis.get('total_revenue', 0):.2f}")
                print(f"   📦 Pedidos: {kpis.get('total_orders', 0)}")
                
                # Custos
                costs = dashboard_data.get('costs', {})
                print(f"   🎯 Marketing: R$ {costs.get('marketing_cost', 0):.2f}")
                print(f"   💳 Sale Fees: R$ {costs.get('ml_fees', 0):.2f}")
                print(f"   🚚 Shipping: R$ {costs.get('shipping_fees', 0):.2f}")
                
                # Billing Data
                billing = dashboard_data.get('billing', {})
                if billing:
                    print(f"   📊 Billing: Marketing R$ {billing.get('total_advertising_cost', 0):.2f}, Sale Fees R$ {billing.get('total_sale_fees', 0):.2f}, Shipping R$ {billing.get('total_shipping_fees', 0):.2f}")
                else:
                    print(f"   ❌ Nenhum dado de billing")
            else:
                print(f"   ❌ Erro: {dashboard_data.get('error', 'Desconhecido')}")
        
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
    print("🔍 Testando Filtro de Mês Específico")
    print("=" * 60)
    print()
    
    success = test_month_filter()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE CONCLUÍDO!")
        print("📊 Verifique se os filtros estão funcionando no dashboard")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
