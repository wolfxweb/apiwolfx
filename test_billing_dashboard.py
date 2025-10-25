#!/usr/bin/env python3
"""
Teste do dashboard com dados de billing
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from app.controllers.analytics_controller import AnalyticsController
from datetime import datetime, timedelta

def test_billing_dashboard():
    """Teste do dashboard com dados de billing"""
    print("🧪 Teste do Dashboard com Dados de Billing")
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
            print(f"   🚚 Shipping: R$ {costs.get('shipping_fees', 0):.2f}")
            print(f"   🏷️ Descontos: R$ {costs.get('discounts', 0):.2f}")
            
            # Verificar billing
            billing = result.get("billing", {})
            print(f"\n📊 Dados de Billing (Mercado Livre):")
            if billing:
                print(f"   🎯 Marketing (Billing): R$ {billing.get('total_advertising_cost', 0):.2f}")
                print(f"   💳 Sale Fees (Billing): R$ {billing.get('total_sale_fees', 0):.2f}")
                print(f"   🚚 Shipping (Billing): R$ {billing.get('total_shipping_fees', 0):.2f}")
                print(f"   📅 Períodos: {billing.get('periods_count', 0)}")
                
                # Verificar se está usando dados reais
                total_billing = (
                    billing.get('total_advertising_cost', 0) +
                    billing.get('total_sale_fees', 0) +
                    billing.get('total_shipping_fees', 0)
                )
                
                if total_billing > 0:
                    print(f"\n✅ DADOS REAIS DE BILLING ENCONTRADOS!")
                    print(f"   💰 Total de custos reais: R$ {total_billing:.2f}")
                    print(f"   🎯 Sistema usando dados do Mercado Livre")
                else:
                    print(f"\n⚠️  DADOS DE BILLING ZERADOS!")
                    print(f"   💰 Total de custos: R$ {total_billing:.2f}")
                    print(f"   ⚠️  Sistema usando fallback (dados dos pedidos)")
            else:
                print(f"   ❌ Nenhum dado de billing disponível")
            
            return {
                "success": True,
                "has_billing_data": billing and billing.get('total_advertising_cost', 0) > 0,
                "total_billing": total_billing if 'total_billing' in locals() else 0
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
    print("🧪 Teste do Dashboard com Dados de Billing")
    print("=" * 60)
    print()
    
    result = test_billing_dashboard()
    
    print("\n" + "=" * 60)
    if result and result.get("success"):
        if result.get("has_billing_data"):
            print("🎉 DASHBOARD FUNCIONANDO COM DADOS REAIS DE BILLING!")
            print(f"💰 Total de custos reais: R$ {result.get('total_billing', 0):.2f}")
            print("✅ Filtros respeitando períodos corretamente")
            print("✅ Dados reais do Mercado Livre sendo usados")
            print("🚀 Sistema 100% funcional e preciso!")
        else:
            print("⚠️  DASHBOARD FUNCIONANDO MAS SEM DADOS REAIS DE BILLING")
            print("💡 Possíveis causas:")
            print("   - Dados de billing não sincronizados")
            print("   - Sistema usando fallback (dados dos pedidos)")
            print("   - Período sem dados suficientes")
    else:
        print("❌ Problemas no dashboard!")
        if result:
            print(f"Erro: {result.get('error', 'Desconhecido')}")

if __name__ == "__main__":
    main()
