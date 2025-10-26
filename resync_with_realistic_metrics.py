#!/usr/bin/env python3
"""
Limpar métricas antigas e resincronizar com métricas realistas
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.config.database import SessionLocal
from app.models.advertising_models import MLCampaignMetrics
from app.services.campaign_sync_service import CampaignSyncService

def resync():
    db = SessionLocal()
    
    try:
        print("\n" + "="*80)
        print("🔄 RESINCRONIZANDO COM MÉTRICAS REALISTAS")
        print("="*80 + "\n")
        
        # 1. Limpar métricas antigas
        print("1️⃣ Limpando métricas antigas...")
        deleted = db.query(MLCampaignMetrics).delete()
        db.commit()
        print(f"   ✅ {deleted} métricas removidas\n")
        
        # 2. Resincronizar
        print("2️⃣ Sincronizando com métricas realistas...")
        service = CampaignSyncService(db)
        result = service.sync_campaigns_for_company(15)
        
        print(f"\n📊 RESULTADO:")
        print(f"   Success: {result.get('success')}")
        print(f"   Campanhas: {result.get('campaigns_synced')}")
        print(f"   Produtos: {result.get('products_synced')}")
        print(f"   Métricas: {result.get('metrics_synced')}")
        
        # 3. Verificar diferenças
        print(f"\n3️⃣ Verificando variação entre campanhas...")
        from app.models.advertising_models import MLCampaign
        
        campaigns = db.query(MLCampaign).filter(MLCampaign.company_id == 15).limit(5).all()
        
        for i, campaign in enumerate(campaigns, 1):
            print(f"\n   {i}. {campaign.name}")
            print(f"      Gasto: R$ {campaign.total_spent:.2f}")
            print(f"      Receita: R$ {campaign.total_revenue:.2f}")
            print(f"      ROAS: {campaign.roas:.2f}x")
            print(f"      Cliques: {campaign.total_clicks}")
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    
    finally:
        db.close()

if __name__ == "__main__":
    resync()

