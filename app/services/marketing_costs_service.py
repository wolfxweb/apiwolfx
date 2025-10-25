"""
Serviço para captura e distribuição de custos de marketing (Product Ads)
do Mercado Livre através da Billing API.

Este serviço:
1. Captura custos consolidados mensais da Billing API
2. Distribui proporcionalmente entre pedidos do período
3. Armazena custos por pedido para análises financeiras
4. Fornece métricas de marketing para dashboards
"""
import requests
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.saas_models import MLAccount, MLOrder, MLAccountStatus
from app.services.token_manager import TokenManager

logger = logging.getLogger(__name__)

class MarketingCostsService:
    """Serviço para captura e distribuição de custos de marketing"""
    
    def __init__(self, db: Session):
        self.db = db
        self.token_manager = TokenManager(db)
        self.base_url = "https://api.mercadolibre.com"
    
    def sync_marketing_costs_for_company(self, company_id: int, months: int = 3) -> Dict:
        """
        Sincroniza custos de marketing para uma empresa
        
        Args:
            company_id: ID da empresa
            months: Número de meses para sincronizar (padrão: 3)
            
        Returns:
            Dicionário com resultados da sincronização
        """
        try:
            logger.info(f"🔄 Iniciando sincronização de custos de marketing para empresa {company_id}")
            
            # Buscar contas ML ativas da empresa
            accounts = self.db.query(MLAccount).filter(
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).all()
            
            if not accounts:
                return {
                    "success": False,
                    "error": "Nenhuma conta ML ativa encontrada",
                    "total_cost": 0,
                    "orders_updated": 0
                }
            
            logger.info(f"📊 Encontradas {len(accounts)} conta(s) ML ativa(s)")
            
            total_cost = 0
            total_orders_updated = 0
            accounts_processed = []
            
            for account in accounts:
                try:
                    account_result = self._sync_account_marketing_costs(account, months)
                    
                    if account_result["success"]:
                        total_cost += account_result["total_cost"]
                        total_orders_updated += account_result["orders_updated"]
                        
                        accounts_processed.append({
                            "account_id": account.id,
                            "nickname": account.nickname,
                            "total_cost": account_result["total_cost"],
                            "orders_updated": account_result["orders_updated"]
                        })
                        
                        logger.info(f"✅ Conta {account.nickname}: R$ {account_result['total_cost']:.2f} / {account_result['orders_updated']} pedidos")
                    else:
                        logger.warning(f"⚠️ Erro na conta {account.nickname}: {account_result['error']}")
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao processar conta {account.nickname}: {e}")
                    continue
            
            return {
                "success": True,
                "total_cost": total_cost,
                "orders_updated": total_orders_updated,
                "accounts_processed": len(accounts_processed),
                "accounts_data": accounts_processed,
                "message": f"Sincronização concluída: R$ {total_cost:.2f} em {total_orders_updated} pedidos"
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na sincronização de custos de marketing: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_cost": 0,
                "orders_updated": 0
            }
    
    def _sync_account_marketing_costs(self, account: MLAccount, months: int) -> Dict:
        """
        Sincroniza custos de marketing para uma conta específica
        
        Args:
            account: Conta ML
            months: Número de meses para sincronizar
            
        Returns:
            Resultado da sincronização da conta
        """
        try:
            # Buscar token válido
            token = None
            if account.tokens:
                token = sorted(account.tokens, key=lambda t: t.created_at, reverse=True)[0]
            
            if not token or not token.access_token:
                return {
                    "success": False,
                    "error": "Token não encontrado ou inválido",
                    "total_cost": 0,
                    "orders_updated": 0
                }
            
            # Buscar períodos de billing
            periods = self._get_billing_periods(token.access_token, months)
            if not periods:
                return {
                    "success": False,
                    "error": "Nenhum período de billing encontrado",
                    "total_cost": 0,
                    "orders_updated": 0
                }
            
            total_cost = 0
            total_orders_updated = 0
            
            # Processar cada período
            for period in periods:
                period_result = self._process_period_marketing_costs(account, token.access_token, period)
                
                if period_result["success"]:
                    total_cost += period_result["cost"]
                    total_orders_updated += period_result["orders_updated"]
                    
                    logger.info(f"  📅 Período {period['key']}: R$ {period_result['cost']:.2f} / {period_result['orders_updated']} pedidos")
            
            return {
                "success": True,
                "total_cost": total_cost,
                "orders_updated": total_orders_updated
            }
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar conta {account.nickname}: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_cost": 0,
                "orders_updated": 0
            }
    
    def _get_billing_periods(self, access_token: str, months: int) -> List[Dict]:
        """
        Busca períodos de billing disponíveis
        
        Args:
            access_token: Token de acesso
            months: Número de meses para buscar
            
        Returns:
            Lista de períodos disponíveis
        """
        try:
            url = f"{self.base_url}/billing/integration/monthly/periods"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            params = {
                "group": "ML",
                "document_type": "BILL",
                "limit": min(months, 12)  # Máximo 12 meses
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                periods = data.get("results", [])
                logger.info(f"📅 Encontrados {len(periods)} períodos de billing")
                return periods
            else:
                logger.error(f"Erro ao buscar períodos: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao buscar períodos de billing: {e}")
            return []
    
    def _process_period_marketing_costs(self, account: MLAccount, access_token: str, period: Dict) -> Dict:
        """
        Processa custos de marketing de um período específico
        
        Args:
            account: Conta ML
            access_token: Token de acesso
            period: Dados do período
            
        Returns:
            Resultado do processamento do período
        """
        try:
            period_key = period.get("key")
            period_from = period.get("period", {}).get("date_from")
            period_to = period.get("period", {}).get("date_to")
            
            if not all([period_key, period_from, period_to]):
                return {
                    "success": False,
                    "cost": 0,
                    "orders_updated": 0,
                    "error": "Dados do período incompletos"
                }
            
            # Buscar resumo do período
            summary = self._get_period_summary(access_token, period_key)
            if not summary:
                return {
                    "success": False,
                    "cost": 0,
                    "orders_updated": 0,
                    "error": "Resumo do período não encontrado"
                }
            
            # Extrair custos de Product Ads (PADS)
            pads_cost = self._extract_pads_cost(summary)
            if pads_cost <= 0:
                return {
                    "success": True,
                    "cost": 0,
                    "orders_updated": 0,
                    "message": "Nenhum custo de Product Ads encontrado"
                }
            
            # Buscar pedidos do período
            orders = self._get_orders_in_period(account.id, period_from, period_to)
            if not orders:
                return {
                    "success": True,
                    "cost": 0,
                    "orders_updated": 0,
                    "message": "Nenhum pedido encontrado no período"
                }
            
            # Distribuir custo proporcionalmente
            cost_per_order = pads_cost / len(orders)
            
            # Atualizar pedidos
            orders_updated = 0
            for order in orders:
                order.advertising_cost = cost_per_order
                order.is_advertising_sale = True
                orders_updated += 1
            
            # Salvar no banco
            self.db.commit()
            
            return {
                "success": True,
                "cost": pads_cost,
                "orders_updated": orders_updated,
                "cost_per_order": cost_per_order
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar período {period.get('key', 'unknown')}: {e}")
            return {
                "success": False,
                "cost": 0,
                "orders_updated": 0,
                "error": str(e)
            }
    
    def _get_period_summary(self, access_token: str, period_key: str) -> Optional[Dict]:
        """
        Busca resumo de billing de um período
        
        Args:
            access_token: Token de acesso
            period_key: Chave do período
            
        Returns:
            Resumo do período ou None
        """
        try:
            url = f"{self.base_url}/billing/integration/periods/key/{period_key}/summary/details"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            params = {
                "group": "ML",
                "document_type": "BILL"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Resumo não encontrado para período {period_key}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar resumo do período {period_key}: {e}")
            return None
    
    def _extract_pads_cost(self, summary: Dict) -> float:
        """
        Extrai custos de Product Ads (PADS) do resumo
        
        Args:
            summary: Resumo de billing
            
        Returns:
            Custo total de Product Ads
        """
        try:
            bill_includes = summary.get("bill_includes", {})
            charges = bill_includes.get("charges", [])
            
            pads_cost = 0.0
            for charge in charges:
                if charge.get("type") == "PADS":  # Product Ads
                    pads_cost += float(charge.get("amount", 0))
            
            return pads_cost
            
        except Exception as e:
            logger.error(f"Erro ao extrair custos PADS: {e}")
            return 0.0
    
    def _get_orders_in_period(self, ml_account_id: int, date_from: str, date_to: str) -> List[MLOrder]:
        """
        Busca pedidos de um período específico
        
        Args:
            ml_account_id: ID da conta ML
            date_from: Data inicial (YYYY-MM-DD)
            date_to: Data final (YYYY-MM-DD)
            
        Returns:
            Lista de pedidos do período
        """
        try:
            # Converter strings para datetime
            from_date = datetime.strptime(date_from, "%Y-%m-%d")
            to_date = datetime.strptime(date_to, "%Y-%m-%d")
            
            # Buscar pedidos do período
            orders = self.db.query(MLOrder).filter(
                and_(
                    MLOrder.ml_account_id == ml_account_id,
                    MLOrder.date_created >= from_date,
                    MLOrder.date_created <= to_date
                )
            ).all()
            
            return orders
            
        except Exception as e:
            logger.error(f"Erro ao buscar pedidos do período: {e}")
            return []
    
    def get_marketing_summary(self, company_id: int, months: int = 3) -> Dict:
        """
        Busca resumo de custos de marketing de uma empresa
        
        Args:
            company_id: ID da empresa
            months: Número de meses para analisar
            
        Returns:
            Resumo de custos de marketing
        """
        try:
            # Buscar pedidos com custos de marketing
            from_date = datetime.now() - timedelta(days=months * 30)
            
            orders = self.db.query(MLOrder).filter(
                and_(
                    MLOrder.ml_account_id.in_(
                        self.db.query(MLAccount.id).filter(
                            MLAccount.company_id == company_id
                        )
                    ),
                    MLOrder.date_created >= from_date,
                    MLOrder.is_advertising_sale == True
                )
            ).all()
            
            total_cost = sum(float(order.advertising_cost or 0) for order in orders)
            total_orders = len(orders)
            
            # Agrupar por mês
            monthly_costs = {}
            for order in orders:
                month_key = order.date_created.strftime("%Y-%m")
                if month_key not in monthly_costs:
                    monthly_costs[month_key] = {"cost": 0, "orders": 0}
                monthly_costs[month_key]["cost"] += float(order.advertising_cost or 0)
                monthly_costs[month_key]["orders"] += 1
            
            return {
                "total_cost": total_cost,
                "total_orders": total_orders,
                "average_cost_per_order": total_cost / total_orders if total_orders > 0 else 0,
                "monthly_breakdown": monthly_costs,
                "period_months": months
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar resumo de marketing: {e}")
            return {
                "total_cost": 0,
                "total_orders": 0,
                "average_cost_per_order": 0,
                "monthly_breakdown": {},
                "period_months": months
            }
