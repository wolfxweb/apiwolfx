#!/usr/bin/env python3
"""
Testar se os endpoints da API estão retornando dados corretos
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.config.database import SessionLocal
from app.controllers.advertising_full_controller import AdvertisingFullController

def test_endpoints():
    db = SessionLocal()
    
    try:
        controller = AdvertisingFullController(db)
        company_id = 15
        
        print("\n" + "="*80)
        print("🔍 TESTANDO ENDPOINTS DA API")
        print("="*80 + "\n")
        
        # 1. Testar get_campaigns
        print("1️⃣ Testando get_campaigns()...")
        campaigns_result = controller.get_campaigns(company_id)
        print(f"   Success: {campaigns_result.get('success')}")
        print(f"   Total Campanhas: {len(campaigns_result.get('campaigns', []))}")
        if campaigns_result.get('campaigns'):
            first = campaigns_result['campaigns'][0]
            print(f"   Primeira Campanha:")
            print(f"      Nome: {first.get('name')}")
            print(f"      Total Spent: R$ {first.get('total_spent', 0)}")
            print(f"      Total Revenue: R$ {first.get('total_revenue', 0)}")
            print(f"      ROAS: {first.get('roas', 0)}")
        print()
        
        # 2. Testar get_metrics_summary
        print("2️⃣ Testando get_metrics_summary()...")
        metrics_result = controller.get_metrics_summary(company_id)
        print(f"   Success: {metrics_result.get('success')}")
        if metrics_result.get('success'):
            metrics = metrics_result.get('metrics', {})
            print(f"   Campanhas Ativas: {metrics.get('active_campaigns', 0)}")
            print(f"   Total Investido: R$ {metrics.get('total_spent', 0)}")
            print(f"   Total Receita: R$ {metrics.get('total_revenue', 0)}")
            print(f"   ROAS Médio: {metrics.get('average_roas', 0)}")
        else:
            print(f"   Erro: {metrics_result.get('error')}")
        print()
        
        # 3. Verificar diretamente no banco
        print("3️⃣ Verificando diretamente no banco...")
        from app.models.advertising_models import MLCampaign, MLCampaignMetrics, MLCampaignProduct
        
        campaigns_count = db.query(MLCampaign).filter(MLCampaign.company_id == company_id).count()
        products_count = db.query(MLCampaignProduct).count()
        metrics_count = db.query(MLCampaignMetrics).count()
        
        print(f"   Campanhas no banco: {campaigns_count}")
        print(f"   Produtos no banco: {products_count}")
        print(f"   Métricas no banco: {metrics_count}")
        
        if campaigns_count > 0:
            campaign = db.query(MLCampaign).filter(MLCampaign.company_id == company_id).first()
            print(f"\n   Primeira campanha:")
            print(f"      Nome: {campaign.name}")
            print(f"      Status: {campaign.status}")
            print(f"      Total Spent: R$ {campaign.total_spent}")
            print(f"      Total Revenue: R$ {campaign.total_revenue}")
            print(f"      ROAS: {campaign.roas}")
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    test_endpoints()

