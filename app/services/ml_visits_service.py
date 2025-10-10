"""
Serviço para gerenciar Visits (visitas) do Mercado Livre
"""
import logging
import requests
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class MLVisitsService:
    """Serviço para buscar visitas de produtos"""
    
    def __init__(self):
        self.base_url = "https://api.mercadolibre.com"
    
    def get_user_visits(self, user_id: str, access_token: str, date_from: datetime, date_to: datetime) -> Dict:
        """
        Busca total de visitas de um usuário no período usando time_window
        
        Args:
            user_id: ID do usuário ML
            access_token: Token de acesso
            date_from: Data inicial
            date_to: Data final
            
        Returns:
            Dict com total de visitas
        """
        try:
            # Usar time_window que é mais simples (últimos X dias)
            days_diff = (date_to - date_from).days
            
            url = f"{self.base_url}/users/{user_id}/items_visits/time_window"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "last": max(1, days_diff),  # Últimos N dias
                "unit": "day"
            }
            
            logger.info(f"👁️  Buscando visitas dos últimos {days_diff} dias")
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Erro ao buscar visitas: {response.status_code} - {response.text}")
                return {"total_visits": 0}
            
            data = response.json()
            total_visits = data.get("total_visits", 0)
            
            logger.info(f"👁️  Total de visitas: {total_visits}")
            
            return {"total_visits": total_visits}
            
        except Exception as e:
            logger.error(f"Erro ao buscar visitas: {e}")
            return {"total_visits": 0}

