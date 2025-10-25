"""
Teste para verificar o cálculo correto de lucro e margem
Produto: Kit Eletronica MLB5069302578
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Configuração do banco de dados
DATABASE_URL = "postgresql://wolfx:S7h7hYTuJrRIkLMG2kx0@localhost:5432/apiwolfx"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

print("=" * 80)
print("TESTE DE CÁLCULO DE LUCRO E MARGEM")
print("=" * 80)

# Buscar dados do produto
company_id = 15
sku = "KIT-ARDUINO"
month = 10
year = 2025

# 1. Buscar produto interno
query_internal = text("""
    SELECT 
        internal_sku,
        cost_price,
        marketing_cost,
        other_costs,
        tax_rate
    FROM internal_products
    WHERE company_id = :company_id
        AND internal_sku = :sku
        AND status = 'active'
""")
internal_product = db.execute(query_internal, {"company_id": company_id, "sku": sku}).fetchone()

if not internal_product:
    print(f"❌ Produto interno '{sku}' não encontrado!")
    sys.exit(1)

print("\n📦 PRODUTO INTERNO:")
print(f"   SKU: {internal_product.internal_sku}")
print(f"   Custo Unitário: R$ {internal_product.cost_price:.2f}")
print(f"   Marketing (%): {internal_product.marketing_cost:.2f}%")
print(f"   Outros Custos Unitários: R$ {internal_product.other_costs:.2f}")
print(f"   Taxa de Imposto (%): {internal_product.tax_rate:.2f}%")

# 2. Buscar dados da empresa
query_company = text("""
    SELECT 
        regime_tributario,
        aliquota_simples,
        percentual_marketing,
        custo_adicional_por_pedido
    FROM companies
    WHERE id = :company_id
""")
company = db.execute(query_company, {"company_id": company_id}).fetchone()

print("\n🏢 EMPRESA:")
print(f"   Regime: {company.regime_tributario}")
print(f"   Alíquota Simples: {company.aliquota_simples}%")
print(f"   Marketing Empresa (%): {company.percentual_marketing}%")
print(f"   Custo por Pedido: R$ {company.custo_adicional_por_pedido:.2f}")

# 3. Buscar vendas do produto no período
query_sales = text("""
    SELECT 
        mo.ml_order_id,
        mo.seller_sku,
        mo.quantity,
        mo.unit_price,
        mo.total_amount,
        COUNT(DISTINCT mo.ml_order_id) as orders
    FROM ml_orders mo
    LEFT JOIN ml_products mp ON mo.item_id = mp.ml_id
    WHERE mo.company_id = :company_id
        AND mp.seller_sku = :sku
        AND mo.payments::text != '[]'
        AND mo.payments::text != '{}'
        AND (mo.payments->0->>'date_approved')::timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'UTC-4' >= 
            DATE_TRUNC('month', TO_DATE(:year || '-' || :month || '-01', 'YYYY-MM-DD'))
        AND (mo.payments->0->>'date_approved')::timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'UTC-4' < 
            DATE_TRUNC('month', TO_DATE(:year || '-' || :month || '-01', 'YYYY-MM-DD')) + INTERVAL '1 month'
        AND mo.status IN ('PAID', 'CONFIRMED', 'SHIPPED', 'DELIVERED')
    GROUP BY mo.ml_order_id, mo.seller_sku, mo.quantity, mo.unit_price, mo.total_amount
