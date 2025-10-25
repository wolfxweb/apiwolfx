#!/usr/bin/env python3
"""
Debug do Marketing para Setembro - verificar se está somando com Outubro
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from sqlalchemy import text
from datetime import datetime
import time

def debug_september_marketing():
    """Debug do Marketing para Setembro"""
    print("🔍 Debug do Marketing para Setembro 2025")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Teste 1: Verificar períodos de billing que se sobrepõem a Setembro
        print("📊 Teste 1: Períodos de Billing que se Sobrepoem a Setembro")
        print("-" * 40)
        
        result_billing = db.execute(text("""
            SELECT 
                period_from,
                period_to,
                advertising_cost,
                sale_fees,
                shipping_fees,
                is_closed
            FROM ml_billing_periods 
            WHERE company_id = :company_id
            AND period_from <= :end_date 
            AND period_to >= :start_date
        """), {
            "company_id": company_id,
            "start_date": datetime(2025, 9, 1),
            "end_date": datetime(2025, 9, 30, 23, 59, 59)
        })
        
        billing_data = result_billing.fetchall()
        
        if billing_data:
            total_marketing = sum(float(row.advertising_cost or 0) for row in billing_data)
            total_sale_fees = sum(float(row.sale_fees or 0) for row in billing_data)
            total_shipping = sum(float(row.shipping_fees or 0) for row in billing_data)
            
            print(f"   📊 Períodos encontrados: {len(billing_data)}")
            print(f"   💰 Marketing Total: R$ {total_marketing:.2f}")
            print(f"   💰 Sale Fees Total: R$ {total_sale_fees:.2f}")
            print(f"   💰 Shipping Total: R$ {total_shipping:.2f}")
            
            for row in billing_data:
                print(f"      📅 {row.period_from} a {row.period_to}")
                print(f"         💰 Marketing: R$ {float(row.advertising_cost or 0):.2f}")
                print(f"         💰 Sale Fees: R$ {float(row.sale_fees or 0):.2f}")
                print(f"         💰 Shipping: R$ {float(row.shipping_fees or 0):.2f}")
                print(f"         🔒 Fechado: {row.is_closed}")
                print()
        else:
            print(f"   ❌ Nenhum período de billing encontrado para Setembro")
        
        # Teste 2: Dashboard com Setembro 2025
        print("📊 Teste 2: Dashboard com Setembro 2025")
        print("-" * 40)
        
        start_time = time.time()
        
        controller = AnalyticsController(db)
        dashboard_data = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=15,
            specific_month=9,
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
            
            # Verificar se há sobreposição
            if len(billing_data) > 1:
                print(f"\n⚠️  PROBLEMA: Múltiplos períodos encontrados para Setembro")
                print(f"   📊 Períodos: {len(billing_data)}")
                print(f"   💡 Isso pode estar somando dados de diferentes meses")
            elif len(billing_data) == 1:
                period = billing_data[0]
                if period.period_from.month != 9 or period.period_to.month != 9:
                    print(f"\n⚠️  PROBLEMA: Período não é específico de Setembro")
                    print(f"   📅 Período: {period.period_from} a {period.period_to}")
                    print(f"   💡 Este período se sobrepõe a Setembro mas inclui outros meses")
        
        # Teste 3: Comparar com Outubro
        print(f"\n📊 Teste 3: Comparação com Outubro 2025")
        print("-" * 40)
        
        dashboard_oct = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=15,
            specific_month=10,
            specific_year=2025
        )
        
        if dashboard_oct and dashboard_oct.get('success'):
            billing_oct = dashboard_oct.get('billing', {})
            marketing_oct = billing_oct.get('total_advertising_cost', 0)
            
            print(f"   📊 Marketing Setembro: R$ {marketing_billing:.2f}")
            print(f"   📊 Marketing Outubro: R$ {marketing_oct:.2f}")
            
            if marketing_billing == marketing_oct:
                print(f"   ⚠️  PROBLEMA: Mesmo valor para Setembro e Outubro")
                print(f"   💡 Isso indica que está usando o mesmo período de billing")
            else:
                print(f"   ✅ Valores diferentes - dados corretos")
        
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
    print("🔍 Debug do Marketing para Setembro 2025")
    print("=" * 60)
    print()
    
    success = debug_september_marketing()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ DEBUG CONCLUÍDO!")
    else:
        print("❌ Erro no debug!")

if __name__ == "__main__":
    main()
