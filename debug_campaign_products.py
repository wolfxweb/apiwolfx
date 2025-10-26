#!/usr/bin/env python3
"""Script para debugar quais produtos estão na campanha"""
import sys
sys.path.insert(0, '/app')

from app.config.database import SessionLocal
from app.models.advertising_models import MLCampaign, MLCampaignProduct
from app.models.saas_models import MLProduct

def debug_campaign():
    db = SessionLocal()
    try:
        # Campanha ID do ML
        campaign_id_ml = "349735846"
        company_id = 15
        
        print("\n" + "="*100)
        print(f"ANÁLISE DA CAMPANHA {campaign_id_ml}")
        print("="*100)
        
        # Buscar campanha interna
        campaign = db.query(MLCampaign).filter(
            MLCampaign.campaign_id == campaign_id_ml,
            MLCampaign.company_id == company_id
        ).first()
        
        if not campaign:
            print("❌ Campanha não encontrada!")
            return
        
        print(f"\n✅ Campanha encontrada:")
        print(f"   ID interno: {campaign.id}")
        print(f"   Nome: {campaign.name}")
        print(f"   Status: {campaign.status}")
        
        # Buscar produtos da campanha
        campaign_products = db.query(
            MLProduct.id,
            MLProduct.ml_item_id,
            MLProduct.user_product_id,
            MLProduct.catalog_product_id,
            MLProduct.title
        ).join(
            MLCampaignProduct,
            MLCampaignProduct.ml_product_id == MLProduct.id
        ).filter(
            MLCampaignProduct.campaign_id == campaign.id
        ).all()
        
        print(f"\n📦 PRODUTOS NA CAMPANHA ({len(campaign_products)}):")
        print("="*100)
        
        all_ids = set()
        for p in campaign_products:
            print(f"\n{p.id}. {p.title[:60]}")
            print(f"   ml_item_id: {p.ml_item_id}")
            if p.ml_item_id:
                all_ids.add(p.ml_item_id)
            
            if p.user_product_id:
                print(f"   user_product_id: {p.user_product_id}")
                all_ids.add(p.user_product_id)
            
            if p.catalog_product_id:
                print(f"   catalog_product_id: {p.catalog_product_id}")
        
        print(f"\n{'='*100}")
        print(f"📋 LISTA DE TODOS OS IDs PARA BUSCAR ({len(all_ids)}):")
        print("="*100)
        for item_id in sorted(all_ids):
            print(f"  - {item_id}")
        
        # Verificar IDs que estão aparecendo mas não deveriam
        print(f"\n{'='*100}")
        print("🔍 VERIFICANDO IDs QUE APARECEM NA LISTAGEM:")
        print("="*100)
        
        suspicious_ids = [
            "MLB3894965669",  # Kit Chaves
            "MLB5598362090",  # Suporte TV
            "MLB4139476777",  # Kit Espaguete
            "MLB5126862634",  # Placa Amplificadora
            "MLB4166851761",  # Suporte TV - User Product ID
            "MLB4156159337",  # Placa Uno R4
        ]
        
        for sus_id in suspicious_ids:
            if sus_id in all_ids:
                print(f"  ✅ {sus_id} - ESTÁ na campanha (correto)")
            else:
                print(f"  ❌ {sus_id} - NÃO ESTÁ na campanha (ERRO!)")
                # Verificar se esse ID existe em ml_products
                prod = db.query(MLProduct).filter(MLProduct.ml_item_id == sus_id).first()
                if prod:
                    print(f"      → Produto existe: {prod.title[:50]}")
                    print(f"      → user_product_id: {prod.user_product_id}")
                    print(f"      → catalog_product_id: {prod.catalog_product_id}")
        
    finally:
        db.close()

if __name__ == '__main__':
    debug_campaign()

