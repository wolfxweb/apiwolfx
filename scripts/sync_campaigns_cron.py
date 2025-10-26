#!/usr/bin/env python3
"""
Script para sincronização diária de campanhas de publicidade
Executado via cron
"""
import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config.settings import settings
from app.services.campaign_sync_service import CampaignSyncService
from app.models.saas_models import Company
from app.utils.notification_logger import global_logger as logger
from datetime import datetime

def sync_all_companies():
    """Sincroniza campanhas de todas as empresas ativas"""
    try:
        logger.info("=" * 80)
        logger.info(f"🚀 INICIANDO SINCRONIZAÇÃO DE CAMPANHAS - {datetime.now()}")
        logger.info("=" * 80)
        
        # Conectar ao banco
        engine = create_engine(settings.database_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        try:
            # Buscar todas as empresas
            companies = db.query(Company).all()
            logger.info(f"📊 Total de empresas encontradas: {len(companies)}")
            
            total_synced = 0
            total_campaigns = 0
            errors = 0
            
            for company in companies:
                try:
                    logger.info(f"\n{'='*60}")
                    logger.info(f"🏢 Sincronizando empresa: {company.name} (ID: {company.id})")
                    logger.info(f"{'='*60}")
                    
                    # Sincronizar campanhas da empresa
                    sync_service = CampaignSyncService(db)
                    result = sync_service.sync_campaigns_for_company(company.id)
                    
                    if result.get("success"):
                        campaigns_synced = result.get("campaigns_synced", 0)
                        products_synced = result.get("products_synced", 0)
                        total_synced += campaigns_synced
                        total_campaigns += result.get("total_campaigns", 0)
                        logger.info(f"✅ Empresa {company.name}: {campaigns_synced} campanhas, {products_synced} produtos sincronizados")
                    else:
                        errors += 1
                        error_msg = result.get("error", "Erro desconhecido")
                        logger.warning(f"⚠️ Empresa {company.name}: {error_msg}")
                        
                except Exception as e:
                    errors += 1
                    logger.error(f"❌ Erro ao sincronizar empresa {company.id}: {e}", exc_info=True)
                    continue
            
            logger.info("\n" + "=" * 80)
            logger.info("📊 RESUMO DA SINCRONIZAÇÃO")
            logger.info("=" * 80)
            logger.info(f"✅ Total de campanhas sincronizadas: {total_synced}/{total_campaigns}")
            logger.info(f"🏢 Empresas processadas: {len(companies)}")
            logger.info(f"❌ Erros: {errors}")
            logger.info("=" * 80)
            logger.info(f"✅ SINCRONIZAÇÃO CONCLUÍDA - {datetime.now()}")
            logger.info("=" * 80)
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ ERRO CRÍTICO na sincronização: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    sync_all_companies()

