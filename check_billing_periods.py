#!/usr/bin/env python3
"""
Verificar dados específicos de billing
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from sqlalchemy import text
from datetime import datetime, timedelta

def check_billing_periods():
    """Verificar dados específicos de billing"""
    print("🔍 Verificando Dados Específicos de Billing")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # 1. Verificar todos os períodos
        print(f"\n📊 1. Todos os Períodos de Billing:")
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
            ORDER BY period_from DESC
        """), {"company_id": company_id})
        
        periods = result.fetchall()
        for period in periods:
            print(f"   📅 ID {period.id}: {period.period_from} a {period.period_to}")
            print(f"      🎯 Marketing: R$ {period.advertising_cost:.2f}")
            print(f"      💳 Sale Fees: R$ {period.sale_fees:.2f}")
            print(f"      🚚 Shipping: R$ {period.shipping_fees:.2f}")
            print(f"      💰 Total: R$ {period.total_amount:.2f}")
            print(f"      📊 Atual: {period.is_current}, Fechado: {period.is_closed}")
        
        # 2. Verificar período atual (últimos 30 dias)
        print(f"\n📊 2. Período Atual (Últimos 30 dias):")
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
            AND period_from >= :start_date
            AND period_to <= :end_date
        """), {
            "company_id": company_id,
            "start_date": start_date,
            "end_date": end_date
        })
        
        billing_data = result.fetchone()
        if billing_data and billing_data.periods_count > 0:
            print(f"   ✅ Dados encontrados para o período:")
            print(f"      🎯 Marketing: R$ {billing_data.total_advertising_cost:.2f}")
            print(f"      💳 Sale Fees: R$ {billing_data.total_sale_fees:.2f}")
            print(f"      🚚 Shipping: R$ {billing_data.total_shipping_fees:.2f}")
            print(f"      📅 Períodos: {billing_data.periods_count}")
        else:
            print(f"   ❌ Nenhum dado encontrado para o período")
            print(f"      📅 Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
        
        # 3. Verificar períodos disponíveis
        print(f"\n📊 3. Períodos Disponíveis:")
        result = db.execute(text("""
            SELECT 
                MIN(period_from) as earliest_period,
                MAX(period_to) as latest_period,
                COUNT(*) as total_periods
            FROM ml_billing_periods 
            WHERE company_id = :company_id
        """), {"company_id": company_id})
        
        period_info = result.fetchone()
        if period_info:
            print(f"   📅 Período mais antigo: {period_info.earliest_period}")
            print(f"   📅 Período mais recente: {period_info.latest_period}")
            print(f"   📊 Total de períodos: {period_info.total_periods}")
        
        return {
            "success": True,
            "total_periods": len(periods),
            "current_period_data": billing_data.periods_count if billing_data else 0
        }
    
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
    finally:
        db.close()

def main():
    """Função principal"""
    print("🔍 Verificando Dados Específicos de Billing")
    print("=" * 60)
    print()
    
    result = check_billing_periods()
    
    print("\n" + "=" * 60)
    if result and result.get("success"):
        print("✅ Verificação concluída!")
        print(f"📊 Total de períodos: {result.get('total_periods', 0)}")
        print(f"📅 Dados no período atual: {result.get('current_period_data', 0)}")
    else:
        print("❌ Erro na verificação!")

if __name__ == "__main__":
    main()
