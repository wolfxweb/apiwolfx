#!/usr/bin/env python3
"""
Testar controller corrigido com date_approved
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from datetime import datetime
import time

def test_corrected_controller():
    """Testar controller corrigido"""
    print("🔧 Testando Controller Corrigido com date_approved")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Teste: Outubro 2025
        print("📊 Teste: Outubro 2025 (usando date_approved)")
        print("-" * 40)
        
        start_time = time.time()
        
        controller = AnalyticsController(db)
        dashboard_data = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=15,
            period_days=31,
            specific_month=10,
            specific_year=2025
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"⏱️  Tempo de execução: {execution_time:.2f} segundos")
        
        if dashboard_data and dashboard_data.get('success'):
            kpis = dashboard_data.get('kpis', {})
            costs = dashboard_data.get('costs', {})
            billing = dashboard_data.get('billing', {})
            
            print(f"   💰 Receita Total: R$ {kpis.get('total_revenue', 0):.2f}")
            print(f"   📦 Total Pedidos: {kpis.get('total_orders', 0)}")
            print(f"   📦 Produtos Vendidos: {kpis.get('total_sold', 0)}")
            print(f"   💳 Ticket Médio: R$ {kpis.get('avg_ticket', 0):.2f}")
            print(f"   ❌ Cancelados: {kpis.get('cancelled_orders', 0)} (R$ {kpis.get('cancelled_value', 0):.2f})")
            print(f"   🔄 Devoluções: {kpis.get('returns_count', 0)} (R$ {kpis.get('returns_value', 0):.2f})")
            
            print(f"\n   💰 Custos:")
            print(f"      📊 ML Fees: R$ {costs.get('ml_fees', 0):.2f} ({costs.get('ml_fees_percent', 0):.1f}%)")
            print(f"      🚚 Shipping: R$ {costs.get('shipping_fees', 0):.2f} ({costs.get('shipping_fees_percent', 0):.1f}%)")
            print(f"      📢 Marketing: R$ {costs.get('marketing_cost', 0):.2f} ({costs.get('marketing_percent', 0):.1f}%)")
            print(f"      📦 Produtos: R$ {costs.get('product_cost', 0):.2f} ({costs.get('product_cost_percent', 0):.1f}%)")
            print(f"      💰 Total Custos: R$ {costs.get('total_costs', 0):.2f} ({costs.get('total_costs_percent', 0):.1f}%)")
            
            if billing:
                print(f"\n   📊 Billing Data:")
                print(f"      📢 Advertising: R$ {billing.get('total_advertising_cost', 0):.2f}")
                print(f"      💳 Sale Fees: R$ {billing.get('total_sale_fees', 0):.2f}")
                print(f"      🚚 Shipping Fees: R$ {billing.get('total_shipping_fees', 0):.2f}")
                print(f"      📅 Períodos: {billing.get('periods_count', 0)}")
            
            # Comparar com dados esperados
            print(f"\n📊 Comparação com Dados Esperados:")
            print(f"   🎯 Esperado (ML): ~R$ 28.457 (Vendas concluídas)")
            print(f"   🎯 Esperado (ML): ~R$ 8.698 (Tarifas e investimentos)")
            print(f"   ✅ Atual: R$ {kpis.get('total_revenue', 0):.2f}")
            
            # Verificar se está mais próximo dos valores do ML
            expected_revenue = 28457
            actual_revenue = kpis.get('total_revenue', 0)
            difference_percent = abs(actual_revenue - expected_revenue) / expected_revenue * 100
            
            print(f"   📊 Diferença: {difference_percent:.1f}%")
            
            if difference_percent < 20:  # Menos de 20% de diferença
                print(f"   ✅ Valores estão mais próximos do ML!")
            else:
                print(f"   ⚠️  Ainda há diferença significativa")
            
        else:
            print(f"   ❌ Erro: {dashboard_data.get('error', 'Desconhecido')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def main():
    """Função principal"""
    print("🔧 Testando Controller Corrigido com date_approved")
    print("=" * 60)
    print()
    
    success = test_corrected_controller()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE DO CONTROLLER CORRIGIDO CONCLUÍDO!")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
