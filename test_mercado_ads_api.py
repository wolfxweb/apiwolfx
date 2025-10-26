#!/usr/bin/env python3
"""
Testar endpoints específicos do Mercado Ads
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
import json

def test_mercado_ads():
    db = SessionLocal()
    
    try:
        print("\n" + "="*80)
        print("🔍 TESTANDO API MERCADO ADS")
        print("="*80 + "\n")
        
        # Setup
        account = db.query(MLAccount).filter(MLAccount.company_id == 15).first()
        user_ml = db.query(UserMLAccount).filter(UserMLAccount.ml_account_id == account.id).first()
        token_manager = TokenManager(db)
        access_token = token_manager.get_valid_token(user_ml.user_id)
        campaign = db.query(MLCampaign).filter(MLCampaign.company_id == 15).first()
        
        print(f"📋 DADOS:")
        print(f"   Advertiser ID: {campaign.advertiser_id}")
        print(f"   Campaign ID: {campaign.campaign_id}\n")
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=90)  # 90 dias como mencionado
        
        # Endpoints baseados em padrões comuns de APIs de ads
        test_endpoints = [
            # Variações de reports
            {
                "name": "Reports v2 - with api-version header",
                "url": f"https://api.mercadolibre.com/ads/reports/campaigns",
                "headers": {
                    "Authorization": f"Bearer {access_token}",
                    "api-version": "2",
                    "Content-Type": "application/json"
                },
                "params": {
                    "advertiser_id": campaign.advertiser_id,
                    "campaign_id": campaign.campaign_id,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }
            },
            {
                "name": "Product Ads Reports",
                "url": f"https://api.mercadolibre.com/product-ads/reports/campaigns/{campaign.campaign_id}",
                "headers": {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                "params": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }
            },
            {
                "name": "Campaigns Stats Detailed",
                "url": f"https://api.mercadolibre.com/advertising/product-ads/campaigns/{campaign.campaign_id}/stats",
                "headers": {
                    "Authorization": f"Bearer {access_token}",
                    "api-version": "2"
                },
                "params": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "group_by": "day"
                }
            },
            {
                "name": "Advertiser Performance",
                "url": f"https://api.mercadolibre.com/advertising/{account.site_id}/advertisers/{campaign.advertiser_id}/performance",
                "headers": {
                    "Authorization": f"Bearer {access_token}",
                    "api-version": "2"
                },
                "params": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }
            },
            {
                "name": "Campaign Performance Report",
                "url": f"https://api.mercadolibre.com/advertising/{account.site_id}/product_ads/campaigns/{campaign.campaign_id}/report",
                "headers": {
                    "Authorization": f"Bearer {access_token}",
                    "api-version": "2"
                },
                "params": {
                    "date_from": start_date.strftime("%Y-%m-%d"),
                    "date_to": end_date.strftime("%Y-%m-%d")
                }
            },
            {
                "name": "Dashboard Data",
                "url": f"https://api.mercadolibre.com/advertising/dashboard/campaigns/{campaign.campaign_id}",
                "headers": {
                    "Authorization": f"Bearer {access_token}"
                },
                "params": {
                    "days": 90
                }
            },
            {
                "name": "Campaign Insights",
                "url": f"https://api.mercadolibre.com/advertising/{account.site_id}/product_ads/campaigns/{campaign.campaign_id}/insights",
                "headers": {
                    "Authorization": f"Bearer {access_token}",
                    "api-version": "2"
                }
            }
        ]
        
        for i, endpoint in enumerate(test_endpoints, 1):
            print(f"\n{'-'*80}")
            print(f"{i}. {endpoint['name']}")
            print(f"{'-'*80}")
            print(f"URL: {endpoint['url']}")
            
            try:
                response = requests.get(
                    endpoint['url'],
                    params=endpoint.get('params'),
                    headers=endpoint['headers'],
                    timeout=15
                )
                
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"\n✅ ✅ ✅ SUCESSO! ✅ ✅ ✅")
                    data = response.json()
                    print(f"\nResponse Keys: {list(data.keys())}")
                    print(f"\nFull Response:")
                    print(json.dumps(data, indent=2)[:2000])
                    print("\n" + "="*80)
                    print("🎉 ENDPOINT FUNCIONANDO! ESTE É O QUE PRECISAMOS!")
                    print("="*80)
                    break
                elif response.status_code == 401:
                    print(f"❌ Unauthorized (token pode estar inválido)")
                elif response.status_code == 403:
                    print(f"❌ Forbidden (sem permissão)")
                elif response.status_code == 404:
                    print(f"❌ Not Found")
                else:
                    print(f"❌ Error {response.status_code}")
                    print(f"Response: {response.text[:200]}")
                    
            except Exception as e:
                print(f"❌ Exception: {e}")
        
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    test_mercado_ads()

