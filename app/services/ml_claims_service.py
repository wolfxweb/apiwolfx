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
    
    def get_returns_metrics(self, access_token: str, date_from: datetime, date_to: datetime, seller_id: int = None) -> Dict:
        """
        Busca métricas de devoluções do período
        
        ML conta: "vendas do período selecionado em que compradores solicitaram devolução"
        Ou seja: vendas CONFIRMADAS no período que TÊM claim/return (não importa quando o claim foi criado)
        
        Args:
            access_token: Token de acesso  
            date_from: Data inicial (para filtrar vendas)
            date_to: Data final (para filtrar vendas)
            
        Returns:
            Dict com total de devoluções e valor
        """
        try:
            # ABORDAGEM CORRETA: Buscar CLAIMS criados no período que sejam devoluções
            # ML conta: "vendas em que compradores SOLICITARAM devolução" = data do CLAIM, não da venda
            
            print(f"🔄 CLAIMS SERVICE: Iniciando busca de devoluções...")
            print(f"   Period: {date_from} to {date_to}")
            print(f"   Seller ID: {seller_id}")
            logger.info(f"🔄 Buscando claims de devoluções criados no período...")
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Buscar todos os claims do seller (não filtrar por data na API, filtrar depois)
            claims_url = f"{self.base_url}/post-purchase/v1/claims/search"
            claims_params = {
                "type": "mediations",  # Claims que podem ter devoluções
                "limit": 50  # Limite máximo
            }
            
            claims_response = requests.get(claims_url, headers=headers, params=claims_params, timeout=30)
            
            if claims_response.status_code != 200:
                logger.error(f"Erro ao buscar claims: {claims_response.status_code}")
                return {"returns_count": 0, "returns_value": 0}
            
            claims_data = claims_response.json()
            claims = claims_data.get("data", [])
            
            logger.info(f"📦 Total de claims encontrados: {len(claims)}")
            
            returns_count = 0
            returns_value = 0
            
            # Filtrar claims do período que têm devolução
            for claim in claims:
                claim_id = claim.get("id")
                
                # Verificar data do claim
                date_created_str = claim.get("date_created", "")
                if not date_created_str:
                    continue
                
                try:
                    # Parse date
                    claim_date = datetime.strptime(date_created_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                    
                    # Verificar se está no período
                    if claim_date < date_from or claim_date > date_to:
                        continue
                        
                except:
                    continue
                
                # Verificar se tem devolução
                has_return = False
                
                # Método 1: Verificar related_entities
                if "return" in claim.get("related_entities", []):
                    has_return = True
                
                # Método 2: Verificar resolution
                resolution = claim.get("resolution", {})
                if resolution and resolution.get("reason") == "item_returned":
                    has_return = True
                
                if has_return:
                    # Buscar valor do pedido
                    resource_id = claim.get("resource_id")
                    if resource_id:
                        try:
                            order_url = f"{self.base_url}/orders/{resource_id}"
                            order_response = requests.get(order_url, headers=headers, timeout=10)
                            if order_response.status_code == 200:
                                order_data = order_response.json()
                                total_amount = float(order_data.get("total_amount", 0))
                                returns_count += 1
                                returns_value += total_amount
                                logger.info(f"  ✅ Devolução: claim_id={claim_id}, order={resource_id}, valor=R$ {total_amount:.2f}, data={claim_date}")
                        except Exception as e:
                            logger.debug(f"  Erro ao buscar pedido {resource_id}: {e}")
            
            logger.info(f"📋 Returns finais: {returns_count} devoluções, R$ {returns_value:.2f}")
            print(f"✅ CLAIMS SERVICE: {returns_count} devoluções, R$ {returns_value:.2f}")
            
            return {
                "returns_count": returns_count,
                "returns_value": returns_value
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar returns: {e}")
            print(f"❌ CLAIMS SERVICE ERROR: {e}")
            import traceback
            traceback.print_exc()
            return {"returns_count": 0, "returns_value": 0}

