#!/usr/bin/env python3
"""
Testar dados de Marketing para Outubro 2025
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from datetime import datetime
import time

def test_october_marketing():
    """Testar dados de Marketing para Outubro 2025"""
    print("🔍 Testando Dados de Marketing para Outubro 2025")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Teste: Dashboard com Outubro 2025
        print("📊 Teste: Dashboard com Outubro 2025")
        print("-" * 40)
        
        start_time = time.time()
        
        controller = AnalyticsController(db)
        dashboard_data = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=15,
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
            
            print(f"\n   📊 Custos (Fonte dos Dados):")
            print(f"      💰 Marketing: R$ {costs.get('marketing_cost', 0):.2f}")
            print(f"      💰 ML Fees: R$ {costs.get('ml_fees', 0):.2f}")
            print(f"      💰 Shipping: R$ {costs.get('shipping_fees', 0):.2f}")
            print(f"      💰 Descontos: R$ {costs.get('discounts', 0):.2f}")
            print(f"      💰 Total Custos: R$ {costs.get('total_costs', 0):.2f}")
            
            print(f"\n   📊 Billing (Dados Reais do Mercado Livre):")
            print(f"      💰 Marketing: R$ {billing.get('total_advertising_cost', 0):.2f}")
            print(f"      💰 Sale Fees: R$ {billing.get('total_sale_fees', 0):.2f}")
            print(f"      💰 Shipping: R$ {billing.get('total_shipping_fees', 0):.2f}")
            print(f"      📅 Períodos: {billing.get('periods_count', 0)}")
            
            # Análise da fonte dos dados
            marketing_costs = costs.get('marketing_cost', 0)
            marketing_billing = billing.get('total_advertising_cost', 0)
            
            print(f"\n📊 Análise da Fonte dos Dados:")
            print("-" * 40)
            
            if marketing_billing > 0:
                print(f"   ✅ Marketing vem de BILLING: R$ {marketing_billing:.2f}")
                print(f"   📊 Fonte: Dados reais do Mercado Livre")
            else:
                print(f"   ❌ Marketing vem de CUSTOS: R$ {marketing_costs:.2f}")
                print(f"   📊 Fonte: Dados dos pedidos ou estimativas")
            
            if marketing_costs > 0 and marketing_billing == 0:
                print(f"   ⚠️  PROBLEMA: Marketing está vindo dos custos em vez do billing")
                print(f"   💡 Solução: Verificar se há dados de billing para Outubro")
            elif marketing_costs > 0 and marketing_billing > 0:
                print(f"   ✅ Marketing vem de ambas as fontes (billing + custos)")
            elif marketing_costs == 0 and marketing_billing == 0:
                print(f"   ❌ Nenhum dado de marketing encontrado")
            
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
    print("🔍 Testando Dados de Marketing para Outubro 2025")
    print("=" * 60)
    print()
    
    success = test_october_marketing()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE CONCLUÍDO!")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
