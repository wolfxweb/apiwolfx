#!/usr/bin/env python3
"""
Debug da fonte dos dados de Marketing - verificar se vem de billing ou custos
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from sqlalchemy import text
from datetime import datetime
import json

def debug_marketing_source():
    """Debug da fonte dos dados de Marketing"""
    print("🔍 Debug da Fonte dos Dados de Marketing")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Teste 1: Verificar dados de billing para Novembro 2025
        print("📊 Teste 1: Dados de Billing para Novembro 2025")
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
            AND (
                (period_from >= :start_date AND period_to <= :end_date)
                OR
                (period_from <= :start_date AND period_to >= :end_date 
                 AND (period_to - period_from) <= INTERVAL '30 days')
            )
        """), {
            "company_id": company_id,
            "start_date": datetime(2025, 11, 1),
            "end_date": datetime(2025, 11, 30, 23, 59, 59)
        })
        
        billing_data = result_billing.fetchall()
        
        if billing_data:
            total_marketing = sum(float(row.advertising_cost or 0) for row in billing_data)
            total_sale_fees = sum(float(row.sale_fees or 0) for row in billing_data)
            total_shipping = sum(float(row.shipping_fees or 0) for row in billing_data)
            
            print(f"   📊 Períodos de billing encontrados: {len(billing_data)}")
            print(f"   💰 Marketing Billing: R$ {total_marketing:.2f}")
            print(f"   💰 Sale Fees Billing: R$ {total_sale_fees:.2f}")
            print(f"   💰 Shipping Billing: R$ {total_shipping:.2f}")
            
            for row in billing_data:
                print(f"      📅 {row.period_from} a {row.period_to} - Marketing: R$ {float(row.advertising_cost or 0):.2f}")
        else:
            print(f"   ❌ Nenhum período de billing encontrado para Novembro 2025")
            print(f"   💡 Sistema vai usar fallback (custos dos pedidos)")
        
        # Teste 2: Verificar dados dos pedidos para Novembro 2025
        print(f"\n📊 Teste 2: Dados dos Pedidos para Novembro 2025")
        print("-" * 40)
        
        result_orders = db.execute(text("""
            SELECT 
                COUNT(*) as total_orders,
                SUM(total_amount) as total_revenue,
                SUM(advertising_cost) as total_advertising_cost,
                SUM(sale_fees) as total_sale_fees,
                SUM(shipping_fees) as total_shipping_fees,
                SUM(coupon_amount) as total_discounts
            FROM ml_orders 
            WHERE company_id = :company_id
            AND date_created >= :start_date
            AND date_created <= :end_date
            AND status IN ('PAID', 'CONFIRMED', 'SHIPPED', 'DELIVERED')
        """), {
            "company_id": company_id,
            "start_date": datetime(2025, 11, 1),
            "end_date": datetime(2025, 11, 30, 23, 59, 59)
        })
        
        orders_data = result_orders.fetchone()
        
        if orders_data and orders_data.total_orders > 0:
            print(f"   📦 Total Pedidos: {orders_data.total_orders}")
            print(f"   💰 Receita Total: R$ {float(orders_data.total_revenue or 0):.2f}")
            print(f"   💰 Marketing Pedidos: R$ {float(orders_data.total_advertising_cost or 0):.2f}")
            print(f"   💰 Sale Fees Pedidos: R$ {float(orders_data.total_sale_fees or 0):.2f}")
            print(f"   💰 Shipping Pedidos: R$ {float(orders_data.total_shipping_fees or 0):.2f}")
            print(f"   💰 Descontos Pedidos: R$ {float(orders_data.total_discounts or 0):.2f}")
        else:
            print(f"   ❌ Nenhum pedido encontrado para Novembro 2025")
            print(f"   💡 Sistema vai usar estimativas")
        
        # Teste 3: Verificar dados de billing para Outubro 2025 (para comparação)
        print(f"\n📊 Teste 3: Dados de Billing para Outubro 2025 (Comparação)")
        print("-" * 40)
        
        result_oct = db.execute(text("""
            SELECT 
                period_from,
                period_to,
                advertising_cost,
                sale_fees,
                shipping_fees,
                is_closed
            FROM ml_billing_periods 
            WHERE company_id = :company_id
            AND (
                (period_from >= :start_date AND period_to <= :end_date)
                OR
                (period_from <= :start_date AND period_to >= :end_date 
                 AND (period_to - period_from) <= INTERVAL '30 days')
            )
        """), {
            "company_id": company_id,
            "start_date": datetime(2025, 10, 1),
            "end_date": datetime(2025, 10, 31, 23, 59, 59)
        })
        
        billing_oct = result_oct.fetchall()
        
        if billing_oct:
            total_marketing_oct = sum(float(row.advertising_cost or 0) for row in billing_oct)
            print(f"   📊 Períodos de billing encontrados: {len(billing_oct)}")
            print(f"   💰 Marketing Billing Outubro: R$ {total_marketing_oct:.2f}")
            
            for row in billing_oct:
                print(f"      📅 {row.period_from} a {row.period_to} - Marketing: R$ {float(row.advertising_cost or 0):.2f}")
        else:
            print(f"   ❌ Nenhum período de billing encontrado para Outubro 2025")
        
        # Conclusão
        print(f"\n📊 Conclusão:")
        print("-" * 40)
        
        if billing_data:
            print(f"   ✅ Novembro: Usando dados de BILLING")
        else:
            print(f"   ❌ Novembro: Usando dados de PEDIDOS (fallback)")
        
        if billing_oct:
            print(f"   ✅ Outubro: Usando dados de BILLING")
        else:
            print(f"   ❌ Outubro: Usando dados de PEDIDOS (fallback)")
        
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
    print("🔍 Debug da Fonte dos Dados de Marketing")
    print("=" * 60)
    print()
    
    success = debug_marketing_source()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ DEBUG CONCLUÍDO!")
    else:
        print("❌ Erro no debug!")

if __name__ == "__main__":
    main()
