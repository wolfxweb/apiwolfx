#!/usr/bin/env python3
"""
Testar a análise de Pareto por lucro
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from datetime import datetime

def test_profit_pareto():
    """Testar análise de Pareto por lucro"""
    print("🔍 Teste da Análise de Pareto por Lucro")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15
        user_id = 15
        
        # Teste com Setembro 2025
        print("📊 Teste: Setembro 2025")
        print("-" * 40)
        
        controller = AnalyticsController(db)
        dashboard_data = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=user_id,
            specific_month=9,
            specific_year=2025
        )
        
        if dashboard_data and dashboard_data.get('success'):
            pareto_analysis = dashboard_data.get('pareto_analysis', {})
            profit_80 = pareto_analysis.get('profit_80_percent', [])
            
            print(f"✅ Dashboard carregado com sucesso")
            print(f"📊 Produtos na análise de lucro (80%): {len(profit_80)}")
            
            if profit_80:
                print(f"\n💰 Exemplos de produtos por lucro:")
                for i, product in enumerate(profit_80[:5], 1):
                    print(f"   {i}. {product.get('title', 'N/A')[:50]}...")
                    print(f"      💰 Receita: R$ {product.get('revenue', 0):.2f}")
                    print(f"      💹 Lucro: R$ {product.get('profit', 0):.2f}")
                    print(f"      📊 Margem: {product.get('margin_percent', 0):.1f}%")
                    print(f"      📊 % Acumulado: {product.get('cumulative_percent', 0):.1f}%")
                    print()
                
                # Verificar se os dados estão corretos
                total_profit = sum(p.get('profit', 0) for p in profit_80)
                print(f"📊 Total de lucro nos produtos 80%: R$ {total_profit:.2f}")
                
                # Verificar se há produtos com lucro válido
                products_with_profit = [p for p in profit_80 if not (p.get('profit', 0) == 0 or str(p.get('profit', 0)) == 'nan')]
                print(f"📊 Produtos com lucro válido: {len(products_with_profit)}")
                
                if products_with_profit:
                    print(f"✅ Dados de lucro estão corretos!")
                else:
                    print(f"❌ Nenhum produto com lucro válido encontrado")
            else:
                print(f"❌ Nenhum produto encontrado na análise de lucro")
        else:
            print(f"❌ Erro ao carregar dashboard: {dashboard_data.get('error', 'Erro desconhecido')}")
        
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
    print("🔍 Teste da Análise de Pareto por Lucro")
    print("=" * 60)
    print()
    
    success = test_profit_pareto()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE CONCLUÍDO!")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
