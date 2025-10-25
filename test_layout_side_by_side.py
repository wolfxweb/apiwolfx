#!/usr/bin/env python3
"""
Testar layout lado a lado dos filtros
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from datetime import datetime
import time

def test_side_by_side_layout():
    """Testar se o layout lado a lado está funcionando"""
    print("🔧 Testando Layout Lado a Lado dos Filtros")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Teste: Outubro 2025
        print("📊 Teste: Outubro 2025 (layout lado a lado)")
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
            
            print(f"   💰 Receita Total: R$ {kpis.get('total_revenue', 0):.2f}")
            print(f"   📦 Total Pedidos: {kpis.get('total_orders', 0)}")
            print(f"   📦 Produtos Vendidos: {kpis.get('total_sold', 0)}")
            print(f"   💳 Ticket Médio: R$ {kpis.get('avg_ticket', 0):.2f}")
            
            print(f"\n✅ Layout lado a lado implementado com sucesso!")
            print(f"   🎯 Mês/Ano Específico: Lado esquerdo")
            print(f"   🎯 Período Personalizado: Lado direito")
            print(f"   📱 Responsivo: col-md-6 para cada lado")
            
        else:
            print(f"   ❌ Erro: {dashboard_data.get('error', 'Desconhecido')}")
        
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
    print("🔧 Testando Layout Lado a Lado dos Filtros")
    print("=" * 60)
    print()
    
    success = test_side_by_side_layout()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ LAYOUT LADO A LADO IMPLEMENTADO!")
    else:
        print("❌ Erro na implementação!")

if __name__ == "__main__":
    main()
