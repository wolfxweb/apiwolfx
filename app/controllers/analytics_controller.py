"""
Controller para Analytics & Performance - VERSÃO SIMPLIFICADA
Mantém apenas o HTML atual, remove consultas pesadas
"""
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, text
from datetime import datetime, timedelta

from app.models.saas_models import MLProduct, MLOrder, MLAccount, MLProductStatus, OrderStatus

logger = logging.getLogger(__name__)

class AnalyticsController:
    """Controller para analytics de vendas e performance - VERSÃO SIMPLIFICADA"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_sales_dashboard(self, company_id: int, ml_account_id: Optional[int] = None, 
                           period_days: int = 30, search: Optional[str] = None, 
                           current_month: bool = False, last_month: bool = False,
                           current_year: bool = False, date_from: Optional[str] = None,
                           date_to: Optional[str] = None) -> Dict:
        """
        Dashboard de vendas SIMPLIFICADO - retorna dados mock para manter HTML funcionando
        
        ESTRATÉGIA:
        1. Manter HTML atual funcionando
        2. Retornar dados mock temporários
        3. Remover consultas pesadas
        4. Focar na interface primeiro
        """
        try:
            logger.info(f"🚀 DASHBOARD SIMPLIFICADO - company_id={company_id}, period_days={period_days}")
            
            # Retornar dados mock para manter HTML funcionando
            return {
                'success': True,
                'kpis': {
                    'total_revenue': 0.0,
                    'total_sold': 0,
                    'total_orders': 0,
                    'avg_ticket': 0.0,
                    'cancelled_orders': 0,
                    'cancelled_value': 0.0,
                    'returns_count': 0,
                    'returns_value': 0.0,
                    'total_visits': 0,
                    'total_products': 0
                },
                'costs': {
                    'ml_fees': 0.0,
                    'ml_fees_percent': 0.0,
                    'shipping_fees': 0.0,
                    'shipping_fees_percent': 0.0,
                    'discounts': 0.0,
                    'discounts_percent': 0.0,
                    'product_cost': 0.0,
                    'product_cost_percent': 0.0,
                    'taxes': 0.0,
                    'taxes_percent': 0.0,
                    'other_costs': 0.0,
                    'other_costs_percent': 0.0,
                    'other_costs_per_unit': 0.0,
                    'marketing_cost': 0.0,
                    'marketing_percent': 0.0,
                    'marketing_per_unit': 0.0,
                    'total_costs': 0.0,
                    'total_costs_percent': 0.0
                },
                'profit': {
                    'net_profit': 0.0,
                    'net_margin': 0.0,
                    'avg_profit_per_order': 0.0
                },
                'products': [],
                'total': 0,
                'timeline': []
            }
            
        except Exception as e:
            logger.error(f"Erro no dashboard simplificado: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_top_products(self, company_id: int, ml_account_id: Optional[int] = None, 
                        limit: int = 10, period_days: int = 30, search: Optional[str] = None) -> Dict:
        """Top produtos - VERSÃO SIMPLIFICADA"""
        try:
            return {
                'success': True,
                'top_sold': [],
                'top_revenue': []
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar top produtos: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_accounts_summary(self, company_id: int) -> Dict:
        """Resumo de contas - VERSÃO SIMPLIFICADA"""
        try:
            return {
                'success': True,
                'accounts': []
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar resumo de contas: {e}")
            return {
                'success': False,
                'error': str(e)
            }