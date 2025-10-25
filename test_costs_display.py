#!/usr/bin/env python3
"""
Teste da exibição de custos no dashboard
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from app.controllers.analytics_controller import AnalyticsController
from datetime import datetime, timedelta

def test_costs_display():
    """Teste da exibição de custos"""
    print("🧪 Teste da Exibição de Custos no Dashboard")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        user_id = 2  # usuário da empresa
        
        print(f"🏢 Testando dashboard para empresa ID: {company_id}")
        
        # Criar controller
        controller = AnalyticsController(db)
        
        # Testar com período de 30 dias
        print(f"\n📊 Testando Período de 30 dias:")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        print(f"   📅 Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
        
        result = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=user_id,
            date_from=start_date.strftime('%Y-%m-%d'),
            date_to=end_date.strftime('%Y-%m-%d')
        )
        
        if result.get("success"):
            print(f"   ✅ Dashboard carregado com sucesso!")
            
            # Verificar dados de custos
            costs = result.get("costs", {})
            print(f"\n💰 Dados de Custos Retornados:")
            print(f"   🎯 Marketing: R$ {costs.get('marketing_cost', 0):.2f} ({costs.get('marketing_percent', 0):.1f}%)")
            print(f"   💳 Sale Fees: R$ {costs.get('ml_fees', 0):.2f} ({costs.get('ml_fees_percent', 0):.1f}%)")
            print(f"   🚚 Shipping: R$ {costs.get('shipping_fees', 0):.2f} ({costs.get('shipping_fees_percent', 0):.1f}%)")
            print(f"   🏷️ Descontos: R$ {costs.get('discounts', 0):.2f} ({costs.get('discounts_percent', 0):.1f}%)")
            print(f"   📦 Custo Produtos: R$ {costs.get('product_cost', 0):.2f} ({costs.get('product_cost_percent', 0):.1f}%)")
            print(f"   🏛️ Impostos: R$ {costs.get('taxes', 0):.2f} ({costs.get('taxes_percent', 0):.1f}%)")
            print(f"   💰 Total Custos: R$ {costs.get('total_costs', 0):.2f} ({costs.get('total_costs_percent', 0):.1f}%)")
            
            # Verificar dados de lucro
            profit = result.get("profit", {})
            print(f"\n📈 Dados de Lucro:")
            print(f"   💰 Lucro Líquido: R$ {profit.get('net_profit', 0):.2f}")
            print(f"   📊 Margem Líquida: {profit.get('net_margin', 0):.1f}%")
            print(f"   🛒 Lucro Médio/Pedido: R$ {profit.get('avg_profit_per_order', 0):.2f}")
            
            # Verificar KPIs
            kpis = result.get("kpis", {})
            print(f"\n📊 KPIs:")
            print(f"   💰 Receita Total: R$ {kpis.get('total_revenue', 0):.2f}")
            print(f"   🛒 Total Pedidos: {kpis.get('total_orders', 0)}")
            
            # Verificar se há dados de billing
            billing = result.get("billing", {})
            print(f"\n📊 Dados de Billing:")
            if billing and billing.get('total_advertising_cost', 0) > 0:
                print(f"   🎯 Marketing (Billing): R$ {billing.get('total_advertising_cost', 0):.2f}")
                print(f"   💳 Sale Fees (Billing): R$ {billing.get('total_sale_fees', 0):.2f}")
                print(f"   🚚 Shipping (Billing): R$ {billing.get('total_shipping_fees', 0):.2f}")
                print(f"   📅 Períodos: {billing.get('periods_count', 0)}")
            else:
                print(f"   ❌ Nenhum dado de billing disponível")
            
            return {
                "success": True,
                "has_costs_data": any(costs.values()),
                "has_profit_data": any(profit.values()),
                "has_billing_data": billing and billing.get('total_advertising_cost', 0) > 0
            }
        else:
            print(f"   ❌ Erro no dashboard: {result.get('error')}")
            return {"success": False, "error": result.get('error')}
    
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
    finally:
        db.close()

def main():
    """Função principal"""
    print("🧪 Teste da Exibição de Custos no Dashboard")
    print("=" * 60)
    print()
    
    result = test_costs_display()
    
    print("\n" + "=" * 60)
    if result and result.get("success"):
        print("✅ DADOS DE CUSTOS DISPONÍVEIS!")
        print(f"📊 Dados de custos: {'Sim' if result.get('has_costs_data') else 'Não'}")
        print(f"📊 Dados de lucro: {'Sim' if result.get('has_profit_data') else 'Não'}")
        print(f"📊 Dados de billing: {'Sim' if result.get('has_billing_data') else 'Não'}")
        
        if result.get('has_costs_data'):
            print("\n💡 Possíveis causas dos valores não aparecerem:")
            print("   🔍 Verificar se os elementos HTML existem")
            print("   🔍 Verificar se a função updateCostsAndMargins está sendo chamada")
            print("   🔍 Verificar se há erros no console do navegador")
            print("   🔍 Verificar se os IDs dos elementos estão corretos")
        else:
            print("\n⚠️  NENHUM DADO DE CUSTOS ENCONTRADO!")
            print("💡 Verificar se o controller está retornando dados de custos")
    else:
        print("❌ Problemas no dashboard!")
        if result:
            print(f"Erro: {result.get('error', 'Desconhecido')}")

if __name__ == "__main__":
    main()
