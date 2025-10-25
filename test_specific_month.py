#!/usr/bin/env python3
"""
Testar filtro de mês específico com parâmetros
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from datetime import datetime

def test_specific_month():
    """Testar filtro de mês específico com parâmetros"""
    print("🔍 Testando Filtro de Mês Específico com Parâmetros")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        controller = AnalyticsController(db)
        
        # Testar Outubro de 2025 com parâmetros específicos
        print(f"📅 Testando Outubro de 2025 com parâmetros específicos:")
        print("-" * 50)
        
        dashboard_data = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=15,  # Usar ID fixo para teste
            period_days=31,
            specific_month=10,
            specific_year=2025
        )
        
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
        
        # Testar Setembro de 2025
        print(f"\n📅 Testando Setembro de 2025:")
        print("-" * 50)
        
        dashboard_data = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=15,
            period_days=30,
            specific_month=9,
            specific_year=2025
        )
        
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
    print("🔍 Testando Filtro de Mês Específico com Parâmetros")
    print("=" * 60)
    print()
    
    success = test_specific_month()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE CONCLUÍDO!")
        print("📊 Verifique se os filtros estão funcionando no dashboard")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
