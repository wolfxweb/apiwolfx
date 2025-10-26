"""
Serviço para gestão completa de campanhas de Product Ads
"""
import requests
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class MLCampaignService:
    """Serviço para criar, editar e gerenciar campanhas de Product Ads"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.base_url = "https://api.mercadolibre.com"
    
    def list_campaigns(self, site_id: str, advertiser_id: int, access_token: str, status: Optional[str] = None) -> List[Dict]:
        """
        Lista todas as campanhas de um anunciante
        
        Args:
            site_id: ID do site (MLB, MLA, etc.)
            advertiser_id: ID do anunciante
            access_token: Token de acesso
            status: Filtrar por status (active, paused, ended)
        
        Returns:
            Lista de campanhas
        """
        try:
            url = f"{self.base_url}/advertising/{site_id}/advertisers/{advertiser_id}/product_ads/campaigns/search"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "api-version": "2"
            }
            
            params = {}
            if status:
                params["status"] = status
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            campaigns = data.get("campaigns", [])
            
            logger.info(f"✅ {len(campaigns)} campanhas encontradas")
            return campaigns
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar campanhas: {e}")
            return []
    
    def get_campaign(self, site_id: str, advertiser_id: int, campaign_id: int, access_token: str) -> Optional[Dict]:
        """
        Busca detalhes de uma campanha específica
        
        Args:
            site_id: ID do site
            advertiser_id: ID do anunciante
            campaign_id: ID da campanha
            access_token: Token de acesso
        
        Returns:
            Dados da campanha ou None
        """
        try:
            url = f"{self.base_url}/advertising/{site_id}/advertisers/{advertiser_id}/product_ads/campaigns/{campaign_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "api-version": "2"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            campaign = response.json()
            logger.info(f"✅ Campanha {campaign_id} encontrada")
            return campaign
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar campanha: {e}")
            return None
    
    def create_campaign(self, site_id: str, advertiser_id: int, access_token: str, campaign_data: Dict) -> Optional[Dict]:
        """
        Cria nova campanha
        
        Args:
            site_id: ID do site
            advertiser_id: ID do anunciante
            access_token: Token de acesso
            campaign_data: Dados da campanha
                {
                    "name": "Nome da Campanha",
                    "budget": 100.00,  # Orçamento diário
                    "bid_type": "auto" ou "manual",
                    "status": "active" ou "paused"
                }
        
        Returns:
            Dados da campanha criada ou None
        """
        try:
            url = f"{self.base_url}/advertising/{site_id}/advertisers/{advertiser_id}/product_ads/campaigns"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "api-version": "2"
            }
            
            payload = {
                "name": campaign_data.get("name"),
                "budget": {
                    "amount": float(campaign_data.get("budget", 0)),
                    "currency_id": "BRL"
                },
                "bid_type": campaign_data.get("bid_type", "auto"),
                "status": campaign_data.get("status", "paused")
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            campaign = response.json()
            logger.info(f"✅ Campanha {campaign.get('id')} criada com sucesso")
            return campaign
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar campanha: {e}")
            return None
    
    def update_campaign(self, site_id: str, advertiser_id: int, campaign_id: int, access_token: str, updates: Dict) -> Optional[Dict]:
        """
        Atualiza campanha existente
        
        Args:
            site_id: ID do site
            advertiser_id: ID do anunciante
            campaign_id: ID da campanha
            access_token: Token de acesso
            updates: Dados para atualizar
        
        Returns:
            Dados da campanha atualizada ou None
        """
        try:
            url = f"{self.base_url}/advertising/{site_id}/advertisers/{advertiser_id}/product_ads/campaigns/{campaign_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "api-version": "2"
            }
            
            response = requests.put(url, json=updates, headers=headers, timeout=30)
            response.raise_for_status()
            
            campaign = response.json()
            logger.info(f"✅ Campanha {campaign_id} atualizada")
            return campaign
            
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar campanha: {e}")
            return None
    
    def change_campaign_status(self, site_id: str, advertiser_id: int, campaign_id: int, access_token: str, status: str) -> bool:
        """
        Altera status da campanha (active, paused)
        
        Args:
            site_id: ID do site
            advertiser_id: ID do anunciante
            campaign_id: ID da campanha
            access_token: Token de acesso
            status: Novo status (active, paused)
        
        Returns:
            True se alterado com sucesso
        """
        try:
            url = f"{self.base_url}/advertising/{site_id}/advertisers/{advertiser_id}/product_ads/campaigns/{campaign_id}/status"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "api-version": "2"
            }
            
            payload = {"status": status}
            response = requests.patch(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            logger.info(f"✅ Status da campanha {campaign_id} alterado para {status}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao alterar status: {e}")
            return False
    
    def delete_campaign(self, site_id: str, advertiser_id: int, campaign_id: int, access_token: str) -> bool:
        """
        Deleta campanha
        
        Args:
            site_id: ID do site
            advertiser_id: ID do anunciante
            campaign_id: ID da campanha
            access_token: Token de acesso
        
        Returns:
            True se deletada com sucesso
        """
        try:
            url = f"{self.base_url}/advertising/{site_id}/advertisers/{advertiser_id}/product_ads/campaigns/{campaign_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "api-version": "2"
            }
            
            response = requests.delete(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            logger.info(f"✅ Campanha {campaign_id} deletada")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao deletar campanha: {e}")
            return False
    
    def add_products_to_campaign(self, site_id: str, campaign_id: int, access_token: str, item_ids: List[str]) -> bool:
        """
        Adiciona produtos à campanha
        
        Args:
            site_id: ID do site
            campaign_id: ID da campanha
            access_token: Token de acesso
            item_ids: Lista de IDs dos produtos (MLB1234...)
        
        Returns:
            True se adicionados com sucesso
        """
        try:
            url = f"{self.base_url}/advertising/{site_id}/product_ads/campaigns/{campaign_id}/ads"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "api-version": "2"
            }
            
            payload = {
                "items": [{"item_id": item_id} for item_id in item_ids]
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            logger.info(f"✅ {len(item_ids)} produtos adicionados à campanha {campaign_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao adicionar produtos: {e}")
            return False
    
    def remove_product_from_campaign(self, site_id: str, campaign_id: int, ad_id: int, access_token: str) -> bool:
        """
        Remove produto da campanha
        
        Args:
            site_id: ID do site
            campaign_id: ID da campanha
            ad_id: ID do anúncio (ad_id, não item_id)
            access_token: Token de acesso
        
        Returns:
            True se removido com sucesso
        """
        try:
            url = f"{self.base_url}/advertising/{site_id}/product_ads/campaigns/{campaign_id}/ads/{ad_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "api-version": "2"
            }
            
            response = requests.delete(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            logger.info(f"✅ Produto removido da campanha {campaign_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao remover produto: {e}")
            return False
    
    def get_campaign_products(self, site_id: str, campaign_id: int, access_token: str) -> List[Dict]:
        """
        Lista produtos de uma campanha
        
        Args:
            site_id: ID do site
            campaign_id: ID da campanha
            access_token: Token de acesso
        
        Returns:
            Lista de produtos anunciados
        """
        try:
            url = f"{self.base_url}/advertising/{site_id}/product_ads/campaigns/{campaign_id}/ads"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "api-version": "2"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            ads = data.get("ads", [])
            
            logger.info(f"✅ {len(ads)} produtos encontrados na campanha {campaign_id}")
            return ads
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar produtos da campanha: {e}")
            return []
