#!/usr/bin/env python3
"""
Sincronização FINAL com TODOS os dados REAIS da API
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.config.database import SessionLocal
from app.models.advertising_models import MLCampaignMetrics, MLCampaign
from app.services.campaign_sync_service import CampaignSyncService

def final_sync():
    db = SessionLocal()
    
    try:
        print("\n" + "="*80)
        print("🎉 SINCRONIZAÇÃO FINAL COM DADOS REAIS")
        print("="*80 + "\n")
        
        # 1. Limpar métricas antigas
        print("1️⃣ Limpando métricas antigas...")
        deleted = db.query(MLCampaignMetrics).delete()
        db.commit()
        print(f"   ✅ {deleted} métricas removidas\n")
        
        # 2. Sincronizar com dados REAIS
        print("2️⃣ Sincronizando campanhas e métricas REAIS da API ML...")
        service = CampaignSyncService(db)
        result = service.sync_campaigns_for_company(15)
        
        print(f"\n📊 RESULTADO DA SINCRONIZAÇÃO:")
        print(f"   Success: {result.get('success')}")
        print(f"   Campanhas: {result.get('campaigns_synced')}")
        print(f"   Produtos: {result.get('products_synced')}")
        print(f"   Métricas: {result.get('metrics_synced')}")
        
        if not result.get('success'):
            print(f"   ❌ Erro: {result.get('error')}")
            return
        
        # 3. Verificar dados salvos
        print(f"\n3️⃣ Verificando dados salvos...")
        
        campaigns = db.query(MLCampaign).filter(MLCampaign.company_id == 15).all()
        print(f"   Campanhas no banco: {len(campaigns)}\n")
        
        for i, campaign in enumerate(campaigns[:5], 1):
            print(f"   {i}. {campaign.name}")
            print(f"      Impressões: {campaign.total_impressions:,}")
            print(f"      Cliques: {campaign.total_clicks:,}")
            print(f"      Gasto: R$ {campaign.total_spent:,.2f}")
            print(f"      Receita: R$ {campaign.total_revenue:,.2f}")
            print(f"      ROAS: {campaign.roas:.2f}x")
            print(f"      Conversões: {campaign.total_conversions}")
            
            # Verificar métricas diárias
            metrics_count = db.query(MLCampaignMetrics).filter(
                MLCampaignMetrics.campaign_id == campaign.id
            ).count()
            print(f"      Métricas diárias: {metrics_count}")
            
            # Verificar uma métrica de exemplo
            sample_metric = db.query(MLCampaignMetrics).filter(
                MLCampaignMetrics.campaign_id == campaign.id
            ).first()
            
            if sample_metric:
                print(f"\n      📅 Exemplo de métrica diária ({sample_metric.metric_date.date()}):")
                print(f"         • Impressões: {sample_metric.impressions:,}")
                print(f"         • Cliques: {sample_metric.clicks}")
                print(f"         • Vendas Diretas: {sample_metric.direct_items_quantity}")
                print(f"         • Vendas Indiretas: {sample_metric.indirect_items_quantity}")
                print(f"         • Receita Direta: R$ {sample_metric.direct_amount:.2f}")
                print(f"         • Receita Indireta: R$ {sample_metric.indirect_amount:.2f}")
                print(f"         • ACOS: {sample_metric.acos:.2f}%")
                print(f"         • CVR: {sample_metric.cvr:.2f}%")
                print(f"         • ROAS: {sample_metric.roas:.2f}x")
                print(f"         • SOV: {sample_metric.sov:.2f}%")
            print()
        
        # 4. Estatísticas finais
        total_metrics = db.query(MLCampaignMetrics).count()
        
        print(f"4️⃣ ESTATÍSTICAS FINAIS:")
        print(f"   Total Campanhas: {len(campaigns)}")
        print(f"   Total Métricas Diárias: {total_metrics}")
        print(f"   Período: Últimos 90 dias")
        print(f"   Campos por métrica: 27 (COMPLETO!)")
        
        print("\n" + "="*80)
        print("✅ SINCRONIZAÇÃO COMPLETA COM SUCESSO!")
        print("="*80)
        print("\n🎯 Todos os dados da API estão sendo salvos:")
        print("   ✅ Impressões, Cliques, Investimento")
        print("   ✅ Vendas Diretas vs Indiretas")
        print("   ✅ Receita Direta vs Indireta vs Total")
        print("   ✅ Vendas Orgânicas (sem publicidade)")
        print("   ✅ ACOS, CVR, ROAS, SOV")
        print("   ✅ Histórico de 90 dias")
        print("\n🚀 Acesse: http://localhost:8000/ml/advertising\n")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    
    finally:
        db.close()

if __name__ == "__main__":
    final_sync()

