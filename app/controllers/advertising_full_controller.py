"""Controller completo para gestão de publicidade"""
from sqlalchemy.orm import Session
from app.services.ml_campaign_service import MLCampaignService
from app.services.ml_product_ads_service import MLProductAdsService
from app.models.saas_models import MLAccount, UserMLAccount, Token, User
import logging

logger = logging.getLogger(__name__)

class AdvertisingFullController:
    def __init__(self, db: Session):
        self.db = db
        self.campaign_service = MLCampaignService(db)
        self.ads_service = MLProductAdsService(db)
    
    def get_campaigns(self, company_id: int):
        """Lista campanhas da empresa"""
        try:
            accounts = self.db.query(MLAccount).filter(MLAccount.company_id == company_id).all()
            all_campaigns = []
            
            for account in accounts:
                user_ml = self.db.query(UserMLAccount).filter(UserMLAccount.ml_account_id == account.id).first()
                if user_ml:
                    token = self.db.query(Token).filter(Token.user_id == user_ml.user_id).first()
                    if token:
                        campaigns = self.campaign_service.list_campaigns(
                            account.site_id, account.advertiser_id, token.access_token
                        )
                        all_campaigns.extend(campaigns)
            
            return {"success": True, "campaigns": all_campaigns}
        except Exception as e:
            logger.error(f"Erro: {e}")
            return {"success": False, "error": str(e)}
    
    def create_campaign(self, company_id: int, campaign_data: dict):
        """Cria nova campanha"""
        try:
            account = self.db.query(MLAccount).filter(MLAccount.company_id == company_id).first()
            user_ml = self.db.query(UserMLAccount).filter(UserMLAccount.ml_account_id == account.id).first()
            token = self.db.query(Token).filter(Token.user_id == user_ml.user_id).first()
            
            campaign = self.campaign_service.create_campaign(
                account.site_id, account.advertiser_id, token.access_token, campaign_data
            )
            
            return {"success": True, "campaign": campaign}
        except Exception as e:
            logger.error(f"Erro: {e}")
            return {"success": False, "error": str(e)}
    
    def update_campaign(self, company_id: int, campaign_id: int, updates: dict):
        """Atualiza campanha"""
        try:
            account = self.db.query(MLAccount).filter(MLAccount.company_id == company_id).first()
            user_ml = self.db.query(UserMLAccount).filter(UserMLAccount.ml_account_id == account.id).first()
            token = self.db.query(Token).filter(Token.user_id == user_ml.user_id).first()
            
            result = self.campaign_service.update_campaign(
                account.site_id, account.advertiser_id, campaign_id, token.access_token, updates
            )
            
            return {"success": True, "campaign": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete_campaign(self, company_id: int, campaign_id: int):
        """Deleta campanha"""
        try:
            account = self.db.query(MLAccount).filter(MLAccount.company_id == company_id).first()
            user_ml = self.db.query(UserMLAccount).filter(UserMLAccount.ml_account_id == account.id).first()
            token = self.db.query(Token).filter(Token.user_id == user_ml.user_id).first()
            
            result = self.campaign_service.delete_campaign(
                account.site_id, account.advertiser_id, campaign_id, token.access_token
            )
            
            return {"success": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
