#!/usr/bin/env python3
"""
Teste final da exibição de custos
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from app.controllers.analytics_controller import AnalyticsController
from datetime import datetime, timedelta

def test_final_costs():
    """Teste final da exibição de custos"""
    print("🧪 Teste Final da Exibição de Custos")
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
            
            # Verificar estrutura dos dados
            print(f"\n📊 Estrutura dos Dados:")
            print(f"   ✅ Success: {result.get('success')}")
            print(f"   ✅ KPIs: {'Sim' if result.get('kpis') else 'Não'}")
            print(f"   ✅ Costs: {'Sim' if result.get('costs') else 'Não'}")
            print(f"   ✅ Profit: {'Sim' if result.get('profit') else 'Não'}")
            print(f"   ✅ Billing: {'Sim' if result.get('billing') else 'Não'}")
            
            # Verificar dados de custos
            costs = result.get("costs", {})
            print(f"\n💰 Dados de Custos:")
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
                "has_billing_data": billing and billing.get('total_advertising_cost', 0) > 0,
                "costs_summary": {
                    "marketing": costs.get('marketing_cost', 0),
                    "ml_fees": costs.get('ml_fees', 0),
                    "shipping": costs.get('shipping_fees', 0),
                    "total": costs.get('total_costs', 0)
                }
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
    print("🧪 Teste Final da Exibição de Custos")
    print("=" * 60)
    print()
    
    result = test_final_costs()
    
    print("\n" + "=" * 60)
    if result and result.get("success"):
        print("✅ DADOS DE CUSTOS DISPONÍVEIS NO BACKEND!")
        print(f"📊 Dados de custos: {'Sim' if result.get('has_costs_data') else 'Não'}")
        print(f"📊 Dados de lucro: {'Sim' if result.get('has_profit_data') else 'Não'}")
        print(f"📊 Dados de billing: {'Sim' if result.get('has_billing_data') else 'Não'}")
        
        costs_summary = result.get('costs_summary', {})
        print(f"\n💰 Resumo dos Custos:")
        print(f"   🎯 Marketing: R$ {costs_summary.get('marketing', 0):.2f}")
        print(f"   💳 Sale Fees: R$ {costs_summary.get('ml_fees', 0):.2f}")
        print(f"   🚚 Shipping: R$ {costs_summary.get('shipping', 0):.2f}")
        print(f"   💰 Total: R$ {costs_summary.get('total', 0):.2f}")
        
        print(f"\n💡 Próximos passos para debug:")
        print(f"   1. Abrir o navegador em http://localhost:8000/analytics")
        print(f"   2. Abrir o Console do navegador (F12)")
        print(f"   3. Verificar se aparecem os logs:")
        print(f"      - '🔧 Chamando updateCostsAndMargins com dados:'")
        print(f"      - '🔧 updateCostsAndMargins chamada com:'")
        print(f"      - '✅ Receita Bruta atualizada:'")
        print(f"      - '✅ ML Fees atualizado:'")
        print(f"      - '🎉 updateCostsAndMargins concluída com sucesso!'")
        print(f"   4. Se não aparecerem os logs, verificar se há erros no console")
        print(f"   5. Se aparecerem os logs mas os valores não mudam, verificar se os elementos HTML existem")
    else:
        print("❌ Problemas no dashboard!")
        if result:
            print(f"Erro: {result.get('error', 'Desconhecido')}")

if __name__ == "__main__":
    main()
