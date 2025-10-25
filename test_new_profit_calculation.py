#!/usr/bin/env python3
"""
Teste para mostrar o cálculo de lucro com a nova fórmula
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import get_db
from app.models.saas_models import MLProduct, InternalProduct, Company
from sqlalchemy import text

def test_profit_calculation():
    """Testa cálculo de lucro para produtos específicos"""
    db = next(get_db())
    
    try:
        # Produtos do dashboard
        products_data = [
            {"ml_item_id": "MLB5069302578", "revenue": 6669.86, "quantity": 202},
            {"ml_item_id": "MLB5383263850", "revenue": 4271.55, "quantity": 111},
            {"ml_item_id": "MLB3893708591", "revenue": 3625.86, "quantity": 73},
            {"ml_item_id": "MLB5408864960", "revenue": 2047.56, "quantity": 39}
        ]
        
        # Buscar dados da empresa
        company = db.query(Company).filter(Company.id == 15).first()
        
        print(f"🏢 Empresa: {company.name}")
        print(f"   Regime Tributário: {company.regime_tributario}")
        print(f"   Alíquota Simples: {company.aliquota_simples}%")
        print(f"   Marketing (%): {company.percentual_marketing}%")
        print(f"   Custo Adicional por Pedido: R$ {company.custo_adicional_por_pedido}")
        print()
        
        for product_data in products_data:
            ml_item_id = product_data["ml_item_id"]
            revenue = product_data["revenue"]
            quantity = product_data["quantity"]
            
            # Buscar produto ML
            product = db.query(MLProduct).filter(
                MLProduct.ml_item_id == ml_item_id,
                MLProduct.company_id == 15
            ).first()
            
            if not product:
                continue
                
            print(f"📦 Produto: {product.title}")
            print(f"   ML Item ID: {ml_item_id}")
            print(f"   SKU: {product.seller_sku}")
            print(f"   Receita: R$ {revenue:.2f}")
            print(f"   Quantidade: {quantity} unidades")
            print()
            
            # Buscar produto interno
            internal_product = None
            if product.seller_sku:
                internal_product = db.query(InternalProduct).filter(
                    InternalProduct.company_id == 15,
                    InternalProduct.internal_sku == product.seller_sku,
                    InternalProduct.status == 'active'
                ).first()
            
            if internal_product:
                print(f"   ✅ Produto interno encontrado:")
                print(f"      Custo produto: R$ {internal_product.cost_price}")
                print(f"      Marketing (%): {internal_product.marketing_cost}%")
                print(f"      Outros custos: R$ {internal_product.other_costs}")
                print()
                
                # Calcular custos
                product_cost = float(internal_product.cost_price or 0)
                
                # Marketing: usar percentual da EMPRESA
                marketing_percent = float(company.percentual_marketing or 0) if company.percentual_marketing else 0
                if marketing_percent == 0:
                    marketing_percent = float(internal_product.marketing_cost or 0)
                marketing_cost = revenue * (marketing_percent / 100)
                
                # Outros custos: R$ 0,50 por unidade
                other_costs_per_unit = float(internal_product.other_costs or 0)
                other_costs = other_costs_per_unit * quantity
                
                # Custo adicional por pedido (assumindo 1 pedido por simplicidade)
                cost_per_order = float(company.custo_adicional_por_pedido or 0)
                orders = quantity  # Assumindo 1 pedido por unidade para simplificar
                total_cost_per_order = cost_per_order * orders
                
                # Impostos (Simples Nacional)
                taxes_amount = 0.0
                if company.regime_tributario == 'simples_nacional':
                    if company.aliquota_simples:
                        taxes_amount = revenue * (float(company.aliquota_simples) / 100)
                
                # Total de custos
                total_costs = product_cost + marketing_cost + other_costs + total_cost_per_order + taxes_amount
                
                # Lucro bruto
                profit = revenue - total_costs
                margin = (profit / revenue * 100) if revenue > 0 else 0
                
                print(f"   💰 Cálculo de Custos:")
                print(f"      1. Custo do Produto: R$ {product_cost:.2f}")
                print(f"      2. Marketing ({marketing_percent}% da receita): R$ {marketing_cost:.2f}")
                print(f"      3. Outros Custos (R$ {other_costs_per_unit} × {quantity}): R$ {other_costs:.2f}")
                print(f"      4. Custo por Pedido (R$ {cost_per_order} × {orders}): R$ {total_cost_per_order:.2f}")
                print(f"      5. Impostos ({company.aliquota_simples}% da receita): R$ {taxes_amount:.2f}")
                print(f"      = Total de Custos: R$ {total_costs:.2f}")
                print()
                print(f"   📈 Resultado:")
                print(f"      Receita: R$ {revenue:.2f}")
                print(f"      Total Custos: R$ {total_costs:.2f}")
                print(f"      Lucro Bruto: R$ {profit:.2f}")
                print(f"      Margem: {margin:.1f}%")
                print()
                print(f"   🔍 Comparação com o Dashboard:")
                print(f"      Dashboard mostra margem: 12.4%")
                print(f"      Cálculo correto: {margin:.1f}%")
                print()
            else:
                print(f"   ❌ Produto interno não encontrado")
                print()
            
            print("=" * 80)
            print()
    
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_profit_calculation()

