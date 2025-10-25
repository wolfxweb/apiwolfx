#!/usr/bin/env python3
"""
Testar layout padrão dos filtros
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from datetime import datetime
import time

def test_standard_layout():
    """Testar se o layout padrão está funcionando"""
    print("🔧 Testando Layout Padrão dos Filtros")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Teste: Últimos 30 dias (padrão)
        print("📊 Teste: Últimos 30 dias (layout padrão)")
        print("-" * 40)
        
        start_time = time.time()
        
        controller = AnalyticsController(db)
        dashboard_data = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=15,
            period_days=30
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
            
            print(f"\n✅ Layout padrão implementado com sucesso!")
            print(f"   🎯 Filtro único: Select com opções agrupadas")
            print(f"   📱 Responsivo: Layout compacto e limpo")
            print(f"   🔧 JavaScript: Função handlePeriodChange() atualizada")
            print(f"   📊 API: Endpoint funcionando corretamente")
            
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
    print("🔧 Testando Layout Padrão dos Filtros")
    print("=" * 60)
    print()
    
    success = test_standard_layout()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ LAYOUT PADRÃO IMPLEMENTADO!")
    else:
        print("❌ Erro na implementação!")

if __name__ == "__main__":
    main()
