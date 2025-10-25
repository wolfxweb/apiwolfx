#!/usr/bin/env python3
"""
Testar a correção do Marketing para Setembro
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from sqlalchemy import text
from datetime import datetime
import time

def test_fixed_september():
    """Testar a correção do Marketing para Setembro"""
    print("🔧 Testando Correção do Marketing para Setembro")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Teste 1: Verificar consulta corrigida
        print("📊 Teste 1: Consulta Corrigida para Setembro")
        print("-" * 40)
        
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
            AND (
                -- Priorizar períodos que estão DENTRO do range solicitado
                (period_from >= :start_date AND period_to <= :end_date)
                OR
                -- Se não há períodos específicos, usar períodos que se sobrepõem
                -- mas limitar a períodos de no máximo 2 meses
                (period_from < :start_date AND period_to > :end_date 
                 AND (period_to - period_from) <= INTERVAL '60 days')
            )
        """), {
            "company_id": company_id,
            "start_date": datetime(2025, 9, 1),
            "end_date": datetime(2025, 9, 30, 23, 59, 59)
        })
        
        billing_data = result.fetchone()
        
        if billing_data:
            print(f"   📊 Períodos encontrados: {billing_data.periods_count}")
            print(f"   💰 Marketing: R$ {float(billing_data.total_advertising_cost or 0):.2f}")
            print(f"   💰 Sale Fees: R$ {float(billing_data.total_sale_fees or 0):.2f}")
            print(f"   💰 Shipping: R$ {float(billing_data.total_shipping_fees or 0):.2f}")
        else:
            print(f"   ❌ Nenhum período encontrado")
        
        # Teste 2: Dashboard com Setembro 2025
        print(f"\n📊 Teste 2: Dashboard com Setembro 2025")
        print("-" * 40)
        
        start_time = time.time()
        
        controller = AnalyticsController(db)
        dashboard_data = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=15,
            specific_month=9,
            specific_year=2025
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"⏱️  Tempo de execução: {execution_time:.2f} segundos")
        
        if dashboard_data and dashboard_data.get('success'):
            billing = dashboard_data.get('billing', {})
            costs = dashboard_data.get('costs', {})
            
            print(f"   📊 Marketing (Billing): R$ {billing.get('total_advertising_cost', 0):.2f}")
            print(f"   📊 Marketing (Costs): R$ {costs.get('marketing_cost', 0):.2f}")
            print(f"   📊 Períodos: {billing.get('periods_count', 0)}")
            
            # Verificar se a correção funcionou
            marketing_billing = billing.get('total_advertising_cost', 0)
            if marketing_billing == 1843.40:
                print(f"   ⚠️  AINDA SOMANDO: R$ {marketing_billing:.2f}")
                print(f"   💡 Correção não funcionou - ainda somando períodos")
            elif marketing_billing == 1162.99:
                print(f"   ✅ CORREÇÃO FUNCIONOU: R$ {marketing_billing:.2f}")
                print(f"   💡 Agora usando apenas o período específico de Setembro")
            else:
                print(f"   ❓ VALOR INESPERADO: R$ {marketing_billing:.2f}")
        
        # Teste 3: Comparar com Outubro
        print(f"\n📊 Teste 3: Comparação com Outubro 2025")
        print("-" * 40)
        
        dashboard_oct = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=15,
            specific_month=10,
            specific_year=2025
        )
        
        if dashboard_oct and dashboard_oct.get('success'):
            billing_oct = dashboard_oct.get('billing', {})
            marketing_oct = billing_oct.get('total_advertising_cost', 0)
            
            print(f"   📊 Marketing Setembro: R$ {billing.get('total_advertising_cost', 0):.2f}")
            print(f"   📊 Marketing Outubro: R$ {marketing_oct:.2f}")
            
            if billing.get('total_advertising_cost', 0) != marketing_oct:
                print(f"   ✅ Valores diferentes - correção funcionou!")
            else:
                print(f"   ⚠️  Mesmo valor - ainda há problema")
        
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
    print("🔧 Teste da Correção do Marketing para Setembro")
    print("=" * 60)
    print()
    
    success = test_fixed_september()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE CONCLUÍDO!")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
