#!/usr/bin/env python3
"""
Testar query de billing diretamente
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from sqlalchemy import text
from datetime import datetime

def test_billing_query():
    """Testar query de billing diretamente"""
    print("🔍 Testando Query de Billing Diretamente")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Período de Outubro de 2025
        october_start = datetime(2025, 10, 1)
        october_end = datetime(2025, 10, 31, 23, 59, 59)
        
        print(f"📅 Período: {october_start.strftime('%d/%m/%Y')} a {october_end.strftime('%d/%m/%Y')}")
        
        # Query exata que está sendo usada no _get_billing_data
        result = db.execute(text("""
            SELECT 
                SUM(advertising_cost) as total_advertising_cost,
                SUM(sale_fees) as total_sale_fees,
                SUM(shipping_fees) as total_shipping_fees,
                COUNT(*) as periods_count
            FROM ml_billing_periods 
            WHERE company_id = :company_id
            AND period_from <= :end_date 
            AND period_to >= :start_date
        """), {
            "company_id": company_id,
            "start_date": october_start,
            "end_date": october_end
        })
        
        billing_data = result.fetchone()
        
        print(f"\n📊 Resultado da query:")
        print(f"   🎯 Marketing: R$ {billing_data.total_advertising_cost:.2f}")
        print(f"   💳 Sale Fees: R$ {billing_data.total_sale_fees:.2f}")
        print(f"   🚚 Shipping: R$ {billing_data.total_shipping_fees:.2f}")
        print(f"   📅 Períodos: {billing_data.periods_count}")
        
        # Verificar quais períodos estão sendo incluídos
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
            AND period_from <= :end_date 
            AND period_to >= :start_date
            ORDER BY period_from
        """), {
            "company_id": company_id,
            "start_date": october_start,
            "end_date": october_end
        })
        
        periods = result.fetchall()
        
        print(f"\n📊 Períodos incluídos na query:")
        for period in periods:
            print(f"   📅 ID {period.id}: {period.period_from.strftime('%d/%m/%Y')} a {period.period_to.strftime('%d/%m/%Y')}")
            print(f"      🎯 Marketing: R$ {period.advertising_cost:.2f}")
            print(f"      💳 Sale Fees: R$ {period.sale_fees:.2f}")
            print(f"      🚚 Shipping: R$ {period.shipping_fees:.2f}")
        
        # Testar com período mais amplo (últimos 30 dias)
        print(f"\n📊 Testando com período mais amplo (últimos 30 dias):")
        from datetime import timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        result = db.execute(text("""
            SELECT 
                SUM(advertising_cost) as total_advertising_cost,
                SUM(sale_fees) as total_sale_fees,
                SUM(shipping_fees) as total_shipping_fees,
                COUNT(*) as periods_count
            FROM ml_billing_periods 
            WHERE company_id = :company_id
            AND period_from <= :end_date 
            AND period_to >= :start_date
        """), {
            "company_id": company_id,
            "start_date": start_date,
            "end_date": end_date
        })
        
        billing_data_30d = result.fetchone()
        
        print(f"   🎯 Marketing: R$ {billing_data_30d.total_advertising_cost:.2f}")
        print(f"   💳 Sale Fees: R$ {billing_data_30d.total_sale_fees:.2f}")
        print(f"   🚚 Shipping: R$ {billing_data_30d.total_shipping_fees:.2f}")
        print(f"   📅 Períodos: {billing_data_30d.periods_count}")
        
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
    print("🔍 Testando Query de Billing Diretamente")
    print("=" * 60)
    print()
    
    success = test_billing_query()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE CONCLUÍDO!")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
