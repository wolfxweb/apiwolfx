from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import logging

from app.services.ads_analytics_service import AdsAnalyticsService

logger = logging.getLogger(__name__)

class AdsAnalyticsController:
    def __init__(self, db: Session):
        self.db = db
        self.ads_service = AdsAnalyticsService(db)
    
    def get_dashboard_data(self, company_id: int, date_from: str = None, date_to: str = None) -> Dict:
        """Busca dados para o dashboard principal de Analytics"""
        try:
            logger.info(f"Buscando dados do dashboard para company_id: {company_id}, date_from: {date_from}, date_to: {date_to}")
            
            # Buscar resumo geral de performance
            summary = self.ads_service.get_performance_summary(company_id)
            logger.info(f"Summary recebido: {summary}")
            
            if "error" in summary:
                logger.error(f"Erro no summary: {summary['error']}")
                return {
                    "success": False,
                    "error": summary["error"],
                    "data": {}
                }
            
            # Calcular métricas adicionais
            dashboard_data = {
                "summary": summary,
                "kpis": {
                    "total_spend": summary.get("total_spend", 0),
                    "total_revenue": summary.get("total_revenue", 0),
                    "total_clicks": summary.get("total_clicks", 0),
                    "total_impressions": summary.get("total_impressions", 0),
                    "total_sales": summary.get("total_sales", 0),
                    "average_roas": summary.get("average_roas", 0),
                    "total_accounts": summary.get("total_accounts", 0),
                    "active_accounts": len([acc for acc in summary.get("accounts_data", []) if acc.get("advertisers")])
                },
                "performance_metrics": self._calculate_performance_metrics(summary),
                "accounts": summary.get("accounts_data", []),
                "top_products": [],  # Será preenchido se houver dados
                "daily_metrics": []  # Será preenchido se houver dados
            }
            
            logger.info(f"Dashboard data criado com sucesso: {dashboard_data}")
            
            return {
                "success": True,
                "data": dashboard_data
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados do dashboard: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": {}
            }
    
    def get_account_analytics(self, company_id: int, ml_account_id: int, 
                            date_from: str = None, date_to: str = None) -> Dict:
        """Busca analytics detalhados para uma conta específica"""
        try:
            logger.info(f"Buscando analytics para conta {ml_account_id} da empresa {company_id}")
            
            # Verificar se a conta pertence à empresa
            from app.models.saas_models import MLAccount, MLAccountStatus
            
            account = self.db.query(MLAccount).filter(
                MLAccount.id == ml_account_id,
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).first()
            
            if not account:
                return {
                    "success": False,
                    "error": "Conta não encontrada ou inativa"
                }
            
            # Buscar dados específicos da conta
            summary = self.ads_service.get_performance_summary(company_id)
            
            if "error" in summary:
                return {
                    "success": False,
                    "error": summary["error"]
                }
            
            # Filtrar dados apenas para esta conta
            account_data = next((acc for acc in summary.get("accounts_data", []) if acc["id"] == ml_account_id), None)
            
            if not account_data:
                return {
                    "success": False,
                    "error": "Nenhum dado encontrado para esta conta"
                }
            
            return {
                "success": True,
                "data": {
                    "account": account_data,
                    "metrics": self._calculate_account_metrics(account_data)
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar analytics da conta: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_product_performance(self, company_id: int, ml_account_id: int, 
                              advertiser_id: str, date_from: str = None, date_to: str = None) -> Dict:
        """Busca performance de produtos para um advertiser específico"""
        try:
            logger.info(f"Buscando performance de produtos para advertiser {advertiser_id}")
            
            # Verificar se a conta pertence à empresa
            from app.models.saas_models import MLAccount, MLAccountStatus
            
            account = self.db.query(MLAccount).filter(
                MLAccount.id == ml_account_id,
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).first()
            
            if not account:
                return {
                    "success": False,
                    "error": "Conta não encontrada ou inativa"
                }
            
            # Buscar dados dos produtos
            summary = self.ads_service.get_performance_summary(company_id)
            
            if "error" in summary:
                return {
                    "success": False,
                    "error": summary["error"]
                }
            
            # Filtrar produtos do advertiser
            account_data = next((acc for acc in summary.get("accounts_data", []) if acc["id"] == ml_account_id), None)
            
            if not account_data:
                return {
                    "success": False,
                    "error": "Nenhum dado encontrado para esta conta"
                }
            
            advertiser_data = next((adv for adv in account_data.get("advertisers", []) if adv["advertiser_id"] == advertiser_id), None)
            
            if not advertiser_data:
                return {
                    "success": False,
                    "error": "Nenhum dado encontrado para este advertiser"
                }
            
            return {
                "success": True,
                "data": {
                    "advertiser": advertiser_data,
                    "products": self._extract_product_performance(advertiser_data)
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar performance de produtos: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_performance_metrics(self, summary: Dict) -> Dict:
        """Calcula métricas de performance adicionais"""
        try:
            total_spend = summary.get("total_spend", 0)
            total_revenue = summary.get("total_revenue", 0)
            total_clicks = summary.get("total_clicks", 0)
            total_impressions = summary.get("total_impressions", 0)
            total_sales = summary.get("total_sales", 0)
            
            return {
                "roas": total_revenue / total_spend if total_spend > 0 else 0,
                "cpc": total_spend / total_clicks if total_clicks > 0 else 0,
                "ctr": (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
                "cpa": total_spend / total_sales if total_sales > 0 else 0,
                "conversion_rate": (total_sales / total_clicks * 100) if total_clicks > 0 else 0
            }
        except Exception as e:
            logger.error(f"Erro ao calcular métricas de performance: {e}")
            return {}
    
    def _calculate_account_metrics(self, account_data: Dict) -> Dict:
        """Calcula métricas específicas de uma conta"""
        try:
            total_spend = account_data.get("total_spend", 0)
            total_revenue = account_data.get("total_revenue", 0)
            total_clicks = account_data.get("total_clicks", 0)
            total_impressions = account_data.get("total_impressions", 0)
            total_sales = account_data.get("total_sales", 0)
            
            return {
                "roas": total_revenue / total_spend if total_spend > 0 else 0,
                "cpc": total_spend / total_clicks if total_clicks > 0 else 0,
                "ctr": (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
                "cpa": total_spend / total_sales if total_sales > 0 else 0,
                "conversion_rate": (total_sales / total_clicks * 100) if total_clicks > 0 else 0,
                "active_campaigns": len(account_data.get("advertisers", [])),
                "total_advertisers": len(account_data.get("advertisers", []))
            }
        except Exception as e:
            logger.error(f"Erro ao calcular métricas da conta: {e}")
            return {}
    
    def _extract_product_performance(self, advertiser_data: Dict) -> List[Dict]:
        """Extrai performance de produtos dos dados do advertiser"""
        try:
            # Por enquanto, retorna dados mockados
            # Em uma implementação real, isso viria da API de produtos específicos
            return [
                {
                    "product_id": "PROD001",
                    "title": "Produto Exemplo 1",
                    "thumbnail": "/static/images/no-image.png",
                    "spend": advertiser_data.get("spend", 0) * 0.5,
                    "revenue": advertiser_data.get("revenue", 0) * 0.5,
                    "clicks": advertiser_data.get("clicks", 0) * 0.5,
                    "impressions": advertiser_data.get("impressions", 0) * 0.5,
                    "sales": advertiser_data.get("sales", 0) * 0.5,
                    "roas": (advertiser_data.get("revenue", 0) * 0.5) / (advertiser_data.get("spend", 1) * 0.5) if advertiser_data.get("spend", 0) > 0 else 0
                }
            ]
        except Exception as e:
            logger.error(f"Erro ao extrair performance de produtos: {e}")
            return []
