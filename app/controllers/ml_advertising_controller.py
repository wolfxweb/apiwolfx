"""
Controller para gerenciar dados de publicidade (Product Ads)
"""
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.saas_models import MLOrder, MLAccount

logger = logging.getLogger(__name__)

class MLAdvertisingController:
    """Controller para sincronizar e gerenciar dados de Product Ads"""
    
    def __init__(self, db: Session):
        self.db = db
        self.base_url = "https://api.mercadolibre.com"
    
    async def sync_advertising_costs(self, company_id: int, periods: int = 3) -> Dict:
        """
        Sincroniza custos de Product Ads do Billing API
        
        Args:
            company_id: ID da empresa
            periods: Número de períodos (meses) para sincronizar
            
        Returns:
            Dicionário com resultados da sincronização
        """
        try:
            # Buscar contas ML da empresa
            accounts = self.db.query(MLAccount).filter(
                MLAccount.company_id == company_id
            ).all()
            
            if not accounts:
                return {
                    "total_accounts": 0,
                    "error": "Nenhuma conta ML encontrada"
                }
            
            logger.info(f"📊 Sincronizando custos de {len(accounts)} conta(s) ML")
            
            total_cost = 0
            total_orders_updated = 0
            accounts_processed = []
            
            for account in accounts:
                # Buscar token válido
                token = None
                if account.tokens:
                    token = sorted(account.tokens, key=lambda t: t.created_at, reverse=True)[0]
                
                if not token or not token.access_token:
                    logger.warning(f"⚠️  Conta {account.nickname} sem token válido")
                    continue
                
                access_token = token.access_token
                
                # Buscar períodos de billing
                periods_url = f"{self.base_url}/billing/integration/monthly/periods"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                params = {
                    "group": "ML",
                    "document_type": "BILL",
                    "limit": periods
                }
                
                logger.info(f"🔄 Processando conta: {account.nickname}")
                
                try:
                    response = requests.get(periods_url, headers=headers, params=params, timeout=30)
                    
                    if response.status_code != 200:
                        logger.error(f"❌ Erro ao buscar períodos: {response.status_code}")
                        continue
                    
                    periods_data = response.json()
                    results = periods_data.get("results", [])
                    
                    if not results:
                        logger.warning(f"⚠️  Nenhum período encontrado")
                        continue
                    
                    account_cost = 0
                    account_orders = 0
                    
                    # Processar cada período
                    for period in results:
                        period_key = period.get("key")
                        period_from = period.get("period", {}).get("date_from")
                        period_to = period.get("period", {}).get("date_to")
                        
                        # Buscar summary/details do período
                        summary_url = f"{self.base_url}/billing/integration/periods/key/{period_key}/summary/details"
                        summary_params = {
                            "group": "ML",
                            "document_type": "BILL"
                        }
                        
                        summary_response = requests.get(summary_url, headers=headers, params=summary_params, timeout=30)
                        
                        if summary_response.status_code != 200:
                            logger.error(f"❌ Erro ao buscar summary do período {period_key}")
                            continue
                        
                        summary_data = summary_response.json()
                        
                        # Procurar custos de Product Ads
                        period_pads_cost = 0
                        charges = summary_data.get("bill_includes", {}).get("charges", [])
                        
                        for charge in charges:
                            if charge.get("type") == "PADS":
                                period_pads_cost += float(charge.get("amount", 0))
                        
                        if period_pads_cost > 0:
                            # Converter datas do período
                            date_from = datetime.strptime(period_from, "%Y-%m-%d")
                            date_to = datetime.strptime(period_to, "%Y-%m-%d")
                            
                            # Buscar pedidos do período
                            orders = self.db.query(MLOrder).filter(
                                MLOrder.ml_account_id == account.id,
                                MLOrder.date_created >= date_from,
                                MLOrder.date_created <= date_to
                            ).all()
                            
                            if len(orders) > 0:
                                # Distribuir custo proporcionalmente
                                cost_per_order = period_pads_cost / len(orders)
                                
                                for order in orders:
                                    order.advertising_cost = cost_per_order
                                    order.is_advertising_sale = True
                                
                                self.db.commit()
                                
                                account_cost += period_pads_cost
                                account_orders += len(orders)
                                
                                logger.info(f"  ✅ Período {period_key}: R$ {period_pads_cost:.2f} / {len(orders)} pedidos")
                    
                    accounts_processed.append({
                        "account_id": account.id,
                        "nickname": account.nickname,
                        "total_cost": account_cost,
                        "orders_updated": account_orders
                    })
                    
                    total_cost += account_cost
                    total_orders_updated += account_orders
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao processar conta {account.nickname}: {e}")
                    continue
            
            return {
                "total_accounts": len(accounts_processed),
                "accounts": accounts_processed,
                "total_cost": total_cost,
                "total_orders_updated": total_orders_updated
            }
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar custos de publicidade: {e}")
            raise
    
    def get_advertising_summary(self, company_id: int, days: int = 30) -> Dict:
        """
        Retorna resumo dos custos de publicidade
        
        Args:
            company_id: ID da empresa
            days: Número de dias para análise
            
        Returns:
            Dicionário com resumo dos custos
        """
        try:
            date_from = datetime.utcnow() - timedelta(days=days)
            
            # Total de custos
            total_cost = self.db.query(
                func.sum(MLOrder.advertising_cost)
            ).filter(
                MLOrder.company_id == company_id,
                MLOrder.date_created >= date_from,
                MLOrder.advertising_cost.isnot(None)
            ).scalar() or 0
            
            # Total de pedidos com publicidade
            orders_with_ads = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id,
                MLOrder.date_created >= date_from,
                MLOrder.advertising_cost.isnot(None),
                MLOrder.advertising_cost > 0
            ).count()
            
            # Total de pedidos
            total_orders = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id,
                MLOrder.date_created >= date_from
            ).count()
            
            # Custo médio por pedido
            avg_cost_per_order = total_cost / orders_with_ads if orders_with_ads > 0 else 0
            
            # Porcentagem de pedidos com publicidade
            ads_percentage = (orders_with_ads / total_orders * 100) if total_orders > 0 else 0
            
            return {
                "period_days": days,
                "total_cost": float(total_cost),
                "orders_with_ads": orders_with_ads,
                "total_orders": total_orders,
                "avg_cost_per_order": float(avg_cost_per_order),
                "ads_percentage": float(ads_percentage)
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar resumo de publicidade: {e}")
            raise

