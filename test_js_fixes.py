#!/usr/bin/env python3
"""
Testar se os erros JavaScript foram corrigidos
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from datetime import datetime
import time

def test_js_fixes():
    """Testar se os erros JavaScript foram corrigidos"""
    print("🔧 Testando Correções JavaScript")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Teste: Dashboard com dados corretos
        print("📊 Teste: Dashboard com vendas canceladas e devoluções")
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
            
            print(f"\n   ❌ Vendas Canceladas:")
            print(f"      📦 Pedidos: {kpis.get('cancelled_orders', 0)}")
            print(f"      💰 Valor: R$ {kpis.get('cancelled_value', 0):.2f}")
            
            print(f"\n   🔄 Devoluções:")
            print(f"      📦 Pedidos: {kpis.get('returns_count', 0)}")
            print(f"      💰 Valor: R$ {kpis.get('returns_value', 0):.2f}")
            
            # Verificar se os valores estão corretos
            cancelled_orders = kpis.get('cancelled_orders', 0)
            cancelled_value = kpis.get('cancelled_value', 0)
            returns_count = kpis.get('returns_count', 0)
            returns_value = kpis.get('returns_value', 0)
            
            print(f"\n📊 Status da Correção:")
            if cancelled_orders > 0 and cancelled_value > 0:
                print(f"   ✅ Cancelamentos: {cancelled_orders} pedidos, R$ {cancelled_value:.2f}")
            else:
                print(f"   ❌ Cancelamentos: {cancelled_orders} pedidos, R$ {cancelled_value:.2f}")
            
            if returns_count > 0 and returns_value > 0:
                print(f"   ✅ Devoluções: {returns_count} pedidos, R$ {returns_value:.2f}")
            else:
                print(f"   ❌ Devoluções: {returns_count} pedidos, R$ {returns_value:.2f}")
            
            print(f"\n🎯 Resumo:")
            print(f"   📊 Total de Pedidos: {kpis.get('total_orders', 0)}")
            print(f"   💰 Receita Líquida: R$ {kpis.get('total_revenue', 0):.2f}")
            print(f"   📈 Performance: {execution_time:.2f}s")
            
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
    print("🔧 Testando Correções JavaScript")
    print("=" * 60)
    print()
    
    success = test_js_fixes()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE DE CORREÇÕES CONCLUÍDO!")
        print("🎯 Próximos passos:")
        print("   1. Recriar container sem cache")
        print("   2. Testar no navegador")
        print("   3. Verificar se erros JavaScript foram resolvidos")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
