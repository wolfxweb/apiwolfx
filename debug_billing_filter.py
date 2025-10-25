#!/usr/bin/env python3
"""
Debug do filtro de billing - verificar por que marketing aparece para 7 dias em vez do mês atual
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from sqlalchemy import text
from datetime import datetime, timedelta
import json

def debug_billing_filter():
    """Debug do filtro de billing"""
    print("🔍 Debug do Filtro de Billing")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Teste 1: Verificar dados de billing para diferentes períodos
        print("📊 Teste 1: Dados de Billing por Período")
        print("-" * 40)
        
        # Período de 7 dias (últimos 7 dias)
        end_date_7d = datetime.now()
        start_date_7d = end_date_7d - timedelta(days=7)
        
        print(f"📅 Período 7 dias: {start_date_7d.strftime('%Y-%m-%d')} a {end_date_7d.strftime('%Y-%m-%d')}")
        
        result_7d = db.execute(text("""
            SELECT 
                period_from,
                period_to,
                advertising_cost,
                sale_fees,
                shipping_fees,
                is_closed
            FROM ml_billing_periods 
            WHERE company_id = :company_id
            AND period_from <= :end_date 
            AND period_to >= :start_date
            ORDER BY period_from DESC
        """), {
            "company_id": company_id,
            "start_date": start_date_7d,
            "end_date": end_date_7d
        })
        
        billing_7d = result_7d.fetchall()
        
        if billing_7d:
            total_marketing_7d = sum(float(row.advertising_cost or 0) for row in billing_7d)
            total_sale_fees_7d = sum(float(row.sale_fees or 0) for row in billing_7d)
            total_shipping_7d = sum(float(row.shipping_fees or 0) for row in billing_7d)
            
            print(f"   📊 Períodos encontrados: {len(billing_7d)}")
            print(f"   💰 Marketing 7 dias: R$ {total_marketing_7d:.2f}")
            print(f"   💰 Sale Fees 7 dias: R$ {total_sale_fees_7d:.2f}")
            print(f"   💰 Shipping 7 dias: R$ {total_shipping_7d:.2f}")
            
            for row in billing_7d:
                print(f"      📅 {row.period_from} a {row.period_to} - Marketing: R$ {float(row.advertising_cost or 0):.2f} (Fechado: {row.is_closed})")
        else:
            print(f"   ❌ Nenhum período de billing encontrado para 7 dias")
        
        # Período do mês atual (novembro 2025)
        print(f"\n📅 Período Mês Atual (Novembro 2025): 2025-11-01 a 2025-11-30")
        
        result_month = db.execute(text("""
            SELECT 
                period_from,
                period_to,
                advertising_cost,
                sale_fees,
                shipping_fees,
                is_closed
            FROM ml_billing_periods 
            WHERE company_id = :company_id
            AND period_from <= :end_date 
            AND period_to >= :start_date
            ORDER BY period_from DESC
        """), {
            "company_id": company_id,
            "start_date": datetime(2025, 11, 1),
            "end_date": datetime(2025, 11, 30, 23, 59, 59)
        })
        
        billing_month = result_month.fetchall()
        
        if billing_month:
            total_marketing_month = sum(float(row.advertising_cost or 0) for row in billing_month)
            total_sale_fees_month = sum(float(row.sale_fees or 0) for row in billing_month)
            total_shipping_month = sum(float(row.shipping_fees or 0) for row in billing_month)
            
            print(f"   📊 Períodos encontrados: {len(billing_month)}")
            print(f"   💰 Marketing Mês: R$ {total_marketing_month:.2f}")
            print(f"   💰 Sale Fees Mês: R$ {total_sale_fees_month:.2f}")
            print(f"   💰 Shipping Mês: R$ {total_shipping_month:.2f}")
            
            for row in billing_month:
                print(f"      📅 {row.period_from} a {row.period_to} - Marketing: R$ {float(row.advertising_cost or 0):.2f} (Fechado: {row.is_closed})")
        else:
            print(f"   ❌ Nenhum período de billing encontrado para o mês")
        
        # Teste 2: Verificar todos os períodos de billing disponíveis
        print(f"\n📊 Teste 2: Todos os Períodos de Billing")
        print("-" * 40)
        
        result_all = db.execute(text("""
            SELECT 
                period_from,
                period_to,
                advertising_cost,
                sale_fees,
                shipping_fees,
                is_closed,
                created_at
            FROM ml_billing_periods 
            WHERE company_id = :company_id
            ORDER BY period_from DESC
        """), {
            "company_id": company_id
        })
        
        billing_all = result_all.fetchall()
        
        if billing_all:
            print(f"   📊 Total de períodos: {len(billing_all)}")
            for row in billing_all:
                print(f"      📅 {row.period_from} a {row.period_to} - Marketing: R$ {float(row.advertising_cost or 0):.2f} (Fechado: {row.is_closed}) - Criado: {row.created_at}")
        else:
            print(f"   ❌ Nenhum período de billing encontrado")
        
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
    print("🔍 Debug do Filtro de Billing")
    print("=" * 60)
    print()
    
    success = debug_billing_filter()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ DEBUG CONCLUÍDO!")
    else:
        print("❌ Erro no debug!")

if __name__ == "__main__":
    main()
