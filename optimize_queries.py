#!/usr/bin/env python3
"""
Otimizar consultas do dashboard
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from datetime import datetime, timedelta
import time

def test_query_performance():
    """Testar performance das consultas"""
    print("🔍 Testando Performance das Consultas")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Teste 1: Consulta atual (lenta)
        print("📊 Teste 1: Consulta Atual (Lenta)")
        print("-" * 40)
        
        start_time = time.time()
        
        controller = AnalyticsController(db)
        dashboard_data = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=15,
            period_days=31,
            specific_month=10,
            specific_year=2025
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"⏱️  Tempo de execução: {execution_time:.2f} segundos")
        
        if dashboard_data and dashboard_data.get('success'):
            kpis = dashboard_data.get('kpis', {})
            print(f"   💰 Receita: R$ {kpis.get('total_revenue', 0):.2f}")
            print(f"   📦 Pedidos: {kpis.get('total_orders', 0)}")
        else:
            print(f"   ❌ Erro: {dashboard_data.get('error', 'Desconhecido')}")
        
        # Teste 2: Consulta otimizada
        print(f"\n📊 Teste 2: Consulta Otimizada")
        print("-" * 40)
        
        start_time = time.time()
        
        # Consulta otimizada usando SQL direto
        from sqlalchemy import text
        
        result = db.execute(text("""
            SELECT 
                COUNT(*) as total_orders,
                SUM(CASE 
                    WHEN status IN ('PAID', 'CONFIRMED', 'SHIPPED', 'DELIVERED') 
                    THEN total_amount 
                    ELSE 0 
                END) as total_revenue,
                SUM(CASE 
                    WHEN status IN ('PAID', 'CONFIRMED', 'SHIPPED', 'DELIVERED') 
                    THEN 1 
                    ELSE 0 
                END) as valid_orders,
                SUM(CASE 
                    WHEN status = 'CANCELLED' 
                    THEN total_amount 
                    ELSE 0 
                END) as cancelled_value,
                SUM(CASE 
                    WHEN status = 'CANCELLED' 
                    THEN 1 
                    ELSE 0 
                END) as cancelled_count
            FROM ml_orders 
            WHERE company_id = :company_id
            AND date_created >= :start_date
            AND date_created <= :end_date
        """), {
            "company_id": company_id,
            "start_date": datetime(2025, 10, 1),
            "end_date": datetime(2025, 10, 31, 23, 59, 59)
        })
        
        optimized_data = result.fetchone()
        
        end_time = time.time()
        execution_time_optimized = end_time - start_time
        
        print(f"⏱️  Tempo de execução: {execution_time_optimized:.2f} segundos")
        print(f"   📦 Total Pedidos: {optimized_data.total_orders}")
        print(f"   💰 Receita: R$ {float(optimized_data.total_revenue or 0):.2f}")
        print(f"   ✅ Pedidos Válidos: {optimized_data.valid_orders}")
        print(f"   ❌ Cancelados: {optimized_data.cancelled_count} (R$ {float(optimized_data.cancelled_value or 0):.2f})")
        
        # Comparação de performance
        improvement = ((execution_time - execution_time_optimized) / execution_time) * 100
        print(f"\n📈 Melhoria de Performance: {improvement:.1f}%")
        
        if execution_time_optimized < execution_time:
            print(f"✅ Consulta otimizada é {execution_time/execution_time_optimized:.1f}x mais rápida")
        else:
            print(f"⚠️  Consulta otimizada não melhorou significativamente")
        
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
    print("🔍 Testando Performance das Consultas")
    print("=" * 60)
    print()
    
    success = test_query_performance()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE DE PERFORMANCE CONCLUÍDO!")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
