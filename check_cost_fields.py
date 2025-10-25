#!/usr/bin/env python3
"""
Verificar campos de custos para entender se são percentuais ou valores fixos
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import get_db
from app.models.saas_models import InternalProduct, Company

def check_cost_fields():
    """Verifica campos de custos"""
    db = next(get_db())
    
    try:
        # Buscar produto interno
        internal = db.query(InternalProduct).filter(
            InternalProduct.company_id == 15,
            InternalProduct.internal_sku == 'KIT-ARDUINO-UNO-INICIANTE',
            InternalProduct.status == 'active'
        ).first()
        
        # Buscar empresa
        company = db.query(Company).filter(Company.id == 15).first()
        
        print(f"📦 Produto Interno: {internal.name}")
        print(f"   marketing_cost: {internal.marketing_cost} (campo no DB)")
        print(f"   other_costs: {internal.other_costs} (campo no DB)")
        print(f"   tax_rate: {internal.tax_rate} (campo no DB)")
        print()
        
        print(f"🏢 Empresa: {company.name}")
        print(f"   percentual_marketing: {company.percentual_marketing} (campo no DB)")
        print(f"   aliquota_simples: {company.aliquota_simples} (campo no DB)")
        print()
        
        print(f"🤔 Interpretação:")
        print(f"   Marketing: {internal.marketing_cost} = 5% ou R$ 5,00?")
        print(f"   Impostos: {company.aliquota_simples}% = Simples Nacional")
        print()
        
        # Teste de cálculo
        receita_total = 6474.95
        quantidade = 97
        preco_unitario = receita_total / quantidade
        
        print(f"📊 Cálculo com Receita: R$ {receita_total:.2f} / {quantidade} unidades")
        print(f"   Preço unitário médio: R$ {preco_unitario:.2f}")
        print()
        
        print(f"💰 Cenário 1: Marketing e Impostos são PERCENTUAIS da receita")
        marketing_percent = receita_total * 0.05
        impostos_percent = receita_total * 0.05
        print(f"   Marketing (5% da receita): R$ {marketing_percent:.2f}")
        print(f"   Impostos (5% da receita): R$ {impostos_percent:.2f}")
        print()
        
        print(f"💰 Cenário 2: Marketing e Impostos são VALORES FIXOS por unidade")
        marketing_fixo = 5.00 * quantidade
        impostos_fixo = 5.00 * quantidade
        print(f"   Marketing (R$ 5,00 × {quantidade}): R$ {marketing_fixo:.2f}")
        print(f"   Impostos (R$ 5,00 × {quantidade}): R$ {impostos_fixo:.2f}")
        print()
        
        print(f"🎯 Qual é o correto?")
        print(f"   O usuário disse: 'o impsto e o maketing e 55 por uncidade'")
        print(f"   Interpretação: R$ 5,00 por unidade (não 5% da receita)")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_cost_fields()

