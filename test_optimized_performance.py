#!/usr/bin/env python3
"""
Testar performance da versão otimizada
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.controllers.analytics_controller_optimized import OptimizedAnalyticsController
from app.config.database import SessionLocal
from datetime import datetime
import time

def test_optimized_performance():
    """Testar performance da versão otimizada"""
    print("🔍 Testando Performance da Versão Otimizada")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Datas de teste
        start_date = datetime(2025, 10, 1)
        end_date = datetime(2025, 10, 31, 23, 59, 59)
        
        # Teste 1: Versão original
        print("📊 Teste 1: Versão Original")
        print("-" * 40)
        
        start_time = time.time()
        
        controller_original = AnalyticsController(db)
        dashboard_data_original = controller_original.get_sales_dashboard(
            company_id=company_id,
            user_id=15,
            period_days=31,
            specific_month=10,
            specific_year=2025
        )
        
        end_time = time.time()
        execution_time_original = end_time - start_time
        
        print(f"⏱️  Tempo de execução: {execution_time_original:.2f} segundos")
        
        if dashboard_data_original and dashboard_data_original.get('success'):
            kpis = dashboard_data_original.get('kpis', {})
            print(f"   💰 Receita: R$ {kpis.get('total_revenue', 0):.2f}")
            print(f"   📦 Pedidos: {kpis.get('total_orders', 0)}")
        else:
            print(f"   ❌ Erro: {dashboard_data_original.get('error', 'Desconhecido')}")
        
        # Teste 2: Versão otimizada
        print(f"\n📊 Teste 2: Versão Otimizada")
        print("-" * 40)
        
        start_time = time.time()
        
        controller_optimized = OptimizedAnalyticsController(db)
        dashboard_data_optimized = controller_optimized.get_sales_dashboard_optimized(
            company_id=company_id,
            user_id=15,
            start_date=start_date,
            end_date=end_date
        )
        
        end_time = time.time()
        execution_time_optimized = end_time - start_time
        
        print(f"⏱️  Tempo de execução: {execution_time_optimized:.2f} segundos")
        
        if dashboard_data_optimized and dashboard_data_optimized.get('success'):
            kpis = dashboard_data_optimized.get('kpis', {})
            print(f"   💰 Receita: R$ {kpis.get('total_revenue', 0):.2f}")
            print(f"   📦 Pedidos: {kpis.get('total_orders', 0)}")
        else:
            print(f"   ❌ Erro: {dashboard_data_optimized.get('error', 'Desconhecido')}")
        
        # Comparação de performance
        improvement = ((execution_time_original - execution_time_optimized) / execution_time_original) * 100
        speedup = execution_time_original / execution_time_optimized if execution_time_optimized > 0 else 0
        
        print(f"\n📈 Comparação de Performance:")
        print(f"   ⏱️  Tempo original: {execution_time_original:.2f}s")
        print(f"   ⏱️  Tempo otimizado: {execution_time_optimized:.2f}s")
        print(f"   📊 Melhoria: {improvement:.1f}%")
        print(f"   🚀 Speedup: {speedup:.1f}x mais rápido")
        
        if execution_time_optimized < execution_time_original:
            print(f"✅ Versão otimizada é {speedup:.1f}x mais rápida")
        else:
            print(f"⚠️  Versão otimizada não melhorou significativamente")
        
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
    print("🔍 Testando Performance da Versão Otimizada")
    print("=" * 60)
    print()
    
    success = test_optimized_performance()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE DE PERFORMANCE CONCLUÍDO!")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
