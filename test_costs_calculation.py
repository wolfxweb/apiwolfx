#!/usr/bin/env python3
"""
Script para testar o cálculo de custos reais no dashboard.

Este script:
1. Testa o cálculo de custos de marketing, frete e outros
2. Mostra dados reais vs estimados
3. Verifica se os custos estão aparecendo no dashboard
"""
import sys
import os
from datetime import datetime, timedelta

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import get_db
from app.controllers.analytics_controller import AnalyticsController
from app.models.saas_models import MLOrder, OrderStatus, Company

def test_costs_calculation():
    """Testa o cálculo de custos"""
    print("🧮 Testando cálculo de custos reais")
    print("=" * 50)
    
    try:
        # Obter sessão do banco
        db = next(get_db())
        
        # Buscar primeira empresa
        company = db.query(Company).first()
        if not company:
            print("❌ Nenhuma empresa ativa encontrada")
            return
        
        print(f"🏢 Testando com empresa: {company.name} (ID: {company.id})")
        
        # Buscar pedidos reais
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        orders = db.query(MLOrder).filter(
            MLOrder.company_id == company.id,
            MLOrder.date_created >= start_date,
            MLOrder.date_created <= end_date,
            MLOrder.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.SHIPPED, OrderStatus.DELIVERED])
        ).all()
        
        print(f"📦 Encontrados {len(orders)} pedidos no período")
        
        if orders:
            # Calcular custos reais
            total_revenue = sum(float(order.total_amount or 0) for order in orders)
            ml_fees = sum(float(order.sale_fees or 0) for order in orders)
            shipping_fees = sum(float(order.shipping_fees or 0) for order in orders)
            discounts = sum(float(order.coupon_amount or 0) for order in orders)
            marketing_cost = sum(float(order.advertising_cost or 0) for order in orders)
            
            print(f"\n💰 Receita total: R$ {total_revenue:.2f}")
            print(f"💳 Taxas ML: R$ {ml_fees:.2f} ({ml_fees/total_revenue*100:.1f}%)")
            print(f"🚚 Frete: R$ {shipping_fees:.2f} ({shipping_fees/total_revenue*100:.1f}%)")
            print(f"🎯 Marketing: R$ {marketing_cost:.2f} ({marketing_cost/total_revenue*100:.1f}%)")
            print(f"🎫 Descontos: R$ {discounts:.2f} ({discounts/total_revenue*100:.1f}%)")
            
            # Contar pedidos com marketing
            marketing_orders = [o for o in orders if o.is_advertising_sale and o.advertising_cost]
            print(f"\n📊 Pedidos com marketing: {len(marketing_orders)}")
            
            if marketing_orders:
                avg_marketing_cost = sum(float(o.advertising_cost or 0) for o in marketing_orders) / len(marketing_orders)
                print(f"📈 Custo médio de marketing por pedido: R$ {avg_marketing_cost:.2f}")
        
        # Testar controller de analytics
        print(f"\n🔧 Testando controller de analytics...")
        controller = AnalyticsController(db)
        
        # Simular dados do dashboard
        dashboard_data = controller.get_sales_dashboard(
            company_id=company.id,
            user_id=1,  # Usuário fictício
            period_days=30
        )
        
        if dashboard_data.get('success'):
            costs = dashboard_data.get('costs', {})
            print(f"\n✅ Custos calculados pelo controller:")
            print(f"   💳 Taxas ML: R$ {costs.get('ml_fees', 0):.2f} ({costs.get('ml_fees_percent', 0):.1f}%)")
            print(f"   🚚 Frete: R$ {costs.get('shipping_fees', 0):.2f} ({costs.get('shipping_fees_percent', 0):.1f}%)")
            print(f"   🎯 Marketing: R$ {costs.get('marketing_cost', 0):.2f} ({costs.get('marketing_percent', 0):.1f}%)")
            print(f"   🎫 Descontos: R$ {costs.get('discounts', 0):.2f} ({costs.get('discounts_percent', 0):.1f}%)")
            print(f"   📦 Custo Produtos: R$ {costs.get('product_cost', 0):.2f} ({costs.get('product_cost_percent', 0):.1f}%)")
            print(f"   🏛️ Impostos: R$ {costs.get('taxes', 0):.2f} ({costs.get('taxes_percent', 0):.1f}%)")
            print(f"   💰 Total: R$ {costs.get('total_costs', 0):.2f} ({costs.get('total_costs_percent', 0):.1f}%)")
        else:
            print(f"❌ Erro no controller: {dashboard_data.get('error', 'Erro desconhecido')}")
        
        print("\n" + "=" * 50)
        print("✅ Teste concluído!")
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Função principal"""
    print("🧪 Teste de Cálculo de Custos Reais")
    print("=" * 50)
    print(f"⏰ Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    test_costs_calculation()
    
    print("\n🏁 Teste finalizado!")

if __name__ == "__main__":
    main()
