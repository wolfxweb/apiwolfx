#!/usr/bin/env python3
"""
Testar se a correção do filtro de billing funcionou
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from datetime import datetime, timedelta
import time

def test_billing_filter_fix():
    """Testar se a correção do filtro funcionou"""
    print("🔧 Testando Correção do Filtro de Billing")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Teste 1: Período de 7 dias
        print("📊 Teste 1: Período de 7 dias")
        print("-" * 40)
        
        start_time = time.time()
        
        controller = AnalyticsController(db)
        dashboard_7d = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=15,
            period_days=7
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"⏱️  Tempo de execução: {execution_time:.2f} segundos")
        
        if dashboard_7d and dashboard_7d.get('success'):
            billing_7d = dashboard_7d.get('billing', {})
            costs_7d = dashboard_7d.get('costs', {})
            
            print(f"   📊 Billing 7 dias:")
            print(f"      💰 Marketing: R$ {billing_7d.get('total_advertising_cost', 0):.2f}")
            print(f"      💰 Sale Fees: R$ {billing_7d.get('total_sale_fees', 0):.2f}")
            print(f"      💰 Shipping: R$ {billing_7d.get('total_shipping_fees', 0):.2f}")
            print(f"      📅 Períodos: {billing_7d.get('periods_count', 0)}")
            
            print(f"   📊 Costs 7 dias:")
            print(f"      💰 Marketing: R$ {costs_7d.get('marketing_cost', 0):.2f}")
            print(f"      💰 ML Fees: R$ {costs_7d.get('ml_fees', 0):.2f}")
            print(f"      💰 Shipping: R$ {costs_7d.get('shipping_fees', 0):.2f}")
        
        # Teste 2: Período de 30 dias
        print(f"\n📊 Teste 2: Período de 30 dias")
        print("-" * 40)
        
        start_time = time.time()
        
        dashboard_30d = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=15,
            period_days=30
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"⏱️  Tempo de execução: {execution_time:.2f} segundos")
        
        if dashboard_30d and dashboard_30d.get('success'):
            billing_30d = dashboard_30d.get('billing', {})
            costs_30d = dashboard_30d.get('costs', {})
            
            print(f"   📊 Billing 30 dias:")
            print(f"      💰 Marketing: R$ {billing_30d.get('total_advertising_cost', 0):.2f}")
            print(f"      💰 Sale Fees: R$ {billing_30d.get('total_sale_fees', 0):.2f}")
            print(f"      💰 Shipping: R$ {billing_30d.get('total_shipping_fees', 0):.2f}")
            print(f"      📅 Períodos: {billing_30d.get('periods_count', 0)}")
            
            print(f"   📊 Costs 30 dias:")
            print(f"      💰 Marketing: R$ {costs_30d.get('marketing_cost', 0):.2f}")
            print(f"      💰 ML Fees: R$ {costs_30d.get('ml_fees', 0):.2f}")
            print(f"      💰 Shipping: R$ {costs_30d.get('shipping_fees', 0):.2f}")
        
        # Comparação
        print(f"\n📊 Comparação:")
        print("-" * 40)
        
        marketing_7d = billing_7d.get('total_advertising_cost', 0) if dashboard_7d and dashboard_7d.get('success') else 0
        marketing_30d = billing_30d.get('total_advertising_cost', 0) if dashboard_30d and dashboard_30d.get('success') else 0
        
        print(f"   📊 Marketing 7 dias: R$ {marketing_7d:.2f}")
        print(f"   📊 Marketing 30 dias: R$ {marketing_30d:.2f}")
        
        if marketing_7d > 0 and marketing_30d > 0:
            ratio = marketing_7d / marketing_30d
            print(f"   📈 Proporção 7d/30d: {ratio:.2f}")
            
            if ratio < 0.5:  # 7 dias deve ser menor que 30 dias
                print(f"   ✅ CORREÇÃO FUNCIONOU! Proporção lógica")
            else:
                print(f"   ⚠️  Ainda pode haver problema na lógica")
        else:
            print(f"   ❌ Dados insuficientes para comparação")
        
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
    print("🔧 Testando Correção do Filtro de Billing")
    print("=" * 60)
    print()
    
    success = test_billing_filter_fix()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE DE CORREÇÃO CONCLUÍDO!")
        print("💡 Próximos passos:")
        print("   1. Verificar se a proporção está lógica")
        print("   2. Testar no navegador")
        print("   3. Considerar atualizar dados de billing")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
