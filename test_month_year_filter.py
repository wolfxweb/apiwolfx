#!/usr/bin/env python3
"""
Testar o novo filtro de mês e ano
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from datetime import datetime
import time

def test_month_year_filter():
    """Testar o novo filtro de mês e ano"""
    print("🔧 Testando Novo Filtro de Mês e Ano")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Teste 1: Mês atual (Novembro 2025)
        print("📊 Teste 1: Mês Atual (Novembro 2025)")
        print("-" * 40)
        
        start_time = time.time()
        
        controller = AnalyticsController(db)
        dashboard_nov = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=15,
            specific_month=11,
            specific_year=2025
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"⏱️  Tempo de execução: {execution_time:.2f} segundos")
        
        if dashboard_nov and dashboard_nov.get('success'):
            kpis = dashboard_nov.get('kpis', {})
            billing = dashboard_nov.get('billing', {})
            costs = dashboard_nov.get('costs', {})
            
            print(f"   💰 Receita Total: R$ {kpis.get('total_revenue', 0):.2f}")
            print(f"   📦 Total Pedidos: {kpis.get('total_orders', 0)}")
            print(f"   📦 Produtos Vendidos: {kpis.get('total_sold', 0)}")
            print(f"   💳 Ticket Médio: R$ {kpis.get('avg_ticket', 0):.2f}")
            
            print(f"\n   📊 Billing Novembro:")
            print(f"      💰 Marketing: R$ {billing.get('total_advertising_cost', 0):.2f}")
            print(f"      💰 Sale Fees: R$ {billing.get('total_sale_fees', 0):.2f}")
            print(f"      💰 Shipping: R$ {billing.get('total_shipping_fees', 0):.2f}")
            
            print(f"\n   📊 Costs Novembro:")
            print(f"      💰 Marketing: R$ {costs.get('marketing_cost', 0):.2f}")
            print(f"      💰 ML Fees: R$ {costs.get('ml_fees', 0):.2f}")
            print(f"      💰 Shipping: R$ {costs.get('shipping_fees', 0):.2f}")
        
        # Teste 2: Mês anterior (Outubro 2025)
        print(f"\n📊 Teste 2: Mês Anterior (Outubro 2025)")
        print("-" * 40)
        
        start_time = time.time()
        
        dashboard_out = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=15,
            specific_month=10,
            specific_year=2025
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"⏱️  Tempo de execução: {execution_time:.2f} segundos")
        
        if dashboard_out and dashboard_out.get('success'):
            kpis = dashboard_out.get('kpis', {})
            billing = dashboard_out.get('billing', {})
            costs = dashboard_out.get('costs', {})
            
            print(f"   💰 Receita Total: R$ {kpis.get('total_revenue', 0):.2f}")
            print(f"   📦 Total Pedidos: {kpis.get('total_orders', 0)}")
            print(f"   📦 Produtos Vendidos: {kpis.get('total_sold', 0)}")
            print(f"   💳 Ticket Médio: R$ {kpis.get('avg_ticket', 0):.2f}")
            
            print(f"\n   📊 Billing Outubro:")
            print(f"      💰 Marketing: R$ {billing.get('total_advertising_cost', 0):.2f}")
            print(f"      💰 Sale Fees: R$ {billing.get('total_sale_fees', 0):.2f}")
            print(f"      💰 Shipping: R$ {billing.get('total_shipping_fees', 0):.2f}")
            
            print(f"\n   📊 Costs Outubro:")
            print(f"      💰 Marketing: R$ {costs.get('marketing_cost', 0):.2f}")
            print(f"      💰 ML Fees: R$ {costs.get('ml_fees', 0):.2f}")
            print(f"      💰 Shipping: R$ {costs.get('shipping_fees', 0):.2f}")
        
        # Comparação
        print(f"\n📊 Comparação Novembro vs Outubro:")
        print("-" * 40)
        
        if (dashboard_nov and dashboard_nov.get('success') and 
            dashboard_out and dashboard_out.get('success')):
            
            revenue_nov = dashboard_nov.get('kpis', {}).get('total_revenue', 0)
            revenue_out = dashboard_out.get('kpis', {}).get('total_revenue', 0)
            
            marketing_nov = dashboard_nov.get('billing', {}).get('total_advertising_cost', 0)
            marketing_out = dashboard_out.get('billing', {}).get('total_advertising_cost', 0)
            
            print(f"   💰 Receita Novembro: R$ {revenue_nov:.2f}")
            print(f"   💰 Receita Outubro: R$ {revenue_out:.2f}")
            print(f"   📈 Diferença: R$ {revenue_nov - revenue_out:.2f}")
            
            print(f"\n   💰 Marketing Novembro: R$ {marketing_nov:.2f}")
            print(f"   💰 Marketing Outubro: R$ {marketing_out:.2f}")
            print(f"   📈 Diferença: R$ {marketing_nov - marketing_out:.2f}")
            
            if revenue_nov != revenue_out or marketing_nov != marketing_out:
                print(f"\n   ✅ FILTRO FUNCIONANDO! Dados diferentes entre os meses")
            else:
                print(f"\n   ⚠️  Dados iguais - verificar se há dados para Novembro")
        
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
    print("🔧 Testando Novo Filtro de Mês e Ano")
    print("=" * 60)
    print()
    
    success = test_month_year_filter()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE DO FILTRO CONCLUÍDO!")
        print("💡 Próximos passos:")
        print("   1. Recriar container sem cache")
        print("   2. Testar no navegador")
        print("   3. Verificar se mês atual está selecionado por padrão")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
