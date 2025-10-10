"""
Serviço para gerenciar Claims/Returns do Mercado Livre
"""
import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MLClaimsService:
    """Serviço para buscar reclamações e devoluções"""
    
    def __init__(self):
        self.base_url = "https://api.mercadolibre.com"
    
    def get_returns_metrics(self, access_token: str, date_from: datetime, date_to: datetime) -> Dict:
        """
        Busca métricas de devoluções (returns) do período
        
        Args:
            access_token: Token de acesso
            date_from: Data inicial
            date_to: Data final
            
        Returns:
            Dict com total de devoluções e valor
        """
        try:
            # Buscar claims do tipo "return" (devoluções)
            url = f"{self.base_url}/post-purchase/v1/claims/search"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Formatar datas para o formato da API (formato UTC)
            date_from_str = date_from.strftime("%Y-%m-%dT00:00:00.000-00:00")
            date_to_str = date_to.strftime("%Y-%m-%dT23:59:59.000-00:00")
            
            params = {
                "type": "return",
                "status": "closed",  # Devoluções finalizadas
                "range": f"date_created:after:{date_from_str},before:{date_to_str}",
                "limit": 100
            }
            
            logger.info(f"🔄 Buscando claims/returns de {date_from_str} a {date_to_str}")
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Erro ao buscar claims: {response.status_code} - {response.text}")
                return {"returns_count": 0, "returns_value": 0}
            
            data = response.json()
            claims = data.get("data", [])
            
            returns_count = len(claims)
            returns_value = 0
            
            # Para cada claim, buscar detalhes e somar valores
            for claim in claims:
                claim_id = claim.get("id")
                
                # Buscar detalhes do claim para pegar o valor
                detail_url = f"{self.base_url}/post-purchase/v1/claims/{claim_id}"
                detail_response = requests.get(detail_url, headers=headers, timeout=30)
                
                if detail_response.status_code == 200:
                    claim_detail = detail_response.json()
                    
                    # Buscar valor das coverages (reembolsos)
                    coverages = claim_detail.get("coverages", [])
                    for coverage in coverages:
                        returns_value += float(coverage.get("amount", 0))
            
            logger.info(f"📋 Returns encontradas: {returns_count} devoluções, R$ {returns_value:.2f}")
            
            return {
                "returns_count": returns_count,
                "returns_value": returns_value
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar returns: {e}")
            return {"returns_count": 0, "returns_value": 0}

