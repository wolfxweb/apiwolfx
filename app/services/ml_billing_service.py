"""
Serviço para buscar dados de billing do Mercado Livre

Este serviço fornece acesso aos dados de faturamento consolidados mensalmente.
O Mercado Livre não fornece dados de billing detalhados por pedido individual,
apenas relatórios mensais consolidados através do endpoint /billing/integration/periods/

Funcionalidades:
- Buscar períodos de billing disponíveis
- Buscar resumo de billing de um período específico
- Buscar detalhes de billing de um período
- Sincronizar dados de billing com o banco de dados
"""
import requests
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.services.token_manager import TokenManager

logger = logging.getLogger(__name__)

class MLBillingService:
    """Serviço para buscar dados de billing do Mercado Livre"""
    
    def __init__(self, db_session: Session = None):
        self.db = db_session
        self.token_manager = TokenManager(db_session) if db_session else None
        self.base_url = "https://api.mercadolibre.com"
    
    def get_billing_details_by_order(self, user_id: int, order_id: str) -> Optional[Dict]:
        """Busca detalhes de billing para um pedido específico"""
        try:
            if not self.token_manager:
                logger.error("TokenManager não inicializado")
                return None
                
            # Obter token válido
            access_token = self.token_manager.get_valid_token(user_id)
            if not access_token:
                logger.error(f"Token inválido para user_id: {user_id}")
                return None
            
            # Buscar dados de billing da API
            url = f"{self.base_url}/billing/integration/group/ML/order/details"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "order_id": order_id,
                "document_type": "BILL"
            }
            
            logger.info(f"Buscando billing para order_id: {order_id}")
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                billing_data = response.json()
                logger.info(f"Billing encontrado para order_id: {order_id}")
                return billing_data
            elif response.status_code == 404:
                logger.warning(f"Billing não encontrado para order_id: {order_id}")
                return None
            else:
                logger.error(f"Erro ao buscar billing para order_id: {order_id}, status: {response.status_code}")
                logger.error(f"Resposta: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar billing para order_id {order_id}: {e}")
            return None
    
    def get_billing_details_by_period(self, user_id: int, start_date: str, end_date: str, limit: int = 150) -> List[Dict]:
        """Busca detalhes de billing para um período específico"""
        try:
            if not self.token_manager:
                logger.error("TokenManager não inicializado")
                return []
                
            # Obter token válido
            access_token = self.token_manager.get_valid_token(user_id)
            if not access_token:
                logger.error(f"Token inválido para user_id: {user_id}")
                return []
            
            # Buscar dados de billing da API
            url = f"{self.base_url}/billing/integration/group/ML"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "start_date": start_date,
                "end_date": end_date,
                "document_type": "BILL",
                "limit": limit
            }
            
            logger.info(f"Buscando billing para período: {start_date} a {end_date}")
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                billing_data = response.json()
                logger.info(f"Billing encontrado: {len(billing_data.get('results', []))} registros")
                return billing_data.get("results", [])
            else:
                logger.error(f"Erro ao buscar billing, status: {response.status_code}")
                logger.error(f"Resposta: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao buscar billing para período {start_date} a {end_date}: {e}")
            return []
    
    def extract_sale_fee_breakdown(self, billing_data: Dict) -> Dict:
        """Extrai breakdown detalhado das taxas de venda"""
        try:
            sale_fee_breakdown = {}
            
            # Procurar por sale_fee no billing_data
            if "sale_fee" in billing_data:
                sale_fee = billing_data["sale_fee"]
                sale_fee_breakdown = {
                    "gross": sale_fee.get("gross", 0),
                    "net": sale_fee.get("net", 0),
                    "rebate": sale_fee.get("rebate", 0),
                    "discount": sale_fee.get("discount", 0)
                }
            
            return sale_fee_breakdown
            
        except Exception as e:
            logger.error(f"Erro ao extrair sale_fee_breakdown: {e}")
            return {}
    
    def extract_financing_details(self, billing_data: Dict) -> Dict:
        """Extrai detalhes de financiamento"""
        try:
            financing_details = {}
            
            # Procurar por financing_fee no billing_data
            if "financing_fee" in billing_data:
                financing_fee = billing_data["financing_fee"]
                financing_details = {
                    "financing_fee": financing_fee.get("amount", 0),
                    "financing_transfer_total": financing_fee.get("transfer_total", 0)
                }
            
            return financing_details
            
        except Exception as e:
            logger.error(f"Erro ao extrair financing_details: {e}")
            return {}
    
    def extract_marketplace_fee_breakdown(self, billing_data: Dict) -> Dict:
        """Extrai breakdown das taxas do marketplace"""
        try:
            marketplace_breakdown = {}
            
            # Procurar por marketplace_fee no billing_data
            if "marketplace_fee" in billing_data:
                marketplace_fee = billing_data["marketplace_fee"]
                marketplace_breakdown = {
                    "amount": marketplace_fee.get("amount", 0),
                    "currency_id": marketplace_fee.get("currency_id", "BRL"),
                    "type": marketplace_fee.get("type", "")
                }
            
            return marketplace_breakdown
            
        except Exception as e:
            logger.error(f"Erro ao extrair marketplace_fee_breakdown: {e}")
            return {}
    
    # ========== MÉTODOS DE BILLING POR PERÍODO ==========
    
    def get_billing_periods(self, user_id: int, group: str = "ML", 
                          document_type: str = "BILL", limit: int = 6) -> List[Dict]:
        """
        Busca períodos de billing disponíveis
        
        Args:
            user_id: ID do usuário
            group: Grupo de billing (ML = Mercado Livre, MP = Mercado Pago)
            document_type: Tipo de documento (BILL ou CREDIT_NOTE)
            limit: Quantidade de períodos (máximo 12)
            
        Returns:
            Lista de períodos disponíveis
        """
        try:
            if not self.token_manager:
                logger.error("TokenManager não inicializado")
                return []
            
            # Obter token válido
            access_token = self.token_manager.get_valid_token(user_id)
            if not access_token:
                logger.error(f"Token inválido para user_id: {user_id}")
                return []
            
            # Buscar períodos da API
            url = f"{self.base_url}/billing/integration/monthly/periods"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "group": group,
                "document_type": document_type,
                "limit": min(limit, 12)  # Máximo 12
            }
            
            logger.info(f"Buscando períodos de billing (group={group}, limit={limit})")
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                periods = data.get("results", [])
                logger.info(f"Períodos encontrados: {len(periods)}")
                return periods
            else:
                logger.error(f"Erro ao buscar períodos: {response.status_code}")
                logger.error(f"Resposta: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao buscar períodos de billing: {e}")
            return []
    
    def get_period_summary(self, user_id: int, period_key: str, group: str = "ML") -> Optional[Dict]:
        """
        Busca resumo de billing de um período específico
        
        Args:
            user_id: ID do usuário
            period_key: Chave do período (ex: "2023-10-01")
            group: Grupo de billing (ML ou MP)
            
        Returns:
            Resumo do período com comissões e bonificações
        """
        try:
            if not self.token_manager:
                logger.error("TokenManager não inicializado")
                return None
            
            # Obter token válido
            access_token = self.token_manager.get_valid_token(user_id)
            if not access_token:
                logger.error(f"Token inválido para user_id: {user_id}")
                return None
            
            # Buscar resumo da API
            url = f"{self.base_url}/billing/integration/periods/key/{period_key}/summary/details"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "group": group,
                "document_type": "BILL"  # Parâmetro obrigatório
            }
            
            logger.info(f"Buscando resumo do período {period_key}")
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                summary = response.json()
                logger.info(f"Resumo encontrado para período {period_key}")
                return summary
            elif response.status_code == 404:
                logger.warning(f"Resumo não encontrado para período {period_key}")
                return None
            else:
                logger.error(f"Erro ao buscar resumo: {response.status_code}")
                logger.error(f"Resposta: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar resumo do período {period_key}: {e}")
            return None
    
    def get_current_month_billing(self, user_id: int, group: str = "ML") -> Optional[Dict]:
        """
        Busca billing do mês atual
        
        Args:
            user_id: ID do usuário
            group: Grupo de billing (ML ou MP)
            
        Returns:
            Resumo do mês atual
        """
        try:
            # Gerar chave do período atual (primeiro dia do mês)
            now = datetime.now()
            period_key = now.strftime("%Y-%m-01")
            
            logger.info(f"Buscando billing do mês atual: {period_key}")
            return self.get_period_summary(user_id, period_key, group)
            
        except Exception as e:
            logger.error(f"Erro ao buscar billing do mês atual: {e}")
            return None
    
    def get_last_n_months_billing(self, user_id: int, months: int = 3, group: str = "ML") -> List[Dict]:
        """
        Busca billing dos últimos N meses
        
        Args:
            user_id: ID do usuário
            months: Quantidade de meses (máximo 12)
            group: Grupo de billing (ML ou MP)
            
        Returns:
            Lista de resumos de billing
        """
        try:
            billing_data = []
            months = min(months, 12)  # Máximo 12 meses
            
            # Gerar chaves dos últimos N meses
            now = datetime.now()
            for i in range(months):
                # Calcular data do primeiro dia do mês
                target_date = now - timedelta(days=30 * i)
                period_key = target_date.strftime("%Y-%m-01")
                
                # Buscar resumo do período
                summary = self.get_period_summary(user_id, period_key, group)
                if summary:
                    billing_data.append({
                        "period_key": period_key,
                        "summary": summary
                    })
            
            logger.info(f"Billing encontrado para {len(billing_data)} dos últimos {months} meses")
            return billing_data
            
        except Exception as e:
            logger.error(f"Erro ao buscar billing dos últimos {months} meses: {e}")
            return []
    
    def extract_billing_metrics(self, summary: Dict) -> Dict:
        """
        Extrai métricas principais de um resumo de billing
        
        Args:
            summary: Resumo de billing retornado pela API
            
        Returns:
            Dicionário com métricas principais
        """
        try:
            bill_includes = summary.get("bill_includes", {})
            payment_collected = summary.get("payment_collected", {})
            
            # Extrair totais
            total_amount = bill_includes.get("total_amount", 0)
            total_perceptions = bill_includes.get("total_perceptions", 0)
            
            # Extrair bonificações
            bonuses = bill_includes.get("bonuses", [])
            total_bonuses = sum(bonus.get("amount", 0) for bonus in bonuses)
            
            # Extrair cobranças
            charges = bill_includes.get("charges", [])
            total_charges = sum(charge.get("amount", 0) for charge in charges)
            
            # Separar tipos de cobranças
            sale_fees = sum(
                charge.get("amount", 0) 
                for charge in charges 
                if charge.get("type") == "CV"  # Cargo por venta
            )
            
            shipping_fees = sum(
                charge.get("amount", 0) 
                for charge in charges 
                if charge.get("type") == "CXD" and "envio" in charge.get("label", "").lower()
            )
            
            advertising_fees = sum(
                charge.get("amount", 0) 
                for charge in charges 
                if charge.get("type") == "PADS"  # Product Ads
            )
            
            # Extrair dados de pagamento
            total_collected = payment_collected.get("total_collected", 0)
            total_debt = payment_collected.get("total_debt", 0)
            
            return {
                "total_amount": total_amount,
                "total_perceptions": total_perceptions,
                "total_bonuses": total_bonuses,
                "total_charges": total_charges,
                "sale_fees": sale_fees,
                "shipping_fees": shipping_fees,
                "advertising_fees": advertising_fees,
                "total_collected": total_collected,
                "total_debt": total_debt,
                "net_amount": total_collected - total_charges,
                "charges_breakdown": charges,
                "bonuses_breakdown": bonuses
            }
            
        except Exception as e:
            logger.error(f"Erro ao extrair métricas de billing: {e}")
            return {}
