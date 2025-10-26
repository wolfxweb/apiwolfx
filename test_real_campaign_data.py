#!/usr/bin/env python3
"""
Verificar quais dados reais temos das campanhas
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.config.database import SessionLocal
from app.models.advertising_models import MLCampaign
import json

def check_campaign_data():
    db = SessionLocal()
    
    try:
        print("\n" + "="*80)
        print("🔍 VERIFICANDO DADOS REAIS DAS CAMPANHAS")
        print("="*80 + "\n")
        
        campaigns = db.query(MLCampaign).filter(MLCampaign.company_id == 15).all()
        
        for i, campaign in enumerate(campaigns, 1):
            print(f"\n{i}. {campaign.name}")
            print(f"   ID: {campaign.campaign_id}")
            print(f"   Status: {campaign.status}")
            print(f"   Daily Budget: R$ {campaign.daily_budget}")
            print(f"   Total Budget: R$ {campaign.total_budget}")
            
            # Verificar se tem dados adicionais no JSON
            if campaign.campaign_data:
                data = campaign.campaign_data
                print(f"\n   📦 DADOS DISPONÍVEIS NO campaign_data:")
                for key in data.keys():
                    print(f"      • {key}: {data.get(key)}")
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    check_campaign_data()

