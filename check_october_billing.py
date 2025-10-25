#!/usr/bin/env python3
"""
Verificar dados de billing para Outubro 2025
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from sqlalchemy import text
from datetime import datetime

def check_october_billing():
    """Verificar dados de billing para Outubro 2025"""
    print("🔍 Verificando Dados de Billing para Outubro 2025")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Teste 1: Verificar todos os períodos de billing
        print("📊 Teste 1: Todos os Períodos de Billing")
        print("-" * 40)
        
        result_all = db.execute(text("""
            SELECT 
                period_from,
                period_to,
                advertising_cost,
                sale_fees,
                shipping_fees,
                is_closed
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
                print(f"      📅 {row.period_from} a {row.period_to}")
                print(f"         💰 Marketing: R$ {float(row.advertising_cost or 0):.2f}")
                print(f"         💰 Sale Fees: R$ {float(row.sale_fees or 0):.2f}")
                print(f"         💰 Shipping: R$ {float(row.shipping_fees or 0):.2f}")
                print(f"         🔒 Fechado: {row.is_closed}")
                print()
        else:
            print(f"   ❌ Nenhum período de billing encontrado")
        
        # Teste 2: Verificar se há períodos que se sobrepõem a Outubro
        print("📊 Teste 2: Períodos que se Sobrepoem a Outubro 2025")
        print("-" * 40)
        
        result_overlap = db.execute(text("""
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
        """), {
            "company_id": company_id,
            "start_date": datetime(2025, 10, 1),
            "end_date": datetime(2025, 10, 31, 23, 59, 59)
        })
        
        billing_overlap = result_overlap.fetchall()
        
        if billing_overlap:
            total_marketing = sum(float(row.advertising_cost or 0) for row in billing_overlap)
            total_sale_fees = sum(float(row.sale_fees or 0) for row in billing_overlap)
            total_shipping = sum(float(row.shipping_fees or 0) for row in billing_overlap)
            
            print(f"   📊 Períodos que se sobrepõem: {len(billing_overlap)}")
            print(f"   💰 Marketing Total: R$ {total_marketing:.2f}")
            print(f"   💰 Sale Fees Total: R$ {total_sale_fees:.2f}")
            print(f"   💰 Shipping Total: R$ {total_shipping:.2f}")
            
            for row in billing_overlap:
                print(f"      📅 {row.period_from} a {row.period_to}")
                print(f"         💰 Marketing: R$ {float(row.advertising_cost or 0):.2f}")
        else:
            print(f"   ❌ Nenhum período se sobrepõe a Outubro 2025")
        
        # Teste 3: Verificar consulta específica do controller
        print("📊 Teste 3: Consulta Específica do Controller")
        print("-" * 40)
        
        result_controller = db.execute(text("""
            SELECT 
                SUM(advertising_cost) as total_advertising_cost,
                SUM(sale_fees) as total_sale_fees,
                SUM(shipping_fees) as total_shipping_fees,
                COUNT(*) as periods_count
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
        
        billing_controller = result_controller.fetchone()
        
        if billing_controller and billing_controller.periods_count > 0:
            print(f"   📊 Períodos encontrados: {billing_controller.periods_count}")
            print(f"   💰 Marketing: R$ {float(billing_controller.total_advertising_cost or 0):.2f}")
            print(f"   💰 Sale Fees: R$ {float(billing_controller.total_sale_fees or 0):.2f}")
            print(f"   💰 Shipping: R$ {float(billing_controller.total_shipping_fees or 0):.2f}")
        else:
            print(f"   ❌ Nenhum período encontrado pela consulta do controller")
            print(f"   💡 Isso explica por que o sistema usa fallback")
        
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
    print("🔍 Verificando Dados de Billing para Outubro 2025")
    print("=" * 60)
    print()
    
    success = check_october_billing()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ VERIFICAÇÃO CONCLUÍDA!")
    else:
        print("❌ Erro na verificação!")

if __name__ == "__main__":
    main()
