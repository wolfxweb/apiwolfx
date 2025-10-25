#!/usr/bin/env python3
"""
Testar filtro de Outubro de 2025
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from datetime import datetime, timedelta

def test_october_filter():
    """Testar filtro de Outubro de 2025"""
    print("🔍 Testando Filtro de Outubro de 2025")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Calcular período de Outubro de 2025
        october_start = datetime(2025, 10, 1)
        october_end = datetime(2025, 10, 31, 23, 59, 59)
        october_days = 31
        
        print(f"📅 Período: {october_start.strftime('%d/%m/%Y')} a {october_end.strftime('%d/%m/%Y')}")
        print(f"📊 Dias: {october_days}")
        
        controller = AnalyticsController(db)
        
        # Buscar dados do dashboard para Outubro
        dashboard_data = controller.get_sales_dashboard(company_id, october_days)
        
        if dashboard_data and dashboard_data.get('success'):
            # KPIs
            kpis = dashboard_data.get('kpis', {})
            print(f"\n📊 KPIs para Outubro de 2025:")
            print(f"   💰 Receita Total: R$ {kpis.get('total_revenue', 0):.2f}")
            print(f"   📦 Total de Pedidos: {kpis.get('total_orders', 0)}")
            print(f"   🛒 Produtos Vendidos: {kpis.get('total_sold', 0)}")
            print(f"   💳 Ticket Médio: R$ {kpis.get('avg_ticket', 0):.2f}")
            
            # Custos
            costs = dashboard_data.get('costs', {})
            print(f"\n💰 Custos para Outubro de 2025:")
            print(f"   🎯 Marketing: R$ {costs.get('marketing_cost', 0):.2f} ({costs.get('marketing_percent', 0):.1f}%)")
            print(f"   💳 Sale Fees: R$ {costs.get('ml_fees', 0):.2f} ({costs.get('ml_fees_percent', 0):.1f}%)")
            print(f"   🚚 Shipping: R$ {costs.get('shipping_fees', 0):.2f} ({costs.get('shipping_fees_percent', 0):.1f}%)")
            print(f"   💰 Total Custos: R$ {costs.get('total_costs', 0):.2f}")
            
            # Billing Data
            billing = dashboard_data.get('billing', {})
            if billing:
                print(f"\n📊 Dados de Billing para Outubro:")
                print(f"   🎯 Marketing Billing: R$ {billing.get('total_advertising_cost', 0):.2f}")
                print(f"   💳 Sale Fees Billing: R$ {billing.get('total_sale_fees', 0):.2f}")
                print(f"   🚚 Shipping Billing: R$ {billing.get('total_shipping_fees', 0):.2f}")
                print(f"   📅 Períodos: {billing.get('periods_count', 0)}")
            else:
                print(f"\n❌ Nenhum dado de billing encontrado para Outubro")
            
            # Verificar dados de billing no banco para Outubro
            print(f"\n🔍 Verificando dados de billing no banco para Outubro de 2025:")
            from sqlalchemy import text
            
            result = db.execute(text("""
                SELECT 
                    id,
                    period_from,
                    period_to,
                    advertising_cost,
                    sale_fees,
                    shipping_fees,
                    total_amount,
                    is_current,
                    is_closed
                FROM ml_billing_periods 
                WHERE company_id = :company_id
                AND (
                    (period_from <= :end_date AND period_to >= :start_date)
                    OR (period_from >= :start_date AND period_from <= :end_date)
                    OR (period_to >= :start_date AND period_to <= :end_date)
                )
                ORDER BY period_from
            """), {
                "company_id": company_id,
                "start_date": october_start,
                "end_date": october_end
            })
            
            billing_periods = result.fetchall()
            
            if billing_periods:
                print(f"   ✅ Encontrados {len(billing_periods)} períodos de billing para Outubro:")
                total_marketing = 0
                total_sale_fees = 0
                total_shipping = 0
                
                for period in billing_periods:
                    print(f"      📅 Período {period.id}: {period.period_from.strftime('%d/%m/%Y')} a {period.period_to.strftime('%d/%m/%Y')}")
                    print(f"         🎯 Marketing: R$ {period.advertising_cost:.2f}")
                    print(f"         💳 Sale Fees: R$ {period.sale_fees:.2f}")
                    print(f"         🚚 Shipping: R$ {period.shipping_fees:.2f}")
                    print(f"         💰 Total: R$ {period.total_amount:.2f}")
                    print(f"         📊 Atual: {period.is_current}, Fechado: {period.is_closed}")
                    
                    total_marketing += period.advertising_cost
                    total_sale_fees += period.sale_fees
                    total_shipping += period.shipping_fees
                
                print(f"\n   📊 Totais para Outubro:")
                print(f"      🎯 Marketing Total: R$ {total_marketing:.2f}")
                print(f"      💳 Sale Fees Total: R$ {total_sale_fees:.2f}")
                print(f"      🚚 Shipping Total: R$ {total_shipping:.2f}")
                
            else:
                print(f"   ❌ Nenhum período de billing encontrado para Outubro de 2025")
                print(f"      📅 Buscando períodos próximos...")
                
                # Buscar períodos próximos
                result = db.execute(text("""
                    SELECT 
                        id,
                        period_from,
                        period_to,
                        advertising_cost,
                        sale_fees,
                        shipping_fees
                    FROM ml_billing_periods 
                    WHERE company_id = :company_id
                    ORDER BY ABS(EXTRACT(EPOCH FROM (period_from - :october_start)))
                    LIMIT 3
                """), {
                    "company_id": company_id,
                    "october_start": october_start
                })
                
                nearby_periods = result.fetchall()
                if nearby_periods:
                    print(f"      📅 Períodos próximos encontrados:")
                    for period in nearby_periods:
                        print(f"         ID {period.id}: {period.period_from.strftime('%d/%m/%Y')} a {period.period_to.strftime('%d/%m/%Y')}")
                        print(f"            🎯 Marketing: R$ {period.advertising_cost:.2f}")
                        print(f"            💳 Sale Fees: R$ {period.sale_fees:.2f}")
                        print(f"            🚚 Shipping: R$ {period.shipping_fees:.2f}")
        
        else:
            print(f"❌ Erro ao buscar dados: {dashboard_data.get('error', 'Desconhecido')}")
        
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
    print("🔍 Testando Filtro de Outubro de 2025")
    print("=" * 60)
    print()
    
    success = test_october_filter()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE CONCLUÍDO!")
        print("📊 Verifique se os dados de billing estão corretos para Outubro de 2025")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
