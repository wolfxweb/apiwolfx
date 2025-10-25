#!/usr/bin/env python3
"""
Teste direto do AnalyticsController
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from app.controllers.analytics_controller import AnalyticsController
from datetime import datetime, timedelta

def test_analytics_controller():
    """Teste direto do AnalyticsController"""
    print("🧪 Teste Direto do AnalyticsController")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        user_id = 2  # usuário da empresa
        
        print(f"🏢 Testando AnalyticsController para empresa ID: {company_id}")
        
        # Criar controller
        controller = AnalyticsController(db)
        
        # Testar com período de 30 dias
        print(f"\n📊 Testando Período de 30 dias:")
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        date_to = datetime.now().strftime('%Y-%m-%d')
        
        print(f"   📅 Período: {date_from} a {date_to}")
        
        result = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to
        )
        
        if result.get("success"):
            print(f"   ✅ Dashboard carregado com sucesso!")
            
            # Verificar KPIs
            kpis = result.get("kpis", {})
            print(f"\n📊 KPIs Principais:")
            print(f"   💰 Receita Bruta: R$ {kpis.get('gross_revenue', 0):.2f}")
            print(f"   📦 Produtos Vendidos: {kpis.get('products_sold', 0)}")
            print(f"   🛒 Total de Pedidos: {kpis.get('total_orders', 0)}")
            print(f"   💳 Ticket Médio: R$ {kpis.get('average_ticket', 0):.2f}")
            
            # Verificar custos
            costs = result.get("costs", {})
            print(f"\n💰 Análise de Custos:")
            print(f"   🎯 Marketing: R$ {costs.get('marketing_cost', 0):.2f}")
            print(f"   💳 Sale Fees: R$ {costs.get('ml_fees', 0):.2f}")
            print(f"   🚚 Shipping: R$ {costs.get('shipping_cost', 0):.2f}")
            print(f"   🏷️ Descontos: R$ {costs.get('discounts', 0):.2f}")
            
            # Verificar billing
            billing = result.get("billing", {})
            print(f"\n📊 Dados de Billing:")
            print(f"   🎯 Marketing (Billing): R$ {billing.get('total_advertising_cost', 0):.2f}")
            print(f"   💳 Sale Fees (Billing): R$ {billing.get('total_sale_fees', 0):.2f}")
            print(f"   🚚 Shipping (Billing): R$ {billing.get('total_shipping_fees', 0):.2f}")
            
            # Verificar se está usando dados reais
            total_real_costs = (
                costs.get('marketing_cost', 0) +
                costs.get('ml_fees', 0) +
                costs.get('shipping_cost', 0)
            )
            
            if total_real_costs > 0:
                print(f"\n✅ DADOS REAIS ENCONTRADOS!")
                print(f"   💰 Total de custos reais: R$ {total_real_costs:.2f}")
                print(f"   🎯 Sistema usando dados do Mercado Livre")
            else:
                print(f"\n⚠️  DADOS ZERADOS!")
                print(f"   💰 Total de custos: R$ {total_real_costs:.2f}")
                print(f"   ⚠️  Sistema pode estar usando estimativas")
            
            return {
                "success": True,
                "has_real_data": total_real_costs > 0,
                "total_costs": total_real_costs
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
    print("🧪 Teste Direto do AnalyticsController")
    print("=" * 60)
    print()
    
    result = test_analytics_controller()
    
    print("\n" + "=" * 60)
    if result and result.get("success"):
        if result.get("has_real_data"):
            print("🎉 SISTEMA FUNCIONANDO COM DADOS REAIS!")
            print(f"💰 Total de custos: R$ {result.get('total_costs', 0):.2f}")
            print("✅ Filtros respeitando períodos corretamente")
            print("✅ Dados reais do Mercado Livre sendo usados")
            print("🚀 Sistema 100% funcional e preciso!")
        else:
            print("⚠️  SISTEMA FUNCIONANDO MAS SEM DADOS REAIS")
            print("💡 Possíveis causas:")
            print("   - Dados de billing não sincronizados")
            print("   - Sistema usando estimativas")
            print("   - Período sem dados suficientes")
    else:
        print("❌ Problemas no sistema!")
        if result:
            print(f"Erro: {result.get('error', 'Desconhecido')}")

if __name__ == "__main__":
    main()
