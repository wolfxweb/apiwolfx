#!/usr/bin/env python3
"""
Debug dos dados de Pareto/Curva ABC
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.controllers.analytics_controller import AnalyticsController
from app.config.database import SessionLocal
from datetime import datetime
import json

def debug_pareto_data():
    """Debug dos dados de Pareto"""
    print("🔍 Debug dos Dados de Pareto/Curva ABC")
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
            print(f"✅ Dashboard carregado com sucesso")
            
            # Verificar estrutura dos dados
            print(f"\n📊 Estrutura dos Dados:")
            print(f"   🔑 Chaves principais: {list(dashboard_data.keys())}")
            
            # Verificar pareto_analysis
            pareto_analysis = dashboard_data.get('pareto_analysis', {})
            print(f"\n📊 Dados de Pareto:")
            print(f"   🔑 Chaves do pareto_analysis: {list(pareto_analysis.keys())}")
            
            if pareto_analysis:
                print(f"   📈 Revenue 80%: {len(pareto_analysis.get('revenue_80_percent', []))} produtos")
                print(f"   📦 Quantity 80%: {len(pareto_analysis.get('quantity_80_percent', []))} produtos")
                print(f"   💰 Profit 80%: {len(pareto_analysis.get('profit_80_percent', []))} produtos")
                print(f"   📉 Tail 20%: {len(pareto_analysis.get('tail_20_percent', []))} produtos")
                
                # Mostrar alguns produtos de exemplo
                revenue_80 = pareto_analysis.get('revenue_80_percent', [])
                if revenue_80:
                    print(f"\n   📈 Exemplo Revenue 80% (primeiro produto):")
                    first_product = revenue_80[0]
                    print(f"      🆔 ID: {first_product.get('id')}")
                    print(f"      📝 Título: {first_product.get('title', 'N/A')[:50]}...")
                    print(f"      💰 Receita: R$ {first_product.get('revenue', 0):.2f}")
                    print(f"      📦 Quantidade: {first_product.get('quantity', 0)}")
                    print(f"      💹 Lucro: R$ {first_product.get('profit', 0):.2f}")
                    print(f"      📊 % Acumulado: {first_product.get('cumulative_percent', 0):.1f}%")
                else:
                    print(f"   ❌ Nenhum produto encontrado no Revenue 80%")
                
                quantity_80 = pareto_analysis.get('quantity_80_percent', [])
                if quantity_80:
                    print(f"\n   📦 Exemplo Quantity 80% (primeiro produto):")
                    first_product = quantity_80[0]
                    print(f"      🆔 ID: {first_product.get('id')}")
                    print(f"      📝 Título: {first_product.get('title', 'N/A')[:50]}...")
                    print(f"      📦 Quantidade: {first_product.get('quantity', 0)}")
                    print(f"      💰 Receita: R$ {first_product.get('revenue', 0):.2f}")
                    print(f"      📊 % Acumulado: {first_product.get('cumulative_percent', 0):.1f}%")
                else:
                    print(f"   ❌ Nenhum produto encontrado no Quantity 80%")
                
                profit_80 = pareto_analysis.get('profit_80_percent', [])
                if profit_80:
                    print(f"\n   💰 Exemplo Profit 80% (primeiro produto):")
                    first_product = profit_80[0]
                    print(f"      🆔 ID: {first_product.get('id')}")
                    print(f"      📝 Título: {first_product.get('title', 'N/A')[:50]}...")
                    print(f"      💹 Lucro: R$ {first_product.get('profit', 0):.2f}")
                    print(f"      💰 Receita: R$ {first_product.get('revenue', 0):.2f}")
                    print(f"      📊 % Acumulado: {first_product.get('cumulative_percent', 0):.1f}%")
                else:
                    print(f"   ❌ Nenhum produto encontrado no Profit 80%")
                
                tail_20 = pareto_analysis.get('tail_20_percent', [])
                if tail_20:
                    print(f"\n   📉 Exemplo Tail 20% (primeiro produto):")
                    first_product = tail_20[0]
                    print(f"      🆔 ID: {first_product.get('id')}")
                    print(f"      📝 Título: {first_product.get('title', 'N/A')[:50]}...")
                    print(f"      💰 Receita: R$ {first_product.get('revenue', 0):.2f}")
                    print(f"      📦 Quantidade: {first_product.get('quantity', 0)}")
                    print(f"      📊 % Acumulado: {first_product.get('cumulative_percent', 0):.1f}%")
                else:
                    print(f"   ❌ Nenhum produto encontrado no Tail 20%")
            else:
                print(f"   ❌ Nenhum dado de pareto_analysis encontrado")
            
            # Verificar se há dados de produtos
            products = dashboard_data.get('products', [])
            print(f"\n📊 Dados de Produtos:")
            print(f"   📦 Total de produtos: {len(products)}")
            
            if products:
                print(f"   📝 Primeiro produto:")
                first_product = products[0]
                print(f"      🆔 ID: {first_product.get('id')}")
                print(f"      📝 Título: {first_product.get('title', 'N/A')[:50]}...")
                print(f"      📊 Status: {first_product.get('status')}")
            else:
                print(f"   ❌ Nenhum produto encontrado")
            
            # Verificar KPIs
            kpis = dashboard_data.get('kpis', {})
            print(f"\n📊 KPIs:")
            print(f"   💰 Receita Total: R$ {kpis.get('total_revenue', 0):.2f}")
            print(f"   📦 Produtos Vendidos: {kpis.get('total_sold', 0)}")
            print(f"   📦 Total de Pedidos: {kpis.get('total_orders', 0)}")
            
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
    print("🔍 Debug dos Dados de Pareto/Curva ABC")
    print("=" * 60)
    print()
    
    success = debug_pareto_data()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ DEBUG CONCLUÍDO!")
    else:
        print("❌ Erro no debug!")

if __name__ == "__main__":
    main()
