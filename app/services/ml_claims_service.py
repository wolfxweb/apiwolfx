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
        Baseado na documentação: https://developers.mercadolibre.com.br/pt_br/gerenciar-devolucoes
        
        Args:
            access_token: Token de acesso
            date_from: Data inicial
            date_to: Data final
            
        Returns:
            Dict com total de devoluções e valor
        """
        try:
            # Buscar TODOS os claims e filtrar os que têm devoluções
            url = f"{self.base_url}/post-purchase/v1/claims/search"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # API exige pelo menos um filtro - usar status e type
            params = {
                "status": "closed",  # Buscar claims finalizados
                "type": "mediations",  # Tipo mediations pode ter devoluções
                "limit": 100
            }
            
            logger.info(f"🔄 Buscando claims fechados (type=mediations)...")
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Erro ao buscar claims: {response.status_code} - {response.text}")
                return {"returns_count": 0, "returns_value": 0}
            
            data = response.json()
            claims = data.get("data", [])
            
            returns_count = 0
            returns_value = 0
            
            logger.info(f"📦 Total de claims encontrados: {len(claims)}")
            
            # Para cada claim, verificar se tem devolução associada
            for claim in claims:
                claim_id = claim.get("id")
                
                # Verificar se a data do claim está no período
                claim_date_str = claim.get("date_created", "")
                if claim_date_str:
                    try:
                        # Converter data do claim
                        claim_date = datetime.strptime(claim_date_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                        
                        # Verificar se está no período
                        if claim_date < date_from or claim_date > date_to:
                            continue
                    except:
                        pass
                
                # Buscar detalhes do claim para verificar se tem devolução
                try:
                    detail_url = f"{self.base_url}/post-purchase/v1/claims/{claim_id}"
                    detail_response = requests.get(detail_url, headers=headers, timeout=10)
                    
                    if detail_response.status_code == 200:
                        claim_detail = detail_response.json()
                        
                        # Verificar se tem "return" em related_entities (nova forma)
                        # ou se resolution.reason = "item_returned"
                        has_return = False
                        
                        # Método 1: Verificar related_entities
                        if "return" in claim_detail.get("related_entities", []):
                            has_return = True
                        
                        # Método 2: Verificar resolution
                        resolution = claim_detail.get("resolution", {})
                        if resolution and resolution.get("reason") == "item_returned":
                            has_return = True
                        
                        if has_return:
                            # Buscar dados da devolução usando a nova API v2
                            returns_url = f"{self.base_url}/post-purchase/v2/claims/{claim_id}/returns"
                            returns_response = requests.get(returns_url, headers=headers, timeout=10)
                            
                            if returns_response.status_code == 200:
                                returns_data = returns_response.json()
                                returns_count += 1
                                
                                # Buscar valor do pedido original
                                resource_id = claim_detail.get("resource_id")
                                if resource_id:
                                    # Buscar pedido para pegar valor
                                    order_url = f"{self.base_url}/orders/{resource_id}"
                                    order_response = requests.get(order_url, headers=headers, timeout=10)
                                    if order_response.status_code == 200:
                                        order_data = order_response.json()
                                        returns_value += float(order_data.get("total_amount", 0))
                                
                                logger.info(f"  ✅ Devolução encontrada: claim_id={claim_id}, resource_id={resource_id}")
                except Exception as e:
                    logger.debug(f"  Erro ao verificar claim {claim_id}: {e}")
                    continue
            
            logger.info(f"📋 Returns finais: {returns_count} devoluções, R$ {returns_value:.2f}")
            
            return {
                "returns_count": returns_count,
                "returns_value": returns_value
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar returns: {e}")
            import traceback
            traceback.print_exc()
            return {"returns_count": 0, "returns_value": 0}

