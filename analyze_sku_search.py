#!/usr/bin/env python3
"""
Script para analisar a busca de produto por SKU
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from app.models.saas_models import InternalProduct, SKUManagement, MLProduct
from sqlalchemy import or_, and_

def analyze_sku_search(sku: str):
    """Analisa como o SKU está sendo buscado"""
    db = SessionLocal()
    
    try:
        print(f"🔍 Analisando busca para SKU: '{sku}'\n")
        
        # 1. Buscar em InternalProduct pelo internal_sku
        print("1️⃣ Buscando em InternalProduct pelo internal_sku:")
        internal_products = db.query(InternalProduct).filter(
            InternalProduct.internal_sku == sku
        ).all()
        
        if internal_products:
            for p in internal_products:
                print(f"   ✅ Encontrado: ID={p.id}, SKU={p.internal_sku}, Name={p.name}, Company={p.company_id}, Status={p.status}")
        else:
            print("   ❌ Nenhum produto encontrado")
        
        # 2. Buscar em SKUManagement pelo sku
        print("\n2️⃣ Buscando em SKUManagement pelo sku:")
        sku_managements = db.query(SKUManagement).filter(
            SKUManagement.sku == sku
        ).all()
        
        if sku_managements:
            for sm in sku_managements:
                print(f"   ✅ Encontrado: ID={sm.id}, SKU={sm.sku}, Platform={sm.platform}, Platform Item={sm.platform_item_id}")
                print(f"      Internal Product ID: {sm.internal_product_id}, Company={sm.company_id}, Status={sm.status}")
                
                if sm.internal_product_id:
                    internal = db.query(InternalProduct).filter(InternalProduct.id == sm.internal_product_id).first()
                    if internal:
                        print(f"      → Produto Interno: ID={internal.id}, SKU={internal.internal_sku}, Name={internal.name}, Status={internal.status}")
        else:
            print("   ❌ Nenhum registro encontrado")
        
        # 3. Buscar em MLProduct pelo seller_sku ou seller_custom_field
        print("\n3️⃣ Buscando em MLProduct pelo seller_sku ou seller_custom_field:")
        ml_products = db.query(MLProduct).filter(
            or_(
                MLProduct.seller_sku == sku,
                MLProduct.seller_custom_field == sku
            )
        ).all()
        
        if ml_products:
            for mp in ml_products:
                print(f"   ✅ Encontrado: ID={mp.id}, ML Item ID={mp.ml_item_id}")
                print(f"      Seller SKU={mp.seller_sku}, Seller Custom Field={mp.seller_custom_field}, Company={mp.company_id}")
        else:
            print("   ❌ Nenhum produto ML encontrado")
        
        # 4. Buscar variações do SKU (case insensitive, com/sem espaços)
        print("\n4️⃣ Buscando variações do SKU (case insensitive):")
        variations = [
            sku.upper(),
            sku.lower(),
            sku.strip(),
            sku.replace('-', ''),
            sku.replace('_', ''),
        ]
        
        for variant in set(variations):
            if variant == sku:
                continue
            print(f"   🔍 Tentando variação: '{variant}'")
            
            # InternalProduct
            found = db.query(InternalProduct).filter(
                InternalProduct.internal_sku.ilike(variant)
            ).first()
            if found:
                print(f"      ✅ Encontrado em InternalProduct: ID={found.id}, SKU={found.internal_sku}")
            
            # SKUManagement
            found = db.query(SKUManagement).filter(
                SKUManagement.sku.ilike(variant)
            ).first()
            if found:
                print(f"      ✅ Encontrado em SKUManagement: ID={found.id}, SKU={found.sku}")
            
            # MLProduct
            found = db.query(MLProduct).filter(
                or_(
                    MLProduct.seller_sku.ilike(variant),
                    MLProduct.seller_custom_field.ilike(variant)
                )
            ).first()
            if found:
                print(f"      ✅ Encontrado em MLProduct: ID={found.id}, Seller SKU={found.seller_sku}")
        
        # 5. Simular a busca atual do código
        print("\n5️⃣ Simulando busca atual do código (get_pricing_data_by_sku):")
        
        # Primeira tentativa: InternalProduct direto
        product = db.query(InternalProduct).filter(
            and_(
                InternalProduct.internal_sku == sku,
                InternalProduct.status == "active"
            )
        ).first()
        
        if product:
            print(f"   ✅ Encontrado diretamente em InternalProduct: ID={product.id}, Company={product.company_id}")
        else:
            print("   ❌ Não encontrado diretamente em InternalProduct")
            
            # Segunda tentativa: via SKUManagement
            sku_mgmt = db.query(SKUManagement).filter(
                and_(
                    SKUManagement.sku == sku,
                    SKUManagement.status == "active",
                    SKUManagement.internal_product_id.isnot(None)
                )
            ).first()
            
            if sku_mgmt:
                print(f"   ✅ Encontrado em SKUManagement: ID={sku_mgmt.id}, Internal Product ID={sku_mgmt.internal_product_id}")
                
                product = db.query(InternalProduct).filter(
                    and_(
                        InternalProduct.id == sku_mgmt.internal_product_id,
                        InternalProduct.status == "active"
                    )
                ).first()
                
                if product:
                    print(f"   ✅ Produto interno encontrado via SKUManagement: ID={product.id}, Company={product.company_id}")
                else:
                    print(f"   ❌ Produto interno não encontrado pelo ID {sku_mgmt.internal_product_id}")
            else:
                print("   ❌ Não encontrado em SKUManagement")
        
        # 6. Verificar se há problemas de case sensitivity ou espaços
        print("\n6️⃣ Verificando problemas de case sensitivity ou espaços:")
        print(f"   SKU original: '{sku}' (len={len(sku)})")
        print(f"   SKU upper: '{sku.upper()}'")
        print(f"   SKU lower: '{sku.lower()}'")
        print(f"   SKU strip: '{sku.strip()}'")
        
        # Buscar com ILIKE (case insensitive)
        print("\n   Buscando com ILIKE (case insensitive):")
        found_ilike = db.query(InternalProduct).filter(
            InternalProduct.internal_sku.ilike(sku)
        ).all()
        if found_ilike:
            for p in found_ilike:
                print(f"      ✅ Encontrado: ID={p.id}, SKU='{p.internal_sku}' (exato: {p.internal_sku == sku})")
        
        found_ilike_sku = db.query(SKUManagement).filter(
            SKUManagement.sku.ilike(sku)
        ).all()
        if found_ilike_sku:
            for sm in found_ilike_sku:
                print(f"      ✅ Encontrado em SKUManagement: ID={sm.id}, SKU='{sm.sku}' (exato: {sm.sku == sku})")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    sku = "M24fb-610a"
    if len(sys.argv) > 1:
        sku = sys.argv[1]
    analyze_sku_search(sku)

