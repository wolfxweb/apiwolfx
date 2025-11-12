from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
import logging
import requests
from datetime import datetime, timedelta

from app.models.saas_models import MLOrder, MLAccount, MLAccountStatus, OrderStatus
from app.services.token_manager import TokenManager

logger = logging.getLogger(__name__)

class MLOrdersService:
    def __init__(self, db: Session):
        self.db = db
        self.base_url = "https://api.mercadolibre.com"
        self.billing_service = None
    
    def get_orders_by_account(self, ml_account_id: int, company_id: int, 
                             limit: int = 50, offset: int = 0,
                             shipping_status_filter: Optional[str] = None,
                             logistic_filter: Optional[str] = None,
                             date_from: Optional[str] = None,
                             date_to: Optional[str] = None) -> Dict:
        """Busca orders de uma conta ML específica"""
        try:
            logger.info(f"Buscando orders para ml_account_id: {ml_account_id}")
            
            # Verificar se a conta pertence à empresa
            account = self.db.query(MLAccount).filter(
                MLAccount.id == ml_account_id,
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).first()
            
            if not account:
                return {
                    "success": False,
                    "error": "Conta não encontrada ou inativa",
                    "orders": [],
                    "total": 0
                }
            
            # Buscar orders do banco de dados
            query = self.db.query(MLOrder).filter(
                MLOrder.ml_account_id == ml_account_id,
                MLOrder.company_id == company_id
            )
            
            # Aplicar filtros
            if shipping_status_filter:
                from sqlalchemy import func
                query = query.filter(func.lower(MLOrder.shipping_status) == shipping_status_filter.lower())
            
            if logistic_filter:
                logistic_values = [value.strip().lower() for value in logistic_filter.split(',') if value.strip()]
                mapping = {
                    "fulfillment": ["fulfillment", "full"],
                    "full": ["fulfillment", "full"],
                    "xd_drop_off": ["xd_drop_off", "drop_off"],
                    "drop_off": ["xd_drop_off", "drop_off"],
                    "ponto_de_coleta": ["xd_drop_off", "drop_off"],
                    "me2": ["me2"],
                    "me1": ["me1"],
                    "cross_docking": ["cross_docking"],
                    "self_service": ["self_service"]
                }

                expanded_values: List[str] = []
                for value in logistic_values:
                    if value in mapping:
                        expanded_values.extend(mapping[value])
                    else:
                        expanded_values.append(value)

                if expanded_values:
                    query = query.filter(func.lower(MLOrder.shipping_type).in_([val.lower() for val in expanded_values]))
            
            if date_from:
                try:
                    date_from_obj = datetime.fromisoformat(date_from)
                    query = query.filter(MLOrder.date_created >= date_from_obj)
                except ValueError:
                    logger.warning(f"Data inválida: {date_from}")
            
            if date_to:
                try:
                    date_to_obj = datetime.fromisoformat(date_to)
                    query = query.filter(MLOrder.date_created <= date_to_obj)
                except ValueError:
                    logger.warning(f"Data inválida: {date_to}")
            
            # Ordenar por data de criação (mais recentes primeiro)
            query = query.order_by(MLOrder.date_created.desc())
            
            # Paginação
            total = query.count()
            orders = query.offset(offset).limit(limit).all()
            
            # Converter para formato de resposta
            orders_data = []
            for order in orders:
                orders_data.append({
                    "id": order.id,
                    "ml_order_id": order.ml_order_id,
                    "order_id": order.order_id,
                    
                    # Dados do comprador
                    "buyer_nickname": order.buyer_nickname,
                    "buyer_email": order.buyer_email,
                    "buyer_first_name": order.buyer_first_name,
                    "buyer_last_name": order.buyer_last_name,
                    
                    # Dados do vendedor
                    "seller_nickname": order.seller_nickname,
                    
                    # Status e valores
                    "status": order.status.value if order.status else None,
                    "status_detail": order.status_detail,
                    "total_amount": order.total_amount,
                    "paid_amount": order.paid_amount,
                    "currency_id": order.currency_id,
                    
                    # Pagamento
                    "payment_status": order.payment_status,
                    "payment_method_id": order.payment_method_id,
                    "payment_type_id": order.payment_type_id,
                    
                    # Envio
                    "shipping_cost": order.shipping_cost,
                    "shipping_method": order.shipping_method,
                    "shipping_status": order.shipping_status,
                    
                    # Taxas
                    "total_fees": order.total_fees,
                    "sale_fees": order.sale_fees,
                    "shipping_fees": order.shipping_fees,
                    
                    # Publicidade
                    "is_advertising_sale": order.is_advertising_sale,
                    "advertising_cost": order.advertising_cost,
                    
                    # Descontos
                    "coupon_amount": order.coupon_amount,
                    "discounts_applied": order.discounts_applied,
                    
                    # Datas
                    "date_created": order.date_created.isoformat() if order.date_created else None,
                    "date_closed": order.date_closed.isoformat() if order.date_closed else None,
                    "last_updated": order.last_updated.isoformat() if order.last_updated else None,
                    
                    # Dados completos
                    "order_items": order.order_items,
                    "shipping_address": order.shipping_address,
                    "payments": order.payments,
                    "tags": order.tags,
                    "feedback": order.feedback,
                    "context": order.context
                })
            
            return {
                "success": True,
                "orders": orders_data,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar orders: {e}")
            return {
                "success": False,
                "error": str(e),
                "orders": [],
                "total": 0
            }
    
    def sync_today_orders(self, ml_account_id: int, company_id: int, limit: int = 50) -> Dict:
        """Sincroniza apenas pedidos NOVOS que não estão no sistema"""
        try:
            logger.info(f"Sincronizando pedidos novos para ml_account_id: {ml_account_id}")
            
            # Verificar se a conta pertence à empresa
            account = self.db.query(MLAccount).filter(
                MLAccount.id == ml_account_id,
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).first()
            
            if not account:
                return {
                    "success": False,
                    "error": "Conta não encontrada ou inativa"
                }
            
            # Obter token ativo
            access_token = self._get_active_token(ml_account_id, company_id)
            if not access_token:
                return {
                    "success": False,
                    "error": "Token não encontrado ou expirado"
                }
            
            # Buscar pedidos recentes da API (últimas 2 horas para capturar pedidos novos)
            logger.info("Sincronização de pedidos novos - buscando pedidos recentes")
            orders_data = self._fetch_orders_from_api(access_token, account.ml_user_id, limit, days_back=0.1)  # ~2.4 horas
            
            if not orders_data:
                return {
                    "success": True,
                    "message": "Nenhum pedido encontrado para hoje",
                    "saved_count": 0,
                    "updated_count": 0,
                    "total_processed": 0
                }
            
            # Processar orders - salvar apenas os novos
            new_orders_count = 0
            existing_orders_count = 0
            
            for order_data in orders_data:
                try:
                    ml_order_id = order_data.get("id")
                    
                    # Verificar se o pedido já existe no sistema
                    existing_order = self.db.query(MLOrder).filter(
                        MLOrder.ml_order_id == ml_order_id
                    ).first()
                    
                    if existing_order:
                        # Pedido já existe, pular
                        existing_orders_count += 1
                        logger.debug(f"Pedido {ml_order_id} já existe no sistema, pulando...")
                        continue
                    
                    # Pedido é novo, salvar
                    result = self._save_order_to_database(order_data, ml_account_id, company_id)
                    if result:
                        new_orders_count += 1
                        logger.info(f"✅ Novo pedido {ml_order_id} salvo com sucesso")
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao processar pedido {order_data.get('id', 'unknown')}: {e}")
                    continue
            
            self.db.commit()
            
            # Sincronizar custos de publicidade do período atual
            advertising_result = None
            try:
                logger.info("🎯 Sincronizando custos de Product Ads (período atual)...")
                advertising_result = self._sync_advertising_costs_for_account(
                    account_id=ml_account_id,
                    access_token=access_token,
                    periods=1  # Somente o período atual
                )
                if advertising_result and advertising_result.get('total_cost', 0) > 0:
                    logger.info(f"✅ Product Ads sincronizado: R$ {advertising_result.get('total_cost', 0):.2f} em {advertising_result.get('orders_updated', 0)} pedidos")
            except Exception as e:
                logger.warning(f"⚠️  Erro ao sincronizar Product Ads (não crítico): {e}")
            
            return {
                "success": True,
                "message": f"Sincronização de pedidos novos: {new_orders_count} novos pedidos, {existing_orders_count} já existiam",
                "new_orders": new_orders_count,
                "existing_orders": existing_orders_count,
                "total_processed": new_orders_count,
                "advertising_sync": advertising_result
            }
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar pedidos do dia: {e}")
            return {
                "success": False,
                "error": f"Erro na sincronização: {str(e)}"
            }

    def sync_orders_from_api(self, ml_account_id: int, company_id: int, 
                           limit: int = 50, is_full_import: bool = False, days_back: Optional[int] = None, access_token: Optional[str] = None) -> Dict:
        """Sincroniza orders da API do Mercado Libre para o banco"""
        try:
            logger.info(f"🔄 ========== INICIANDO SINCRONIZAÇÃO DE PEDIDOS ==========")
            logger.info(f"🔄 ml_account_id: {ml_account_id}")
            logger.info(f"🔄 company_id: {company_id}")
            
            # Verificar se a conta pertence à empresa
            account = self.db.query(MLAccount).filter(
                MLAccount.id == ml_account_id,
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).first()
            
            if not account:
                logger.error(f"❌ Conta ML {ml_account_id} não encontrada ou não pertence ao company_id {company_id}")
                return {
                    "success": False,
                    "error": "Conta não encontrada ou inativa"
                }
            
            logger.info(f"✅ Conta ML encontrada: {account.nickname} (ml_user_id: {account.ml_user_id})")
            logger.info(f"✅ Seller ID que será usado na API: {account.ml_user_id}")
            
            # Obter token ativo: usar o fornecido (via TokenManager) ou buscar por ml_account_id
            if not access_token:
                access_token = self._get_active_token(ml_account_id, company_id)
            
            if not access_token:
                logger.error(f"❌ Token não encontrado para conta {account.nickname} (ml_account_id: {ml_account_id})")
                return {
                    "success": False,
                    "error": f"Token não encontrado para conta {account.nickname}. Reconecte a conta em 'Contas ML'."
                }
            
            # Testar token antes de sincronizar
            logger.info(f"🔑 Testando token antes de sincronizar...")
            token_test = self._test_token_validity(access_token, account.ml_user_id)
            if not token_test["valid"]:
                logger.error(f"❌ Token inválido para conta {account.nickname}: {token_test.get('error', 'Token expirado')}")
                return {
                    "success": False,
                    "error": f"Token inválido ou expirado para conta {account.nickname}. {token_test.get('error', 'Reconecte a conta em Contas ML.')}"
                }
            
            logger.info(f"✅ Token válido! Iniciando sincronização...")
            
            # Buscar orders da API
            if is_full_import:
                # Importação completa - limitar para evitar sobrecarga
                logger.info("Importação completa - limitando a 50 pedidos para evitar sobrecarga")
                orders_data = self._fetch_orders_from_api(access_token, account.ml_user_id, limit=50, days_back=30)
            elif days_back is not None:
                # Dias personalizados
                logger.info(f"Sincronização - buscando pedidos dos últimos {days_back} dias")
                orders_data = self._fetch_orders_from_api(access_token, account.ml_user_id, limit, days_back=days_back)
            else:
                # Sincronização rápida - apenas os mais recentes (últimos 7 dias)
                logger.info("Sincronização rápida - buscando pedidos dos últimos 7 dias")
                orders_data = self._fetch_orders_from_api(access_token, account.ml_user_id, limit, days_back=7)
            
            # Se retornou lista vazia, pode ser erro de API ou realmente não há pedidos
            if not orders_data:
                # Verificar se houve erro de autenticação testando o token
                logger.warning(f"⚠️ Nenhum pedido retornado para conta {account.nickname} (ml_user_id: {account.ml_user_id})")
                logger.warning(f"⚠️ Isso pode indicar: 1) Não há pedidos no período, 2) Token inválido, 3) Erro 403/401")
                
                # Retornar SUCESSO mas com 0 pedidos (não é um erro crítico)
                return {
                    "success": True,
                    "message": f"Nenhum pedido encontrado no período para conta {account.nickname}",
                    "saved_count": 0,
                    "updated_count": 0
                }
            
            # Salvar orders no banco
            saved_count = 0
            updated_count = 0
            
            # Adicionar delay entre processamentos para evitar sobrecarga
            # import time  # ⚡ OTIMIZAÇÃO: Removido sleep para acelerar sincronização
            
            for i, order_data in enumerate(orders_data):
                # ⚡ OTIMIZADO: Removido delay de 5s a cada 5 pedidos (causava timeout no ngrok)
                # if i > 0 and i % 5 == 0:
                #     logger.info(f"Processando pedido {i+1}/{len(orders_data)} - pausa para evitar sobrecarga")
                #     time.sleep(5)
                try:
                    result = self._save_order_to_database(order_data, ml_account_id, company_id)
                    if result["action"] == "created":
                        saved_count += 1
                    elif result["action"] == "updated":
                        updated_count += 1
                    
                    # ✅ NOVO: Verificar nota fiscal após salvar pedido (se status for PAID/CONFIRMED)
                    order_status = order_data.get("status", "").lower()
                    order_id = order_data.get("id")
                    if order_status in ["paid", "confirmed"] and order_id:
                        try:
                            logger.info(f"🧾 Verificando nota fiscal para pedido {order_id} (status: {order_status})")
                            self._check_invoice_for_order_sync(order_id, company_id, access_token)
                        except Exception as invoice_error:
                            # Não falhar a sincronização se houver erro na verificação de NF
                            logger.warning(f"⚠️ Erro ao verificar NF do pedido {order_id}: {invoice_error}")
                except Exception as e:
                    logger.error(f"Erro ao salvar order {order_data.get('id')}: {e}")
                    continue
            
            self.db.commit()
            
            # Sincronizar custos de publicidade após salvar os pedidos
            # Na sincronização normal: apenas 1 período
            # Na importação completa: últimos 3 períodos
            advertising_result = None
            try:
                periods_to_sync = 3 if is_full_import else 1
                logger.info(f"🎯 Sincronizando custos de Product Ads ({periods_to_sync} período{'s' if periods_to_sync > 1 else ''})...")
                advertising_result = self._sync_advertising_costs_for_account(
                    account_id=ml_account_id,
                    access_token=access_token,
                    periods=periods_to_sync
                )
                if advertising_result and advertising_result.get('total_cost', 0) > 0:
                    logger.info(f"✅ Product Ads sincronizado: R$ {advertising_result.get('total_cost', 0):.2f} em {advertising_result.get('orders_updated', 0)} pedidos")
            except Exception as e:
                logger.warning(f"⚠️  Erro ao sincronizar Product Ads (não crítico): {e}")
            
            return {
                "success": True,
                "message": f"Sincronização concluída: {saved_count} orders criadas, {updated_count} orders atualizadas",
                "saved_count": saved_count,
                "updated_count": updated_count,
                "total_processed": len(orders_data),
                "advertising_sync": advertising_result
            }
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar orders: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _fetch_all_orders_from_api(self, access_token: str, seller_id: str) -> List[Dict]:
        """Busca TODOS os orders da API do Mercado Libre em lotes"""
        try:
            all_orders = []
            offset = 0
            limit = 50  # Máximo permitido pela API
            max_requests = 20  # Limite de segurança para evitar loops infinitos
            
            for request_count in range(max_requests):
                logger.info(f"Buscando orders - offset: {offset}, limit: {limit}")
                
                orders_batch = self._fetch_orders_from_api(access_token, seller_id, limit, offset)
                
                if not orders_batch:
                    logger.info(f"Nenhuma order encontrada no lote {request_count + 1}")
                    break
                
                all_orders.extend(orders_batch)
                logger.info(f"Lote {request_count + 1}: {len(orders_batch)} orders encontradas")
                
                # Se retornou menos que o limite, chegamos ao fim
                if len(orders_batch) < limit:
                    logger.info(f"Fim dos orders atingido - total: {len(all_orders)}")
                    break
                
                offset += limit
                
                # ⚡ OTIMIZADO: Removido pausa entre requisições para acelerar
                # import time
                # time.sleep(0.5)
            
            logger.info(f"Importação completa finalizada: {len(all_orders)} orders totais")
            return all_orders
                
        except Exception as e:
            logger.error(f"Erro ao buscar todos os orders da API: {e}")
            return []

    def _fetch_orders_from_api(self, access_token: str, seller_id: str, limit: int = 50, offset: int = 0, days_back: int = 7) -> List[Dict]:
        """
        Busca orders da API do Mercado Libre com paginação inteligente
        
        IMPORTANTE: Filtra por date_closed (vendas confirmadas), não date_created
        
        Estratégia:
        1. Primeira chamada: descobre o TOTAL de pedidos
        2. Calcula quantas páginas são necessárias
        3. Baixa todos os pedidos em lotes de 50
        """
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Calcular data de início (da meia-noite do dia -N até agora)
            from datetime import datetime, timedelta
            date_to = datetime.utcnow()
            date_from = (date_to.date() - timedelta(days=days_back))
            date_from = datetime.combine(date_from, datetime.min.time())
            
            # Formatar para API (ISO 8601)
            date_from_str = date_from.strftime("%Y-%m-%dT00:00:00.000-00:00")
            date_to_str = date_to.strftime("%Y-%m-%dT23:59:59.000-00:00")
            
            logger.info(f"📅 Buscando vendas CONFIRMADAS de {date_from_str} até {date_to_str}")
            
            # PASSO 1: Primeira chamada para descobrir o TOTAL
            orders_url = f"{self.base_url}/orders/search"
            params_first = {
                "seller": seller_id,
                "order.date_closed.from": date_from_str,  # ✅ Filtro por CONFIRMAÇÃO
                "order.date_closed.to": date_to_str,
                "limit": 1,  # Buscar apenas 1 para saber o total
                "offset": 0,
                "sort": "date_desc"
            }
            
            logger.info(f"🔍 PASSO 1: Consultando quantidade total de pedidos...")
            response_first = requests.get(orders_url, headers=headers, params=params_first, timeout=30)
            
            if response_first.status_code != 200:
                error_text = response_first.text[:500] if hasattr(response_first, 'text') else 'N/A'
                logger.error(f"Erro ao consultar total: {response_first.status_code} - {error_text}")
                
                # Log específico para erro 403 (acesso negado)
                if response_first.status_code == 403:
                    logger.error(f"❌ ERRO 403: Tentando acessar pedidos com seller_id={seller_id}")
                    logger.error(f"❌ Este token pode não pertencer a este seller_id")
                    logger.error(f"❌ Verifique se o ml_user_id da conta ML está correto")
                
                # Log específico para erro 401 (não autorizado)
                elif response_first.status_code == 401:
                    logger.error(f"❌ ERRO 401: Token inválido ou expirado para seller_id={seller_id}")
                    logger.error(f"❌ Necessário reconectar a conta ML")
                
                return []
            
            first_data = response_first.json()
            total_orders = first_data.get("paging", {}).get("total", 0)
            
            logger.info(f"✅ Total de pedidos disponíveis na API: {total_orders}")
            
            if total_orders == 0:
                logger.info(f"✅ API retornou com sucesso, mas não há pedidos no período para seller_id={seller_id}")
                logger.info(f"📅 Período consultado: {date_from_str} até {date_to_str}")
                return []
            
            # PASSO 2: Calcular quantas páginas precisamos buscar
            max_per_page = 50  # Limite máximo da API
            total_pages = (total_orders + max_per_page - 1) // max_per_page  # Arredondar para cima
            
            logger.info(f"📦 PASSO 2: Buscando {total_orders} pedidos em {total_pages} lotes de até {max_per_page}")
            
            # PASSO 3: Buscar todos os pedidos em lotes
            all_orders = []
            
            for page in range(total_pages):
                current_offset = page * max_per_page
                
                params = {
                    "seller": seller_id,
                    "order.date_closed.from": date_from_str,
                    "order.date_closed.to": date_to_str,
                    "limit": max_per_page,
                    "offset": current_offset,
                    "sort": "date_desc"
                }
                
                logger.info(f"   📄 Lote {page + 1}/{total_pages} (offset: {current_offset})...")
                
                response = requests.get(orders_url, headers=headers, params=params, timeout=60)
                
                if response.status_code == 200:
                    data = response.json()
                    orders = data.get("results", [])
                    
                    logger.info(f"      ✅ Baixados {len(orders)} pedidos")
                    all_orders.extend(orders)
                    
                    # Parar se não retornou nada
                    if len(orders) == 0:
                        break
                else:
                    logger.error(f"   ❌ Erro no lote {page + 1}: {response.status_code}")
                    break
                
                # ⚡ OTIMIZADO: Removido pausa entre requisições para acelerar
                # if page < total_pages - 1:  # Não pausar no último
                #     import time
                #     time.sleep(0.5)  # 500ms entre requisições
            
            logger.info(f"✅ CONCLUÍDO: {len(all_orders)}/{total_orders} pedidos baixados com sucesso")
            
            return all_orders
                
        except Exception as e:
            logger.error(f"Erro ao buscar orders da API: {e}")
            return []
    
    def _fetch_complete_order_data(self, order_data: Dict, access_token: str, ml_account_id: Optional[int] = None, company_id: Optional[int] = None) -> Dict:
        """Busca informações completas de uma order incluindo detalhes de envio, descontos e publicidade"""
        try:
            ml_order_id = order_data.get("id")
            complete_data = order_data.copy()
            
            # 1. Buscar detalhes completos da order
            order_details = self._fetch_order_details(ml_order_id, access_token, ml_account_id, company_id)
            if order_details:
                complete_data.update(order_details)
            
            # 2. Buscar detalhes de envio se existir shipping_id
            shipping_id = order_data.get("shipping", {}).get("id")
            if shipping_id:
                shipping_details = self._fetch_shipping_details(shipping_id, access_token, ml_account_id, company_id)
                if shipping_details:
                    complete_data["shipping_details"] = shipping_details
            
            # 3. Buscar descontos aplicados (com tratamento de erro para evitar sobrecarga)
            try:
                discounts = self._fetch_order_discounts(ml_order_id, access_token, ml_account_id, company_id)
                if discounts:
                    complete_data["discounts_applied"] = discounts
            except Exception as e:
                logger.warning(f"Erro ao buscar descontos da order {ml_order_id}: {e}")
                # Continuar sem descontos se houver erro
            
            # 4. Buscar dados de publicidade da API
            advertising_info = self._fetch_advertising_data(ml_order_id, access_token, ml_account_id, company_id)
            if advertising_info:
                complete_data.update(advertising_info)
            
            # 5. Verificar se foi venda por anúncio (Product Ads)
            advertising_sale_info = self._check_advertising_sale(order_data, access_token)
            if advertising_sale_info:
                complete_data.update(advertising_sale_info)
            
            # 6. Verificar se contém produtos de catálogo
            catalog_info = self._check_catalog_products(order_data)
            if catalog_info:
                complete_data.update(catalog_info)
            
            # 7. Calcular taxas e comissões
            fees_info = self._calculate_order_fees(order_data)
            if fees_info:
                complete_data.update(fees_info)
            
            return complete_data
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados completos da order {ml_order_id}: {e}")
            return order_data
    
    def _get_user_id_by_ml_account(self, ml_account_id: int) -> Optional[int]:
        """Obtém user_id a partir do ml_account_id"""
        try:
            from app.models.saas_models import Token
            token = self.db.query(Token).filter(
                Token.ml_account_id == ml_account_id,
                Token.is_active == True
            ).first()
            
            return token.user_id if token else None
            
        except Exception as e:
            logger.error(f"Erro ao obter user_id para ml_account_id {ml_account_id}: {e}")
            return None
    
    def _fetch_order_details(self, ml_order_id: int, access_token: str, ml_account_id: Optional[int] = None, company_id: Optional[int] = None) -> Optional[Dict]:
        """Busca detalhes completos de uma order específica"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            url = f"{self.base_url}/orders/{ml_order_id}"
            
            response = requests.get(url, headers=headers, timeout=30)
            
            # Se receber 401/403, tentar renovar o token e tentar novamente
            if response.status_code in (401, 403) and ml_account_id and company_id:
                logger.info(f"🔄 Token retornou {response.status_code}, tentando renovar token para conta ML {ml_account_id}")
                from app.services.token_manager import TokenManager
                token_manager = TokenManager(self.db)
                token_record = token_manager.get_token_record_for_account(
                    ml_account_id=ml_account_id,
                    company_id=company_id
                )
                if token_record and token_record.access_token:
                    access_token = token_record.access_token
                    headers = {"Authorization": f"Bearer {access_token}"}
                    logger.info(f"✅ Token renovado, tentando novamente")
                    response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Erro ao buscar detalhes da order {ml_order_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes da order: {e}")
            return None
    
    def _fetch_shipping_details(self, shipping_id: str, access_token: str, ml_account_id: Optional[int] = None, company_id: Optional[int] = None) -> Optional[Dict]:
        """Busca detalhes de envio"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            url = f"{self.base_url}/shipments/{shipping_id}"
            
            response = requests.get(url, headers=headers, timeout=30)
            
            # Se receber 401/403, tentar renovar o token e tentar novamente
            if response.status_code in (401, 403) and ml_account_id and company_id:
                logger.info(f"🔄 Token retornou {response.status_code}, tentando renovar token para conta ML {ml_account_id}")
                from app.services.token_manager import TokenManager
                token_manager = TokenManager(self.db)
                token_record = token_manager.get_token_record_for_account(
                    ml_account_id=ml_account_id,
                    company_id=company_id
                )
                if token_record and token_record.access_token:
                    access_token = token_record.access_token
                    headers = {"Authorization": f"Bearer {access_token}"}
                    logger.info(f"✅ Token renovado, tentando novamente")
                    response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Erro ao buscar detalhes do envio {shipping_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes do envio: {e}")
            return None
    
    def _fetch_order_discounts(self, ml_order_id: int, access_token: str, ml_account_id: Optional[int] = None, company_id: Optional[int] = None) -> Optional[Dict]:
        """Busca descontos aplicados em uma order"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            url = f"{self.base_url}/orders/{ml_order_id}/discounts"
            
            # Timeout menor para evitar sobrecarga
            response = requests.get(url, headers=headers, timeout=10)
            
            # Se receber 401/403, tentar renovar o token e tentar novamente
            if response.status_code in (401, 403) and ml_account_id and company_id:
                logger.info(f"🔄 Token retornou {response.status_code}, tentando renovar token para conta ML {ml_account_id}")
                from app.services.token_manager import TokenManager
                token_manager = TokenManager(self.db)
                token_record = token_manager.get_token_record_for_account(
                    ml_account_id=ml_account_id,
                    company_id=company_id
                )
                if token_record and token_record.access_token:
                    access_token = token_record.access_token
                    headers = {"Authorization": f"Bearer {access_token}"}
                    logger.info(f"✅ Token renovado, tentando novamente")
                    response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                # 404 é normal - nem todos os pedidos têm descontos
                return None
            else:
                logger.warning(f"Erro ao buscar descontos da order {ml_order_id}: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout ao buscar descontos da order {ml_order_id}")
            return None
        except Exception as e:
            logger.warning(f"Erro ao buscar descontos da order {ml_order_id}: {e}")
            return None
    
    def _fetch_advertising_data(self, ml_order_id: int, access_token: str, ml_account_id: Optional[int] = None, company_id: Optional[int] = None) -> Optional[Dict]:
        """Busca dados de publicidade de um pedido específico"""
        try:
            logger.info(f"Buscando dados de publicidade para order {ml_order_id}")
            
            # 1. Buscar dados de publicidade dos anunciantes
            advertisers_data = self._fetch_advertisers_data(access_token, ml_account_id, company_id)
            if not advertisers_data:
                logger.warning("Nenhum anunciante encontrado")
                return None
            
            # 2. Para cada anunciante, buscar métricas de campanhas
            advertising_info = {
                "advertising_campaign_id": None,
                "advertising_cost": 0,
                "advertising_metrics": {}
            }
            
            for advertiser in advertisers_data:
                advertiser_id = advertiser.get("advertiser_id")
                site_id = advertiser.get("site_id")
                
                if advertiser_id and site_id:
                    # Buscar métricas de campanhas do anunciante
                    campaign_metrics = self._fetch_campaign_metrics(advertiser_id, site_id, access_token)
                    if campaign_metrics:
                        # Correlacionar com o pedido específico
                        order_advertising_data = self._correlate_order_with_advertising(
                            ml_order_id, campaign_metrics
                        )
                        if order_advertising_data:
                            advertising_info.update(order_advertising_data)
                            break
            
            return advertising_info
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados de publicidade da order {ml_order_id}: {e}")
            return None
    
    def _fetch_advertisers_data(self, access_token: str, ml_account_id: Optional[int] = None, company_id: Optional[int] = None) -> Optional[List[Dict]]:
        """Busca dados dos anunciantes"""
        try:
            url = f"{self.base_url}/advertising/advertisers"
            params = {"product_id": "PADS"}
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Api-Version": "1"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            # Se receber 401/403, tentar renovar o token e tentar novamente
            if response.status_code in (401, 403) and ml_account_id and company_id:
                logger.info(f"🔄 Token retornou {response.status_code}, tentando renovar token para conta ML {ml_account_id}")
                from app.services.token_manager import TokenManager
                token_manager = TokenManager(self.db)
                token_record = token_manager.get_token_record_for_account(
                    ml_account_id=ml_account_id,
                    company_id=company_id
                )
                if token_record and token_record.access_token:
                    access_token = token_record.access_token
                    headers = {
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                        "Api-Version": "1"
                    }
                    logger.info(f"✅ Token renovado, tentando novamente")
                    response = requests.get(url, params=params, headers=headers, timeout=30)
            
            # 404 pode ser normal se não houver anunciantes configurados
            if response.status_code == 404:
                logger.info("Nenhum anunciante encontrado (404)")
                return []
            
            response.raise_for_status()
            
            data = response.json()
            return data.get("advertisers", [])
            
        except Exception as e:
            logger.error(f"Erro ao buscar anunciantes: {e}")
            return None
    
    def _fetch_campaign_metrics(self, advertiser_id: int, site_id: str, access_token: str) -> Optional[Dict]:
        """Busca métricas de campanhas de um anunciante"""
        try:
            # Buscar campanhas do anunciante
            url = f"{self.base_url}/advertising/{site_id}/advertisers/{advertiser_id}/product_ads/campaigns/search"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "api-version": "2"
            }
            
            # Buscar métricas dos últimos 30 dias
            from datetime import datetime, timedelta
            date_to = datetime.now()
            date_from = date_to - timedelta(days=30)
            
            params = {
                "date_from": date_from.strftime("%Y-%m-%d"),
                "date_to": date_to.strftime("%Y-%m-%d"),
                "metrics": "clicks,prints,cost,cpc,acos,direct_amount,indirect_amount,total_amount"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return data
            
        except Exception as e:
            logger.error(f"Erro ao buscar métricas de campanhas: {e}")
            return None
    
    def _correlate_order_with_advertising(self, ml_order_id: int, campaign_metrics: Dict) -> Optional[Dict]:
        """Correlaciona um pedido específico com dados de publicidade"""
        try:
            # Por enquanto, retornar dados estimados baseados nas métricas
            # TODO: Implementar correlação mais precisa
            
            results = campaign_metrics.get("results", [])
            if not results:
                return None
            
            # Calcular métricas agregadas
            total_cost = sum(campaign.get("metrics", {}).get("cost", 0) for campaign in results)
            total_revenue = sum(campaign.get("metrics", {}).get("total_amount", 0) for campaign in results)
            
            # Estimar custo por pedido (aproximação)
            estimated_cost_per_order = total_cost / max(len(results), 1)
            
            return {
                "advertising_campaign_id": results[0].get("id") if results else None,
                "advertising_cost": estimated_cost_per_order,
                "advertising_metrics": {
                    "total_cost": total_cost,
                    "total_revenue": total_revenue,
                    "roas": total_revenue / max(total_cost, 1),
                    "campaigns_count": len(results)
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao correlacionar pedido com publicidade: {e}")
            return None
    
    def _check_advertising_sale(self, order_data: Dict, access_token: str) -> Optional[Dict]:
        """Verifica se a venda foi através de anúncio (Product Ads)"""
        try:
            advertising_info = {
                "is_advertising_sale": False,
                "advertising_campaign_id": None,
                "advertising_cost": 0,
                "advertising_metrics": {}
            }
            
            # Verificar contexto da venda (flows específicos que indicam publicidade)
            context = order_data.get("context", {})
            flows = context.get("flows", [])
            
            # Flows que podem indicar publicidade real
            advertising_flows = ["cbt", "subscription", "reservation", "advertising", "promoted"]
            for flow in flows:
                if flow in advertising_flows:
                    advertising_info["is_advertising_sale"] = True
                    logger.info(f"Venda identificada como anúncio por flow: {flow}")
                    break
            
            # Verificar se há tags que indicam publicidade
            tags = order_data.get("tags", [])
            advertising_tags = ["advertising", "promoted", "sponsored", "ad", "ads"]
            for tag in tags:
                if tag.lower() in advertising_tags:
                    advertising_info["is_advertising_sale"] = True
                    logger.info(f"Venda identificada como anúncio por tag: {tag}")
                    break
            
            # Verificar se há dados de publicidade nos campos específicos
            if order_data.get("advertising_campaign_id"):
                advertising_info["is_advertising_sale"] = True
                advertising_info["advertising_campaign_id"] = order_data.get("advertising_campaign_id")
                logger.info(f"Venda identificada como anúncio por campaign_id: {order_data.get('advertising_campaign_id')}")
            
            if order_data.get("advertising_cost", 0) > 0:
                advertising_info["is_advertising_sale"] = True
                advertising_info["advertising_cost"] = order_data.get("advertising_cost", 0)
                logger.info(f"Venda identificada como anúncio por cost: {order_data.get('advertising_cost')}")
            
            # Verificar se há dados de publicidade nos order_items
            order_items = order_data.get("order_items", [])
            for item in order_items:
                # Verificar se há dados de publicidade no item
                if item.get("advertising_data"):
                    advertising_info["is_advertising_sale"] = True
                    logger.info(f"Venda identificada como anúncio por advertising_data no item")
                    break
                
                # Verificar se há dados de publicidade no listing_type_id
                listing_type_id = item.get("listing_type_id")
                if listing_type_id in ["gold_pro", "gold_special"]:
                    # Verificar se há dados de publicidade no context do item
                    item_context = item.get("context", {})
                    if item_context.get("advertising") or item_context.get("promoted"):
                        advertising_info["is_advertising_sale"] = True
                        logger.info(f"Venda identificada como anúncio por context do item: {listing_type_id}")
                        break
            
            # Por padrão, considerar como busca orgânica
            # A menos que haja evidência clara de publicidade
            if not advertising_info["is_advertising_sale"]:
                logger.info("Venda identificada como busca orgânica (sem evidência de publicidade)")
            
            return advertising_info
            
        except Exception as e:
            logger.error(f"Erro ao verificar venda por anúncio: {e}")
            return None
    
    def _check_catalog_products(self, order_data: Dict) -> Optional[Dict]:
        """Verifica se o pedido contém produtos de catálogo"""
        try:
            catalog_info = {
                "has_catalog_products": False,
                "catalog_products_count": 0,
                "catalog_products": []
            }
            
            # Verificar itens do pedido
            order_items = order_data.get("order_items", [])
            for item in order_items:
                item_data = item.get("item", {})
                
                # Verificar se é produto de catálogo
                is_catalog = False
                
                # 1. Verificar campo catalog_listing
                if item.get("catalog_listing") is True:
                    is_catalog = True
                    logger.info(f"Produto identificado como catálogo (catalog_listing: true)")
                
                # 2. Verificar se tem user_product_id (indica User Product/Catálogo)
                user_product_id = item_data.get("user_product_id")
                if user_product_id:
                    is_catalog = True
                    logger.info(f"Produto identificado como catálogo (user_product_id: {user_product_id})")
                
                # 3. Verificar listing_type_id específico para catálogo
                listing_type_id = item.get("listing_type_id")
                if listing_type_id in ["gold_pro", "gold_special"] and item.get("catalog_listing") is not False:
                    # Se não foi explicitamente marcado como não-catálogo, pode ser catálogo
                    is_catalog = True
                    logger.info(f"Produto identificado como possível catálogo (listing_type: {listing_type_id})")
                
                if is_catalog:
                    catalog_info["has_catalog_products"] = True
                    catalog_info["catalog_products_count"] += 1
                    catalog_info["catalog_products"].append({
                        "item_id": item_data.get("id"),
                        "title": item_data.get("title"),
                        "user_product_id": user_product_id,
                        "catalog_listing": item.get("catalog_listing"),
                        "listing_type_id": listing_type_id
                    })
            
            return catalog_info
            
        except Exception as e:
            logger.error(f"Erro ao verificar produtos de catálogo: {e}")
            return None
    
    def _calculate_order_fees(self, order_data: Dict) -> Optional[Dict]:
        """Calcula taxas e comissões da order a partir dos order_items"""
        try:
            order_items = order_data.get("order_items", [])
            
            total_fees = 0
            listing_fees = 0
            sale_fees = 0
            shipping_fees = 0
            
            # Extrair sale_fee de cada item (este é o dado oficial do ML)
            for item in order_items:
                sale_fee = item.get("sale_fee", 0)
                if sale_fee:
                    # sale_fee já vem em centavos ou valor decimal dependendo da moeda
                    sale_fees += sale_fee
                    logger.debug(f"Sale fee encontrada no item: {sale_fee}")
            
            # O total_fees é a soma de sale_fees (não incluir shipping_cost aqui)
            # pois shipping_cost é custo do envio, não taxa do ML
            total_fees = sale_fees
            
            logger.info(f"Taxas calculadas - Total: {total_fees}, Sale: {sale_fees}")
            
            return {
                "total_fees": total_fees,
                "listing_fees": listing_fees,  # Sempre 0 no Brasil (apenas venda)
                "sale_fees": sale_fees,
                "shipping_fees": shipping_fees  # Mantido para referência, mas não é taxa do ML
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular taxas da order: {e}")
            return None
    
    def _save_order_to_database(self, order_data: Dict, ml_account_id: int, company_id: int) -> Dict:
        """Salva ou atualiza uma order no banco de dados com informações completas"""
        try:
            ml_order_id = order_data.get("id")
            
            logger.info(f"💾 ========== SALVANDO PEDIDO NO BANCO ==========")
            logger.info(f"💾 ML Order ID: {ml_order_id}")
            logger.info(f"💾 ML Account ID: {ml_account_id}")
            logger.info(f"💾 Company ID: {company_id}")
            
            # Verificar se a order já existe (filtrando por company_id para evitar conflitos entre empresas)
            logger.info(f"🔍 Verificando se pedido já existe: ml_order_id={ml_order_id}, company_id={company_id}")
            existing_order = self.db.query(MLOrder).filter(
                MLOrder.ml_order_id == ml_order_id,
                MLOrder.company_id == company_id
            ).first()
            
            if existing_order:
                logger.info(f"✅ Pedido EXISTENTE encontrado: ID={existing_order.id}, company_id={existing_order.company_id}")
            else:
                logger.info(f"✨ Novo pedido - será criado com company_id={company_id}")
            
            access_token = self._get_active_token(ml_account_id, company_id)

            if not access_token:
                raise RuntimeError(
                    f"Token não disponível para ml_account_id={ml_account_id} (company_id={company_id}) ao salvar pedido."
                )

            # Buscar informações completas da order
            complete_order_data = self._fetch_complete_order_data(order_data, access_token, ml_account_id, company_id)
            
            # Nota: Dados de billing detalhados não estão disponíveis por pedido individual
            # Eles são fornecidos pelo ML apenas em relatórios mensais consolidados
            # O sale_fee de cada item já é extraído e salvo corretamente
            
            # Converter dados da API para o modelo
            logger.info(f"🔄 Convertendo dados da API para o modelo...")
            order_dict = self._convert_api_order_to_model(complete_order_data, ml_account_id, company_id)
            
            # Verificar se company_id está no order_dict
            if "company_id" in order_dict:
                logger.info(f"✅ company_id incluído no order_dict: {order_dict['company_id']}")
            else:
                logger.error(f"❌ ERRO CRÍTICO: company_id NÃO está no order_dict!")
                logger.error(f"❌ Campos no order_dict: {list(order_dict.keys())}")
            
            if existing_order:
                # Atualizar order existente
                logger.info(f"📝 Atualizando pedido existente ID={existing_order.id}")
                logger.info(f"📝 Company ID atual do pedido: {existing_order.company_id}")
                logger.info(f"📝 Company ID que será usado: {company_id}")
                
                for key, value in order_dict.items():
                    if key not in ["id", "ml_order_id", "created_at"]:
                        setattr(existing_order, key, value)
                
                existing_order.updated_at = datetime.utcnow()
                logger.info(f"✅ Pedido atualizado: ID={existing_order.id}, company_id={existing_order.company_id}")
                return {"action": "updated", "order": existing_order}
            else:
                # Criar nova order
                logger.info(f"✨ Criando novo pedido com company_id={company_id}")
                new_order = MLOrder(**order_dict)
                logger.info(f"✅ Objeto MLOrder criado: company_id={new_order.company_id}, ml_order_id={new_order.ml_order_id}")
                self.db.add(new_order)
                logger.info(f"✅ Pedido adicionado à sessão do banco")
                return {"action": "created", "order": new_order}
                
        except Exception as e:
            logger.error(f"Erro ao salvar order no banco: {e}", exc_info=True)
            raise e
    
    def _extract_shipping_cost(self, order_data: Dict) -> float:
        """Extrai o custo de frete do vendedor de múltiplas fontes possíveis"""
        try:
            # 1. Tentar buscar do shipping_details.shipping_option.list_cost (custo real para vendedor)
            shipping_details = order_data.get("shipping_details", {})
            if shipping_details:
                shipping_option = shipping_details.get("shipping_option", {})
                if shipping_option and shipping_option.get("list_cost"):
                    list_cost = float(shipping_option.get("list_cost", 0))
                    if list_cost > 0:
                        logger.info(f"Frete encontrado em shipping_details.shipping_option.list_cost: R$ {list_cost}")
                        return list_cost
                
                # 1b. Tentar shipping_option.cost
                if shipping_option and shipping_option.get("cost"):
                    cost = float(shipping_option.get("cost", 0))
                    if cost > 0:
                        logger.info(f"Frete encontrado em shipping_details.shipping_option.cost: R$ {cost}")
                        return cost
                
                # 1c. Tentar shipping_details.cost direto
                if shipping_details.get("cost"):
                    cost = float(shipping_details.get("cost", 0))
                    if cost > 0:
                        return cost
            
            # 2. Tentar buscar do shipping direto
            shipping = order_data.get("shipping", {})
            if shipping and shipping.get("cost"):
                cost = float(shipping.get("cost", 0))
                if cost > 0:
                    return cost
            
            # 3. Buscar do payment (alguns casos)
            payments = order_data.get("payments", [])
            if payments and len(payments) > 0:
                payment_shipping = payments[0].get("shipping_cost", 0)
                if payment_shipping and payment_shipping > 0:
                    return float(payment_shipping)
            
            # Se não encontrou frete, retornar 0
            return 0.0
            
        except Exception as e:
            logger.warning(f"Erro ao extrair shipping_cost: {e}")
            return 0.0
    
    def _convert_api_order_to_model(self, order_data: Dict, ml_account_id: int, company_id: int) -> Dict:
        """Converte dados da API para formato do modelo - Versão Completa"""
        try:
            logger.info(f"🔄 Convertendo dados da API para modelo: company_id={company_id}, ml_account_id={ml_account_id}")
            # Converter status - usar valores diretos do enum
            status_mapping = {
                "confirmed": "CONFIRMED",
                "payment_required": "PENDING", 
                "payment_in_process": "PENDING",
                "paid": "PAID",
                "ready_to_ship": "PAID",
                "shipped": "SHIPPED",
                "delivered": "DELIVERED",
                "cancelled": "CANCELLED",
                "refunded": "REFUNDED"
            }
            
            status = order_data.get("status")
            if not status:
                logger.warning(f"⚠️ Status não encontrado no order_data, usando 'pending' como padrão")
                status = "pending"
            
            order_status = status_mapping.get(status, "PENDING")
            logger.info(f"📊 Status do pedido: '{status}' -> '{order_status}'")
            
            # Converter datas
            date_created = None
            if order_data.get("date_created"):
                try:
                    date_created = datetime.fromisoformat(order_data["date_created"].replace('Z', '+00:00'))
                except:
                    pass
            
            date_closed = None
            if order_data.get("date_closed"):
                try:
                    date_closed = datetime.fromisoformat(order_data["date_closed"].replace('Z', '+00:00'))
                except:
                    pass
            
            last_updated = None
            if order_data.get("last_updated"):
                try:
                    last_updated = datetime.fromisoformat(order_data["last_updated"].replace('Z', '+00:00'))
                except:
                    pass
            
            # Extrair dados do comprador
            buyer = order_data.get("buyer", {})
            
            # Extrair dados do vendedor
            seller = order_data.get("seller", {})
            
            # Extrair dados de pagamento
            payments = order_data.get("payments", [])
            payment_status = None
            payment_method_id = None
            payment_type_id = None
            
            if payments:
                payment = payments[0]
                payment_status = payment.get("status")
                payment_method_id = payment.get("payment_method_id")
                payment_type_id = payment.get("payment_type_id")
            
            # Extrair dados de envio
            shipping = order_data.get("shipping", {})
            shipping_details = order_data.get("shipping_details", {})
            
            # Extrair cupom
            coupon = order_data.get("coupon", {})
            
            order_dict = {
                # === DADOS BÁSICOS ===
                "company_id": company_id,
                "ml_account_id": ml_account_id,
                "ml_order_id": order_data.get("id"),
                "order_id": str(order_data.get("id")),
                
                # Status e datas - Converter string para Enum
                "status": OrderStatus(order_status) if order_status in [s.value for s in OrderStatus] else OrderStatus.PENDING,
                "status_detail": order_data.get("status_detail"),
                "date_created": date_created,
                "date_closed": date_closed,
                "last_updated": last_updated,
                
                # Valores monetários
                "total_amount": order_data.get("total_amount"),
                "paid_amount": order_data.get("paid_amount"),
                "currency_id": order_data.get("currency_id"),
                
                # === DADOS DO COMPRADOR ===
                "buyer_id": buyer.get("id"),
                "buyer_nickname": buyer.get("nickname"),
                "buyer_email": buyer.get("email"),
                "buyer_first_name": buyer.get("first_name"),
                "buyer_last_name": buyer.get("last_name"),
                "buyer_phone": buyer.get("phone"),
                
                # === DADOS DO VENDEDOR ===
                "seller_id": seller.get("id"),
                "seller_nickname": seller.get("nickname"),
                "seller_phone": seller.get("phone"),
                
                # === PAGAMENTOS ===
                "payments": payments,
                "payment_method_id": payment_method_id,
                "payment_type_id": payment_type_id,
                "payment_status": payment_status,
                
                # === ENVIO E LOGÍSTICA ===
                "shipping_id": shipping.get("id"),
                "shipping_cost": self._extract_shipping_cost(order_data),
                "shipping_method": shipping.get("method") or shipping_details.get("shipping_method"),
                "shipping_status": shipping.get("status") or shipping_details.get("status"),
                "shipping_address": shipping.get("receiver_address") or shipping_details.get("receiver_address"),
                "shipping_details": shipping_details,
                
                # === ITENS DO PEDIDO ===
                "order_items": order_data.get("order_items"),
                
                # === TAXAS E COMISSÕES ===
                "total_fees": order_data.get("total_fees", 0),
                "listing_fees": order_data.get("listing_fees", 0),
                "sale_fees": order_data.get("sale_fees", 0),
                "shipping_fees": order_data.get("shipping_fees", 0),
                
                # === DESCONTOS E PROMOÇÕES ===
                "discounts_applied": order_data.get("discounts_applied"),
                "coupon_amount": coupon.get("amount", 0),
                "coupon_id": coupon.get("id"),
                
                # === PUBLICIDADE E ANÚNCIOS ===
                "is_advertising_sale": order_data.get("is_advertising_sale", False),
                "advertising_campaign_id": order_data.get("advertising_campaign_id"),
                "advertising_cost": order_data.get("advertising_cost", 0),
                "advertising_metrics": order_data.get("advertising_metrics", {}),
                
                # === PRODUTOS DE CATÁLOGO ===
                "has_catalog_products": order_data.get("has_catalog_products", False),
                "catalog_products_count": order_data.get("catalog_products_count", 0),
                "catalog_products": order_data.get("catalog_products", []),
                
                # === CONTEXTO DA VENDA ===
                "context": order_data.get("context"),
                "pack_id": order_data.get("pack_id"),
                "pickup_id": order_data.get("pickup_id"),
                
                # === MEDIAÇÕES E DISPUTAS ===
                "mediations": order_data.get("mediations"),
                "order_request": order_data.get("order_request"),
                
                # === FEEDBACK ===
                "feedback": order_data.get("feedback"),
                
                # === TAGS E METADADOS ===
                "tags": order_data.get("tags"),
                "fulfilled": order_data.get("fulfilled"),
                "comment": order_data.get("comment"),
                
                # === IMPOSTOS ===
                "taxes": order_data.get("taxes"),
                
                # === DETALHES DE CANCELAMENTO ===
                "cancel_detail": order_data.get("cancel_detail"),
                
                # === DADOS DE BILLING ===
                # Nota: Dados detalhados de billing (financing_fee, breakdowns) só estão disponíveis
                # em relatórios mensais do endpoint /billing/integration/periods/
                # Aqui salvamos apenas o sale_fee básico extraído dos order_items
                "financing_fee": None,  # Disponível apenas em relatórios mensais
                "financing_transfer_total": None,  # Disponível apenas em relatórios mensais
                "sale_fee_breakdown": None,  # Disponível apenas em relatórios mensais
                "billing_details": None,  # Disponível apenas em relatórios mensais
                "marketplace_fee_breakdown": None  # Disponível apenas em relatórios mensais
            }
            
            logger.info(f"✅ Dicionário order_dict criado com sucesso")
            return order_dict
            
        except Exception as e:
            logger.error(f"Erro ao converter dados da order: {e}", exc_info=True)
            raise e
    
    def _test_token_validity(self, access_token: str, seller_id: str) -> Dict[str, Any]:
        """Testa se o token é válido fazendo uma chamada simples à API"""
        try:
            import requests
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Testar com endpoint simples de usuário
            response = requests.get(
                f"{self.base_url}/users/me",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                user_data = response.json()
                returned_user_id = str(user_data.get("id", ""))
                
                # Verificar se o user_id do token corresponde ao seller_id esperado
                if returned_user_id != str(seller_id):
                    logger.warning(f"⚠️ Token pertence a user_id {returned_user_id}, mas esperado {seller_id}")
                    return {
                        "valid": False,
                        "error": f"Token pertence a outro usuário (ID: {returned_user_id})"
                    }
                
                return {"valid": True}
            
            elif response.status_code == 401:
                return {
                    "valid": False,
                    "error": "Token expirado ou inválido (401 Unauthorized)"
                }
            
            elif response.status_code == 403:
                return {
                    "valid": False,
                    "error": "Acesso negado (403 Forbidden)"
                }
            
            else:
                return {
                    "valid": False,
                    "error": f"Erro ao validar token: HTTP {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Erro ao testar token: {e}")
            return {
                "valid": False,
                "error": f"Erro ao validar token: {str(e)}"
            }
    
    def _get_active_token(self, ml_account_id: int, company_id: Optional[int] = None) -> Optional[str]:
        """Obtém token ativo usando TokenManager, tentando renovação automática se necessário"""
        try:
            token_manager = TokenManager(self.db)

            account = (
                self.db.query(MLAccount)
                .filter(MLAccount.id == ml_account_id)
                .first()
            )

            if not account:
                logger.error(
                    "❌ Conta ML %s não encontrada ao buscar token",
                    ml_account_id,
                )
                return None

            resolved_company_id = company_id or account.company_id

            if resolved_company_id is None:
                logger.error(
                    "❌ Não foi possível determinar company_id para ml_account_id=%s ao buscar token",
                    ml_account_id,
                )
                return None

            expected_seller_id = str(account.ml_user_id) if account.ml_user_id else None

            token_record = token_manager.get_token_record_for_account(
                ml_account_id,
                resolved_company_id,
                expected_ml_user_id=expected_seller_id,
            )

            if token_record and token_record.access_token:
                return token_record.access_token

            logger.warning(
                "⚠️ Nenhum token ativo encontrado para ml_account_id=%s (company_id=%s)",
                ml_account_id,
                resolved_company_id,
            )
            return None

        except Exception as e:
            logger.error(f"Erro ao obter token ativo: {e}")
            return None
    
    def _refresh_token(self, refresh_token: str, ml_account_id: int) -> Optional[str]:
        """Tenta renovar token usando refresh token"""
        try:
            import requests
            from app.config.settings import Settings
            
            settings = Settings()
            
            # Dados para renovar token (usa credenciais do ambiente)
            data = {
                "grant_type": "refresh_token",
                "client_id": settings.ml_app_id,
                "client_secret": settings.ml_client_secret,
                "refresh_token": refresh_token
            }
            
            headers = {
                "accept": "application/json",
                "content-type": "application/x-www-form-urlencoded"
            }
            
            response = requests.post("https://api.mercadolibre.com/oauth/token", data=data, headers=headers)
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Salvar novo token no banco
                from app.models.saas_models import Token
                from datetime import datetime, timedelta
                
                # Desativar tokens antigos
                self.db.query(Token).filter(
                    Token.ml_account_id == ml_account_id,
                    Token.is_active == True
                ).update({"is_active": False})
                
                # Buscar user_id da empresa da conta ML (para compatibilidade)
                from app.models.saas_models import MLAccount, User
                account = self.db.query(MLAccount).filter(MLAccount.id == ml_account_id).first()
                user_id = None
                if account:
                    # Buscar qualquer usuário da empresa (pode ser inativo, não importa)
                    user = self.db.query(User).filter(User.company_id == account.company_id).first()
                    user_id = user.id if user else None
                    
                # Se não encontrar usuário, usar o user_id do token anterior
                if not user_id:
                    old_token = self.db.query(Token).filter(
                        Token.ml_account_id == ml_account_id,
                        Token.is_active == False
                    ).order_by(Token.created_at.desc()).first()
                    user_id = old_token.user_id if old_token else None
                
                # Criar novo token
                new_token = Token(
                    user_id=user_id,
                    ml_account_id=ml_account_id,
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token"),
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_in=token_data.get("expires_in", 21600),
                    scope=token_data.get("scope", ""),
                    expires_at=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 21600)),
                    is_active=True
                )
                
                self.db.add(new_token)
                self.db.commit()
                
                logger.info(f"Token renovado com sucesso para ml_account_id: {ml_account_id}")
                return token_data["access_token"]
            else:
                logger.error(f"Erro ao renovar token: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao renovar token: {e}")
            return None
    
    def delete_orders(self, order_ids: List[int], company_id: int) -> Dict:
        """Remove pedidos selecionados do banco de dados"""
        try:
            logger.info(f"Removendo pedidos: {order_ids} para company_id: {company_id}")
            
            # Buscar pedidos que pertencem à empresa
            orders_to_delete = self.db.query(MLOrder).filter(
                MLOrder.id.in_(order_ids),
                MLOrder.company_id == company_id
            ).all()
            
            if not orders_to_delete:
                return {
                    "success": False,
                    "error": "Nenhum pedido encontrado para remoção"
                }
            
            # Verificar se todos os pedidos pertencem à empresa
            found_ids = [order.id for order in orders_to_delete]
            missing_ids = set(order_ids) - set(found_ids)
            
            if missing_ids:
                return {
                    "success": False,
                    "error": f"Alguns pedidos não foram encontrados ou não pertencem à sua empresa: {missing_ids}"
                }
            
            # Remover pedidos
            deleted_count = 0
            for order in orders_to_delete:
                self.db.delete(order)
                deleted_count += 1
            
            self.db.commit()
            
            return {
                "success": True,
                "message": f"{deleted_count} pedido(s) removido(s) com sucesso",
                "deleted_count": deleted_count
            }
            
        except Exception as e:
            logger.error(f"Erro ao remover pedidos: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": f"Erro ao remover pedidos: {str(e)}"
            }
    
    def delete_all_orders(self, company_id: int) -> Dict:
        """Remove todos os pedidos da empresa do banco de dados"""
        try:
            logger.info(f"Removendo todos os pedidos para company_id: {company_id}")
            
            # Buscar todos os pedidos da empresa
            orders_to_delete = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id
            ).all()
            
            if not orders_to_delete:
                return {
                    "success": False,
                    "error": "Nenhum pedido encontrado para remoção"
                }
            
            # Contar pedidos antes de remover
            total_count = len(orders_to_delete)
            
            # Remover todos os pedidos
            for order in orders_to_delete:
                self.db.delete(order)
            
            self.db.commit()
            
            return {
                "success": True,
                "message": f"Todos os pedidos ({total_count}) foram removidos com sucesso",
                "deleted_count": total_count
            }
            
        except Exception as e:
            logger.error(f"Erro ao remover todos os pedidos: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": f"Erro ao remover todos os pedidos: {str(e)}"
            }
    
    def _sync_advertising_costs_for_account(self, account_id: int, access_token: str, periods: int = 1) -> Dict:
        """
        Sincroniza custos de Product Ads do Billing API para uma conta
        
        Args:
            account_id: ID da conta ML
            access_token: Token de acesso
            periods: Número de períodos para sincronizar (padrão: 1 = mês atual)
        """
        try:
            base_url = "https://api.mercadolibre.com"
            
            # Buscar períodos de billing
            periods_url = f"{base_url}/billing/integration/monthly/periods"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            params = {
                "group": "ML",
                "document_type": "BILL",
                "limit": periods
            }
            
            response = requests.get(periods_url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Erro ao buscar períodos de billing: {response.status_code}")
                return None
            
            periods_data = response.json()
            results = periods_data.get("results", [])
            
            if not results:
                logger.warning("Nenhum período de billing encontrado")
                return None
            
            total_cost = 0
            total_orders_updated = 0
            
            # Processar cada período
            for period in results:
                period_key = period.get("key")
                period_from = period.get("period", {}).get("date_from")
                period_to = period.get("period", {}).get("date_to")
                
                # Buscar summary/details do período
                summary_url = f"{base_url}/billing/integration/periods/key/{period_key}/summary/details"
                summary_params = {
                    "group": "ML",
                    "document_type": "BILL"
                }
                
                summary_response = requests.get(summary_url, headers=headers, params=summary_params, timeout=30)
                
                if summary_response.status_code != 200:
                    logger.error(f"Erro ao buscar summary do período {period_key}: {summary_response.status_code}")
                    continue
                
                summary_data = summary_response.json()
                
                # Procurar custos de Product Ads (tipo PADS)
                period_pads_cost = 0
                charges = summary_data.get("bill_includes", {}).get("charges", [])
                
                for charge in charges:
                    if charge.get("type") == "PADS":  # Product Ads
                        period_pads_cost += float(charge.get("amount", 0))
                
                if period_pads_cost > 0:
                    # Converter datas do período
                    from datetime import datetime
                    date_from = datetime.strptime(period_from, "%Y-%m-%d")
                    date_to = datetime.strptime(period_to, "%Y-%m-%d")
                    
                    # Buscar pedidos do período
                    orders = self.db.query(MLOrder).filter(
                        MLOrder.ml_account_id == account_id,
                        MLOrder.date_created >= date_from,
                        MLOrder.date_created <= date_to
                    ).all()
                    
                    if len(orders) > 0:
                        # Distribuir custo proporcionalmente entre os pedidos
                        cost_per_order = period_pads_cost / len(orders)
                        
                        for order in orders:
                            order.advertising_cost = cost_per_order
                            order.is_advertising_sale = True
                        
                        self.db.commit()
                        
                        total_cost += period_pads_cost
                        total_orders_updated += len(orders)
                        
                        logger.info(f"  📅 Período {period_from} a {period_to}: R$ {period_pads_cost:.2f} / {len(orders)} pedidos = R$ {cost_per_order:.2f}/pedido")
            
            return {
                "total_cost": total_cost,
                "orders_updated": total_orders_updated,
                "periods_processed": len(results)
            }
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar custos de publicidade: {e}")
            return None
    
    def _check_invoice_for_order_sync(self, order_id: str, company_id: int, access_token: str):
        """
        Verifica automaticamente se um pedido tem nota fiscal emitida (versão síncrona)
        Chamado quando um pedido é sincronizado com status PAID/CONFIRMED
        """
        try:
            from sqlalchemy import text
            
            # Buscar dados do pedido incluindo pack_id e shipping_id
            order_query = text("""
                SELECT id, ml_order_id, pack_id, shipping_id, invoice_emitted, ml_account_id, seller_id
                FROM ml_orders 
                WHERE ml_order_id = :order_id AND company_id = :company_id
            """)
            
            order_result = self.db.execute(order_query, {"order_id": str(order_id), "company_id": company_id}).fetchone()
            
            if not order_result:
                logger.warning(f"⚠️ Pedido {order_id} não encontrado para verificação de NF")
                return
            
            order_db_id, ml_order_id, pack_id, shipping_id, current_invoice_status, ml_account_id, seller_id = order_result
            
            if current_invoice_status:
                logger.info(f"ℹ️ Pedido {order_id} já tem NF marcada - pulando verificação")
                return
            
            # Verificar NF no ML usando ShipmentService
            from app.services.shipment_service import ShipmentService
            shipment_service = ShipmentService(self.db)
            
            # Tentar buscar NF por pack_id primeiro
            invoice_data = None
            if pack_id:
                logger.info(f"🔍 Buscando NF pelo pack_id {pack_id} para pedido {order_id}")
                invoice_data = shipment_service._check_pack_invoice(pack_id, access_token)
            
            # Se não encontrou pelo pack_id e tem shipping_id, tentar pelo shipping_id (fulfillment)
            if not invoice_data and shipping_id:
                logger.info(f"🔍 Buscando NF pelo shipping_id {shipping_id} para pedido {order_id} (fulfillment)")
                invoice_data = shipment_service._check_shipment_invoice(
                    shipment_id=shipping_id,
                    company_id=company_id,
                    access_token=access_token,
                    seller_id=seller_id,
                    ml_account_id=ml_account_id
                )
            
            if invoice_data and invoice_data.get('has_invoice'):
                # Atualizar pedido com dados da NF
                update_invoice_query = text("""
                    UPDATE ml_orders SET
                        invoice_emitted = true,
                        invoice_emitted_at = NOW(),
                        invoice_number = :invoice_number,
                        invoice_series = :invoice_series,
                        invoice_key = :invoice_key,
                        invoice_xml_url = :invoice_xml_url,
                        invoice_pdf_url = :invoice_pdf_url,
                        updated_at = NOW()
                    WHERE id = :order_db_id
                """)
                
                self.db.execute(update_invoice_query, {
                    "order_db_id": order_db_id,
                    "invoice_number": invoice_data.get('number'),
                    "invoice_series": invoice_data.get('series'),
                    "invoice_key": invoice_data.get('key'),
                    "invoice_xml_url": invoice_data.get('xml_url'),
                    "invoice_pdf_url": invoice_data.get('pdf_url')
                })
                
                # Commit imediato para garantir que a NF seja salva
                self.db.commit()
                
                logger.info(f"✅ [AUTO-NF] Nota fiscal detectada e atualizada para pedido {order_id}")
                
            else:
                logger.info(f"ℹ️ [AUTO-NF] Pedido {order_id} ainda não tem nota fiscal emitida")
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar NF do pedido {order_id}: {e}", exc_info=True)