""")
sales = db.execute(query_sales, {"company_id": company_id, "sku": sku, "month": month, "year": year}).fetchall()

if not sales:
    print(f"\n❌ Nenhuma venda encontrada para '{sku}' em {month}/{year}!")
    sys.exit(1)

print(f"\n💰 VENDAS EM {month}/{year}:")
print(f"   Total de Pedidos: {len(sales)}")

# Calcular totais
total_quantity = sum(sale.quantity for sale in sales)
total_revenue = sum(sale.total_amount for sale in sales)
total_orders = len(sales)

print(f"   Quantidade Vendida: {total_quantity} unidades")
print(f"   Receita Total: R$ {total_revenue:.2f}")
print(f"   Preço Médio: R$ {total_revenue / total_quantity:.2f} por unidade")

# 4. CALCULAR CUSTOS
print("\n" + "=" * 80)
print("CÁLCULO DE CUSTOS")
print("=" * 80)

# Custo do produto (POR UNIDADE, multiplicar pela quantidade)
cost_per_unit = float(internal_product.cost_price)
product_cost = cost_per_unit * total_quantity
print(f"\n1. Custo do Produto:")
print(f"   Custo Unitário: R$ {cost_per_unit:.2f}")
print(f"   Quantidade: {total_quantity} unidades")
print(f"   TOTAL: R$ {cost_per_unit:.2f} × {total_quantity} = R$ {product_cost:.2f}")

# Marketing (% da EMPRESA sobre receita)
marketing_percent = float(company.percentual_marketing or 0) if company.percentual_marketing else float(internal_product.marketing_cost or 0)
marketing_cost = total_revenue * (marketing_percent / 100)
print(f"\n2. Marketing:")
print(f"   Percentual: {marketing_percent}%")
print(f"   Receita: R$ {total_revenue:.2f}")
print(f"   TOTAL: R$ {total_revenue:.2f} × {marketing_percent}% = R$ {marketing_cost:.2f}")

# Outros custos (fixo POR UNIDADE)
other_costs_per_unit = float(internal_product.other_costs or 0)
other_costs = other_costs_per_unit * total_quantity
print(f"\n3. Outros Custos:")
print(f"   Custo Unitário: R$ {other_costs_per_unit:.2f}")
print(f"   Quantidade: {total_quantity} unidades")
print(f"   TOTAL: R$ {other_costs_per_unit:.2f} × {total_quantity} = R$ {other_costs:.2f}")

# Custo adicional por pedido (fixo POR PEDIDO)
cost_per_order = float(company.custo_adicional_por_pedido or 0)
total_cost_per_order = cost_per_order * total_orders
print(f"\n4. Custo Adicional por Pedido:")
print(f"   Custo por Pedido: R$ {cost_per_order:.2f}")
print(f"   Número de Pedidos: {total_orders}")
print(f"   TOTAL: R$ {cost_per_order:.2f} × {total_orders} = R$ {total_cost_per_order:.2f}")

# Impostos (% sobre receita baseado no regime)
taxes_amount = 0.0
if company.regime_tributario == 'simples_nacional':
    if company.aliquota_simples:
        taxes_amount = total_revenue * (float(company.aliquota_simples) / 100)
        print(f"\n5. Impostos (Simples Nacional):")
        print(f"   Alíquota: {company.aliquota_simples}%")
        print(f"   Receita: R$ {total_revenue:.2f}")
        print(f"   TOTAL: R$ {total_revenue:.2f} × {company.aliquota_simples}% = R$ {taxes_amount:.2f}")

# Total de custos
total_costs = product_cost + marketing_cost + other_costs + total_cost_per_order + taxes_amount

print("\n" + "=" * 80)
print("RESUMO DE CUSTOS")
print("=" * 80)
print(f"Custo do Produto:       R$ {product_cost:>10.2f}")
print(f"Marketing:              R$ {marketing_cost:>10.2f}")
print(f"Outros Custos:          R$ {other_costs:>10.2f}")
print(f"Custo por Pedido:       R$ {total_cost_per_order:>10.2f}")
print(f"Impostos:               R$ {taxes_amount:>10.2f}")
print("-" * 80)
print(f"TOTAL DE CUSTOS:        R$ {total_costs:>10.2f}")

# Lucro e margem
profit = total_revenue - total_costs
margin_percent = (profit / total_revenue * 100) if total_revenue > 0 else 0

print("\n" + "=" * 80)
print("RESULTADO")
print("=" * 80)
print(f"Receita Total:          R$ {total_revenue:>10.2f}")
print(f"Total de Custos:        R$ {total_costs:>10.2f}")
print("-" * 80)
print(f"LUCRO BRUTO:            R$ {profit:>10.2f}")
print(f"MARGEM BRUTA:           {margin_percent:>10.1f}%")
print("=" * 80)

db.close()

