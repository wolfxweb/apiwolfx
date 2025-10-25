#!/usr/bin/env python3
"""
Testar a nova lógica de priorização de períodos
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

def test_priority_logic():
    """Testar a nova lógica de priorização"""
    print("🔧 Testando Nova Lógica de Priorização de Períodos")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        company_id = 15
        
        # Teste 1: Agosto 2025
        print("📊 Teste 1: Agosto 2025")
        print("-" * 40)
        
        controller = AnalyticsController(db)
        dashboard_aug = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=15,
            specific_month=8,
            specific_year=2025
        )
        
        if dashboard_aug and dashboard_aug.get('success'):
            billing_aug = dashboard_aug.get('billing', {})
            print(f"   📊 Marketing Agosto: R$ {billing_aug.get('total_advertising_cost', 0):.2f}")
            print(f"   📊 Períodos: {billing_aug.get('periods_count', 0)}")
            print(f"   💡 Esperado: R$ 1.444,50 (Período 1)")
        
        # Teste 2: Setembro 2025
        print(f"\n📊 Teste 2: Setembro 2025")
        print("-" * 40)
        
        dashboard_sep = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=15,
            specific_month=9,
            specific_year=2025
        )
        
        if dashboard_sep and dashboard_sep.get('success'):
            billing_sep = dashboard_sep.get('billing', {})
            print(f"   📊 Marketing Setembro: R$ {billing_sep.get('total_advertising_cost', 0):.2f}")
            print(f"   📊 Períodos: {billing_sep.get('periods_count', 0)}")
            print(f"   💡 Esperado: R$ 1.162,99 (Período 3)")
        
        # Teste 3: Outubro 2025
        print(f"\n📊 Teste 3: Outubro 2025")
        print("-" * 40)
        
        dashboard_oct = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=15,
            specific_month=10,
            specific_year=2025
        )
        
        if dashboard_oct and dashboard_oct.get('success'):
            billing_oct = dashboard_oct.get('billing', {})
            print(f"   📊 Marketing Outubro: R$ {billing_oct.get('total_advertising_cost', 0):.2f}")
            print(f"   📊 Períodos: {billing_oct.get('periods_count', 0)}")
            print(f"   💡 Esperado: R$ 680,41 (Período 2)")
        
        # Teste 4: Verificar se não há mais sobreposições
        print(f"\n📊 Teste 4: Verificação de Sobreposições")
        print("-" * 40)
        
        values = [
            (billing_aug.get('total_advertising_cost', 0), "Agosto"),
            (billing_sep.get('total_advertising_cost', 0), "Setembro"),
            (billing_oct.get('total_advertising_cost', 0), "Outubro")
        ]
        
        print(f"   📊 Valores por mês:")
        for value, month in values:
            print(f"      {month}: R$ {value:.2f}")
        
        # Verificar se os valores são diferentes
        unique_values = set(v[0] for v in values)
        if len(unique_values) == len(values):
            print(f"   ✅ Todos os valores são diferentes - correção funcionou!")
        else:
            print(f"   ⚠️  Alguns valores são iguais - ainda há sobreposição")
        
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
    print("🔧 Teste da Nova Lógica de Priorização")
    print("=" * 70)
    print()
    
    success = test_priority_logic()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ TESTE CONCLUÍDO!")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
