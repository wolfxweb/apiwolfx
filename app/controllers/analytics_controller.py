"""
Controller para Analytics & Performance
"""
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta

from app.models.saas_models import MLProduct, MLOrder, MLAccount, MLProductStatus, OrderStatus
from app.services.ml_claims_service import MLClaimsService
from app.services.ml_visits_service import MLVisitsService

logger = logging.getLogger(__name__)

class AnalyticsController:
    """Controller para analytics de vendas e performance"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_sales_dashboard(self, company_id: int, ml_account_id: Optional[int] = None, 
                           period_days: int = 30, search: Optional[str] = None, 
                           current_month: bool = False, last_month: bool = False,
                           current_year: bool = False, date_from: Optional[str] = None,
                           date_to: Optional[str] = None) -> Dict:
        """Busca dados do dashboard de vendas baseado em pedidos reais"""
        try:
            logger.info(f"📊 Dashboard Analytics - Filtros: company_id={company_id}, ml_account_id={ml_account_id}, period_days={period_days}, search={search}, current_month={current_month}, last_month={last_month}, current_year={current_year}, date_from={date_from}, date_to={date_to}")
            
            # Calcular data de corte
            if date_from and date_to:
                # Período personalizado
                try:
                    date_from = datetime.strptime(date_from, '%Y-%m-%d')
                    date_to = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
                    logger.info(f"📅 Buscando VENDAS CONFIRMADAS PERÍODO PERSONALIZADO: {date_from} até {date_to}")
                except ValueError as e:
                    logger.error(f"Erro ao parsear datas personalizadas: {e}")
                    return {'success': False, 'error': 'Formato de data inválido'}
            elif current_month:
                # Mês atual: do dia 1 do mês atual até agora
                now = datetime.utcnow()
                date_from = datetime(now.year, now.month, 1)  # Primeiro dia do mês atual
                logger.info(f"📅 Buscando VENDAS CONFIRMADAS do MÊS ATUAL desde: {date_from} (1º dia do mês)")
            elif last_month:
                # Mês anterior: do dia 1 ao último dia do mês anterior
                now = datetime.utcnow()
                # Primeiro dia do mês anterior
                if now.month == 1:
                    last_month_date = datetime(now.year - 1, 12, 1)
                else:
                    last_month_date = datetime(now.year, now.month - 1, 1)
                # Último dia do mês anterior
                if now.month == 1:
                    date_to = datetime(now.year - 1, 12, 31, 23, 59, 59)
                else:
                    # Calcular último dia do mês anterior
                    from calendar import monthrange
                    last_day = monthrange(now.year, now.month - 1)[1]
                    date_to = datetime(now.year, now.month - 1, last_day, 23, 59, 59)
                
                date_from = last_month_date
                logger.info(f"📅 Buscando VENDAS CONFIRMADAS do MÊS ANTERIOR: {date_from} até {date_to}")
            elif current_year:
                # Ano atual: do dia 1 de janeiro até agora
                now = datetime.utcnow()
                date_from = datetime(now.year, 1, 1)  # Primeiro dia do ano atual
                logger.info(f"📅 Buscando VENDAS CONFIRMADAS do ANO ATUAL desde: {date_from} (1º de janeiro)")
            else:
                # IMPORTANTE: ML filtra por date_closed (vendas confirmadas), não date_created
                # ML usa período completo: da meia-noite do dia -N até agora
                # Exemplo: 7 dias = de 05/10 00:00:00 até 12/10 23:59:59
                date_from = (datetime.utcnow().date() - timedelta(days=period_days))
                date_from = datetime.combine(date_from, datetime.min.time())  # Meia-noite do dia -N
                logger.info(f"📅 Buscando VENDAS CONFIRMADAS desde: {date_from} (meia-noite do dia -{period_days})")
            
            # Query base de pedidos CONFIRMADOS (com date_closed preenchido)
            orders_query = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id,
                MLOrder.date_closed >= date_from,  # ✅ Filtro por confirmação, não criação
                MLOrder.date_closed.isnot(None)  # Apenas vendas confirmadas
            )
            
            # Para períodos com data final definida, adicionar filtro
            if 'date_to' in locals() and date_to:
                orders_query = orders_query.filter(MLOrder.date_closed <= date_to)
            
            # Filtrar por conta ML
            if ml_account_id:
                logger.info(f"🔍 Filtrando por conta ML: {ml_account_id}")
                orders_query = orders_query.filter(MLOrder.ml_account_id == ml_account_id)
            
            # Buscar pedidos confirmados/pagos
            orders = orders_query.all()
            logger.info(f"📦 Total de VENDAS CONFIRMADAS encontradas: {len(orders)}")
            
            # Buscar VENDAS canceladas
            # ML: "Vendas do período selecionado que DEPOIS foram canceladas"
            # CRITÉRIO AJUSTADO: Vendas que foram ENTREGUES e depois CANCELADAS
            # (baseado na análise: todos os cancelamentos têm "not_paid", então não podemos filtrar por "paid")
            # O ML parece contar apenas cancelamentos que tiveram alguma ação antes (delivered)
            from sqlalchemy import func, cast, Float, text
            
            # Usar query SQL pura para trabalhar com JSONB
            cancelled_sql = text("""
                SELECT *
                FROM ml_orders
                WHERE company_id = :company_id
                  AND date_closed >= :date_from
                  AND status = 'CANCELLED'
                  AND tags::jsonb @> '["delivered"]'::jsonb
                  AND NOT (tags::jsonb @> '["test_order"]'::jsonb)
                ORDER BY date_closed DESC
            """)
            
            params = {
                "company_id": company_id,
                "date_from": date_from
            }
            
            if ml_account_id:
                cancelled_sql = text("""
                    SELECT *
                    FROM ml_orders
                    WHERE company_id = :company_id
                      AND ml_account_id = :ml_account_id
                      AND date_closed >= :date_from
                      AND status = 'CANCELLED'
                      AND tags::jsonb @> '["delivered"]'::jsonb
                      AND NOT (tags::jsonb @> '["test_order"]'::jsonb)
                    ORDER BY date_closed DESC
                """)
                params["ml_account_id"] = ml_account_id
            
            cancelled_result = self.db.execute(cancelled_sql, params).fetchall()
            cancelled_orders = [dict(row._mapping) for row in cancelled_result]
            cancelled_count = len(cancelled_orders)
            cancelled_value = sum(float(order.get('total_amount', 0) or 0) for order in cancelled_orders)
            
            # DEBUG: Mostrar detalhes dos pedidos cancelados
            if cancelled_orders:
                logger.info(f"🔍 DEBUG - Pedidos cancelados encontrados:")
                for order in cancelled_orders:
                    logger.info(f"   Order ID: {order.get('ml_order_id')}, Value: R$ {order.get('total_amount')}, Tags: {order.get('tags')}")
            
            logger.info(f"❌ VENDAS canceladas (confirmadas no período e depois canceladas): {cancelled_count} (R$ {cancelled_value:.2f})")
            
            # Buscar VENDAS devolvidas  
            # ML: "Vendas do período selecionado em que compradores solicitaram devolução"
            # "do período selecionado" = vendas CONFIRMADAS no período (date_closed no período)
            # "em que compradores solicitaram devolução" = status atual é REFUNDED
            # Devoluções normalmente levam dias/semanas, então sem filtro de tempo mínimo
            refunded_query = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id,
                MLOrder.date_closed >= date_from,  # ✅ Vendas CONFIRMADAS no período
                MLOrder.status == OrderStatus.REFUNDED
            )
            
            if ml_account_id:
                refunded_query = refunded_query.filter(MLOrder.ml_account_id == ml_account_id)
            
            refunded_orders = refunded_query.all()
            refunded_count_db = len(refunded_orders)
            refunded_value_db = sum(float(order.total_amount or 0) for order in refunded_orders)
            
            # DEBUG: Mostrar detalhes dos pedidos devolvidos
            if refunded_orders:
                logger.info(f"🔍 DEBUG - Pedidos devolvidos encontrados:")
                for order in refunded_orders:
                    logger.info(f"   Order ID: {order.ml_order_id}, Created: {order.date_created}, Closed: {order.date_closed}, Status: {order.status}, Value: R$ {order.total_amount}")
            
            logger.info(f"💸 VENDAS devolvidas (confirmadas no período e depois devolvidas): {refunded_count_db} (R$ {refunded_value_db:.2f})")
            
            # Buscar dados de devoluções via API e visitas de todas as contas da empresa
            returns_count_api = 0
            returns_value_api = 0
            total_visits = 0
            
            try:
                # Buscar todas as contas ML da empresa
                accounts_query = self.db.query(MLAccount).filter(MLAccount.company_id == company_id)
                if ml_account_id:
                    accounts_query = accounts_query.filter(MLAccount.id == ml_account_id)
                
                ml_accounts = accounts_query.all()
                
                # Importar TokenManager para renovação automática
                from app.services.token_manager import TokenManager
                from app.models.saas_models import User
                
                for ml_account in ml_accounts:
                    # Buscar usuário da empresa para usar TokenManager
                    user = self.db.query(User).filter(
                        User.company_id == company_id,
                        User.is_active == True
                    ).first()
                    
                    if not user:
                        logger.warning(f"⚠️ Usuário não encontrado para company_id={company_id}")
                        continue
                    
                    # Usar TokenManager para obter token válido (renova automaticamente se expirado)
                    token_manager = TokenManager(self.db)
                    valid_token = token_manager.get_valid_token(user.id)
                    
                    if not valid_token:
                        logger.warning(f"⚠️ Token inválido/expirado para conta {ml_account.nickname}")
                        continue
                    
                    # Buscar devoluções via API (Claims) com token válido
                    claims_service = MLClaimsService()
                    returns_data = claims_service.get_returns_metrics(
                        valid_token,  # ✅ Token renovado automaticamente
                        date_from, 
                        datetime.utcnow(),
                        ml_account.ml_user_id
                    )
                    returns_count_api += returns_data.get('returns_count', 0)
                    returns_value_api += returns_data.get('returns_value', 0)
                    
                    # Buscar visitas com token válido
                    visits_service = MLVisitsService()
                    visits_data = visits_service.get_user_visits(
                        ml_account.ml_user_id, 
                        valid_token,  # ✅ Token renovado automaticamente
                        date_from, 
                        datetime.utcnow()
                    )
                    total_visits += visits_data.get('total_visits', 0)
                    
            except Exception as e:
                logger.warning(f"⚠️  Erro ao buscar dados adicionais (não crítico): {e}")
            
            # Usar APENAS dados da API do Claims
            # O painel ML conta devoluções por CLAIMS criados no período, não por status do pedido
            # Claims podem ser criados para vendas antigas (fora do período)
            # Por isso a API do Claims é a fonte correta
            returns_count = returns_count_api
            returns_value = returns_value_api
            
            logger.info(f"📊 Devoluções finais: {returns_count} devoluções (R$ {returns_value:.2f})")
            logger.info(f"   - Do DB (REFUNDED): {refunded_count_db} (R$ {refunded_value_db:.2f})")
            logger.info(f"   - Da API (Claims): {returns_count_api} (R$ {returns_value_api:.2f})")
            
            # Processar pedidos e itens
            total_revenue = 0  # Receita real dos pedidos
            total_items_sold = 0  # Total de itens vendidos
            total_orders = len(orders)  # Total de pedidos
            
            ml_fees_total = 0  # Taxas ML reais
            shipping_fees_total = 0  # Custos de frete reais
            discounts_total = 0  # Descontos reais
            marketing_cost_total = 0  # Custos de marketing (do banco)
            
            products_sales = {}  # Vendas por produto
            
            logger.info(f"🔄 Processando {total_orders} pedidos...")
            
            for order in orders:
                # Receita do pedido (já está em reais)
                order_revenue = float(order.total_amount or 0)
                total_revenue += order_revenue
                
                # Taxas reais do pedido (já estão em reais)
                ml_fees_total += float(order.sale_fees or 0)
                shipping_fees_total += float(order.shipping_cost or 0)
                
                # Custo de marketing salvo no banco (advertising_cost já em reais)
                if order.advertising_cost:
                    ads_cost = float(order.advertising_cost or 0)
                    marketing_cost_total += ads_cost
                
                # Processar itens do pedido
                if order.order_items:
                    for item in order.order_items:
                        item_id = item.get('item', {}).get('id')
                        quantity = item.get('quantity', 0)
                        unit_price = float(item.get('unit_price', 0))  # Já está em reais
                        
                        total_items_sold += quantity
                        
                        # Agrupar vendas por produto
                        if item_id:
                            if item_id not in products_sales:
                                products_sales[item_id] = {
                                    'ml_item_id': item_id,
                                    'title': item.get('item', {}).get('title', 'Produto sem título'),
                                    'quantity_sold': 0,
                                    'revenue': 0,
                                    'unit_price': unit_price
                                }
                            products_sales[item_id]['quantity_sold'] += quantity
                            products_sales[item_id]['revenue'] += unit_price * quantity
                
                # Processar descontos
                if order.coupon_amount:
                    discounts_total += float(order.coupon_amount or 0)
            
            # Buscar produtos para enriquecer dados e aplicar filtro de busca
            products_data = []
            for ml_item_id, sales_data in products_sales.items():
                product = self.db.query(MLProduct).filter(
                    MLProduct.ml_item_id == ml_item_id,
                    MLProduct.company_id == company_id
                ).first()
                
                if product:
                    # Aplicar filtro de busca se fornecido
                    if search:
                        search_term = search.lower()
                        title_match = search_term in product.title.lower()
                        sku_match = product.seller_sku and search_term in product.seller_sku.lower()
                        id_match = search_term in ml_item_id.lower()
                        
                        if not (title_match or sku_match or id_match):
                            continue  # Pular este produto
                    
                    products_data.append({
                        'id': product.id,
                        'ml_item_id': ml_item_id,
                        'title': product.title,
                        'price': sales_data['unit_price'],
                        'available_quantity': product.available_quantity or 0,
                        'sold_quantity': sales_data['quantity_sold'],
                        'status': product.status.value if product.status else 'unknown',
                        'thumbnail': product.thumbnail,
                        'revenue': sales_data['revenue'],
                        'seller_sku': product.seller_sku,
                        'category_name': product.category_name
                    })
            
            # Ticket médio (receita por pedido)
            avg_ticket = total_revenue / total_orders if total_orders > 0 else 0
            
            # Calcular custos estimados
            # Custo dos produtos (40% da receita - configurável)
            product_cost = total_revenue * 0.40
            
            # Impostos (5% da receita - configurável)
            taxes = total_revenue * 0.05
            
            # Outros custos (R$ 0.30 por unidade vendida)
            other_costs = total_items_sold * 0.30
            
            # Total de custos (usando marketing_cost_total do banco)
            total_costs = ml_fees_total + shipping_fees_total + discounts_total + product_cost + taxes + other_costs + marketing_cost_total
            
            # Lucro líquido
            net_profit = total_revenue - total_costs
            
            # Margem líquida
            net_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
            
            # Lucro médio por pedido
            avg_profit_per_order = net_profit / total_orders if total_orders > 0 else 0
            
            # Calcular percentuais
            ml_fees_percent = (ml_fees_total / total_revenue * 100) if total_revenue > 0 else 0
            shipping_fees_percent = (shipping_fees_total / total_revenue * 100) if total_revenue > 0 else 0
            discounts_percent = (discounts_total / total_revenue * 100) if total_revenue > 0 else 0
            product_cost_percent = (product_cost / total_revenue * 100) if total_revenue > 0 else 0
            taxes_percent = (taxes / total_revenue * 100) if total_revenue > 0 else 0
            other_costs_percent = (other_costs / total_revenue * 100) if total_revenue > 0 else 0
            marketing_percent = (marketing_cost_total / total_revenue * 100) if total_revenue > 0 else 0
            total_costs_percent = (total_costs / total_revenue * 100) if total_revenue > 0 else 0
            
            # Custo por unidade para "outros custos"
            other_costs_per_unit = other_costs / total_items_sold if total_items_sold > 0 else 0
            
            # Marketing diluído (custo total / produtos vendidos)
            marketing_per_unit = marketing_cost_total / total_items_sold if total_items_sold > 0 else 0
            
            logger.info(f"✅ Dashboard processado: {len(products_data)} produtos, {total_orders} pedidos, {total_items_sold} itens, R$ {total_revenue:.2f} receita")
            logger.info(f"💰 Custos - ML: R$ {ml_fees_total:.2f}, Frete: R$ {shipping_fees_total:.2f}, Marketing: R$ {marketing_cost_total:.2f}")
            
            # Gerar timeline de vendas por dia - COMPLETA para todo o período
            timeline_data = {}
            
            # Primeiro, coletar dados dos pedidos
            for order in orders:
                if order.date_closed:
                    # Agrupar por data (dia)
                    date_key = order.date_closed.strftime('%d/%m')
                    
                    if date_key not in timeline_data:
                        timeline_data[date_key] = {
                            'date': date_key,
                            'revenue': 0,
                            'orders': 0,
                            'units': 0
                        }
                    
                    timeline_data[date_key]['revenue'] += float(order.total_amount or 0)
                    timeline_data[date_key]['orders'] += 1
                    
                    # Contar unidades
                    if order.order_items:
                        for item in order.order_items:
                            timeline_data[date_key]['units'] += item.get('quantity', 0)
            
            # Criar timeline completa com todos os dias do período
            # Determinar data final
            if 'date_to' in locals() and date_to:
                end_date = date_to.date()
            else:
                end_date = datetime.utcnow().date()
            
            # Criar entradas para todos os dias do período
            current_date = date_from.date()
            while current_date <= end_date:
                date_key = current_date.strftime('%d/%m')
                
                # Se não existe entrada para este dia, criar com zeros
                if date_key not in timeline_data:
                    timeline_data[date_key] = {
                        'date': date_key,
                        'revenue': 0,
                        'orders': 0,
                        'units': 0
                    }
                
                current_date += timedelta(days=1)
            
            # Converter para lista ordenada por data (usando data real para ordenação)
            def sort_key(item):
                # Converter dd/mm de volta para datetime para ordenação correta
                try:
                    day_month = item['date']
                    day, month = day_month.split('/')
                    
                    # Determinar o ano correto baseado no período
                    current_year = datetime.utcnow().year
                    
                    # Se o mês for maior que o mês atual, provavelmente é do ano anterior
                    if int(month) > datetime.utcnow().month:
                        year = current_year - 1
                    else:
                        year = current_year
                    
                    return datetime.strptime(f"{day}/{month}/{year}", '%d/%m/%Y')
                except Exception as e:
                    logger.warning(f"Erro ao ordenar data {item['date']}: {e}")
                    # Fallback para ordenação alfabética
                    return item['date']
            
            timeline = sorted(timeline_data.values(), key=sort_key)
            
            # Total de produtos únicos anunciados
            from app.models.saas_models import MLProductStatus
            total_products = self.db.query(MLProduct).filter(
                MLProduct.company_id == company_id,
                MLProduct.status.in_([MLProductStatus.ACTIVE, MLProductStatus.PAUSED])
            ).count()
            
            return {
                'success': True,
                'kpis': {
                    'total_revenue': total_revenue,
                    'total_sold': total_items_sold,
                    'total_orders': total_orders,
                    'avg_ticket': avg_ticket,
                    'cancelled_orders': cancelled_count,
                    'cancelled_value': cancelled_value,
                    'returns_count': returns_count,
                    'returns_value': returns_value,
                    'total_visits': total_visits,
                    'total_products': total_products
                },
                'costs': {
                    'ml_fees': ml_fees_total,
                    'ml_fees_percent': ml_fees_percent,
                    'shipping_fees': shipping_fees_total,
                    'shipping_fees_percent': shipping_fees_percent,
                    'discounts': discounts_total,
                    'discounts_percent': discounts_percent,
                    'product_cost': product_cost,
                    'product_cost_percent': product_cost_percent,
                    'taxes': taxes,
                    'taxes_percent': taxes_percent,
                    'other_costs': other_costs,
                    'other_costs_percent': other_costs_percent,
                    'other_costs_per_unit': other_costs_per_unit,
                    'marketing_cost': marketing_cost_total,
                    'marketing_percent': marketing_percent,
                    'marketing_per_unit': marketing_per_unit,
                    'total_costs': total_costs,
                    'total_costs_percent': total_costs_percent
                },
                'profit': {
                    'net_profit': net_profit,
                    'net_margin': net_margin,
                    'avg_profit_per_order': avg_profit_per_order
                },
                'products': products_data,
                'total': len(products_data),
                'timeline': timeline
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar dashboard de vendas: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_top_products(self, company_id: int, ml_account_id: Optional[int] = None, 
                        limit: int = 10, period_days: int = 30, search: Optional[str] = None) -> Dict:
        """Busca top produtos mais vendidos e com maior receita baseado em pedidos reais"""
        try:
            # Calcular data de corte
            from datetime import datetime, timedelta
            date_from = datetime.utcnow() - timedelta(days=period_days)
            
            # Buscar pedidos
            orders_query = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id,
                MLOrder.date_created >= date_from
            )
            
            if ml_account_id:
                orders_query = orders_query.filter(MLOrder.ml_account_id == ml_account_id)
            
            orders = orders_query.all()
            
            # Processar itens dos pedidos
            products_sales = {}
            
            for order in orders:
                if order.order_items:
                    for item in order.order_items:
                        item_id = item.get('item', {}).get('id')
                        quantity = item.get('quantity', 0)
                        unit_price = float(item.get('unit_price', 0))  # Já está em reais
                        
                        if item_id:
                            if item_id not in products_sales:
                                products_sales[item_id] = {
                                    'ml_item_id': item_id,
                                    'title': item.get('item', {}).get('title', ''),
                                    'quantity_sold': 0,
                                    'revenue': 0,
                                    'unit_price': unit_price
                                }
                            products_sales[item_id]['quantity_sold'] += quantity
                            products_sales[item_id]['revenue'] += unit_price * quantity
            
            # Enriquecer com dados dos produtos e aplicar filtro de busca
            enriched_products = []
            for ml_item_id, sales_data in products_sales.items():
                product = self.db.query(MLProduct).filter(
                    MLProduct.ml_item_id == ml_item_id,
                    MLProduct.company_id == company_id
                ).first()
                
                # Aplicar filtro de busca se fornecido
                if search:
                    search_term = search.lower()
                    title = product.title if product else sales_data['title']
                    sku = product.seller_sku if product else ''
                    
                    title_match = search_term in title.lower()
                    sku_match = sku and search_term in sku.lower()
                    id_match = search_term in ml_item_id.lower()
                    
                    if not (title_match or sku_match or id_match):
                        continue  # Pular este produto
                
                enriched_products.append({
                    'id': product.id if product else 0,
                    'ml_item_id': ml_item_id,
                    'title': product.title if product else sales_data['title'],
                    'price': sales_data['unit_price'],
                    'sold_quantity': sales_data['quantity_sold'],
                    'revenue': sales_data['revenue'],
                    'thumbnail': product.thumbnail if product else None
                })
            
            # Top mais vendidos (por quantidade)
            top_sold = sorted(enriched_products, key=lambda x: x['sold_quantity'], reverse=True)[:limit]
            
            # Top maior receita
            top_revenue = sorted(enriched_products, key=lambda x: x['revenue'], reverse=True)[:limit]
            
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
        """Busca resumo de vendas por conta ML baseado em pedidos reais"""
        try:
            # Buscar todas as contas da empresa
            accounts = self.db.query(MLAccount).filter(
                MLAccount.company_id == company_id
            ).all()
            
            accounts_data = []
            
            for account in accounts:
                # Buscar pedidos da conta
                orders = self.db.query(MLOrder).filter(
                    MLOrder.ml_account_id == account.id,
                    MLOrder.company_id == company_id
                ).all()
                
                # Calcular métricas reais dos pedidos
                total_revenue = 0
                total_items_sold = 0
                total_orders = len(orders)
                
                for order in orders:
                    # Receita do pedido (já está em reais)
                    total_revenue += float(order.total_amount or 0)
                    
                    # Contar itens vendidos
                    if order.order_items:
                        for item in order.order_items:
                            total_items_sold += item.get('quantity', 0)
                
                # Ticket médio (receita por pedido)
                avg_ticket = total_revenue / total_orders if total_orders > 0 else 0
                
                # Produtos ativos da conta
                active_products = self.db.query(MLProduct).filter(
                    MLProduct.ml_account_id == account.id,
                    MLProduct.company_id == company_id,
                    MLProduct.status == MLProductStatus.ACTIVE
                ).count()
                
                accounts_data.append({
                    'id': account.id,
                    'nickname': account.nickname,
                    'email': account.email,
                    'total_products': active_products,
                    'active_products': active_products,
                    'total_sold': total_items_sold,
                    'total_revenue': total_revenue,
                    'avg_ticket': avg_ticket,
                    'products_with_sales': total_orders
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
