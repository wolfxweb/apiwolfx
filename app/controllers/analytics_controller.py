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
    
    def get_sales_dashboard(self, company_id: int, user_id: int, ml_account_id: Optional[int] = None, 
                           period_days: int = 30, search: Optional[str] = None, 
                           current_month: bool = False, last_month: bool = False,
                           current_year: bool = False, date_from: Optional[str] = None,
                           date_to: Optional[str] = None) -> Dict:
        """
        Dashboard de vendas com dados reais do banco
        """
        try:
            logger.info(f"🚀 DASHBOARD REAL - company_id={company_id}, period_days={period_days}")
            
            # Calcular período
            end_date = datetime.now()
            if current_month:
                start_date = datetime(end_date.year, end_date.month, 1)
            elif last_month:
                if end_date.month == 1:
                    start_date = datetime(end_date.year - 1, 12, 1)
                else:
                    start_date = datetime(end_date.year, end_date.month - 1, 1)
                end_date = datetime(start_date.year, start_date.month + 1, 1) - timedelta(days=1)
            elif current_year:
                start_date = datetime(end_date.year, 1, 1)
            elif date_from and date_to:
                start_date = datetime.strptime(date_from, '%Y-%m-%d')
                end_date = datetime.strptime(date_to, '%Y-%m-%d')
            else:
                start_date = end_date - timedelta(days=period_days)
            
            logger.info(f"📅 Período: {start_date} a {end_date}")
            
            # Buscar pedidos do período (mesmo filtro do dashboard financeiro)
            orders_query = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id,
                MLOrder.date_created >= start_date,
                MLOrder.date_created <= end_date,
                MLOrder.status.in_([OrderStatus.PAID, OrderStatus.DELIVERED])
            )
            
            # Remover filtro de ml_account_id para pegar todas as contas (igual ao financeiro)
            # if ml_account_id:
            #     orders_query = orders_query.filter(MLOrder.ml_account_id == ml_account_id)
            
            orders = orders_query.all()
            logger.info(f"📊 Encontrados {len(orders)} pedidos")
            
            # Calcular KPIs aplicando a mesma regra dos 7 dias do dashboard financeiro
            total_revenue = 0
            total_orders = len(orders)
            
            for order in orders:
                # Aplicar regra dos 7 dias (igual ao dashboard financeiro)
                is_delivered = (
                    order.status == OrderStatus.DELIVERED or 
                    (order.shipping_status and order.shipping_status.lower() == "delivered")
                )
                
                if is_delivered:
                    delivery_date = None
                    if order.shipping_details and isinstance(order.shipping_details, dict):
                        status_history = order.shipping_details.get('status_history', {})
                        if status_history and 'date_delivered' in status_history:
                            try:
                                delivery_date_str = status_history['date_delivered']
                                delivery_date = datetime.fromisoformat(delivery_date_str.replace('Z', '+00:00'))
                            except:
                                pass
                    
                    if delivery_date:
                        days_since_delivery = (datetime.now() - delivery_date.replace(tzinfo=None)).days
                        if days_since_delivery >= 7:
                            total_revenue += float(order.total_amount or 0)
                    # Se entregue há menos de 7 dias, não conta como receita ainda
                else:
                    # Se não foi entregue, não conta como receita ainda
                    pass
            
            # Como não temos quantity direto, vamos usar 1 por pedido como estimativa
            total_sold = total_orders  # Assumindo 1 item por pedido
            avg_ticket = total_revenue / total_orders if total_orders > 0 else 0
            
            # Pedidos cancelados
            cancelled_orders = [o for o in orders if o.status == OrderStatus.CANCELLED]
            cancelled_count = len(cancelled_orders)
            cancelled_value = sum(float(order.total_amount or 0) for order in cancelled_orders)
            
            # Devoluções (mediations/claims)
            returns_orders = []
            returns_count = 0
            returns_value = 0.0
            for order in orders:
                if order.mediations:
                    try:
                        import json
                        mediations = json.loads(order.mediations) if isinstance(order.mediations, str) else order.mediations
                        if isinstance(mediations, list) and len(mediations) > 0:
                            returns_orders.append(order)
                            returns_count += 1
                            returns_value += float(order.total_amount or 0)
                    except:
                        pass
            
            # Visitas (buscar da API do Mercado Livre usando TokenManager)
            total_visits = 0
            try:
                from app.services.token_manager import TokenManager
                from app.services.ml_visits_service import MLVisitsService
                from app.models.saas_models import MLAccount
                
                # Usar TokenManager para obter token válido do usuário logado
                token_manager = TokenManager(self.db)
                access_token = token_manager.get_valid_token(user_id)
                
                if access_token:
                    # Buscar conta ML do usuário
                    ml_account = self.db.query(MLAccount).filter(
                        MLAccount.company_id == company_id
                    ).first()
                    
                    if ml_account:
                        visits_service = MLVisitsService()
                        visits_data = visits_service.get_user_visits(
                            user_id=ml_account.ml_user_id,
                            access_token=access_token,
                            date_from=start_date,
                            date_to=end_date
                        )
                        total_visits = visits_data.get('total_visits', 0)
                        logger.info(f"👁️  Visitas obtidas da API: {total_visits}")
                    else:
                        logger.warning(f"Nenhuma conta ML encontrada para company_id: {company_id}")
                else:
                    logger.warning(f"Nenhum token válido encontrado para user_id: {user_id}")
            except Exception as e:
                logger.error(f"Erro ao buscar visitas: {e}")
                total_visits = 0
            
            # Buscar produtos
            products_query = self.db.query(MLProduct).filter(MLProduct.company_id == company_id)
            if search:
                products_query = products_query.filter(
                    MLProduct.title.ilike(f'%{search}%')
                )
            products = products_query.all()
            
            # Calcular vendas por produto
            product_sales = {}
            for order in orders:
                # Extrair ML item ID do pedido (assumindo que está no order_items JSON)
                if order.order_items:
                    try:
                        import json
                        items = json.loads(order.order_items) if isinstance(order.order_items, str) else order.order_items
                        if isinstance(items, list):
                            for item in items:
                                ml_item_id = item.get('item', {}).get('id')
                                if ml_item_id:
                                    if ml_item_id not in product_sales:
                                        product_sales[ml_item_id] = {
                                            'revenue': 0.0,
                                            'quantity': 0,
                                            'orders': 0
                                        }
                                    product_sales[ml_item_id]['revenue'] += float(order.total_amount or 0)
                                    product_sales[ml_item_id]['quantity'] += 1
                                    product_sales[ml_item_id]['orders'] += 1
                    except:
                        # Se não conseguir extrair itens, assumir que o produto principal é o do pedido
                        pass
            
            # Timeline (últimos 7 dias)
            timeline = []
            for i in range(7):
                date = end_date - timedelta(days=i)
                day_orders = [o for o in orders if o.date_created.date() == date.date()]
                timeline.append({
                    'date': date.strftime('%d/%m'),
                    'revenue': sum(float(o.total_amount or 0) for o in day_orders),
                    'orders': len(day_orders),
                    'units': len(day_orders)  # Assumindo 1 item por pedido
                })
            timeline.reverse()
            
            return {
                'success': True,
                'kpis': {
                    'total_revenue': total_revenue,
                    'total_sold': total_sold,
                    'total_orders': total_orders,
                    'avg_ticket': avg_ticket,
                    'cancelled_orders': cancelled_count,
                    'cancelled_value': cancelled_value,
                    'returns_count': returns_count,
                    'returns_value': returns_value,
                    'total_visits': total_visits,
                    'total_products': len(products)
                },
                'costs': {
                    'ml_fees': total_revenue * 0.10,  # 10% estimado
                    'ml_fees_percent': 10.0,
                    'shipping_fees': 0.0,
                    'shipping_fees_percent': 0.0,
                    'discounts': 0.0,
                    'discounts_percent': 0.0,
                    'product_cost': total_revenue * 0.40,  # 40% estimado
                    'product_cost_percent': 40.0,
                    'taxes': 0.0,
                    'taxes_percent': 0.0,
                    'other_costs': 0.0,
                    'other_costs_percent': 0.0,
                    'other_costs_per_unit': 0.0,
                    'marketing_cost': 0.0,
                    'marketing_percent': 0.0,
                    'marketing_per_unit': 0.0,
                    'total_costs': total_revenue * 0.50,  # 50% estimado
                    'total_costs_percent': 50.0
                },
                'profit': {
                    'net_profit': total_revenue * 0.50,  # 50% estimado
                    'net_margin': 50.0,
                    'avg_profit_per_order': (total_revenue * 0.50) / total_orders if total_orders > 0 else 0
                },
                'products': [
                    {
                        'id': p.id,
                        'ml_item_id': p.ml_item_id,
                        'title': p.title,
                        'price': float(p.price or 0),
                        'available_quantity': int(p.available_quantity or 0),
                        'sold_quantity': product_sales.get(p.ml_item_id, {}).get('quantity', 0),
                        'status': p.status.value if p.status else 'unknown',
                        'revenue': product_sales.get(p.ml_item_id, {}).get('revenue', 0.0),
                        'seller_sku': p.seller_sku,
                        'category_name': p.category_name
                    } for p in products[:50]  # Limitar a 50 produtos
                ],
                'total': len(products),
                'timeline': timeline,
                'pareto_analysis': self._calculate_pareto_analysis(products, product_sales, total_revenue)
            }
            
        except Exception as e:
            logger.error(f"Erro no dashboard simplificado: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_pareto_analysis(self, products, product_sales, total_revenue):
        """Calcula análises de Pareto para produtos"""
        try:
            # Preparar dados dos produtos com vendas
            products_with_sales = []
            for product in products:
                sales_data = product_sales.get(product.ml_item_id, {})
                revenue = sales_data.get('revenue', 0.0)
                quantity = sales_data.get('quantity', 0)
                
                if revenue > 0:  # Apenas produtos com vendas
                    # Calcular margem estimada (assumindo 50% de margem)
                    estimated_cost = revenue * 0.5
                    profit = revenue - estimated_cost
                    margin_percent = (profit / revenue * 100) if revenue > 0 else 0
                    
                    products_with_sales.append({
                        'id': product.id,
                        'ml_item_id': product.ml_item_id,
                        'title': product.title,
                        'revenue': revenue,
                        'quantity': quantity,
                        'profit': profit,
                        'margin_percent': margin_percent,
                        'status': product.status.value if product.status else 'unknown'
                    })
            
            # Ordenar por receita
            products_by_revenue = sorted(products_with_sales, key=lambda x: x['revenue'], reverse=True)
            
            # Análise de Pareto - 80% da receita
            pareto_80_revenue = []
            cumulative_revenue = 0.0
            target_80_percent = total_revenue * 0.8
            
            for product in products_by_revenue:
                cumulative_revenue += product['revenue']
                pareto_80_revenue.append({
                    **product,
                    'cumulative_revenue': cumulative_revenue,
                    'cumulative_percent': (cumulative_revenue / total_revenue * 100) if total_revenue > 0 else 0
                })
                if cumulative_revenue >= target_80_percent:
                    break
            
            # Ordenar por quantidade
            products_by_quantity = sorted(products_with_sales, key=lambda x: x['quantity'], reverse=True)
            
            # Análise de Pareto - 80% da quantidade
            pareto_80_quantity = []
            total_quantity = sum(p['quantity'] for p in products_with_sales)
            cumulative_quantity = 0
            target_80_quantity = total_quantity * 0.8
            
            for product in products_by_quantity:
                cumulative_quantity += product['quantity']
                pareto_80_quantity.append({
                    **product,
                    'cumulative_quantity': cumulative_quantity,
                    'cumulative_percent': (cumulative_quantity / total_quantity * 100) if total_quantity > 0 else 0
                })
                if cumulative_quantity >= target_80_quantity:
                    break
            
            # Ordenar por lucro
            products_by_profit = sorted(products_with_sales, key=lambda x: x['profit'], reverse=True)
            
            # Análise de Pareto - 80% do lucro
            pareto_80_profit = []
            total_profit = sum(p['profit'] for p in products_with_sales)
            cumulative_profit = 0.0
            target_80_profit = total_profit * 0.8
            
            for product in products_by_profit:
                cumulative_profit += product['profit']
                pareto_80_profit.append({
                    **product,
                    'cumulative_profit': cumulative_profit,
                    'cumulative_percent': (cumulative_profit / total_profit * 100) if total_profit > 0 else 0
                })
                if cumulative_profit >= target_80_profit:
                    break
            
            # Cauda longa - 20% da receita (produtos com menor faturamento)
            tail_20_revenue = []
            target_20_percent = total_revenue * 0.2
            tail_revenue = 0.0
            
            # Produtos ordenados por receita (menor para maior)
            products_by_revenue_asc = sorted(products_with_sales, key=lambda x: x['revenue'])
            
            for product in products_by_revenue_asc:
                tail_revenue += product['revenue']
                tail_20_revenue.append({
                    **product,
                    'cumulative_revenue': tail_revenue,
                    'cumulative_percent': (tail_revenue / total_revenue * 100) if total_revenue > 0 else 0
                })
                if tail_revenue >= target_20_percent:
                    break
            
            return {
                'revenue_80_percent': pareto_80_revenue,
                'quantity_80_percent': pareto_80_quantity,
                'profit_80_percent': pareto_80_profit,
                'tail_20_percent': tail_20_revenue,
                'total_products_with_sales': len(products_with_sales),
                'total_revenue': total_revenue,
                'total_quantity': total_quantity,
                'total_profit': total_profit
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular análise de Pareto: {e}")
            return {
                'revenue_80_percent': [],
                'quantity_80_percent': [],
                'profit_80_percent': [],
                'tail_20_percent': [],
                'total_products_with_sales': 0,
                'total_revenue': 0,
                'total_quantity': 0,
                'total_profit': 0
            }
    
    def get_top_products(self, company_id: int, ml_account_id: Optional[int] = None, 
                        limit: int = 10, period_days: int = 30, search: Optional[str] = None) -> Dict:
        """Top produtos por quantidade e receita"""
        try:
            # Buscar dados do dashboard para obter análise de vendas
            dashboard_data = self.get_sales_dashboard(
                company_id=company_id,
                ml_account_id=ml_account_id,
                period_days=period_days,
                search=search
            )
            
            if not dashboard_data.get('success'):
                return {
                    'success': False,
                    'error': 'Erro ao buscar dados do dashboard'
                }
            
            # Extrair análise de Pareto
            pareto = dashboard_data.get('pareto_analysis', {})
            
            # Top por quantidade vendida (80% da quantidade)
            top_sold = pareto.get('quantity_80_percent', [])[:limit]
            
            # Top por receita (80% da receita)
            top_revenue = pareto.get('revenue_80_percent', [])[:limit]
            
            return {
                'success': True,
                'top_sold': top_sold,
                'top_revenue': top_revenue
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