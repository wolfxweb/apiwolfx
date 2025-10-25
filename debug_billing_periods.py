#!/usr/bin/env python3
"""
Debug dos períodos de billing para Outubro
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from sqlalchemy import text
from datetime import datetime

def debug_billing_periods():
    """Debug dos períodos de billing"""
    print("🔍 Debug dos Períodos de Billing")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Período de Outubro de 2025
        october_start = datetime(2025, 10, 1)
        october_end = datetime(2025, 10, 31, 23, 59, 59)
        
        print(f"📅 Período solicitado: {october_start.strftime('%d/%m/%Y')} a {october_end.strftime('%d/%m/%Y')}")
        
        # Buscar todos os períodos de billing
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
            ORDER BY period_from
        """), {"company_id": company_id})
        
        all_periods = result.fetchall()
        
        print(f"\n📊 Todos os períodos de billing:")
        for period in all_periods:
            print(f"   📅 ID {period.id}: {period.period_from.strftime('%d/%m/%Y')} a {period.period_to.strftime('%d/%m/%Y')}")
            print(f"      🎯 Marketing: R$ {period.advertising_cost:.2f}")
            print(f"      💳 Sale Fees: R$ {period.sale_fees:.2f}")
            print(f"      🚚 Shipping: R$ {period.shipping_fees:.2f}")
            print(f"      📊 Atual: {period.is_current}, Fechado: {period.is_closed}")
            
            # Verificar se se sobrepõe com Outubro
            overlaps = (period.period_from <= october_end and period.period_to >= october_start)
            print(f"      🔍 Sobreposição com Outubro: {'✅ SIM' if overlaps else '❌ NÃO'}")
            print()
        
        # Buscar períodos que se sobrepõem com Outubro
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
            AND period_from <= :end_date 
            AND period_to >= :start_date
            ORDER BY period_from
        """), {
            "company_id": company_id,
            "start_date": october_start,
            "end_date": october_end
        })
        
        overlapping_periods = result.fetchall()
        
        print(f"📊 Períodos que se sobrepõem com Outubro:")
        if overlapping_periods:
            total_marketing = 0
            total_sale_fees = 0
            total_shipping = 0
            
            for period in overlapping_periods:
                print(f"   📅 ID {period.id}: {period.period_from.strftime('%d/%m/%Y')} a {period.period_to.strftime('%d/%m/%Y')}")
                print(f"      🎯 Marketing: R$ {period.advertising_cost:.2f}")
                print(f"      💳 Sale Fees: R$ {period.sale_fees:.2f}")
                print(f"      🚚 Shipping: R$ {period.shipping_fees:.2f}")
                print(f"      📊 Atual: {period.is_current}, Fechado: {period.is_closed}")
                
                total_marketing += period.advertising_cost
                total_sale_fees += period.sale_fees
                total_shipping += period.shipping_fees
                print()
            
            print(f"📊 Totais dos períodos sobrepostos:")
            print(f"   🎯 Marketing Total: R$ {total_marketing:.2f}")
            print(f"   💳 Sale Fees Total: R$ {total_sale_fees:.2f}")
            print(f"   🚚 Shipping Total: R$ {total_shipping:.2f}")
        else:
            print(f"   ❌ Nenhum período se sobrepõe com Outubro")
        
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
    print("🔍 Debug dos Períodos de Billing")
    print("=" * 60)
    print()
    
    success = debug_billing_periods()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ DEBUG CONCLUÍDO!")
    else:
        print("❌ Erro no debug!")

if __name__ == "__main__":
    main()
