from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AdsAnalyticsService:
    def __init__(self, db: Session):
        self.db = db
        self.base_url = "https://api.mercadolibre.com"
    
    def get_performance_summary(self, company_id: int) -> Dict:
        """Busca resumo geral de performance para todas as contas ML"""
        try:
            logger.info(f"Buscando resumo de performance para company_id: {company_id}")
            
            # Buscar todas as contas ML da empresa usando ORM
            from app.models.saas_models import MLAccount, MLAccountStatus
            
            accounts_query = self.db.query(MLAccount).filter(
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).all()
            
            logger.info(f"Encontradas {len(accounts_query)} contas ML ativas")
            
            accounts = [(acc.id, acc.nickname, acc.email, acc.country_id, acc.status.value) for acc in accounts_query]
            
            summary = {
                "total_accounts": len(accounts),
                "total_spend": 0,
                "total_revenue": 0,
                "total_clicks": 0,
                "total_impressions": 0,
                "total_sales": 0,
                "average_roas": 0,
                "accounts_data": []
            }
            
            for account in accounts:
                account_data = {
                    "id": account[0],
                    "nickname": account[1],
                    "email": account[2],
                    "country_id": account[3],
                    "status": account[4],
                    "advertisers": [],
                    "total_spend": 0,
                    "total_revenue": 0,
                    "total_clicks": 0,
                    "total_impressions": 0,
                    "total_sales": 0,
                    "roas": 0
                }
                
                # Buscar advertiser_id para a conta
                advertisers_response = self._get_advertisers(account[0])
                if advertisers_response and advertisers_response.get("advertisers"):
                    for adv in advertisers_response["advertisers"]:
                        advertiser_id = adv["advertiser_id"]
                        site_id = adv["site_id"]
                        
                        # Buscar métricas de campanha para o advertiser
                        campaign_metrics = self._get_campaign_metrics(advertiser_id, site_id)
                        if campaign_metrics and campaign_metrics.get("results"):
                            for campaign in campaign_metrics["results"]:
                                metrics = campaign.get("metrics", {})
                                account_data["total_spend"] += metrics.get("cost", 0)
                                account_data["total_revenue"] += metrics.get("total_amount", 0)
                                account_data["total_clicks"] += metrics.get("clicks", 0)
                                account_data["total_impressions"] += metrics.get("prints", 0)
                                account_data["total_sales"] += metrics.get("units_quantity", 0)
                                
                                summary["total_spend"] += metrics.get("cost", 0)
                                summary["total_revenue"] += metrics.get("total_amount", 0)
                                summary["total_clicks"] += metrics.get("clicks", 0)
                                summary["total_impressions"] += metrics.get("prints", 0)
                                summary["total_sales"] += metrics.get("units_quantity", 0)
                                
                                adv_data = {
                                    "advertiser_id": advertiser_id,
                                    "site_id": site_id,
                                    "campaign_id": campaign.get("id"),
                                    "campaign_name": campaign.get("name"),
                                    "spend": metrics.get("cost", 0),
                                    "revenue": metrics.get("total_amount", 0),
                                    "clicks": metrics.get("clicks", 0),
                                    "impressions": metrics.get("prints", 0),
                                    "sales": metrics.get("units_quantity", 0),
                                    "roas": (metrics.get("total_amount", 0) / metrics.get("cost", 1)) if metrics.get("cost", 0) > 0 else 0
                                }
                                account_data["advertisers"].append(adv_data)
                
                if account_data["total_spend"] > 0:
                    account_data["roas"] = account_data["total_revenue"] / account_data["total_spend"]
                
                summary["accounts_data"].append(account_data)
            
            # Calcular ROAS médio
            if summary["total_spend"] > 0:
                summary["average_roas"] = summary["total_revenue"] / summary["total_spend"]
            
            return summary
            
        except Exception as e:
            logger.error(f"Erro ao buscar resumo de performance: {e}")
            return {
                "error": str(e),
                "total_accounts": 0,
                "total_spend": 0,
                "total_revenue": 0,
                "total_clicks": 0,
                "total_impressions": 0,
                "total_sales": 0,
                "average_roas": 0,
                "accounts_data": []
            }
    
    def _get_advertisers(self, ml_account_id: int) -> Optional[Dict]:
        """Busca advertisers para uma conta ML"""
        try:
            access_token = self._get_active_token(ml_account_id)
            if not access_token:
                logger.warning(f"Token não encontrado para ml_account_id: {ml_account_id}")
                return None
            
            headers = {"Authorization": f"Bearer {access_token}"}
            url = f"{self.base_url}/advertising/advertisers"
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Erro ao buscar advertisers: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar advertisers: {e}")
            return None
    
    def _get_campaign_metrics(self, advertiser_id: str, site_id: str) -> Optional[Dict]:
        """Busca métricas de campanhas para um advertiser"""
        try:
            # Usar token de qualquer conta ativa (simplificação)
            access_token = self._get_any_active_token()
            if not access_token:
                logger.warning("Nenhum token ativo encontrado")
                return None
            
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Buscar campanhas
            campaigns_url = f"{self.base_url}/advertising/{advertiser_id}/product_ads/campaigns/search"
            campaigns_response = requests.get(campaigns_url, headers=headers, timeout=10)
            
            if campaigns_response.status_code != 200:
                logger.warning(f"Erro ao buscar campanhas: {campaigns_response.status_code}")
                return None
            
            campaigns_data = campaigns_response.json()
            results = []
            
            # Para cada campanha, buscar métricas
            for campaign in campaigns_data.get("results", []):
                campaign_id = campaign.get("id")
                
                # Buscar métricas da campanha
                metrics_url = f"{self.base_url}/advertising/{advertiser_id}/product_ads/campaigns/{campaign_id}/metrics"
                metrics_response = requests.get(metrics_url, headers=headers, timeout=10)
                
                if metrics_response.status_code == 200:
                    metrics_data = metrics_response.json()
                    campaign["metrics"] = metrics_data
                    results.append(campaign)
                else:
                    logger.warning(f"Erro ao buscar métricas da campanha {campaign_id}: {metrics_response.status_code}")
            
            return {"results": results}
            
        except Exception as e:
            logger.error(f"Erro ao buscar métricas de campanhas: {e}")
            return None
    
    def _get_active_token(self, ml_account_id: int) -> Optional[str]:
        """Obtém token ativo para uma conta ML específica"""
        try:
            from sqlalchemy import text
            
            query = text("""
                SELECT access_token
                FROM tokens 
                WHERE ml_account_id = :ml_account_id 
                AND is_active = true 
                AND expires_at > NOW()
                ORDER BY expires_at DESC
                LIMIT 1
            """)
            
            result = self.db.execute(query, {"ml_account_id": ml_account_id}).fetchone()
            
            if result:
                return result[0]
            else:
                logger.warning(f"Nenhum token ativo encontrado para ml_account_id: {ml_account_id}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao obter token ativo: {e}")
            return None
    
    def _get_any_active_token(self) -> Optional[str]:
        """Obtém qualquer token ativo disponível"""
        try:
            from sqlalchemy import text
            
            query = text("""
                SELECT access_token
                FROM tokens 
                WHERE is_active = true 
                AND expires_at > NOW()
                ORDER BY expires_at DESC
                LIMIT 1
            """)
            
            result = self.db.execute(query).fetchone()
            
            if result:
                return result[0]
            else:
                logger.warning("Nenhum token ativo encontrado")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao obter token ativo: {e}")
            return None
