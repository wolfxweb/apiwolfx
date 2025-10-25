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
                           date_to: Optional[str] = None, specific_month: Optional[int] = None,
                           specific_year: Optional[int] = None) -> Dict:
        """
        Dashboard de vendas com dados reais do banco
        """
        try:
            logger.info(f"🚀 DASHBOARD REAL - company_id={company_id}, period_days={period_days}")
            
            # Calcular período
            end_date = datetime.now()
            if specific_month and specific_year:
                # Usar mês e ano específicos
                if specific_month in [1, 3, 5, 7, 8, 10, 12]:
                    # Mês com 31 dias
                    start_date = datetime(specific_year, specific_month, 1)
                    end_date = datetime(specific_year, specific_month, 31, 23, 59, 59)
                elif specific_month in [4, 6, 9, 11]:
                    # Mês com 30 dias
                    start_date = datetime(specific_year, specific_month, 1)
                    end_date = datetime(specific_year, specific_month, 30, 23, 59, 59)
                elif specific_month == 2:
                    # Fevereiro (28 dias)
                    start_date = datetime(specific_year, 2, 1)
                    end_date = datetime(specific_year, 2, 28, 23, 59, 59)
                else:
                    start_date = end_date - timedelta(days=period_days)
                logger.info(f"🎯 Usando mês/ano específico {specific_month}/{specific_year}: {start_date} a {end_date}")
            elif current_month:
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
            elif period_days in [28, 29, 30, 31]:
                # Se for um mês completo (28-31 dias), verificar se é um mês específico
                # Para qualquer mês de 2025, usar datas específicas
                if end_date.year == 2025:
                    # Calcular o mês baseado no período
                    if period_days == 31:
                        # Mês com 31 dias (Janeiro, Março, Maio, Julho, Agosto, Outubro, Dezembro)
                        if end_date.month in [1, 3, 5, 7, 8, 10, 12]:
                            start_date = datetime(2025, end_date.month, 1)
                            end_date = datetime(2025, end_date.month, 31, 23, 59, 59)
                            logger.info(f"🎯 Usando datas específicas do mês {end_date.month}/2025: {start_date} a {end_date}")
                        else:
                            start_date = end_date - timedelta(days=period_days)
                            logger.info(f"📅 Usando últimos {period_days} dias: {start_date} a {end_date}")
                    elif period_days == 30:
                        # Mês com 30 dias (Abril, Junho, Setembro, Novembro)
                        if end_date.month in [4, 6, 9, 11]:
                            start_date = datetime(2025, end_date.month, 1)
                            end_date = datetime(2025, end_date.month, 30, 23, 59, 59)
                            logger.info(f"🎯 Usando datas específicas do mês {end_date.month}/2025: {start_date} a {end_date}")
                        else:
                            start_date = end_date - timedelta(days=period_days)
                            logger.info(f"📅 Usando últimos {period_days} dias: {start_date} a {end_date}")
                    elif period_days == 28:
                        # Fevereiro (28 dias)
                        if end_date.month == 2:
                            start_date = datetime(2025, 2, 1)
                            end_date = datetime(2025, 2, 28, 23, 59, 59)
                            logger.info(f"🎯 Usando datas específicas de Fevereiro/2025: {start_date} a {end_date}")
                        else:
                            start_date = end_date - timedelta(days=period_days)
                            logger.info(f"📅 Usando últimos {period_days} dias: {start_date} a {end_date}")
                    else:
                        start_date = end_date - timedelta(days=period_days)
                        logger.info(f"📅 Usando últimos {period_days} dias: {start_date} a {end_date}")
                else:
                    start_date = end_date - timedelta(days=period_days)
                    logger.info(f"📅 Usando últimos {period_days} dias: {start_date} a {end_date}")
            else:
                start_date = end_date - timedelta(days=period_days)
            
            logger.info(f"📅 Período: {start_date} a {end_date}")
            
            # Buscar pedidos do período usando date_approved do pagamento (CORREÇÃO CRÍTICA)
            from sqlalchemy import text
            
            # Consulta otimizada que extrai date_approved do JSON de payments
            # Incluir TODOS os pedidos (válidos, cancelados, etc.) para análise completa
            orders_result = self.db.execute(text("""
                SELECT 
                    id,
                    ml_order_id,
                    order_id,
                    status,
                    total_amount,
                    paid_amount,
                    date_created,
                    date_closed,
                    order_items,
                    payments,
                    mediations
                FROM ml_orders 
                WHERE company_id = :company_id
                AND (
                    -- Para pedidos válidos, usar date_approved do pagamento
                    (status IN ('PAID', 'CONFIRMED', 'SHIPPED', 'DELIVERED') 
                     AND payments IS NOT NULL 
                     AND payments::text != '[]' 
                     AND payments::text != '{}'
                     AND (payments->0->>'date_approved')::timestamp AT TIME ZONE 'UTC-4' >= :start_date
                     AND (payments->0->>'date_approved')::timestamp AT TIME ZONE 'UTC-4' <= :end_date)
                    OR
                    -- Para pedidos cancelados e outros, usar date_created
                    (status NOT IN ('PAID', 'CONFIRMED', 'SHIPPED', 'DELIVERED')
                     AND date_created >= :start_date
                     AND date_created <= :end_date)
                )
                ORDER BY date_created DESC
            """), {
                "company_id": company_id,
                "start_date": start_date,
                "end_date": end_date
            })
            
            orders_data = orders_result.fetchall()
            logger.info(f"📊 Encontrados {len(orders_data)} pedidos (usando date_approved)")
            
            # Converter para lista de objetos similares ao ORM
            orders = []
            for row in orders_data:
                # Criar um objeto similar ao MLOrder para compatibilidade
                class OrderData:
                    def __init__(self, row):
                        self.id = row.id
                        self.ml_order_id = row.ml_order_id
                        self.order_id = row.order_id
                        self.status = row.status
                        self.total_amount = row.total_amount
                        self.paid_amount = row.paid_amount
                        self.date_created = row.date_created
                        self.date_closed = row.date_closed
                        self.order_items = row.order_items
                        self.payments = row.payments
                        self.mediations = row.mediations  # Incluir mediations
                        # Adicionar atributos necessários para compatibilidade
                        self.shipping_cost = 0.0
                        self.ml_fees = 0.0
                        self.shipping_fees = 0.0
                        self.discounts = 0.0
                        self.marketing_cost = 0.0
                        self.advertising_cost = 0.0
                
                orders.append(OrderData(row))
            
            # Calcular KPIs baseado no status do pedido (sem regra dos 7 dias)
            vendas_brutas = 0  # Vendas sem descontar cancelamentos
            total_orders = len(orders)
            total_sold = 0  # Contar unidades reais
            
            for order in orders:
                # Contar vendas brutas (pedidos válidos)
                # Verificar se o status é válido (string ou enum)
                valid_statuses = ['PAID', 'CONFIRMED', 'SHIPPED', 'DELIVERED']
                if order.status in valid_statuses or str(order.status) in valid_statuses:
                    vendas_brutas += float(order.total_amount or 0)
                    
                    # Contar unidades reais dos itens do pedido
                    if order.order_items:
                        try:
                            import json
                            order_items = json.loads(order.order_items) if isinstance(order.order_items, str) else order.order_items
                            if isinstance(order_items, list):
                                for item in order_items:
                                    quantity = item.get('quantity', 0)
                                    total_sold += int(quantity)
                        except:
                            # Se não conseguir parsear, assumir 1 item por pedido
                            total_sold += 1
                    else:
                        # Se não tem order_items, assumir 1 item por pedido
                        total_sold += 1
            
            # Pedidos cancelados
            cancelled_orders = [o for o in orders if str(o.status) == 'CANCELLED']
            cancelled_count = len(cancelled_orders)
            cancelled_value = sum(float(order.total_amount or 0) for order in cancelled_orders)
            
            # Devoluções (mediations/claims) - inicializar antes de usar
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
            
            # Receita total = Vendas brutas - Cancelamentos - Devoluções (como no Mercado Livre)
            total_revenue = vendas_brutas - cancelled_value - returns_value
            avg_ticket = total_revenue / total_orders if total_orders > 0 else 0
            
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
                'costs': self._calculate_costs_with_taxes(company_id, total_revenue, total_orders, start_date, end_date),
                'billing': self._get_billing_data(company_id, start_date, end_date) or {},
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
    
    def get_top_products(self, company_id: int, user_id: int, ml_account_id: Optional[int] = None, 
                        limit: int = 10, period_days: int = 30, search: Optional[str] = None) -> Dict:
        """Top produtos por quantidade e receita"""
        try:
            # Buscar dados do dashboard para obter análise de vendas
            dashboard_data = self.get_sales_dashboard(
                company_id=company_id,
                user_id=user_id,
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
    
    def _calculate_costs_with_taxes(self, company_id: int, total_revenue: float, total_orders: int, start_date=None, end_date=None) -> Dict:
        """Calcula custos incluindo impostos baseados no cadastro da empresa"""
        try:
            # Buscar dados da empresa
            from app.models.saas_models import Company
            company = self.db.query(Company).filter(Company.id == company_id).first()
            
            if not company:
                logger.warning(f"Empresa {company_id} não encontrada")
                return self._get_default_costs(total_revenue, total_orders)
            
            logger.info(f"🏢 Empresa encontrada: {company.name}")
            logger.info(f"📊 Regime tributário: {company.regime_tributario}")
            logger.info(f"💰 Alíquota Simples: {company.aliquota_simples}")
            logger.info(f"📈 Alíquota IR: {company.aliquota_ir}")
            logger.info(f"📈 Alíquota CSLL: {company.aliquota_csll}")
            logger.info(f"📈 Alíquota PIS: {company.aliquota_pis}")
            logger.info(f"📈 Alíquota COFINS: {company.aliquota_cofins}")
            logger.info(f"📈 Alíquota ICMS: {company.aliquota_icms}")
            logger.info(f"📈 Alíquota ISS: {company.aliquota_iss}")
            
            # Calcular impostos baseado no regime tributário
            taxes_amount = 0.0
            taxes_percent = 0.0
            
            if company.regime_tributario == 'simples_nacional':
                # Simples Nacional - usar alíquota do Simples
                if company.aliquota_simples:
                    taxes_amount = total_revenue * (float(company.aliquota_simples) / 100)
                    taxes_percent = float(company.aliquota_simples)
                else:
                    # Alíquota padrão do Simples Nacional (6%)
                    taxes_amount = total_revenue * 0.06
                    taxes_percent = 6.0
                    
            elif company.regime_tributario == 'lucro_real':
                # Lucro Real - somar todos os impostos
                taxes_amount = self._calculate_lucro_real_taxes(company, total_revenue)
                taxes_percent = (taxes_amount / total_revenue * 100) if total_revenue > 0 else 0
                
            elif company.regime_tributario == 'lucro_presumido':
                # Lucro Presumido - somar impostos do regime
                taxes_amount = self._calculate_lucro_presumido_taxes(company, total_revenue)
                taxes_percent = (taxes_amount / total_revenue * 100) if total_revenue > 0 else 0
            
            # Buscar dados reais de billing do Mercado Livre para o período específico
            from datetime import datetime, timedelta
            
            # Usar as datas passadas como parâmetro, ou padrão de 30 dias
            if start_date is None or end_date is None:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
            
            billing_data = self._get_billing_data(company_id, start_date, end_date)
            
            # Usar dados de billing se disponíveis, senão usar dados dos pedidos
            if billing_data and billing_data.get('total_advertising_cost', 0) > 0:
                # Usar dados reais de billing
                ml_fees = billing_data.get('total_sale_fees', 0)
                shipping_fees = billing_data.get('total_shipping_fees', 0)
                marketing_cost = billing_data.get('total_advertising_cost', 0)
                discounts = 0  # Descontos não estão no billing
                orders = []  # Inicializar orders como lista vazia
                
                logger.info(f"💰 Usando dados reais de billing:")
                logger.info(f"   🎯 Marketing: R$ {marketing_cost:.2f}")
                logger.info(f"   💳 Sale Fees: R$ {ml_fees:.2f}")
                logger.info(f"   🚚 Shipping: R$ {shipping_fees:.2f}")
            else:
                # Fallback: calcular custos reais dos pedidos
                from app.models.saas_models import MLOrder, OrderStatus
                from datetime import datetime, timedelta
                
                # Buscar pedidos do período (usar as datas passadas como parâmetro)
                if start_date is None or end_date is None:
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=30)
                
                orders = self.db.query(MLOrder).filter(
                    and_(
                        MLOrder.company_id == company_id,
                        MLOrder.date_created >= start_date,
                        MLOrder.date_created <= end_date,
                        MLOrder.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED, OrderStatus.SHIPPED, OrderStatus.DELIVERED])
                    )
                ).all()
                
                # Calcular custos reais
                ml_fees = sum(float(order.sale_fees or 0) for order in orders)
                shipping_fees = sum(float(order.shipping_fees or 0) for order in orders)
                discounts = sum(float(order.coupon_amount or 0) for order in orders)
                marketing_cost = sum(float(order.advertising_cost or 0) for order in orders)
                
                # Custos estimados (quando não há dados reais)
                if ml_fees == 0:
                    ml_fees = total_revenue * 0.10  # 10% estimado
                if shipping_fees == 0:
                    shipping_fees = total_revenue * 0.05  # 5% estimado
                if marketing_cost == 0:
                    marketing_cost = total_revenue * 0.03  # 3% estimado
                
                logger.info(f"💰 Usando dados dos pedidos (fallback):")
                logger.info(f"   🎯 Marketing: R$ {marketing_cost:.2f}")
                logger.info(f"   💳 Sale Fees: R$ {ml_fees:.2f}")
                logger.info(f"   🚚 Shipping: R$ {shipping_fees:.2f}")
            
            # Custo dos produtos (estimado)
            product_cost = total_revenue * 0.40  # 40% estimado
            other_costs = 0.0  # Outros custos
            
            # Total de custos
            total_costs = ml_fees + product_cost + taxes_amount + other_costs + marketing_cost
            total_costs_percent = (total_costs / total_revenue * 100) if total_revenue > 0 else 0
            
            # Calcular detalhamento dos impostos
            taxes_breakdown = self._calculate_taxes_breakdown(company, total_revenue)
            
            # Calcular percentuais
            ml_fees_percent = (ml_fees / total_revenue * 100) if total_revenue > 0 else 0
            shipping_fees_percent = (shipping_fees / total_revenue * 100) if total_revenue > 0 else 0
            discounts_percent = (discounts / total_revenue * 100) if total_revenue > 0 else 0
            product_cost_percent = (product_cost / total_revenue * 100) if total_revenue > 0 else 0
            other_costs_percent = (other_costs / total_revenue * 100) if total_revenue > 0 else 0
            marketing_percent = (marketing_cost / total_revenue * 100) if total_revenue > 0 else 0
            
            return {
                'ml_fees': ml_fees,
                'ml_fees_percent': ml_fees_percent,
                'shipping_fees': shipping_fees,
                'shipping_fees_percent': shipping_fees_percent,
                'discounts': discounts,
                'discounts_percent': discounts_percent,
                'product_cost': product_cost,
                'product_cost_percent': product_cost_percent,
                'taxes': taxes_amount,
                'taxes_percent': taxes_percent,
                'taxes_breakdown': taxes_breakdown,
                'other_costs': other_costs,
                'other_costs_percent': other_costs_percent,
                'other_costs_per_unit': other_costs / len(orders) if orders else 0,
                'marketing_cost': marketing_cost,
                'marketing_percent': marketing_percent,
                'marketing_per_unit': 0.0,
                'total_costs': total_costs,
                'total_costs_percent': total_costs_percent
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular custos com impostos: {e}")
            return self._get_default_costs(total_revenue, total_orders)
    
    def _calculate_lucro_real_taxes(self, company, total_revenue: float) -> float:
        """Calcula impostos para regime de Lucro Real"""
        taxes = 0.0
        
        # IR (Imposto de Renda)
        if company.aliquota_ir_real:
            taxes += total_revenue * (float(company.aliquota_ir_real) / 100)
        elif company.aliquota_ir:
            taxes += total_revenue * (float(company.aliquota_ir) / 100)
            
        # CSLL (Contribuição Social sobre o Lucro Líquido)
        if company.aliquota_csll_real:
            taxes += total_revenue * (float(company.aliquota_csll_real) / 100)
        elif company.aliquota_csll:
            taxes += total_revenue * (float(company.aliquota_csll) / 100)
            
        # PIS
        if company.aliquota_pis_real:
            taxes += total_revenue * (float(company.aliquota_pis_real) / 100)
        elif company.aliquota_pis:
            taxes += total_revenue * (float(company.aliquota_pis) / 100)
            
        # COFINS
        if company.aliquota_cofins_real:
            taxes += total_revenue * (float(company.aliquota_cofins_real) / 100)
        elif company.aliquota_cofins:
            taxes += total_revenue * (float(company.aliquota_cofins) / 100)
            
        # ICMS
        if company.aliquota_icms_real:
            taxes += total_revenue * (float(company.aliquota_icms_real) / 100)
        elif company.aliquota_icms:
            taxes += total_revenue * (float(company.aliquota_icms) / 100)
            
        # ISS
        if company.aliquota_iss_real:
            taxes += total_revenue * (float(company.aliquota_iss_real) / 100)
        elif company.aliquota_iss:
            taxes += total_revenue * (float(company.aliquota_iss) / 100)
            
        return taxes
    
    def _calculate_lucro_presumido_taxes(self, company, total_revenue: float) -> float:
        """Calcula impostos para regime de Lucro Presumido"""
        taxes = 0.0
        
        # IR (Imposto de Renda) - padrão 15%
        if company.aliquota_ir:
            taxes += total_revenue * (float(company.aliquota_ir) / 100)
        else:
            taxes += total_revenue * 0.15  # 15% padrão
            
        # CSLL (Contribuição Social) - padrão 9%
        if company.aliquota_csll:
            taxes += total_revenue * (float(company.aliquota_csll) / 100)
        else:
            taxes += total_revenue * 0.09  # 9% padrão
            
        # PIS - padrão 1.65%
        if company.aliquota_pis:
            taxes += total_revenue * (float(company.aliquota_pis) / 100)
        else:
            taxes += total_revenue * 0.0165  # 1.65% padrão
            
        # COFINS - padrão 7.6%
        if company.aliquota_cofins:
            taxes += total_revenue * (float(company.aliquota_cofins) / 100)
        else:
            taxes += total_revenue * 0.076  # 7.6% padrão
            
        # ICMS - padrão 18%
        if company.aliquota_icms:
            taxes += total_revenue * (float(company.aliquota_icms) / 100)
        else:
            taxes += total_revenue * 0.18  # 18% padrão
            
        # ISS - padrão 5%
        if company.aliquota_iss:
            taxes += total_revenue * (float(company.aliquota_iss) / 100)
        else:
            taxes += total_revenue * 0.05  # 5% padrão
            
        return taxes
    
    def _calculate_taxes_breakdown(self, company, total_revenue: float) -> Dict:
        """Calcula o detalhamento de cada imposto"""
        breakdown = {}
        
        if company.regime_tributario == 'simples_nacional':
            # Simples Nacional - apenas um imposto
            if company.aliquota_simples:
                aliquota = float(company.aliquota_simples)
                valor = total_revenue * (aliquota / 100)
                breakdown['simples_nacional'] = {
                    'name': 'Simples Nacional',
                    'aliquota': aliquota,
                    'valor': valor,
                    'percent': aliquota
                }
        elif company.regime_tributario == 'lucro_real':
            # Lucro Real - todos os impostos
            breakdown = self._get_lucro_real_breakdown(company, total_revenue)
        elif company.regime_tributario == 'lucro_presumido':
            # Lucro Presumido - impostos do regime
            breakdown = self._get_lucro_presumido_breakdown(company, total_revenue)
        
        return breakdown
    
    def _get_lucro_real_breakdown(self, company, total_revenue: float) -> Dict:
        """Detalhamento para Lucro Real"""
        breakdown = {}
        
        # IR (Imposto de Renda)
        if company.aliquota_ir_real:
            aliquota = float(company.aliquota_ir_real)
            valor = total_revenue * (aliquota / 100)
            breakdown['ir'] = {
                'name': 'Imposto de Renda (IR)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
        elif company.aliquota_ir:
            aliquota = float(company.aliquota_ir)
            valor = total_revenue * (aliquota / 100)
            breakdown['ir'] = {
                'name': 'Imposto de Renda (IR)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
            
        # CSLL
        if company.aliquota_csll_real:
            aliquota = float(company.aliquota_csll_real)
            valor = total_revenue * (aliquota / 100)
            breakdown['csll'] = {
                'name': 'Contribuição Social (CSLL)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
        elif company.aliquota_csll:
            aliquota = float(company.aliquota_csll)
            valor = total_revenue * (aliquota / 100)
            breakdown['csll'] = {
                'name': 'Contribuição Social (CSLL)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
            
        # PIS
        if company.aliquota_pis_real:
            aliquota = float(company.aliquota_pis_real)
            valor = total_revenue * (aliquota / 100)
            breakdown['pis'] = {
                'name': 'Programa de Integração Social (PIS)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
        elif company.aliquota_pis:
            aliquota = float(company.aliquota_pis)
            valor = total_revenue * (aliquota / 100)
            breakdown['pis'] = {
                'name': 'Programa de Integração Social (PIS)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
            
        # COFINS
        if company.aliquota_cofins_real:
            aliquota = float(company.aliquota_cofins_real)
            valor = total_revenue * (aliquota / 100)
            breakdown['cofins'] = {
                'name': 'Contribuição para Financiamento (COFINS)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
        elif company.aliquota_cofins:
            aliquota = float(company.aliquota_cofins)
            valor = total_revenue * (aliquota / 100)
            breakdown['cofins'] = {
                'name': 'Contribuição para Financiamento (COFINS)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
            
        # ICMS
        if company.aliquota_icms_real:
            aliquota = float(company.aliquota_icms_real)
            valor = total_revenue * (aliquota / 100)
            breakdown['icms'] = {
                'name': 'Imposto sobre Circulação (ICMS)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
        elif company.aliquota_icms:
            aliquota = float(company.aliquota_icms)
            valor = total_revenue * (aliquota / 100)
            breakdown['icms'] = {
                'name': 'Imposto sobre Circulação (ICMS)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
            
        # ISS
        if company.aliquota_iss_real:
            aliquota = float(company.aliquota_iss_real)
            valor = total_revenue * (aliquota / 100)
            breakdown['iss'] = {
                'name': 'Imposto sobre Serviços (ISS)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
        elif company.aliquota_iss:
            aliquota = float(company.aliquota_iss)
            valor = total_revenue * (aliquota / 100)
            breakdown['iss'] = {
                'name': 'Imposto sobre Serviços (ISS)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
            
        return breakdown
    
    def _get_lucro_presumido_breakdown(self, company, total_revenue: float) -> Dict:
        """Detalhamento para Lucro Presumido"""
        breakdown = {}
        
        # IR (Imposto de Renda)
        if company.aliquota_ir:
            aliquota = float(company.aliquota_ir)
            valor = total_revenue * (aliquota / 100)
            breakdown['ir'] = {
                'name': 'Imposto de Renda (IR)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
        else:
            aliquota = 15.0  # Padrão
            valor = total_revenue * 0.15
            breakdown['ir'] = {
                'name': 'Imposto de Renda (IR)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
            
        # CSLL
        if company.aliquota_csll:
            aliquota = float(company.aliquota_csll)
            valor = total_revenue * (aliquota / 100)
            breakdown['csll'] = {
                'name': 'Contribuição Social (CSLL)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
        else:
            aliquota = 9.0  # Padrão
            valor = total_revenue * 0.09
            breakdown['csll'] = {
                'name': 'Contribuição Social (CSLL)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
            
        # PIS
        if company.aliquota_pis:
            aliquota = float(company.aliquota_pis)
            valor = total_revenue * (aliquota / 100)
            breakdown['pis'] = {
                'name': 'Programa de Integração Social (PIS)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
        else:
            aliquota = 1.65  # Padrão
            valor = total_revenue * 0.0165
            breakdown['pis'] = {
                'name': 'Programa de Integração Social (PIS)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
            
        # COFINS
        if company.aliquota_cofins:
            aliquota = float(company.aliquota_cofins)
            valor = total_revenue * (aliquota / 100)
            breakdown['cofins'] = {
                'name': 'Contribuição para Financiamento (COFINS)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
        else:
            aliquota = 7.6  # Padrão
            valor = total_revenue * 0.076
            breakdown['cofins'] = {
                'name': 'Contribuição para Financiamento (COFINS)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
            
        # ICMS
        if company.aliquota_icms:
            aliquota = float(company.aliquota_icms)
            valor = total_revenue * (aliquota / 100)
            breakdown['icms'] = {
                'name': 'Imposto sobre Circulação (ICMS)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
        else:
            aliquota = 18.0  # Padrão
            valor = total_revenue * 0.18
            breakdown['icms'] = {
                'name': 'Imposto sobre Circulação (ICMS)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
            
        # ISS
        if company.aliquota_iss:
            aliquota = float(company.aliquota_iss)
            valor = total_revenue * (aliquota / 100)
            breakdown['iss'] = {
                'name': 'Imposto sobre Serviços (ISS)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
        else:
            aliquota = 5.0  # Padrão
            valor = total_revenue * 0.05
            breakdown['iss'] = {
                'name': 'Imposto sobre Serviços (ISS)',
                'aliquota': aliquota,
                'valor': valor,
                'percent': aliquota
            }
            
        return breakdown
    
    def _get_default_costs(self, total_revenue: float, total_orders: int) -> Dict:
        """Retorna custos padrão quando não há dados da empresa"""
        return {
            'ml_fees': total_revenue * 0.10,
            'ml_fees_percent': 10.0,
            'shipping_fees': 0.0,
            'shipping_fees_percent': 0.0,
            'discounts': 0.0,
            'discounts_percent': 0.0,
            'product_cost': total_revenue * 0.40,
            'product_cost_percent': 40.0,
            'taxes': 0.0,
            'taxes_percent': 0.0,
            'other_costs': 0.0,
            'other_costs_percent': 0.0,
            'other_costs_per_unit': 0.0,
            'marketing_cost': 0.0,
            'marketing_percent': 0.0,
            'marketing_per_unit': 0.0,
            'total_costs': total_revenue * 0.50,
            'total_costs_percent': 50.0
        }
    
    def _get_billing_data(self, company_id: int, start_date, end_date) -> Dict:
        """Busca dados reais de billing do Mercado Livre"""
        try:
            from sqlalchemy import text
            
            # Buscar dados de billing que se sobrepõem ao período
            # CORREÇÃO: Priorizar período mais específico para cada mês
            result = self.db.execute(text("""
                WITH period_candidates AS (
                    SELECT 
                        id,
                        period_from,
                        period_to,
                        advertising_cost,
                        sale_fees,
                        shipping_fees,
                        -- Calcular sobreposição em dias
                        GREATEST(0, EXTRACT(EPOCH FROM (LEAST(period_to, :end_date) - GREATEST(period_from, :start_date)))) / 86400 as overlap_days,
                        -- Calcular duração total do período
                        EXTRACT(EPOCH FROM (period_to - period_from)) / 86400 as total_days,
                        -- Priorizar períodos que terminam no mês solicitado
                        CASE 
                            WHEN EXTRACT(MONTH FROM period_to) = EXTRACT(MONTH FROM :end_date) 
                                 AND EXTRACT(YEAR FROM period_to) = EXTRACT(YEAR FROM :end_date)
                            THEN 1 ELSE 0 
                        END as ends_in_target_month,
                        -- Priorizar períodos que começam no mês solicitado
                        CASE 
                            WHEN EXTRACT(MONTH FROM period_from) = EXTRACT(MONTH FROM :start_date) 
                                 AND EXTRACT(YEAR FROM period_from) = EXTRACT(YEAR FROM :start_date)
                            THEN 1 ELSE 0 
                        END as starts_in_target_month
                    FROM ml_billing_periods 
                    WHERE company_id = :company_id
                    AND period_from <= :end_date 
                    AND period_to >= :start_date
                ),
                ranked_periods AS (
                    SELECT 
                        *,
                        -- Calcular score de prioridade
                        (ends_in_target_month * 3 + starts_in_target_month * 2 + 
                         (overlap_days / NULLIF(total_days, 0)) * 1) as priority_score,
                        ROW_NUMBER() OVER (ORDER BY 
                            ends_in_target_month DESC,
                            starts_in_target_month DESC,
                            overlap_days DESC,
                            total_days ASC
                        ) as rn
                    FROM period_candidates
                )
                SELECT 
                    SUM(advertising_cost) as total_advertising_cost,
                    SUM(sale_fees) as total_sale_fees,
                    SUM(shipping_fees) as total_shipping_fees,
                    COUNT(*) as periods_count
                FROM ranked_periods 
                WHERE rn = 1  -- Apenas o período com maior prioridade
            """), {
                "company_id": company_id,
                "start_date": start_date,
                "end_date": end_date
            })
            
            billing_data = result.fetchone()
            
            if billing_data and billing_data.periods_count > 0:
                return {
                    'total_advertising_cost': float(billing_data.total_advertising_cost or 0),
                    'total_sale_fees': float(billing_data.total_sale_fees or 0),
                    'total_shipping_fees': float(billing_data.total_shipping_fees or 0),
                    'periods_count': billing_data.periods_count
                }
            else:
                logger.info(f"📊 Nenhum dado de billing encontrado para empresa {company_id} no período")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao buscar dados de billing: {e}")
            return None