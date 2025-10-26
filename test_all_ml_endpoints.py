#!/usr/bin/env python3
"""
Testar todos os possíveis endpoints de métricas do ML
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.config.database import SessionLocal
from app.models.saas_models import MLAccount, UserMLAccount
from app.models.advertising_models import MLCampaign
from app.services.token_manager import TokenManager
import requests
from datetime import datetime, timedelta

def test_all_endpoints():
    db = SessionLocal()
    
    try:
        print("\n" + "="*80)
        print("🔍 TESTANDO TODOS OS ENDPOINTS POSSÍVEIS DE MÉTRICAS")
        print("="*80 + "\n")
        
        # Setup
        account = db.query(MLAccount).filter(MLAccount.company_id == 15).first()
        user_ml = db.query(UserMLAccount).filter(UserMLAccount.ml_account_id == account.id).first()
        token_manager = TokenManager(db)
        access_token = token_manager.get_valid_token(user_ml.user_id)
        campaign = db.query(MLCampaign).filter(MLCampaign.company_id == 15).first()
        
        print(f"📋 DADOS:")
        print(f"   Site ID: {account.site_id}")
        print(f"   Advertiser ID: {campaign.advertiser_id}")
        print(f"   Campaign ID: {campaign.campaign_id}")
        print(f"   Campaign Name: {campaign.name}\n")
        
        # Lista de endpoints para testar
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        endpoints_to_test = [
            # Reports/Analytics
            {
                "name": "Reports - Campaigns",
                "url": "https://api.mercadolibre.com/advertising/reports/campaigns",
                "method": "GET",
                "headers": {"Authorization": f"Bearer {access_token}"},
                "params": {
                    "advertiser_id": campaign.advertiser_id,
                    "campaign_ids": campaign.campaign_id,
                    "date_from": start_date.strftime("%Y-%m-%d"),
                    "date_to": end_date.strftime("%Y-%m-%d")
                }
            },
            {
                "name": "Analytics - Campaigns",
                "url": f"https://api.mercadolibre.com/advertising/analytics/campaigns/{campaign.campaign_id}",
                "method": "GET",
                "headers": {"Authorization": f"Bearer {access_token}"},
                "params": {
                    "date_from": start_date.strftime("%Y-%m-%d"),
                    "date_to": end_date.strftime("%Y-%m-%d")
                }
            },
            {
                "name": "Stats - Campaign",
                "url": f"https://api.mercadolibre.com/advertising/campaigns/{campaign.campaign_id}/stats",
                "method": "GET",
                "headers": {"Authorization": f"Bearer {access_token}"},
                "params": {
                    "date_from": start_date.strftime("%Y-%m-%d"),
                    "date_to": end_date.strftime("%Y-%m-%d")
                }
            },
            {
                "name": "Metrics - Campaign",
                "url": f"https://api.mercadolibre.com/advertising/campaigns/{campaign.campaign_id}/metrics",
                "method": "GET",
                "headers": {"Authorization": f"Bearer {access_token}"},
                "params": {
                    "date_from": start_date.strftime("%Y-%m-%d"),
                    "date_to": end_date.strftime("%Y-%m-%d")
                }
            },
            {
                "name": "Product Ads - Stats",
                "url": f"https://api.mercadolibre.com/advertising/product_ads/campaigns/{campaign.campaign_id}/stats",
                "method": "GET",
                "headers": {"Authorization": f"Bearer {access_token}"},
                "params": {
                    "date_from": start_date.strftime("%Y-%m-%d"),
                    "date_to": end_date.strftime("%Y-%m-%d")
                }
            },
            {
                "name": "Advertiser - Reports",
                "url": f"https://api.mercadolibre.com/advertising/advertisers/{campaign.advertiser_id}/reports",
                "method": "GET",
                "headers": {"Authorization": f"Bearer {access_token}"},
                "params": {
                    "date_from": start_date.strftime("%Y-%m-%d"),
                    "date_to": end_date.strftime("%Y-%m-%d")
                }
            },
            {
                "name": "Billing - Charges (Real Data)",
                "url": f"https://api.mercadolibre.com/advertising/billing/charges",
                "method": "GET",
                "headers": {"Authorization": f"Bearer {access_token}"},
                "params": {
                    "advertiser_id": campaign.advertiser_id,
                    "date_from": start_date.strftime("%Y-%m-%d"),
                    "date_to": end_date.strftime("%Y-%m-%d")
                }
            }
        ]
        
        success_count = 0
        
        for i, endpoint in enumerate(endpoints_to_test, 1):
            print(f"\n{'='*80}")
            print(f"{i}. {endpoint['name']}")
            print(f"{'='*80}")
            print(f"URL: {endpoint['url']}")
            print(f"Params: {endpoint.get('params', {})}")
            
            try:
                response = requests.get(
                    endpoint['url'],
                    params=endpoint.get('params'),
                    headers=endpoint['headers'],
                    timeout=10
                )
                
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"✅ SUCESSO!")
                    data = response.json()
                    print(f"Response keys: {list(data.keys())}")
                    print(f"Data preview: {str(data)[:500]}")
                    success_count += 1
                else:
                    print(f"❌ Error: {response.text[:200]}")
                    
            except Exception as e:
                print(f"❌ Exception: {e}")
        
        print(f"\n{'='*80}")
        print(f"📊 RESUMO: {success_count}/{len(endpoints_to_test)} endpoints funcionando")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    test_all_endpoints()

