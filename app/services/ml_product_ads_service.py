"""
Serviço para buscar métricas de Product Ads (publicidade) por produto
"""
import requests
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class MLProductAdsService:
    """Serviço para buscar dados de Product Ads do Mercado Livre"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.base_url = "https://api.mercadolibre.com"
    
    def get_product_advertising_metrics(self, ml_item_id: str, ml_account_id: int, days: int = 30) -> Optional[Dict]:
        """
        Busca métricas de publicidade (Product Ads) para um produto específico
        
        Args:
            ml_item_id: ID do item no Mercado Livre
            ml_account_id: ID da conta ML
            days: Número de dias para buscar métricas (padrão: 30)
        
        Returns:
            Dict com métricas de publicidade ou None se não encontrado
        """
        try:
            from app.models.saas_models import MLAccount, Token
            
            # Buscar conta ML e token
            ml_account = self.db.query(MLAccount).filter(MLAccount.id == ml_account_id).first()
            if not ml_account:
                logger.error(f"Conta ML {ml_account_id} não encontrada")
                return None
            
            token = self.db.query(Token).filter(Token.ml_account_id == ml_account_id).first()
            if not token:
                logger.error(f"Token não encontrado para conta {ml_account_id}")
                return None
            
            site_id = ml_account.site_id or "MLB"
            
            logger.info(f"Buscando métricas de Product Ads para item {ml_item_id}")
            
            # Buscar métricas diretamente do item usando novo endpoint
            metrics_data = self._fetch_item_metrics(site_id, ml_item_id, token.access_token, days)
            
            if metrics_data and metrics_data.get("metrics"):
                metrics = metrics_data["metrics"]
                
                result = {
                    "has_advertising": metrics.get("cost", 0) > 0,
                    "total_cost": metrics.get("cost", 0),
                    "total_clicks": metrics.get("clicks", 0),
                    "total_impressions": metrics.get("prints", 0),
                    "direct_sales": metrics.get("direct_amount", 0),
                    "indirect_sales": metrics.get("indirect_amount", 0),
                    "total_sales": metrics.get("total_amount", 0),
                    "roas": metrics.get("roas", 0),
                    "acos": metrics.get("acos", 0),
                    "cpc": metrics.get("cpc", 0),
                    "ctr": metrics.get("ctr", 0),
                    "campaigns_count": 1 if metrics.get("cost", 0) > 0 else 0,
                    "period_days": days,
                    "item_status": metrics_data.get("status", "unknown"),
                    "campaign_id": metrics_data.get("campaign_id"),
                    "recommended": metrics_data.get("recommended", False)
                }
                
                logger.info(f"✅ Métricas de Product Ads para {ml_item_id}: Custo R$ {result['total_cost']:.2f}")
                return result
            else:
                logger.info(f"Produto {ml_item_id} não tem dados de Product Ads")
                return self._empty_metrics()
            
        except Exception as e:
            logger.error(f"Erro ao buscar métricas de Product Ads: {e}", exc_info=True)
            return self._empty_metrics()
    
    def _fetch_advertisers(self, site_id: str, access_token: str) -> List[Dict]:
        """Busca lista de anunciantes (advertisers)"""
        try:
            # Endpoint correto conforme documentação
            url = f"{self.base_url}/advertising/advertisers"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Api-Version": "1"  # Header obrigatório
            }
            
            # Parâmetro correto: product_id=PADS (não site_id)
            params = {"product_id": "PADS"}
            
            logger.info(f"Buscando advertisers com product_id=PADS")
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                advertisers = data.get("advertisers", [])
                logger.info(f"✅ Encontrados {len(advertisers)} advertisers")
                return advertisers
            else:
                logger.warning(f"Erro ao buscar advertisers: {response.status_code} - {response.text}")
                return []
            
        except Exception as e:
            logger.error(f"Erro ao buscar anunciantes: {e}")
            return []
    
    def _fetch_item_metrics(self, site_id: str, ml_item_id: str, access_token: str, days: int = 30) -> Optional[Dict]:
        """Busca métricas de Product Ads de um item específico"""
        try:
            # Endpoint correto conforme documentação: /advertising/{SITE_ID}/product_ads/ads/{ITEM_ID}
            url = f"{self.base_url}/advertising/{site_id}/product_ads/ads/{ml_item_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "api-version": "2"  # Minúsculo conforme doc
            }
            
            # Período de busca
            date_to = datetime.now()
            date_from = date_to - timedelta(days=days)
            
            # Todas as métricas disponíveis
            metrics_list = [
                "clicks", "prints", "ctr", "cost", "cpc", "acos",
                "organic_units_quantity", "organic_units_amount", "organic_items_quantity",
                "direct_items_quantity", "indirect_items_quantity", "advertising_items_quantity",
                "cvr", "roas", "sov",
                "direct_units_quantity", "indirect_units_quantity", "units_quantity",
                "direct_amount", "indirect_amount", "total_amount"
            ]
            
            params = {
                "date_from": date_from.strftime("%Y-%m-%d"),
                "date_to": date_to.strftime("%Y-%m-%d"),
                "metrics": ",".join(metrics_list)
            }
            
            logger.info(f"Buscando métricas do item {ml_item_id} no período {params['date_from']} a {params['date_to']}")
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Métricas encontradas para item {ml_item_id}")
                logger.info(f"Status do item: {data.get('status')}, Campaign ID: {data.get('campaign_id')}")
                return data
            else:
                logger.warning(f"Item {ml_item_id} sem Product Ads: {response.status_code}")
                return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar métricas do item: {e}")
            return None
    
    def _empty_metrics(self) -> Dict:
        """Retorna estrutura vazia de métricas"""
        return {
            "has_advertising": False,
            "total_cost": 0,
            "total_clicks": 0,
            "total_impressions": 0,
            "direct_sales": 0,
            "indirect_sales": 0,
            "total_sales": 0,
            "roas": 0,
            "acos": 0,
            "cpc": 0,
            "ctr": 0,
            "campaigns_count": 0,
            "active_campaigns": [],
            "period_days": 0
        }

