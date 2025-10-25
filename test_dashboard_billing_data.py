#!/usr/bin/env python3
"""
Testar se os dados de billing estão sendo retornados no dashboard
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from datetime import datetime, timedelta

def test_dashboard_billing_data():
    """Testar dados de billing no dashboard"""
    print("🔍 Testando Dados de Billing no Dashboard")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Testar diferentes períodos
        periods = [
            ("Últimos 7 dias", 7),
            ("Últimos 30 dias", 30),
            ("Últimos 90 dias", 90)
        ]
        
        controller = AnalyticsController(db)
        
        for period_name, days in periods:
            print(f"\n📊 {period_name}:")
            print("-" * 40)
            
            # Buscar dados do dashboard
            dashboard_data = controller.get_sales_dashboard(company_id, days)
            
            if dashboard_data and dashboard_data.get('success'):
                # KPIs
                kpis = dashboard_data.get('kpis', {})
                print(f"   💰 Receita Total: R$ {kpis.get('total_revenue', 0):.2f}")
                print(f"   📦 Total de Pedidos: {kpis.get('total_orders', 0)}")
                
                # Custos
                costs = dashboard_data.get('costs', {})
                print(f"   🎯 Marketing: R$ {costs.get('marketing_cost', 0):.2f} ({costs.get('marketing_percent', 0):.1f}%)")
                print(f"   💳 Sale Fees: R$ {costs.get('ml_fees', 0):.2f} ({costs.get('ml_fees_percent', 0):.1f}%)")
                print(f"   🚚 Shipping: R$ {costs.get('shipping_fees', 0):.2f} ({costs.get('shipping_fees_percent', 0):.1f}%)")
                print(f"   💰 Total Custos: R$ {costs.get('total_costs', 0):.2f}")
                
                # Billing Data
                billing = dashboard_data.get('billing', {})
                if billing:
                    print(f"   📊 Billing Data:")
                    print(f"      🎯 Marketing Billing: R$ {billing.get('total_advertising_cost', 0):.2f}")
                    print(f"      💳 Sale Fees Billing: R$ {billing.get('total_sale_fees', 0):.2f}")
                    print(f"      🚚 Shipping Billing: R$ {billing.get('total_shipping_fees', 0):.2f}")
                    print(f"      📅 Períodos: {billing.get('periods_count', 0)}")
                else:
                    print(f"   ❌ Nenhum dado de billing encontrado")
                
                # Profit
                profit = dashboard_data.get('profit', {})
                print(f"   💰 Lucro Líquido: R$ {profit.get('net_profit', 0):.2f}")
                print(f"   📈 Margem Líquida: {profit.get('net_margin', 0):.1f}%")
                
            else:
                print(f"   ❌ Erro ao buscar dados: {dashboard_data.get('error', 'Desconhecido')}")
        
        # Testar período específico (mês atual)
        print(f"\n📊 Período Específico (Mês Atual):")
        print("-" * 40)
        
        # Primeiro dia do mês atual
        now = datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_of_month = now
        
        # Buscar dados de billing para o mês atual
        from sqlalchemy import text
        result = db.execute(text("""
            SELECT 
                SUM(advertising_cost) as total_advertising_cost,
                SUM(sale_fees) as total_sale_fees,
                SUM(shipping_fees) as total_shipping_fees,
                COUNT(*) as periods_count
            FROM ml_billing_periods 
            WHERE company_id = :company_id
            AND (
                (period_from <= :end_date AND period_to >= :start_date)
                OR (period_from >= :start_date AND period_from <= :end_date)
                OR (period_to >= :start_date AND period_to <= :end_date)
            )
        """), {
            "company_id": company_id,
            "start_date": start_of_month,
            "end_date": end_of_month
        })
        
        billing_data = result.fetchone()
        
        if billing_data and billing_data.periods_count > 0:
            print(f"   ✅ Dados de billing para o mês atual:")
            print(f"      🎯 Marketing: R$ {billing_data.total_advertising_cost:.2f}")
            print(f"      💳 Sale Fees: R$ {billing_data.total_sale_fees:.2f}")
            print(f"      🚚 Shipping: R$ {billing_data.total_shipping_fees:.2f}")
            print(f"      📅 Períodos: {billing_data.periods_count}")
        else:
            print(f"   ❌ Nenhum dado de billing para o mês atual")
            print(f"      📅 Período: {start_of_month.strftime('%Y-%m-%d')} a {end_of_month.strftime('%Y-%m-%d')}")
        
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
    print("🔍 Testando Dados de Billing no Dashboard")
    print("=" * 60)
    print()
    
    success = test_dashboard_billing_data()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE CONCLUÍDO!")
        print("📊 Verifique se os dados de billing estão sendo exibidos corretamente no dashboard")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
