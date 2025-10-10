"""
Controller para Analytics & Performance
"""
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta

from app.models.saas_models import MLProduct, MLOrder, MLAccount, MLProductStatus

logger = logging.getLogger(__name__)

class AnalyticsController:
    """Controller para analytics de vendas e performance"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_sales_dashboard(self, company_id: int, ml_account_id: Optional[int] = None, 
                           period_days: int = 30, search: Optional[str] = None) -> Dict:
        """Busca dados do dashboard de vendas"""
        try:
            # Query base de produtos
            query = self.db.query(MLProduct).filter(
                MLProduct.company_id == company_id
            )
            
            # Filtrar por conta ML
            if ml_account_id:
                query = query.filter(MLProduct.ml_account_id == ml_account_id)
            
            # Filtrar por busca
            if search:
                search_term = f'%{search}%'
                query = query.filter(
                    (MLProduct.title.ilike(search_term)) |
                    (MLProduct.seller_sku.ilike(search_term)) |
                    (MLProduct.ml_item_id.ilike(search_term))
                )
            
            # Buscar produtos
            products = query.all()
            
            # Calcular KPIs
            total_revenue = 0
            total_sold = 0
            products_with_sales = 0
            
            products_data = []
            for product in products:
                price = float(product.price) if product.price else 0
                sold_qty = product.sold_quantity or 0
                revenue = price * sold_qty
                
                total_revenue += revenue
                total_sold += sold_qty
                if sold_qty > 0:
                    products_with_sales += 1
                
                products_data.append({
                    'id': product.id,
                    'ml_item_id': product.ml_item_id,
                    'title': product.title,
                    'price': price,
                    'available_quantity': product.available_quantity or 0,
                    'sold_quantity': sold_qty,
                    'status': product.status.value if product.status else 'unknown',
                    'thumbnail': product.thumbnail,
                    'revenue': revenue,
                    'seller_sku': product.seller_sku,
                    'category_name': product.category_name
                })
            
            avg_ticket = total_revenue / products_with_sales if products_with_sales > 0 else 0
            
            # Calcular custos e margens
            # Comissões ML (aproximadamente 10-16% dependendo da categoria - vamos usar 13% como média)
            ml_fees = total_revenue * 0.13
            
            # Fretes (assumir 0 por enquanto - pode ser configurado)
            shipping_fees = 0
            
            # Descontos (assumir 0 por enquanto)
            discounts = 0
            
            # Custo dos produtos (assumir 40% da receita - pode ser configurado)
            product_cost = total_revenue * 0.40
            
            # Impostos (aproximadamente 5% - pode ser configurado)
            taxes = total_revenue * 0.05
            
            # Outros custos (assumir R$ 0.30 por unidade)
            other_costs = total_sold * 0.30
            
            # Marketing (pode ser buscado da tabela ml_orders)
            marketing_cost = 0
            
            # Total de custos
            total_costs = ml_fees + shipping_fees + discounts + product_cost + taxes + other_costs + marketing_cost
            
            # Lucro líquido
            net_profit = total_revenue - total_costs
            
            # Margem líquida
            net_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
            
            # Lucro médio por pedido
            avg_profit_per_order = net_profit / products_with_sales if products_with_sales > 0 else 0
            
            # Calcular percentuais
            ml_fees_percent = (ml_fees / total_revenue * 100) if total_revenue > 0 else 0
            shipping_fees_percent = (shipping_fees / total_revenue * 100) if total_revenue > 0 else 0
            discounts_percent = (discounts / total_revenue * 100) if total_revenue > 0 else 0
            product_cost_percent = (product_cost / total_revenue * 100) if total_revenue > 0 else 0
            taxes_percent = (taxes / total_revenue * 100) if total_revenue > 0 else 0
            other_costs_percent = (other_costs / total_revenue * 100) if total_revenue > 0 else 0
            marketing_percent = (marketing_cost / total_revenue * 100) if total_revenue > 0 else 0
            total_costs_percent = (total_costs / total_revenue * 100) if total_revenue > 0 else 0
            
            # Custo por unidade para "outros custos"
            other_costs_per_unit = other_costs / total_sold if total_sold > 0 else 0
            
            return {
                'success': True,
                'kpis': {
                    'total_revenue': total_revenue,
                    'total_sold': total_sold,
                    'total_orders': products_with_sales,
                    'avg_ticket': avg_ticket
                },
                'costs': {
                    'ml_fees': ml_fees,
                    'ml_fees_percent': ml_fees_percent,
                    'shipping_fees': shipping_fees,
                    'shipping_fees_percent': shipping_fees_percent,
                    'discounts': discounts,
                    'discounts_percent': discounts_percent,
                    'product_cost': product_cost,
                    'product_cost_percent': product_cost_percent,
                    'taxes': taxes,
                    'taxes_percent': taxes_percent,
                    'other_costs': other_costs,
                    'other_costs_percent': other_costs_percent,
                    'other_costs_per_unit': other_costs_per_unit,
                    'marketing_cost': marketing_cost,
                    'marketing_percent': marketing_percent,
                    'total_costs': total_costs,
                    'total_costs_percent': total_costs_percent
                },
                'profit': {
                    'net_profit': net_profit,
                    'net_margin': net_margin,
                    'avg_profit_per_order': avg_profit_per_order
                },
                'products': products_data,
                'total': len(products_data)
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar dashboard de vendas: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_top_products(self, company_id: int, ml_account_id: Optional[int] = None, 
                        limit: int = 10) -> Dict:
        """Busca top produtos mais vendidos e com maior receita"""
        try:
            # Query base
            query = self.db.query(MLProduct).filter(
                MLProduct.company_id == company_id,
                MLProduct.sold_quantity > 0
            )
            
            if ml_account_id:
                query = query.filter(MLProduct.ml_account_id == ml_account_id)
            
            # Top mais vendidos
            top_sold = query.order_by(desc(MLProduct.sold_quantity)).limit(limit).all()
            
            # Top maior receita (calculado)
            all_products = query.all()
            products_with_revenue = []
            
            for product in all_products:
                price = float(product.price) if product.price else 0
                sold_qty = product.sold_quantity or 0
                revenue = price * sold_qty
                
                products_with_revenue.append({
                    'id': product.id,
                    'ml_item_id': product.ml_item_id,
                    'title': product.title,
                    'price': price,
                    'sold_quantity': sold_qty,
                    'revenue': revenue,
                    'thumbnail': product.thumbnail
                })
            
            # Ordenar por receita
            top_revenue = sorted(products_with_revenue, key=lambda x: x['revenue'], reverse=True)[:limit]
            
            return {
                'success': True,
                'top_sold': [
                    {
                        'id': p.id,
                        'ml_item_id': p.ml_item_id,
                        'title': p.title,
                        'price': float(p.price) if p.price else 0,
                        'sold_quantity': p.sold_quantity,
                        'thumbnail': p.thumbnail
                    }
                    for p in top_sold
                ],
                'top_revenue': top_revenue
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar top produtos: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_accounts_summary(self, company_id: int) -> Dict:
        """Busca resumo de vendas por conta ML"""
        try:
            # Buscar todas as contas da empresa
            accounts = self.db.query(MLAccount).filter(
                MLAccount.company_id == company_id
            ).all()
            
            accounts_data = []
            
            for account in accounts:
                # Buscar produtos da conta
                products = self.db.query(MLProduct).filter(
                    MLProduct.ml_account_id == account.id,
                    MLProduct.company_id == company_id
                ).all()
                
                # Calcular métricas
                total_products = len(products)
                active_products = len([p for p in products if p.status == MLProductStatus.ACTIVE])
                total_sold = sum(p.sold_quantity or 0 for p in products)
                
                total_revenue = 0
                products_with_sales = 0
                
                for product in products:
                    price = float(product.price) if product.price else 0
                    sold_qty = product.sold_quantity or 0
                    total_revenue += price * sold_qty
                    if sold_qty > 0:
                        products_with_sales += 1
                
                avg_ticket = total_revenue / products_with_sales if products_with_sales > 0 else 0
                
                accounts_data.append({
                    'id': account.id,
                    'nickname': account.nickname,
                    'email': account.email,
                    'total_products': total_products,
                    'active_products': active_products,
                    'total_sold': total_sold,
                    'total_revenue': total_revenue,
                    'avg_ticket': avg_ticket,
                    'products_with_sales': products_with_sales
                })
            
            return {
                'success': True,
                'accounts': accounts_data
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar resumo de contas: {e}")
            return {
                'success': False,
                'error': str(e)
            }

