"""Controller completo para gestão de publicidade"""
from sqlalchemy.orm import Session
from typing import Optional
from app.services.ml_campaign_service import MLCampaignService
from app.services.ml_product_ads_service import MLProductAdsService
from app.services.token_manager import TokenManager
from app.services.campaign_sync_service import CampaignSyncService
from app.models.saas_models import MLAccount, UserMLAccount, Token, User
import logging

logger = logging.getLogger(__name__)

class AdvertisingFullController:
    def __init__(self, db: Session):
        self.db = db
        self.campaign_service = MLCampaignService(db)
        self.ads_service = MLProductAdsService(db)
        self.token_manager = TokenManager(db)
        self.sync_service = CampaignSyncService(db)
    
    def _get_advertiser_id(self, access_token: str) -> Optional[int]:
        """Busca advertiser_id da API do Mercado Livre"""
        logger.info(f"🚀 INICIANDO _get_advertiser_id() - Token: {access_token[:20]}...")
        try:
            import requests
            url = "https://api.mercadolibre.com/advertising/advertisers"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Api-Version": "1"
            }
            params = {"product_id": "PADS"}
            
            logger.info(f"🔎 Chamando API: {url} com product_id=PADS")
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            logger.info(f"📡 Status da resposta: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"📦 Resposta da API: {data}")
                advertisers = data.get("advertisers", [])
                
                if advertisers:
                    advertiser_id = advertisers[0].get("advertiser_id")
                    logger.info(f"✅ Advertiser ID encontrado: {advertiser_id}")
                    return advertiser_id
                else:
                    logger.warning(f"⚠️ Nenhum advertiser retornado pela API")
            else:
                logger.error(f"❌ Erro ao buscar advertiser: {response.status_code} - {response.text[:200]}")
            
            return None
                        
        except Exception as e:
            logger.error(f"❌ Erro ao buscar advertiser_id: {e}", exc_info=True)
            return None
    
    def get_campaigns(self, company_id: int):
        """Lista campanhas da empresa - BUSCA LOCAL"""
        try:
            logger.info(f"📂 Buscando campanhas locais - company_id: {company_id}")
            return self.sync_service.get_local_campaigns(company_id)
        except Exception as e:
            logger.error(f"❌ ERRO: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def sync_campaigns(self, company_id: int):
        """Sincroniza campanhas do ML para o banco local"""
        try:
            logger.info(f"🔄 Sincronizando campanhas - company_id: {company_id}")
            return self.sync_service.sync_campaigns_for_company(company_id)
        except Exception as e:
            logger.error(f"❌ ERRO: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def create_campaign(self, company_id: int, campaign_data: dict):
        """Cria nova campanha"""
        try:
            account = self.db.query(MLAccount).filter(MLAccount.company_id == company_id).first()
            if not account:
                return {"success": False, "error": "Conta ML não encontrada"}
            
            user_ml = self.db.query(UserMLAccount).filter(UserMLAccount.ml_account_id == account.id).first()
            if not user_ml:
                return {"success": False, "error": "Usuário não associado à conta ML"}
            
            # Obter token válido com renovação automática
            access_token = self.token_manager.get_valid_token(user_ml.user_id)
            if not access_token:
                return {"success": False, "error": "Não foi possível obter token válido"}
            
            # Buscar advertiser_id
            advertiser_id = self._get_advertiser_id(access_token)
            if not advertiser_id:
                return {"success": False, "error": "Advertiser ID não encontrado"}
            
            campaign = self.campaign_service.create_campaign(
                account.site_id, advertiser_id, access_token, campaign_data
            )
            
            return {"success": True, "campaign": campaign}
        except Exception as e:
            logger.error(f"Erro ao criar campanha: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def update_campaign(self, company_id: int, campaign_id: int, updates: dict):
        """Atualiza campanha"""
        try:
            account = self.db.query(MLAccount).filter(MLAccount.company_id == company_id).first()
            if not account:
                return {"success": False, "error": "Conta ML não encontrada"}
            
            user_ml = self.db.query(UserMLAccount).filter(UserMLAccount.ml_account_id == account.id).first()
            if not user_ml:
                return {"success": False, "error": "Usuário não associado à conta ML"}
            
            # Obter token válido com renovação automática
            access_token = self.token_manager.get_valid_token(user_ml.user_id)
            if not access_token:
                return {"success": False, "error": "Não foi possível obter token válido"}
            
            # Buscar advertiser_id
            advertiser_id = self._get_advertiser_id(access_token)
            if not advertiser_id:
                return {"success": False, "error": "Advertiser ID não encontrado"}
            
            result = self.campaign_service.update_campaign(
                account.site_id, advertiser_id, campaign_id, access_token, updates
            )
            
            return {"success": True, "campaign": result}
        except Exception as e:
            logger.error(f"Erro ao atualizar campanha: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def delete_campaign(self, company_id: int, campaign_id: int):
        """Deleta campanha"""
        try:
            account = self.db.query(MLAccount).filter(MLAccount.company_id == company_id).first()
            if not account:
                return {"success": False, "error": "Conta ML não encontrada"}
            
            user_ml = self.db.query(UserMLAccount).filter(UserMLAccount.ml_account_id == account.id).first()
            if not user_ml:
                return {"success": False, "error": "Usuário não associado à conta ML"}
            
            # Obter token válido com renovação automática
            access_token = self.token_manager.get_valid_token(user_ml.user_id)
            if not access_token:
                return {"success": False, "error": "Não foi possível obter token válido"}
            
            # Buscar advertiser_id
            advertiser_id = self._get_advertiser_id(access_token)
            if not advertiser_id:
                return {"success": False, "error": "Advertiser ID não encontrado"}
            
            result = self.campaign_service.delete_campaign(
                account.site_id, advertiser_id, campaign_id, access_token
            )
            
            return {"success": result}
        except Exception as e:
            logger.error(f"Erro ao deletar campanha: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_metrics_summary(self, company_id: int):
        """Busca métricas consolidadas de todas as campanhas sincronizadas"""
        try:
            from app.models.advertising_models import MLCampaign
            from sqlalchemy import func
            
            logger.info(f"📊 Buscando métricas consolidadas - company_id: {company_id}")
            
            # Buscar totais agregados das campanhas
            totals = self.db.query(
                func.count(MLCampaign.id).label('total_campaigns'),
                func.sum(MLCampaign.total_spent).label('total_spent'),
                func.sum(MLCampaign.total_revenue).label('total_revenue'),
                func.sum(MLCampaign.total_clicks).label('total_clicks'),
                func.sum(MLCampaign.total_impressions).label('total_impressions'),
                func.sum(MLCampaign.total_conversions).label('total_conversions')
            ).filter(
                MLCampaign.company_id == company_id
            ).first()
            
            # Contar campanhas ativas
            active_campaigns = self.db.query(func.count(MLCampaign.id)).filter(
                MLCampaign.company_id == company_id,
                MLCampaign.status == 'active'
            ).scalar()
            
            # Extrair valores
            total_spent = float(totals.total_spent or 0)
            total_revenue = float(totals.total_revenue or 0)
            total_clicks = int(totals.total_clicks or 0)
            total_impressions = int(totals.total_impressions or 0)
            total_conversions = int(totals.total_conversions or 0)
            total_campaigns = int(totals.total_campaigns or 0)
            
            # Calcular ROAS médio
            avg_roas = (total_revenue / total_spent) if total_spent > 0 else 0
            
            # Calcular CTR
            ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
            
            logger.info(f"✅ Métricas calculadas: {active_campaigns} ativas, R$ {total_spent} gasto, R$ {total_revenue} receita, ROAS {avg_roas:.2f}x")
            
            return {
                "success": True,
                "metrics": {
                    "active_campaigns": active_campaigns,
                    "total_spent": total_spent,
                    "total_investment": total_spent,  # Alias para compatibilidade
                    "total_revenue": total_revenue,
                    "avg_roas": avg_roas,
                    "average_roas": avg_roas,  # Alias para compatibilidade
                    "total_clicks": total_clicks,
                    "total_impressions": total_impressions,
                    "total_conversions": total_conversions,
                    "total_campaigns": total_campaigns,
                    "ctr": ctr
                }
            }
        except Exception as e:
            logger.error(f"❌ Erro ao buscar métricas: {e}", exc_info=True)
            return {"success": False, "error": str(e)}