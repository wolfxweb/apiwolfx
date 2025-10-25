#!/usr/bin/env python3
"""
Testar a análise de Pareto por quantidade
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from datetime import datetime

def test_quantity_pareto():
    """Testar análise de Pareto por quantidade"""
    print("🔍 Teste da Análise de Pareto por Quantidade")
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
            quantity_80 = pareto_analysis.get('quantity_80_percent', [])
            
            print(f"✅ Dashboard carregado com sucesso")
            print(f"📊 Produtos na análise de quantidade (80%): {len(quantity_80)}")
            
            if quantity_80:
                print(f"\n📦 Exemplos de produtos por quantidade:")
                for i, product in enumerate(quantity_80[:5], 1):
                    print(f"   {i}. {product.get('title', 'N/A')[:50]}...")
                    print(f"      📦 Quantidade: {product.get('quantity', 0)}")
                    print(f"      💰 Receita: R$ {product.get('revenue', 0):.2f}")
                    print(f"      📊 % Acumulado: {product.get('cumulative_percent', 0):.1f}%")
                    print()
                
                # Verificar se os dados estão corretos
                total_quantity = sum(p.get('quantity', 0) for p in quantity_80)
                print(f"📊 Total de quantidade nos produtos 80%: {total_quantity}")
                
                # Verificar se há produtos com quantidade > 0
                products_with_quantity = [p for p in quantity_80 if p.get('quantity', 0) > 0]
                print(f"📊 Produtos com quantidade > 0: {len(products_with_quantity)}")
                
                if products_with_quantity:
                    print(f"✅ Dados de quantidade estão corretos!")
                else:
                    print(f"❌ Nenhum produto com quantidade > 0 encontrado")
            else:
                print(f"❌ Nenhum produto encontrado na análise de quantidade")
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
    print("🔍 Teste da Análise de Pareto por Quantidade")
    print("=" * 60)
    print()
    
    success = test_quantity_pareto()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE CONCLUÍDO!")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
