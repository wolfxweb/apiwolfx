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
        Busca métricas de devoluções do período - LÓGICA CORRETA BASEADA NA DOCUMENTAÇÃO DO ML
        
        ML conta: "vendas do período selecionado em que compradores solicitaram devolução"
        = Vendas FECHADAS no período (date_closed) que TÊM claims/returns
        
        LÓGICA:
        1. Buscar TODOS os claims (type=mediations E type=returns)
        2. Filtrar apenas os que têm resolution.reason indicando devolução CONFIRMADA
        3. Para cada claim, buscar a order e verificar se date_closed está no período
        
        Args:
            access_token: Token de acesso  
            date_from: Data inicial do período
            date_to: Data final do período
            
        Returns:
            Dict com total de devoluções e valor
        """
        try:
            logger.info(f"🔄 Buscando devoluções com lógica CORRETA do ML...")
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Resolution reasons que indicam DEVOLUÇÃO CONFIRMADA (baseado na documentação)
            RETURN_RESOLUTIONS = [
                "item_returned",       # Produto devolvido
                "return_canceled",     # Devolução cancelada
                "return_expired",      # Devolução expirada
                "warehouse_decision",  # Decisão do warehouse (produto analisado)
                "warehouse_timeout",   # Timeout do warehouse
                "low_cost",           # Custo de envio > valor produto
                "coverage_decision",   # Cobertura aplicada (devolução)
                "no_bpp",             # Sem cobertura (devolução)
            ]
            
            claims_url = f"{self.base_url}/post-purchase/v1/claims/search"
            
            all_returns = []
            
            # BUSCAR CLAIMS TYPE=MEDIATIONS E TYPE=RETURNS
            for claim_type in ["mediations", "returns"]:
                logger.info(f"📦 Buscando claims type={claim_type}...")
                
                # Buscar com sort por date_created DESC e limit 100 (cobre período de 30 dias)
                claims_params = {
                    "type": claim_type,
                    "limit": 100,
                    "offset": 0,
                    "sort": "date_created:desc"
                }
                
                response = requests.get(claims_url, headers=headers, params=claims_params, timeout=30)
                
                if response.status_code != 200:
                    logger.error(f"Erro ao buscar claims {claim_type}: {response.status_code}")
                    continue
                
                data = response.json()
                claims = data.get("data", [])
                total = data.get("paging", {}).get("total", 0)
                
                logger.info(f"  Total de claims {claim_type}: {total}, recebidos: {len(claims)}")
                
                # Processar cada claim
                for claim in claims:
                    claim_id = claim.get("id")
                    resource_id = claim.get("resource_id")
                    resolution = claim.get("resolution", {})
                    resolution_reason = resolution.get("reason") if resolution else None
                    
                    # Para type=returns: TODOS são devoluções (se tiverem resolution)
                    # Para type=mediations: Apenas os com resolution indicando devolução
                    is_return = False
                    
                    if claim_type == "returns":
                        # Returns sempre são devoluções (se tiverem resolution)
                        if resolution_reason:
                            is_return = True
                    elif claim_type == "mediations":
                        # Mediations: verificar resolution.reason
                        if resolution_reason in RETURN_RESOLUTIONS:
                            is_return = True
                    
                    if is_return and resource_id:
                        try:
                            # Buscar detalhes do pedido
                            order_url = f"{self.base_url}/orders/{resource_id}"
                            order_response = requests.get(order_url, headers=headers, timeout=10)
                            
                            if order_response.status_code == 200:
                                order_data = order_response.json()
                                date_closed_str = order_data.get("date_closed")
                                
                                if date_closed_str:
                                    # Parse date_closed
                                    try:
                                        order_date = datetime.strptime(date_closed_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                                        
                                        # Verificar se a VENDA foi fechada no período
                                        if date_from <= order_date <= date_to:
                                            total_amount = float(order_data.get("total_amount", 0))
                                            
                                            all_returns.append({
                                                "claim_id": claim_id,
                                                "claim_type": claim_type,
                                                "order_id": resource_id,
                                                "total_amount": total_amount,
                                                "date_closed": date_closed_str,
                                                "resolution_reason": resolution_reason
                                            })
                                            
                                            logger.info(f"  ✅ Devolução: Claim {claim_id} ({claim_type}) | Order {resource_id} | R$ {total_amount:.2f} | {resolution_reason}")
                                    except Exception as e:
                                        logger.debug(f"Erro ao parsear date_closed: {e}")
                        except Exception as e:
                            logger.debug(f"Erro ao buscar order {resource_id}: {e}")
            
            # Calcular totais
            returns_count = len(all_returns)
            returns_value = sum(r['total_amount'] for r in all_returns)
            
            logger.info(f"✅ Total de devoluções no período: {returns_count}, R$ {returns_value:.2f}")
            
            return {
                "returns_count": returns_count,
                "returns_value": returns_value,
                "details": all_returns  # Para debug
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar devoluções: {e}")
            import traceback
            traceback.print_exc()
            return {"returns_count": 0, "returns_value": 0}

