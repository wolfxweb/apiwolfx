#!/usr/bin/env python3
"""
Testar o endpoint CORRETO da API do ML
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

def test_correct_api():
    db = SessionLocal()
    
    try:
        print("\n" + "="*80)
        print("🎉 TESTANDO ENDPOINT CORRETO DA DOCUMENTAÇÃO ML")
        print("="*80 + "\n")
        
        # Setup
        account = db.query(MLAccount).filter(MLAccount.company_id == 15).first()
        user_ml = db.query(UserMLAccount).filter(UserMLAccount.ml_account_id == account.id).first()
        token_manager = TokenManager(db)
        access_token = token_manager.get_valid_token(user_ml.user_id)
        
        # Buscar advertiser_id
        adv_url = "https://api.mercadolibre.com/advertising/advertisers"
        adv_headers = {"Authorization": f"Bearer {access_token}", "Api-Version": "1"}
        adv_response = requests.get(adv_url, params={"product_id": "PADS"}, headers=adv_headers)
        advertiser_id = adv_response.json()["advertisers"][0]["advertiser_id"]
        
        print(f"📋 DADOS:")
        print(f"   Site ID: {account.site_id}")
        print(f"   Advertiser ID: {advertiser_id}\n")
        
        # Datas: últimos 90 dias
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=90)
        
        # Endpoint CORRETO da documentação
        url = f"https://api.mercadolibre.com/advertising/{account.site_id}/advertisers/{advertiser_id}/product_ads/campaigns/search"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "api-version": "2"
        }
        
        # Todas as métricas disponíveis
        metrics = [
            "clicks", "prints", "ctr", "cost", "cpc", "acos",
            "organic_units_quantity", "organic_units_amount", "organic_items_quantity",
            "direct_items_quantity", "indirect_items_quantity", "advertising_items_quantity",
            "cvr", "roas", "sov",
            "direct_units_quantity", "indirect_units_quantity", "units_quantity",
            "direct_amount", "indirect_amount", "total_amount"
        ]
        
        params = {
            "date_from": start_date.strftime("%Y-%m-%d"),
            "date_to": end_date.strftime("%Y-%m-%d"),
            "metrics": ",".join(metrics),
            "metrics_summary": "true"
        }
        
        print("="*80)
        print("🔍 TESTANDO: Métricas Agregadas de Campanhas")
        print("="*80)
        print(f"URL: {url}")
        print(f"Params: {json.dumps(params, indent=2)}\n")
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        print(f"Status: {response.status_code}\n")
        
        if response.status_code == 200:
            print("✅" * 40)
            print("🎉 SUCESSO! API FUNCIONANDO!")
            print("✅" * 40)
            
            data = response.json()
            
            print(f"\n📊 ESTRUTURA DA RESPOSTA:")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
            
            if "results" in data:
                print(f"\n📈 TOTAL DE CAMPANHAS: {len(data['results'])}")
                
                if data["results"]:
                    first_campaign = data["results"][0]
                    print(f"\n📋 PRIMEIRA CAMPANHA:")
                    print(f"   Nome: {first_campaign.get('name')}")
                    print(f"   Status: {first_campaign.get('status')}")
                    print(f"   Budget: R$ {first_campaign.get('budget')}")
                    
                    if "metrics" in first_campaign:
                        metrics_data = first_campaign["metrics"]
                        print(f"\n💰 MÉTRICAS REAIS:")
                        print(f"   Impressões (prints): {metrics_data.get('prints')}")
                        print(f"   Cliques: {metrics_data.get('clicks')}")
                        print(f"   Investimento (cost): R$ {metrics_data.get('cost')}")
                        print(f"   Receita Total: R$ {metrics_data.get('total_amount')}")
                        print(f"   ROAS: {metrics_data.get('roas')}")
                        print(f"   CTR: {metrics_data.get('ctr')}%")
                        print(f"   CPC: R$ {metrics_data.get('cpc')}")
                        print(f"   ACOS: {metrics_data.get('acos')}%")
                        print(f"   Vendas Diretas: {metrics_data.get('direct_items_quantity')}")
                        print(f"   Vendas Indiretas: {metrics_data.get('indirect_items_quantity')}")
            
            if "metrics_summary" in data:
                print(f"\n📊 RESUMO CONSOLIDADO:")
                summary = data["metrics_summary"]
                print(json.dumps(summary, indent=2, ensure_ascii=False))
            
            print("\n" + "="*80)
            print("🎯 ESTE É O ENDPOINT QUE PRECISAMOS!")
            print("="*80)
            
        else:
            print(f"❌ ERRO {response.status_code}")
            print(f"Response: {response.text}")
        
        # Testar também métricas diárias
        print(f"\n\n{'='*80}")
        print("🔍 TESTANDO: Métricas Diárias")
        print("="*80)
        
        params["aggregation_type"] = "DAILY"
        params["limit"] = "5"  # Limitar para teste
        
        response_daily = requests.get(url, params=params, headers=headers, timeout=30)
        
        print(f"Status: {response_daily.status_code}\n")
        
        if response_daily.status_code == 200:
            print("✅ Métricas diárias também funcionando!")
            daily_data = response_daily.json()
            print(f"Preview: {json.dumps(daily_data, indent=2, ensure_ascii=False)[:1000]}")
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    test_correct_api()

