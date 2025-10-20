"""
Controller para Analytics & Performance
"""
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, text
from datetime import datetime, timedelta

from app.models.saas_models import MLProduct, MLOrder, MLAccount, MLProductStatus, OrderStatus
from app.services.ml_claims_service import MLClaimsService
from app.services.ml_visits_service import MLVisitsService

logger = logging.getLogger(__name__)

# Cache removido - focando em otimização SQL

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
            logger.info(f"🚀 ANALYTICS CONTROLLER CHAMADO - company_id={company_id}, period_days={period_days}")
            
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
            
            # Query otimizada de pedidos CONFIRMADOS com agregações
            # Usar consulta SQL otimizada com índices criados
            orders_sql = text("""
                SELECT 
                    ml_order_id,
                    total_amount,
                    sale_fees,
                    shipping_cost,
                    advertising_cost,
                    coupon_amount,
                    order_items,
                    date_closed,
                    status
                FROM ml_orders
                WHERE company_id = :company_id
                  AND date_closed >= :date_from
                  AND date_closed IS NOT NULL
            """)
            
            params = {
                "company_id": company_id,
                "date_from": date_from
            }
            
            # Para períodos com data final definida, adicionar filtro
            if 'date_to' in locals() and date_to:
                orders_sql = text("""
                    SELECT 
                        ml_order_id,
                        total_amount,
                        sale_fees,
                        shipping_cost,
                        advertising_cost,
                        coupon_amount,
                        order_items,
                        date_closed,
                        status
                    FROM ml_orders
                    WHERE company_id = :company_id
                      AND date_closed >= :date_from
                      AND date_closed <= :date_to
                      AND date_closed IS NOT NULL
                """)
                params["date_to"] = date_to
            
            # Filtrar por conta ML
            if ml_account_id:
                logger.info(f"🔍 Filtrando por conta ML: {ml_account_id}")
                orders_sql = text("""
                    SELECT 
                        ml_order_id,
                        total_amount,
                        sale_fees,
                        shipping_cost,
                        advertising_cost,
                        coupon_amount,
                        order_items,
                        date_closed,
                        status
                    FROM ml_orders
                    WHERE company_id = :company_id
                      AND ml_account_id = :ml_account_id
                      AND date_closed >= :date_from
                      AND date_closed IS NOT NULL
                """)
                params["ml_account_id"] = ml_account_id
                
                if 'date_to' in locals() and date_to:
                    orders_sql = text("""
                        SELECT 
                            ml_order_id,
                            total_amount,
                            sale_fees,
                            shipping_cost,
                            advertising_cost,
                            coupon_amount,
                            order_items,
                            date_closed,
                            status
                        FROM ml_orders
                        WHERE company_id = :company_id
                          AND ml_account_id = :ml_account_id
                          AND date_closed >= :date_from
                          AND date_closed <= :date_to
                          AND date_closed IS NOT NULL
                    """)
            
            # Executar consulta otimizada com LIMIT para performance
            orders_sql = text(str(orders_sql) + " ORDER BY date_closed DESC LIMIT 1000")
            orders_result = self.db.execute(orders_sql, params).fetchall()
            orders = [dict(row._mapping) for row in orders_result]
            logger.info(f"📦 Total de VENDAS CONFIRMADAS encontradas: {len(orders)} (limitado a 1000 para performance)")
            
            # Buscar VENDAS canceladas
            # ML: "Vendas do período selecionado que DEPOIS foram canceladas"
            # CRITÉRIO AJUSTADO: Vendas que foram ENTREGUES e depois CANCELADAS
            # (baseado na análise: todos os cancelamentos têm "not_paid", então não podemos filtrar por "paid")
            # O ML parece contar apenas cancelamentos que tiveram alguma ação antes (delivered)
            
            # Query otimizada para pedidos cancelados com agregação
            cancelled_sql = text("""
                SELECT 
                    COUNT(*) as count,
                    COALESCE(SUM(total_amount), 0) as total_value
                FROM ml_orders
                WHERE company_id = :company_id
                  AND date_closed >= :date_from
                  AND status = 'CANCELLED'
                  AND tags::jsonb @> '["delivered"]'::jsonb
                  AND NOT (tags::jsonb @> '["test_order"]'::jsonb)
            """)
            
            cancelled_params = {
                "company_id": company_id,
                "date_from": date_from
            }
            
            if ml_account_id:
                cancelled_sql = text("""
                    SELECT 
                        COUNT(*) as count,
                        COALESCE(SUM(total_amount), 0) as total_value
                    FROM ml_orders
                    WHERE company_id = :company_id
                      AND ml_account_id = :ml_account_id
                      AND date_closed >= :date_from
                      AND status = 'CANCELLED'
                      AND tags::jsonb @> '["delivered"]'::jsonb
                      AND NOT (tags::jsonb @> '["test_order"]'::jsonb)
                """)
                cancelled_params["ml_account_id"] = ml_account_id
            
            cancelled_result = self.db.execute(cancelled_sql, cancelled_params).fetchone()
            cancelled_count = cancelled_result.count if cancelled_result else 0
            cancelled_value = float(cancelled_result.total_value) if cancelled_result else 0.0
            
            logger.info(f"❌ VENDAS canceladas (confirmadas no período e depois canceladas): {cancelled_count} (R$ {cancelled_value:.2f})")
            
            # Query otimizada para pedidos devolvidos com agregação
            refunded_sql = text("""
                SELECT 
                    COUNT(*) as count,
                    COALESCE(SUM(total_amount), 0) as total_value
                FROM ml_orders
                WHERE company_id = :company_id
                  AND date_closed >= :date_from
                  AND status = 'REFUNDED'
            """)
            
            refunded_params = {
                "company_id": company_id,
                "date_from": date_from
            }
            
            if ml_account_id:
                refunded_sql = text("""
                    SELECT 
                        COUNT(*) as count,
                        COALESCE(SUM(total_amount), 0) as total_value
                    FROM ml_orders
                    WHERE company_id = :company_id
                      AND ml_account_id = :ml_account_id
                      AND date_closed >= :date_from
                      AND status = 'REFUNDED'
                """)
                refunded_params["ml_account_id"] = ml_account_id
            
            refunded_result = self.db.execute(refunded_sql, refunded_params).fetchone()
            refunded_count_db = refunded_result.count if refunded_result else 0
            refunded_value_db = float(refunded_result.total_value) if refunded_result else 0.0
            
            logger.info(f"💸 VENDAS devolvidas (confirmadas no período e depois devolvidas): {refunded_count_db} (R$ {refunded_value_db:.2f})")
            
            # Buscar dados de devoluções via API e visitas de todas as contas da empresa
            returns_count_api = 0
            returns_value_api = 0
            total_visits = 0
            
            try:
                # Query otimizada para buscar contas ML
                accounts_sql = text("""
                    SELECT id, ml_user_id, nickname
                    FROM ml_accounts
                    WHERE company_id = :company_id
                """)
                
                accounts_params = {"company_id": company_id}
                
                if ml_account_id:
                    accounts_sql = text("""
                        SELECT id, ml_user_id, nickname
                        FROM ml_accounts
                        WHERE company_id = :company_id AND id = :ml_account_id
                    """)
                    accounts_params["ml_account_id"] = ml_account_id
                
                accounts_result = self.db.execute(accounts_sql, accounts_params).fetchall()
                ml_accounts = [dict(row._mapping) for row in accounts_result]
                
                # Importar TokenManager para renovação automática
                from app.services.token_manager import TokenManager
                from app.models.saas_models import User
                
                # Query otimizada para buscar usuário ativo da empresa
                user_sql = text("""
                    SELECT id, company_id, email, first_name, last_name
                    FROM users
                    WHERE company_id = :company_id AND is_active = true
                    LIMIT 1
                """)
                
                user_result = self.db.execute(user_sql, {"company_id": company_id}).fetchone()
                
                if not user_result:
                    logger.warning(f"⚠️ Usuário não encontrado para company_id={company_id}")
                    user = None
                else:
                    user = dict(user_result._mapping)
                
                for ml_account in ml_accounts:
                    if not user:
                        continue
                    
                    # Usar TokenManager para obter token válido (renova automaticamente se expirado)
                    token_manager = TokenManager(self.db)
                    valid_token = token_manager.get_valid_token(user['id'])
                    
                    logger.info(f"🔍 DEBUG - Token obtido: {valid_token[:20] if valid_token else 'None'}...")
                    
                    if not valid_token:
                        logger.warning(f"⚠️ Token inválido/expirado para conta {ml_account['nickname']}")
                        continue
                    
                    # Buscar devoluções via API (Claims) com token válido
                    claims_service = MLClaimsService()
                    returns_data = claims_service.get_returns_metrics(
                        valid_token,  # ✅ Token renovado automaticamente
                        date_from, 
                        datetime.utcnow(),
                        ml_account['ml_user_id']
                    )
                    returns_count_api += returns_data.get('returns_count', 0)
                    returns_value_api += returns_data.get('returns_value', 0)
                    
                    # Buscar visitas com token válido
                    visits_service = MLVisitsService()
                    
                    logger.info(f"🔍 DEBUG - ml_user_id: {ml_account['ml_user_id']}, token: {valid_token[:20]}...")
                    
                    # Buscar visitas diretamente (removendo verificação de permissões por enquanto)
                    visits_data = visits_service.get_user_visits(
                        ml_account['ml_user_id'], 
                        valid_token,
                        date_from, 
                        datetime.utcnow()
                    )
                    account_visits = visits_data.get('total_visits', 0)
                    total_visits += account_visits
                    logger.info(f"👁️  Visitas da conta {ml_account['nickname']}: {account_visits}")
                    
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
            
            # Query otimizada para agregações de pedidos
            aggregation_sql = text("""
                SELECT 
                    COUNT(*) as total_orders,
                    COALESCE(SUM(total_amount), 0) as total_revenue,
                    COALESCE(SUM(sale_fees), 0) as ml_fees_total,
                    COALESCE(SUM(shipping_cost), 0) as shipping_fees_total,
                    COALESCE(SUM(advertising_cost), 0) as marketing_cost_total,
                    COALESCE(SUM(coupon_amount), 0) as discounts_total
                FROM ml_orders
                WHERE company_id = :company_id
                  AND date_closed >= :date_from
                  AND date_closed IS NOT NULL
            """)
            
            agg_params = {
                "company_id": company_id,
                "date_from": date_from
            }
            
            if 'date_to' in locals() and date_to:
                aggregation_sql = text("""
                    SELECT 
                        COUNT(*) as total_orders,
                        COALESCE(SUM(total_amount), 0) as total_revenue,
                        COALESCE(SUM(sale_fees), 0) as ml_fees_total,
                        COALESCE(SUM(shipping_cost), 0) as shipping_fees_total,
                        COALESCE(SUM(advertising_cost), 0) as marketing_cost_total,
                        COALESCE(SUM(coupon_amount), 0) as discounts_total
                    FROM ml_orders
                    WHERE company_id = :company_id
                      AND date_closed >= :date_from
                      AND date_closed <= :date_to
                      AND date_closed IS NOT NULL
                """)
                agg_params["date_to"] = date_to
            
            if ml_account_id:
                aggregation_sql = text("""
                    SELECT 
                        COUNT(*) as total_orders,
                        COALESCE(SUM(total_amount), 0) as total_revenue,
                        COALESCE(SUM(sale_fees), 0) as ml_fees_total,
                        COALESCE(SUM(shipping_cost), 0) as shipping_fees_total,
                        COALESCE(SUM(advertising_cost), 0) as marketing_cost_total,
                        COALESCE(SUM(coupon_amount), 0) as discounts_total
                    FROM ml_orders
                    WHERE company_id = :company_id
                      AND ml_account_id = :ml_account_id
                      AND date_closed >= :date_from
                      AND date_closed IS NOT NULL
                """)
                agg_params["ml_account_id"] = ml_account_id
                
                if 'date_to' in locals() and date_to:
                    aggregation_sql = text("""
                        SELECT 
                            COUNT(*) as total_orders,
                            COALESCE(SUM(total_amount), 0) as total_revenue,
                            COALESCE(SUM(sale_fees), 0) as ml_fees_total,
                            COALESCE(SUM(shipping_cost), 0) as shipping_fees_total,
                            COALESCE(SUM(advertising_cost), 0) as marketing_cost_total,
                            COALESCE(SUM(coupon_amount), 0) as discounts_total
                        FROM ml_orders
                        WHERE company_id = :company_id
                          AND ml_account_id = :ml_account_id
                          AND date_closed >= :date_from
                          AND date_closed <= :date_to
                          AND date_closed IS NOT NULL
                    """)
            
            agg_result = self.db.execute(aggregation_sql, agg_params).fetchone()
            
            total_orders = agg_result.total_orders if agg_result else 0
            total_revenue = float(agg_result.total_revenue) if agg_result else 0.0
            ml_fees_total = float(agg_result.ml_fees_total) if agg_result else 0.0
            shipping_fees_total = float(agg_result.shipping_fees_total) if agg_result else 0.0
            marketing_cost_total = float(agg_result.marketing_cost_total) if agg_result else 0.0
            discounts_total = float(agg_result.discounts_total) if agg_result else 0.0
            
            logger.info(f"📊 Agregações calculadas: {total_orders} pedidos, R$ {total_revenue:.2f} receita")
            
            # Processar itens dos pedidos para produtos (ainda precisa do loop para JSON)
            total_items_sold = 0
            products_sales = {}
            
            logger.info(f"🔄 Processando itens de {total_orders} pedidos...")
            
            for order in orders:
                # Processar itens do pedido
                if order.get('order_items'):
                    for item in order['order_items']:
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
            
            # Query otimizada para buscar produtos
            if products_sales:
                ml_item_ids = list(products_sales.keys())
                
                # Criar placeholders para IN clause
                placeholders = ','.join([f':item_{i}' for i in range(len(ml_item_ids))])
                
                products_sql = text(f"""
                    SELECT id, ml_item_id, title, status, permalink, available_quantity, seller_sku
                    FROM ml_products
                    WHERE company_id = :company_id
                      AND ml_item_id IN ({placeholders})
                """)
                
                products_params = {"company_id": company_id}
                for i, item_id in enumerate(ml_item_ids):
                    products_params[f"item_{i}"] = item_id
                
                products_result = self.db.execute(products_sql, products_params).fetchall()
                products_dict = {row.ml_item_id: dict(row._mapping) for row in products_result}
                
                # Enriquecer dados de vendas com informações dos produtos
                products_data = []
                for ml_item_id, sales_data in products_sales.items():
                    product = products_dict.get(ml_item_id)
                    
                    if product:
                        # Aplicar filtro de busca se fornecido
                        if search:
                            search_term = search.lower()
                            title_match = search_term in product['title'].lower()
                            sku_match = product['seller_sku'] and search_term in product['seller_sku'].lower()
                            id_match = search_term in ml_item_id.lower()
                            
                            if not (title_match or sku_match or id_match):
                                continue  # Pular este produto
                        
                        products_data.append({
                            'id': product['id'],
                            'ml_item_id': ml_item_id,
                            'title': product['title'],
                            'price': sales_data['unit_price'],
                            'available_quantity': product['available_quantity'] or 0,
                            'sold_quantity': sales_data['quantity_sold'],
                            'status': product['status'],
                            'revenue': sales_data['revenue'],
                            'seller_sku': product['seller_sku'],
                            'category_name': product.get('category_name', '')
                        })
            else:
                products_data = []
            
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
                if order.get('date_closed'):
                    # Agrupar por data (dia)
                    date_closed = order['date_closed']
                    if isinstance(date_closed, str):
                        date_closed = datetime.fromisoformat(date_closed.replace('Z', '+00:00'))
                    date_key = date_closed.strftime('%d/%m')
                    
                    if date_key not in timeline_data:
                        timeline_data[date_key] = {
                            'date': date_key,
                            'revenue': 0,
                            'orders': 0,
                            'units': 0
                        }
                    
                    timeline_data[date_key]['revenue'] += float(order.get('total_amount', 0) or 0)
                    timeline_data[date_key]['orders'] += 1
                    
                    # Contar unidades
                    if order.get('order_items'):
                        for item in order['order_items']:
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
            
            # Log para debug
            logger.info(f"🔍 DEBUG - Total de visitas encontradas: {total_visits}")
            
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
            
            return result
            
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
