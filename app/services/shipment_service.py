"""
Serviço para gerenciar expedição e notas fiscais
"""
import requests
import logging
import json
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.models.saas_models import MLOrder, OrderStatus, MLAccount, Token, User, Company
from sqlalchemy import or_

logger = logging.getLogger(__name__)

class ShipmentService:
    def __init__(self, db: Session):
        self.db = db
        self.base_url = "https://api.mercadolibre.com"

    # Hierarquia de status (do menos para o mais avançado)
    # Status finais (nível 0) sempre atualizam independente de ser manual
    STATUS_HIERARCHY = {
        OrderStatus.PENDING: 1,
        OrderStatus.CONFIRMED: 2,
        OrderStatus.READY_TO_PREPARE: 3,  # Status manual
        OrderStatus.PAID: 4,
        OrderStatus.PARTIALLY_PAID: 4,
        OrderStatus.SHIPPED: 5,
        OrderStatus.DELIVERED: 6,
        # Status finais sempre atualizam
        OrderStatus.CANCELLED: 0,
        OrderStatus.PENDING_CANCEL: 0,
        OrderStatus.REFUNDED: 0,
        OrderStatus.PARTIALLY_REFUNDED: 0,
        OrderStatus.INVALID: 0
    }
    
    def should_update_status(self, current_status: OrderStatus, new_status: OrderStatus, is_manual: bool) -> bool:
        """
        Decide se deve atualizar o status considerando se foi definido manualmente
        
        - Se não é manual: sempre atualiza
        - Se é manual: só atualiza se o novo status for mais avançado ou for status final
        """
        if not is_manual:
            return True
        
        # Status importantes sempre atualizam automaticamente (independente de ser manual)
        # Esses status indicam progresso real do pedido e devem sempre ser atualizados
        if new_status in [
            OrderStatus.CANCELLED,           # Cancelamento sempre atualiza
            OrderStatus.DELIVERED,           # Entrega sempre atualiza
            OrderStatus.SHIPPED,             # Envio sempre atualiza (pedido já foi enviado)
            OrderStatus.PAID,                # Pagamento sempre atualiza (pedido foi pago)
            OrderStatus.REFUNDED,            # Reembolso sempre atualiza
            OrderStatus.PARTIALLY_REFUNDED,  # Reembolso parcial sempre atualiza
            OrderStatus.INVALID,              # Inválido sempre atualiza
            OrderStatus.PENDING_CANCEL       # Cancelamento pendente sempre atualiza
        ]:
            return True
        
        # Se novo status é mais avançado que o atual, atualiza
        current_level = self.STATUS_HIERARCHY.get(current_status, 0)
        new_level = self.STATUS_HIERARCHY.get(new_status, 0)
        
        return new_level > current_level

    def get_all_orders(self, company_id: int, filters: Optional[Dict] = None) -> List[MLOrder]:
        """
        Lista TODOS os pedidos da empresa para separação por status
        """
        try:
            query = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id
            )
            
            # Aplicar filtros opcionais
            if filters:
                if filters.get('invoice_status') == 'emitted':
                    query = query.filter(MLOrder.invoice_emitted == True)
                elif filters.get('invoice_status') == 'pending':
                    query = query.filter(MLOrder.invoice_emitted == False)
                
                if filters.get('search'):
                    search = f"%{filters['search']}%"
                    query = query.filter(
                        (MLOrder.order_id.ilike(search)) |
                        (MLOrder.buyer_nickname.ilike(search)) |
                        (MLOrder.buyer_first_name.ilike(search))
                    )
            
            return query.order_by(MLOrder.date_created.desc()).all()
        
        except Exception as e:
            logger.error(f"Erro ao buscar todos os pedidos: {e}")
            return []

    def can_generate_label(self, order: MLOrder) -> bool:
        """
        Verifica se pode gerar etiqueta para o pedido
        """
        return (
            order.status in [OrderStatus.PAID, OrderStatus.CONFIRMED] and
            order.shipping_id is not None and
            not order.invoice_emitted
        )

    def sync_invoice_status(self, company_id: int, access_token: str) -> Dict:
        """
        Sincroniza STATUS e NOTAS FISCAIS do Mercado Livre
        
        Busca TODOS os pedidos e sincroniza:
        - Status do pedido
        - Status do shipping (fulfillment)
        - Notas fiscais
        """
        try:
            import requests
            
            # Buscar TODOS os pedidos (não apenas PAID/CONFIRMED)
            orders = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id
            ).all()
            
            logger.info(f"Sincronizando status e notas fiscais para {len(orders)} pedido(s)")
            
            updated = 0
            already_synced = 0
            status_updated = 0
            invoice_updated = 0
            errors = []
            
            # Processar em lotes de 10 para evitar deadlock
            batch_size = 10
            for i in range(0, len(orders), batch_size):
                batch = orders[i:i + batch_size]
                logger.info(f"Processando lote {i//batch_size + 1} de {(len(orders) + batch_size - 1)//batch_size}")
                
                for order in batch:
                    try:
                        order_updated = False
                        
                        # 1. SINCRONIZAR STATUS DO PEDIDO
                        try:
                            order_url = f"{self.base_url}/orders/{order.order_id}"
                            headers = {"Authorization": f"Bearer {access_token}"}
                            response = requests.get(order_url, headers=headers, timeout=30)
                            
                            if response.status_code == 200:
                                order_data = response.json()
                                
                                # Mapear e atualizar status
                                # Mapear status - Baseado na documentação oficial do Mercado Livre
                                status_mapping = {
                                    "confirmed": OrderStatus.CONFIRMED,
                                    "payment_required": OrderStatus.PENDING,
                                    "payment_in_process": OrderStatus.PENDING,
                                    "paid": OrderStatus.PAID,
                                    "partially_paid": OrderStatus.PARTIALLY_PAID,
                                    "ready_to_ship": OrderStatus.PAID,
                                    "shipped": OrderStatus.SHIPPED,
                                    "delivered": OrderStatus.DELIVERED,
                                    "cancelled": OrderStatus.CANCELLED,
                                    "pending_cancel": OrderStatus.PENDING_CANCEL,
                                    "refunded": OrderStatus.REFUNDED,
                                    "partially_refunded": OrderStatus.PARTIALLY_REFUNDED,
                                    "invalid": OrderStatus.INVALID
                                }
                                
                                # Verificar se tem a tag "delivered" mesmo com status de reembolso
                                tags = order_data.get('tags', [])
                                if 'delivered' in tags:
                                    status_mapping["partially_refunded"] = OrderStatus.DELIVERED
                                
                                api_status = order_data.get("status", "pending")
                                new_status = status_mapping.get(api_status, OrderStatus.PENDING)
                                
                                # Verificar se deve atualizar o status (respeitando status manual)
                                if order.status != new_status:
                                    if self.should_update_status(order.status, new_status, order.status_manual):
                                        order.status = new_status
                                        # Se atualizar via API, remover flag manual
                                        if order.status_manual:
                                            order.status_manual = False
                                            order.status_manual_date = None
                                        order_updated = True
                                        status_updated += 1
                                        logger.info(f"✅ Status do pedido {order.order_id} atualizado: {order.status} -> {new_status}")
                                
                                # Atualizar shipping info
                                shipping = order_data.get("shipping", {})
                                if shipping:
                                    order.shipping_status = shipping.get("status")
                                    shipping_id = shipping.get("id")
                                    if shipping_id:
                                        order.shipping_id = str(shipping_id)
                                        
                                        # Buscar detalhes completos do shipment para obter logistic_type
                                        try:
                                            shipment_url = f"{self.base_url}/shipments/{shipping_id}"
                                            shipment_headers = {
                                                **headers,
                                                "x-format-new": "true"  # Necessário para obter logistic_type
                                            }
                                            shipment_response = requests.get(shipment_url, headers=shipment_headers, timeout=30)
                                            
                                            if shipment_response.status_code == 200:
                                                shipment_data = shipment_response.json()
                                                
                                                # Extrair logistic_type
                                                logistic_type = shipment_data.get("logistic_type")
                                                if not logistic_type:
                                                    logistic = shipment_data.get("logistic", {})
                                                    logistic_type = logistic.get("type") if logistic else None
                                                
                                                if logistic_type:
                                                    order.shipping_type = logistic_type
                                                    logger.debug(f"✅ Shipping type atualizado para pedido {order.order_id}: {logistic_type}")
                                        except Exception as e:
                                            logger.warning(f"Erro ao buscar detalhes do shipment para atualizar shipping_type: {e}")
                                    
                                    order.last_updated = datetime.utcnow()
                        except Exception as e:
                            logger.warning(f"Erro ao sincronizar status do pedido {order.order_id}: {e}")
                        
                        # 2. SINCRONIZAR NOTA FISCAL
                        invoice_data = None
                        
                        if order.pack_id:
                            invoice_data = self._check_pack_invoice(order.pack_id, access_token)
                        
                        if not invoice_data and order.shipping_id:
                            invoice_data = self._check_shipment_invoice(
                                shipment_id=order.shipping_id,
                                company_id=company_id,
                                access_token=access_token,
                                seller_id=getattr(order, "seller_id", None),
                                ml_account_id=getattr(order, "ml_account_id", None)
                            )
                        
                        if invoice_data and invoice_data.get('has_invoice'):
                            if not order.invoice_emitted:
                                order.invoice_emitted = True
                                order.invoice_emitted_at = datetime.now()
                                order.invoice_number = invoice_data.get('number')
                                order.invoice_series = invoice_data.get('series')
                                order.invoice_key = invoice_data.get('key')
                                order.invoice_xml_url = invoice_data.get('xml_url')
                                order.invoice_pdf_url = invoice_data.get('pdf_url')
                                order_updated = True
                                invoice_updated += 1
                                logger.info(f"✅ NF sincronizada para pedido {order.order_id}")
                        
                        if order_updated:
                            updated += 1
                        else:
                            already_synced += 1
                    except Exception as e:
                        error_msg = f"Erro ao sincronizar pedido {order.order_id}: {e}"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                
                # Commit do lote para evitar deadlock
                try:
                    self.db.commit()
                    logger.info(f"✅ Lote {i//batch_size + 1} commitado com sucesso")
                except Exception as e:
                    logger.error(f"Erro ao commitar lote {i//batch_size + 1}: {e}")
                    self.db.rollback()
                    errors.append(f"Erro ao commitar lote {i//batch_size + 1}: {e}")
            
            logger.info(f"✅ Sincronização concluída: {status_updated} status atualizados, {invoice_updated} notas fiscais atualizadas")
            
            return {
                "success": True,
                "updated": updated,
                "status_updated": status_updated,
                "invoice_updated": invoice_updated,
                "already_synced": already_synced,
                "total_processed": len(orders),
                "errors": errors if errors else None
            }
        
        except Exception as e:
            logger.error(f"Erro ao sincronizar notas fiscais: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e),
                "updated": 0
            }

    def sync_shipment_status_and_invoices(self, company_id: int, user_id: Optional[int] = None) -> Dict:
        """
        Obtém automaticamente um token válido e executa a sincronização completa
        de status de envio + notas fiscais para todos os pedidos da empresa.

        Caso user_id não seja informado, usa o primeiro usuário ativo da empresa.
        """
        try:
            from app.services.token_manager import TokenManager

            token_manager = TokenManager(self.db)

            target_user_id = user_id
            if not target_user_id:
                user = (
                    self.db.query(User)
                    .filter(User.company_id == company_id, User.is_active == True)
                    .order_by(User.id.asc())
                    .first()
                )
                if not user:
                    logger.error(f"❌ Nenhum usuário ativo encontrado para company_id={company_id}")
                    return {
                        "success": False,
                        "error": "Nenhum usuário ativo encontrado para esta empresa",
                    }
                target_user_id = user.id

            access_token = token_manager.get_valid_token(target_user_id)
            if not access_token:
                logger.warning(
                    f"⚠️ Token não encontrado para user_id={target_user_id} (company_id={company_id}). Tentando fallback."
                )
                fallback_user = (
                    self.db.query(User)
                    .join(Token, Token.user_id == User.id)
                    .filter(
                        User.company_id == company_id,
                        User.is_active == True,
                        Token.access_token.isnot(None),
                    )
                    .order_by(Token.expires_at.desc())
                    .first()
                )

                if fallback_user:
                    logger.info(
                        f"🔄 Usando fallback user_id={fallback_user.id} para sincronização de NF."
                    )
                    target_user_id = fallback_user.id
                    access_token = token_manager.get_valid_token(target_user_id)

            if not access_token:
                logger.error(
                    f"❌ Token não encontrado ou inválido após fallback para company_id={company_id}"
                )
                return {
                    "success": False,
                    "error": "Token do Mercado Livre inválido ou expirado. Reconecte a conta em Contas ML.",
                }

            logger.info(
                f"🔄 Sincronizando status e notas fiscais (company_id={company_id}, user_id={target_user_id})"
            )
            return self.sync_invoice_status(company_id, access_token)

        except Exception as exc:
            logger.error(
                f"❌ Erro ao sincronizar status/notas (company_id={company_id}): {exc}",
                exc_info=True,
            )
            return {
                "success": False,
                "error": f"Erro ao sincronizar status e notas fiscais: {exc}",
            }

    def sync_single_order_invoice(self, order_id: str, company_id: int, access_token: str) -> Dict:
        """
        Sincroniza COMPLETAMENTE um pedido específico com o Mercado Livre
        
        Sincroniza:
        - Status do pedido
        - Dados básicos (total, pagamento, comprador)
        - Tipo de envio (shipping_type)
        - Datas (criação, fechamento, envio, entrega estimada)
        - Nota fiscal
        - Pack ID e Sale ID
        
        Busca o pedido por ml_order_id, order_id, sale_id ou pack_id
        """
        try:
            from sqlalchemy import or_
            
            logger.info(f"🔍 [SYNC] Buscando pedido {order_id} para company_id={company_id}")
            
            # Buscar o pedido específico - tentar múltiplos campos
            # O order_id pode ser: ml_order_id, order_id ou pack_id
            order = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id,
                or_(
                    MLOrder.ml_order_id == order_id,
                    MLOrder.order_id == order_id,
                    MLOrder.pack_id == order_id
                )
            ).first()
            
            if not order:
                logger.warning(f"⚠️ [SYNC] Pedido {order_id} não encontrado para company_id={company_id}")
                return {
                    "success": False,
                    "error": f"Pedido {order_id} não encontrado (busca por ml_order_id, order_id ou pack_id)"
                }
            
            logger.info(f"✅ [SYNC] Pedido {order_id} encontrado para company_id={company_id}")
            logger.info(f"📋 [SYNC] Status atual: {order.status}, Shipping Status: {order.shipping_status}")
            
            # Usar ml_order_id para buscar na API do Mercado Livre
            # O ml_order_id é o ID que o ML espera
            api_order_id = str(order.ml_order_id)
            
            # Para logs, usar o order_id
            order_id_for_logs = str(order.order_id)
            
            # 1. SINCRONIZAR STATUS DO PEDIDO
            status_updated = False
            invoice_updated = False
            
            print(f"📡 [STEP 1] Buscando pedido na API ML: /orders/{api_order_id}")
            logger.info(f"📡 [STEP 1] Buscando pedido na API ML: /orders/{api_order_id}")
            
            try:
                import requests
                order_url = f"{self.base_url}/orders/{api_order_id}"
                headers = {"Authorization": f"Bearer {access_token}"}
                response = requests.get(order_url, headers=headers, timeout=30)
                
                print(f"📡 [STEP 1] Resposta API: status={response.status_code}")
                logger.info(f"📡 [STEP 1] Resposta API: status={response.status_code}")
                
                if response.status_code == 404:
                    # Se o pedido não existe na API, tentar buscar shipping_details pelo shipping_id
                    print(f"⚠️ [STEP 1] Pedido não encontrado na API (404), tentando buscar shipping_details pelo shipping_id")
                    logger.warning(f"⚠️ [STEP 1] Pedido não encontrado na API (404), tentando buscar shipping_details pelo shipping_id")
                    
                    if order.shipping_id:
                        try:
                            shipment_url = f"{self.base_url}/shipments/{order.shipping_id}"
                            shipment_headers = {
                                **headers,
                                "x-format-new": "true"
                            }
                            shipment_response = requests.get(shipment_url, headers=shipment_headers, timeout=30)
                            
                            if shipment_response.status_code == 200:
                                shipment_data = shipment_response.json()
                                order.shipping_details = shipment_data
                                status_updated = True
                                print(f"✅ [STEP 1] Shipping details obtidos via shipment_id")
                                logger.info(f"✅ [STEP 1] Shipping details obtidos via shipment_id")
                            else:
                                print(f"⚠️ [STEP 1] Não foi possível obter shipping_details: {shipment_response.status_code}")
                                logger.warning(f"⚠️ [STEP 1] Não foi possível obter shipping_details: {shipment_response.status_code}")
                        except Exception as e:
                            print(f"❌ [STEP 1] Erro ao buscar shipping_details: {e}")
                            logger.error(f"❌ [STEP 1] Erro ao buscar shipping_details: {e}")
                
                elif response.status_code == 200:
                    order_data = response.json()
                    print(f"✅ [STEP 1] Dados do pedido recebidos da API")
                    logger.info(f"✅ [STEP 1] Dados do pedido recebidos da API")
                    print(f"   Status: {order_data.get('status')}")
                    logger.info(f"   Status: {order_data.get('status')}")
                    print(f"   Pack ID: {order_data.get('pack_id')}")
                    logger.info(f"   Pack ID: {order_data.get('pack_id')}")
                    print(f"   Shipping: {order_data.get('shipping')}")
                    logger.info(f"   Shipping: {order_data.get('shipping')}")
                    
                    # ============================================
                    # SINCRONIZAR TODOS OS DADOS DO PEDIDO
                    # ============================================
                    
                    # 1. Atualizar dados básicos do pedido
                    order_items = order_data.get("order_items", [])
                    total_amount = sum(
                        item.get("unit_price", 0) * item.get("quantity", 0) 
                        for item in order_items
                    )
                    if total_amount != order.total_amount:
                        order.total_amount = total_amount
                        status_updated = True
                        logger.info(f"💰 Total atualizado: {order.total_amount} -> {total_amount}")
                    
                    # 2. Atualizar dados de pagamento
                    payments = order_data.get("payments", [])
                    if payments:
                        paid_amount = payments[0].get("total_paid_amount", 0)
                        if paid_amount != order.paid_amount:
                            order.paid_amount = paid_amount
                            status_updated = True
                            logger.info(f"💳 Valor pago atualizado: {order.paid_amount} -> {paid_amount}")
                        
                        # SALVAR JSON COMPLETO DE PAYMENTS
                        order.payments = payments
                        status_updated = True
                        logger.info(f"💳 JSON payments salvo para pedido {order_id_for_logs}")
                    
                    # 3. Atualizar dados do comprador
                    buyer = order_data.get("buyer", {})
                    if buyer:
                        buyer_first_name = buyer.get("first_name")
                        buyer_nickname = buyer.get("nickname")
                        if buyer_first_name and buyer_first_name != order.buyer_first_name:
                            order.buyer_first_name = buyer_first_name
                            status_updated = True
                        if buyer_nickname and buyer_nickname != order.buyer_nickname:
                            order.buyer_nickname = buyer_nickname
                            status_updated = True
                    
                    # 4. Atualizar shipping_cost
                    shipping = order_data.get("shipping", {})
                    if shipping:
                        shipping_cost = shipping.get("cost", 0)
                        if shipping_cost != order.shipping_cost:
                            order.shipping_cost = shipping_cost
                            status_updated = True
                    
                    # 5. Atualizar datas importantes
                    date_created = order_data.get("date_created")
                    if date_created:
                        try:
                            parsed_date = datetime.fromisoformat(date_created.replace('Z', '+00:00'))
                            if parsed_date != order.date_created:
                                order.date_created = parsed_date
                                status_updated = True
                        except:
                            pass
                    
                    date_closed = order_data.get("date_closed")
                    if date_closed:
                        try:
                            parsed_date = datetime.fromisoformat(date_closed.replace('Z', '+00:00'))
                            if parsed_date != order.date_closed:
                                order.date_closed = parsed_date
                                status_updated = True
                        except:
                            pass
                    
                    last_updated = order_data.get("last_updated")
                    if last_updated:
                        try:
                            parsed_date = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                            if parsed_date != order.last_updated:
                                order.last_updated = parsed_date
                                status_updated = True
                        except:
                            pass
                    
                    # 6. Atualizar status_detail
                    status_detail = order_data.get("status_detail", {})
                    if status_detail:
                        status_detail_code = status_detail.get("code")
                        if status_detail_code and status_detail_code != order.status_detail:
                            order.status_detail = status_detail_code
                            status_updated = True
                    
                    # ============================================
                    # MAPEAR STATUS DO PEDIDO
                    # ============================================
                    
                    # Mapear status - Baseado na documentação oficial do Mercado Livre
                    # https://developers.mercadolivre.com.br/pt_br/gerenciamento-de-vendas
                    status_mapping = {
                        "confirmed": OrderStatus.CONFIRMED,
                        "payment_required": OrderStatus.PENDING,
                        "payment_in_process": OrderStatus.PENDING,
                        "paid": OrderStatus.PAID,
                        "partially_paid": OrderStatus.PARTIALLY_PAID,
                        "ready_to_ship": OrderStatus.PAID,
                        "shipped": OrderStatus.SHIPPED,
                        "delivered": OrderStatus.DELIVERED,
                        "cancelled": OrderStatus.CANCELLED,
                        "pending_cancel": OrderStatus.PENDING_CANCEL,
                        "refunded": OrderStatus.REFUNDED,
                        "partially_refunded": OrderStatus.PARTIALLY_REFUNDED,
                        "invalid": OrderStatus.INVALID
                    }
                    
                    # Verificar se tem a tag "delivered" mesmo com status de reembolso
                    tags = order_data.get('tags', [])
                    if 'delivered' in tags:
                        # Se foi entregue mas teve reembolso, considerar como entregue
                        status_mapping["partially_refunded"] = OrderStatus.DELIVERED
                    
                    api_status = order_data.get("status", "pending")
                    new_status = status_mapping.get(api_status, OrderStatus.PENDING)
                    
                    # Verificar se deve atualizar o status (respeitando status manual)
                    if order.status != new_status:
                        if self.should_update_status(order.status, new_status, order.status_manual):
                            order.status = new_status
                            # Se atualizar via API, remover flag manual
                            if order.status_manual:
                                order.status_manual = False
                                order.status_manual_date = None
                                logger.info(f"🔄 Status manual removido para pedido {order_id_for_logs} (atualizado via API)")
                            status_updated = True
                            logger.info(f"✅ Status do pedido {order_id_for_logs} atualizado: {order.status} -> {new_status}")
                        else:
                            logger.info(f"⏸️ Status manual preservado para pedido {order_id_for_logs}: {order.status} (API retornou {new_status})")
                    
                    # Atualizar shipping status também
                    shipping = order_data.get("shipping", {})
                    
                    # IMPORTANTE: Verificar pack_id ANTES de tudo - pack_id sempre indica FULFILLMENT
                    pack_id = order_data.get("pack_id")
                    if pack_id:
                        # Atualizar pack_id se não estiver salvo
                        if not order.pack_id:
                            order.pack_id = str(pack_id)
                            logger.info(f"✅ Pack ID salvo para pedido {order_id_for_logs}: {pack_id}")
                        
                        # Se tem pack_id, é FULFILLMENT - marcar imediatamente
                        order.shipping_type = "fulfillment"
                        logger.info(f"✅ Pedido {order_id_for_logs} identificado como FULFILLMENT (tem pack_id: {pack_id})")
                    
                    if shipping:
                        order.shipping_status = shipping.get("status")
                        shipping_id_from_api = shipping.get("id")
                        if shipping_id_from_api:
                            order.shipping_id = str(shipping_id_from_api)
                        order.last_updated = datetime.utcnow()
                        status_updated = True
                        
                        # Se tem shipping_id, SEMPRE buscar dados completos do shipment para salvar shipping_details
                        if shipping_id_from_api:
                            # Buscar dados completos do shipment para salvar shipping_details e obter informações adicionais
                            try:
                                shipment_url = f"{self.base_url}/shipments/{shipping_id_from_api}"
                                shipment_headers = {
                                    **headers,
                                    "x-format-new": "true"  # Necessário para novo formato
                                }
                                shipment_response = requests.get(shipment_url, headers=shipment_headers, timeout=30)
                                
                                if shipment_response.status_code == 200:
                                    shipment_data = shipment_response.json()
                                    
                                    # Persistir detalhes completos do shipment (inclui tracking_method, histories, etc.)
                                    order.shipping_details = shipment_data
                                    logger.info(f"✅ Shipping details salvos para pedido {order_id_for_logs}")
                                    
                                    # Capturar substatus (importante para fulfillment)
                                    substatus = shipment_data.get("substatus")
                                    if substatus:
                                        logger.info(f"📦 Shipment {shipping_id_from_api} - Substatus: {substatus}")
                                    
                                    # Identificar tipo de logística
                                    # Pode estar em shipment_data.get("logistic_type") diretamente ou
                                    # em shipment_data.get("logistic", {}).get("type")
                                    logistic_type = shipment_data.get("logistic_type")
                                    if not logistic_type:
                                        logistic = shipment_data.get("logistic", {})
                                        logistic_type = logistic.get("type") if logistic else None
                                    
                                    logistic_mode = None
                                    if 'logistic' in locals() and logistic:
                                        logistic_mode = logistic.get("mode")  # me2
                                    
                                    # Atualizar shipping_type sempre que encontrar logistic_type
                                    if logistic_type:
                                        # shipping_type: fulfillment, xd_drop_off, cross_docking, etc.
                                        order.shipping_type = logistic_type
                                        
                                        if logistic_type == "fulfillment":
                                            logger.info(f"✅ Pedido {order_id_for_logs} é FULFILLMENT - Processando no CD do ML")
                                            logger.info(f"   Mode: {logistic_mode}, Type: {logistic_type}, Substatus: {substatus}")
                                        else:
                                            logger.info(f"📦 Pedido {order_id_for_logs} - Tipo de logística: {logistic_type}")
                                    
                                    # Tracking method e transportadora
                                    tracking_method = shipment_data.get("tracking_method")
                                    if tracking_method:
                                        order.shipping_method = tracking_method
                                    elif not getattr(order, "shipping_method", None) and logistic_type:
                                        # fallback: usar logistic_type quando não houver tracking_method
                                        order.shipping_method = logistic_type
                                    
                                    # Atualizar shipping_status a partir do shipment (mais confiável)
                                    shipment_status = shipment_data.get("status")
                                    if shipment_status:
                                        order.shipping_status = shipment_status
                                        logger.info(f"✅ Shipping status atualizado: {shipment_status}")
                                    
                                    # Status history: definir marcos importantes (DEVE VIR ANTES de shipping_date)
                                    status_history = shipment_data.get("status_history") or {}
                                    date_shipped = status_history.get("date_shipped")
                                    date_delivered = status_history.get("date_delivered")
                                    date_ready_to_ship = status_history.get("date_ready_to_ship")
                                    
                                    logger.info(f"📅 [HISTORY] Shipped: {date_shipped}, Delivered: {date_delivered}, Ready: {date_ready_to_ship}")
                                    
                                    # Atualizar shipping_date usando date_shipped do status_history (mais preciso)
                                    if date_shipped:
                                        try:
                                            order.shipping_date = datetime.fromisoformat(date_shipped.replace('Z', '+00:00'))
                                            logger.info(f"✅ Shipping date atualizado do status_history: {date_shipped}")
                                        except Exception as e:
                                            logger.warning(f"Erro ao parsear date_shipped: {e}")
                                    else:
                                        # Fallback: usar date_created se não tiver date_shipped
                                        shipping_date = shipment_data.get("date_created")
                                        if shipping_date:
                                            try:
                                                order.shipping_date = datetime.fromisoformat(shipping_date.replace('Z', '+00:00'))
                                                logger.info(f"✅ Shipping date atualizado do date_created: {shipping_date}")
                                            except Exception as e:
                                                logger.warning(f"Erro ao parsear shipping_date: {e}")
                                    
                                    # Atualizar data estimada de entrega
                                    shipping_option = shipment_data.get("shipping_option", {})
                                    estimated_delivery = shipping_option.get("estimated_delivery_final", {})
                                    estimated_date = estimated_delivery.get("date")
                                    if estimated_date:
                                        try:
                                            order.estimated_delivery_date = datetime.fromisoformat(estimated_date.replace('Z', '+00:00'))
                                            logger.info(f"✅ Estimated delivery date atualizado: {estimated_date}")
                                        except Exception as e:
                                            logger.warning(f"Erro ao parsear estimated_date: {e}")
                                    
                                    status_updated = True
                                    logger.info(f"✅ [STEP 2] Shipping details processados e salvos para pedido {order_id_for_logs}")
                                    
                            except Exception as e:
                                logger.error(f"❌ [STEP 2] Erro ao buscar detalhes do shipment: {e}")
                                import traceback
                                logger.error(f"Traceback: {traceback.format_exc()}")
                        
                        # Se ainda não identificamos shipping_type, buscar do produto
                        if not order.shipping_type and order_items:
                            try:
                                # Pegar o primeiro item do pedido
                                first_item = order_items[0].get("item", {})
                                item_id = first_item.get("id")
                                
                                if item_id:
                                    logger.info(f"🔍 [STEP 3] Buscando informações do produto {item_id} para verificar shipping_type")
                                    # Buscar produto na API do ML
                                    item_url = f"{self.base_url}/items/{item_id}"
                                    item_response = requests.get(item_url, headers=headers, timeout=30)
                                    
                                    if item_response.status_code == 200:
                                        item_data = item_response.json()
                                        
                                        # Verificar se o produto tem shipping_options com fulfillment
                                        shipping_options = item_data.get("shipping", {}).get("logistic_type")
                                        if shipping_options:
                                            # Se logistic_type é fulfillment, o produto é Fulfillment
                                            if shipping_options == "fulfillment":
                                                order.shipping_type = "fulfillment"
                                                logger.info(f"✅ Pedido {order_id_for_logs} identificado como FULFILLMENT pelo produto ({item_id})")
                                            else:
                                                order.shipping_type = shipping_options
                                                logger.info(f"✅ Pedido {order_id_for_logs} shipping_type do produto: {shipping_options}")
                                        
                                        # Também verificar se tem tags relacionadas a fulfillment
                                        tags = item_data.get("tags", [])
                                        if "fulfillment" in tags or "meli_fulfillment" in tags or "FULL" in tags:
                                            order.shipping_type = "fulfillment"
                                            logger.info(f"✅ Pedido {order_id_for_logs} identificado como FULFILLMENT pelas tags do produto")
                                    
                            except Exception as e:
                                logger.warning(f"Erro ao buscar informações do produto para pedido {order_id_for_logs}: {e}")
            
            except Exception as e:
                logger.warning(f"Erro ao sincronizar status do pedido {order_id_for_logs}: {e}")
            
            # 2. SINCRONIZAR NOTA FISCAL
            logger.info(f"📄 [STEP 4] Iniciando busca de NF para pedido {order_id_for_logs}")
            
            # Tentar buscar NF diretamente pelo order_id primeiro
            invoice_data = None
            logger.info(f"📄 [STEP 4.0] Buscando NF diretamente pelo order_id {order_id_for_logs}")
            try:
                invoice_data = self._check_order_invoice(
                    order_id=str(order_id_for_logs),
                    company_id=order.company_id,
                    access_token=access_token,
                    seller_id=getattr(order, "seller_id", None),
                    ml_account_id=getattr(order, "ml_account_id", None)
                )
                if invoice_data:
                    logger.info(
                        f"   Resultado order_id: has_invoice={invoice_data.get('has_invoice')}, "
                        f"status={invoice_data.get('status')}, number={invoice_data.get('number')}"
                    )
            except Exception as e:
                logger.error(f"❌ Erro ao buscar NF pelo order_id: {e}")
            
            # Se não encontrou pela order, tentar pelo pack_id
            if (not invoice_data or not invoice_data.get('has_invoice')) and order.pack_id:
                logger.info(f"📦 [STEP 4.1] Buscando NF pelo pack_id: {order.pack_id}")
                try:
                    invoice_data = self._check_pack_invoice(order.pack_id, access_token)
                    logger.info(f"   Resultado pack: has_invoice={invoice_data.get('has_invoice') if invoice_data else False}")
                except Exception as e:
                    logger.error(f"❌ Erro ao buscar NF pelo pack_id: {e}")
            
            # Se ainda não encontrou e tem shipment_id, tentar pelo shipment_id (fulfillment)
            if (not invoice_data or not invoice_data.get('has_invoice')) and order.shipping_id:
                logger.info(f"🔍 [STEP 4.2] Buscando NF pelo shipment_id {order.shipping_id}")
                try:
                    invoice_data = self._check_shipment_invoice(
                        shipment_id=order.shipping_id,
                        company_id=order.company_id,
                        access_token=access_token,
                        seller_id=getattr(order, "seller_id", None),
                        ml_account_id=getattr(order, "ml_account_id", None)
                    )
                    logger.info(f"   Resultado shipment: has_invoice={invoice_data.get('has_invoice') if invoice_data else False}")
                except Exception as e:
                    logger.error(f"❌ Erro ao buscar NF pelo shipment_id: {e}")
            
            # Se encontrou NF, atualizar o pedido
            if invoice_data and invoice_data.get('has_invoice'):
                try:
                    order.invoice_emitted = True
                    order.invoice_emitted_at = datetime.now()
                    order.invoice_number = invoice_data.get('number')
                    order.invoice_series = invoice_data.get('series')
                    order.invoice_key = invoice_data.get('key')
                    order.invoice_xml_url = invoice_data.get('xml_url')
                    order.invoice_pdf_url = invoice_data.get('pdf_url')
                    invoice_updated = True
                    logger.info(f"✅ [STEP 4] NF do pedido {order_id_for_logs} sincronizada - Fonte: {invoice_data.get('source')}")
                except Exception as e:
                    logger.warning(f"Erro ao atualizar dados da NF no pedido {order_id_for_logs}: {e}")
            
            # Commit se houver alterações
            if status_updated or invoice_updated:
                self.db.commit()
                return {
                    "success": True,
                    "message": f"Pedido {order_id_for_logs} sincronizado com sucesso",
                    "status_updated": status_updated,
                    "invoice_updated": invoice_updated,
                    "order_data_updated": status_updated  # Indica que dados do pedido foram atualizados
                }
            else:
                return {
                    "success": True,
                    "message": f"Pedido {order_id_for_logs} já está atualizado",
                    "status_updated": False,
                    "invoice_updated": False,
                    "order_data_updated": False
                }
        
        except Exception as e:
            logger.error(f"Erro ao sincronizar pedido {order_id}: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    def emit_invoice_for_order(self, order_id: str, company_id: int, access_token: str) -> Dict:
        """
        Solicita a emissão da nota fiscal via Faturador do Mercado Livre.
        """
        try:
            logger.info(f"🧾 [EMIT] Iniciando emissão da NF para pedido {order_id} (company_id={company_id})")

            order = (
                self.db.query(MLOrder)
                .filter(
                    MLOrder.company_id == company_id,
                    or_(
                        MLOrder.ml_order_id == order_id,
                        MLOrder.order_id == order_id,
                        MLOrder.pack_id == order_id
                    )
                )
                .first()
            )

            if not order:
                return {"success": False, "error": "Pedido não encontrado."}

            # Garantir que temos um token válido usando TokenManager
            from app.services.token_manager import TokenManager
            token_manager = TokenManager(self.db)
            
            # Tentar obter token válido da conta do pedido
            if order.ml_account_id:
                token_record = token_manager.get_token_record_for_account(
                    ml_account_id=order.ml_account_id,
                    company_id=company_id
                )
                if token_record and token_record.access_token:
                    access_token = token_record.access_token
                    logger.info(f"✅ Token obtido da conta ML {order.ml_account_id}")
                else:
                    logger.warning(f"⚠️ Não foi possível obter token válido da conta ML {order.ml_account_id}, usando token fornecido")

            if order.invoice_emitted:
                return {"success": False, "error": "A nota fiscal já foi emitida para este pedido."}

            shipping_details_raw = self._ensure_dict(order.shipping_details)
            logistic_type = (
                (order.shipping_type)
                or shipping_details_raw.get("logistic_type")
                or self._ensure_dict(shipping_details_raw.get("shipping_option")).get("logistic_type")
                or shipping_details_raw.get("mode")
                or ""
            )
            logistic_type = str(logistic_type).lower()

            shipping_id = order.shipping_id
            if not shipping_id:
                shipping_id = shipping_details_raw.get("shipping_id") or shipping_details_raw.get("id")

            seller_id = order.seller_id
            if not seller_id:
                # Usar a conta do ML específica do pedido
                account = None
                if order.ml_account_id:
                    account = (
                        self.db.query(MLAccount)
                        .filter(
                            MLAccount.id == order.ml_account_id,
                            MLAccount.company_id == company_id
                        )
                        .first()
                    )
                
                # Se não encontrou pela conta do pedido, tentar a primeira conta da empresa
                if not account:
                    account = (
                        self.db.query(MLAccount)
                        .filter(MLAccount.company_id == company_id)
                        .first()
                    )
                
                if account and account.ml_user_id:
                    seller_id = account.ml_user_id

            if not seller_id:
                return {"success": False, "error": "Não foi possível identificar o vendedor (seller_id) para emissão da nota."}

            company = self.db.query(Company).filter(Company.id == company_id).first()
            if not company:
                return {"success": False, "error": "Empresa não encontrada."}

            seller_doc_number = self._sanitize_document(company.cnpj)
            seller_doc_type = None

            if not seller_doc_number:
                seller_identification = self._fetch_seller_identification(
                    seller_id=seller_id, 
                    access_token=access_token,
                    ml_account_id=order.ml_account_id if order else None,
                    company_id=company_id
                )
                if seller_identification:
                    seller_doc_number = seller_identification.get("id_number")
                    seller_doc_type = seller_identification.get("id_type")
            
            # Quando usando o faturador do Mercado Livre (endpoint /invoices/orders),
            # não é necessário enviar os dados fiscais do vendedor no payload,
            # pois o ML já possui esses dados cadastrados.
            # Só vamos exigir CNPJ se precisarmos usar o fallback para shipments.
            # Por enquanto, vamos tentar a emissão mesmo sem CNPJ local.
            
            if not seller_doc_type:
                seller_doc_type = "CNPJ" if seller_doc_number and len(seller_doc_number) > 11 else "CPF"

            seller_doc = {
                "id_type": seller_doc_type,
                "id_number": seller_doc_number or "",
                "name": company.razao_social or company.nome_fantasia or company.name or "Empresa"
            }

            # Não vamos verificar a data de liberação previamente
            # A API do ML é a fonte da verdade e já valida isso
            # Se a nota não estiver liberada, a API retornará um erro específico
            # que será tratado no tratamento de erros abaixo

            buyer_ident = self._extract_buyer_identification(order)
            if not buyer_ident:
                buyer_ident = self._fetch_buyer_identification_from_api(order, access_token)
            if not buyer_ident:
                return {
                    "success": False,
                    "error": "Dados fiscais do comprador ausentes (CPF/CNPJ). Atualize o pedido no Mercado Livre e tente novamente."
                }

            receiver_address = self._extract_receiver_address(order)
            missing_address_fields = [
                key for key in ["zip_code", "street_name", "city", "state"]
                if not receiver_address.get(key)
            ]
            if missing_address_fields:
                return {
                    "success": False,
                    "error": f"Endereço incompleto do comprador para emissão da nota (campos ausentes: {', '.join(missing_address_fields)})."
                }

            items, items_total = self._extract_invoice_items(order)
            if not items:
                return {
                    "success": False,
                    "error": "Itens do pedido não encontrados para emissão da nota fiscal."
                }

            total_amount = self._ensure_decimal(order.total_amount)
            if total_amount <= 0:
                total_amount = items_total

            if total_amount <= 0:
                return {
                    "success": False,
                    "error": "Valor total do pedido inválido para emissão da nota fiscal."
                }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            order_ids_payload = self._collect_related_order_ids(order, company_id)
            if not order_ids_payload:
                return {
                    "success": False,
                    "error": "Não foi possível identificar as vendas relacionadas para emissão da nota fiscal."
                }

            orders_url = f"{self.base_url}/users/{seller_id}/invoices/orders"
            orders_payload = {"orders": order_ids_payload}

            logger.info(f"📡 [EMIT] POST {orders_url} payload={orders_payload}")
            response_orders = requests.post(orders_url, headers=headers, json=orders_payload, timeout=30)

            try:
                response_orders_data = response_orders.json()
            except Exception:
                response_orders_data = None

            if response_orders.status_code in (200, 201):
                logger.info(f"✅ [EMIT] Emissão via orders concluída (status HTTP {response_orders.status_code})")
                invoice_data = self._check_order_invoice(
                    order_id=str(order_ids_payload[0]),
                    company_id=company_id,
                    access_token=access_token,
                    seller_id=seller_id,
                    ml_account_id=order.ml_account_id
                )

                if invoice_data and invoice_data.get("has_invoice"):
                    updated_count = self._apply_invoice_to_orders(order_ids_payload, company_id, invoice_data)
                    self.db.commit()
                    return {
                        "success": True,
                        "message": "Nota fiscal emitida com sucesso.",
                        "invoice": invoice_data,
                        "updated_orders": updated_count
                    }

                return {
                    "success": True,
                    "message": "Solicitação de emissão enviada. A nota fiscal será disponibilizada em alguns instantes.",
                    "invoice": response_orders_data
                }

            error_message = None
            release_date_from_error = None
            
            if isinstance(response_orders_data, dict):
                error_message = (
                    response_orders_data.get("message")
                    or response_orders_data.get("error")
                    or response_orders.text
                )
                error_code = response_orders_data.get("error_code")
                
                # Verificar se o erro está relacionado a data de liberação
                release_date_from_error = self._extract_release_date_from_error(response_orders_data)
                
                if error_code:
                    friendly = self._fetch_invoice_error_description(error_code, access_token)
                    if friendly:
                        error_message = friendly
                        response_orders_data["friendly_message"] = friendly
            if not error_message:
                error_message = response_orders.text
            logger.error(
                f"❌ Erro ao emitir NF via orders (status {response_orders.status_code}) "
                f"para pedido {order_id}, payload {order_ids_payload}: {json.dumps(response_orders_data, default=str)}"
            )

            must_fallback_to_shipment = (
                shipping_id
                and logistic_type in {"fulfillment"}
            )

            if not must_fallback_to_shipment:
                # Se encontramos uma data de liberação no erro, formatar mensagem apropriada
                if release_date_from_error:
                    release_local = release_date_from_error.astimezone()
                    release_formatted = release_local.strftime("%d/%m/%Y %H:%M")
                    logger.error(f"❌ Erro ao emitir NF via orders (sem fallback): {error_message}")
                    return {
                        "success": False,
                        "error": (
                            "Esse pedido ainda não está liberado para emissão de NF. "
                            f"Tente novamente após {release_formatted}."
                        ),
                        "release_date": release_date_from_error.isoformat(),
                        "details": response_orders_data
                    }
                
                logger.error(f"❌ Erro ao emitir NF via orders (sem fallback): {error_message}")
                return {
                    "success": False,
                    "error": f"Erro ao emitir nota fiscal: {error_message}",
                    "details": response_orders_data
                }

            logger.info("ℹ️ Emissão via orders falhou; tentando endpoint de shipments como fallback (Fulfillment).")

            # Para o fallback de shipments, precisamos dos dados fiscais do vendedor
            if not seller_doc_number:
                return {
                    "success": False,
                    "error": "CNPJ da empresa não cadastrado. Configure seus dados fiscais no Mercado Livre."
                }

            payload = self._build_invoice_payload(
                order=order,
                items=items,
                total_amount=float(total_amount),
                seller_doc=seller_doc,
                buyer_ident=buyer_ident,
                receiver_address=receiver_address
            )

            url = f"{self.base_url}/users/{seller_id}/invoices/shipments/{shipping_id}"
            logger.info(f"📡 [EMIT] POST {url} payload={payload}")
            response = requests.post(url, headers=headers, json=payload, timeout=30)

            try:
                response_data = response.json()
            except Exception:
                response_data = None

            if response.status_code not in (200, 201):
                error_message = None
                if isinstance(response_data, dict):
                    error_message = response_data.get("message") or response_data.get("error")
                if not error_message:
                    error_message = response.text
                logger.error(
                    f"❌ Erro ao emitir NF via shipments (status {response.status_code}) "
                    f"para pedido {order_id}: {error_message} | response={json.dumps(response_data, default=str)}"
                )
                return {
                    "success": False,
                    "error": f"Erro ao emitir nota fiscal: {error_message}",
                    "details": response_data
                }

            logger.info(f"✅ [EMIT] Solicitação de emissão concluída (status HTTP {response.status_code}) - response={response_data}")

            invoice_data = None
            if order.pack_id:
                invoice_data = self._check_pack_invoice(order.pack_id, access_token)
            if not invoice_data or not invoice_data.get("has_invoice"):
                invoice_data = self._check_shipment_invoice(
                    shipment_id=str(shipping_id),
                    company_id=company_id,
                    access_token=access_token,
                    seller_id=seller_id,
                    ml_account_id=order.ml_account_id
                )

            if invoice_data and invoice_data.get("has_invoice"):
                self._apply_invoice_to_orders(order_ids_payload, company_id, invoice_data)
                self.db.commit()
                return {
                    "success": True,
                    "message": "Nota fiscal emitida com sucesso.",
                    "invoice": invoice_data
                }

            return {
                "success": True,
                "message": "Solicitação de emissão enviada. A nota fiscal será disponibilizada em alguns instantes.",
                "invoice": response_data
            }

        except Exception as exc:
            logger.error(f"❌ Erro ao emitir nota para pedido {order_id}: {exc}", exc_info=True)
            self.db.rollback()
            return {"success": False, "error": f"Erro ao emitir nota fiscal: {exc}"}

    def _check_pack_invoice(self, pack_id: str, access_token: str) -> Optional[Dict]:
        """
        Verifica se um pack tem nota fiscal emitida
        Busca tanto notas fiscais carregadas pelo vendedor quanto emitidas pelo faturador do ML
        """
        try:
            if not pack_id or str(pack_id).lower() in {"none", "null", "0"}:
                logger.info(f"ℹ️ [PACK] pack_id inválido ({pack_id}) - pulando verificação.")
                return {"has_invoice": False}
            
            import requests
            
            headers = {"Authorization": f"Bearer {access_token}"}
            
            logger.info(f"🔍 [PACK] Verificando NF para pack_id={pack_id}")
            
            # 1. Primeiro verificar notas fiscais carregadas no pack (/packs/{pack_id}/fiscal_documents)
            fiscal_docs_url = f"https://api.mercadolibre.com/packs/{pack_id}/fiscal_documents"
            fiscal_response = requests.get(fiscal_docs_url, headers=headers, timeout=30)
            logger.info(f"🔍 [PACK] /fiscal_documents -> {fiscal_response.status_code}")
            
            if fiscal_response.status_code == 200:
                fiscal_data = fiscal_response.json()
                fiscal_docs = fiscal_data.get('fiscal_documents', [])
                
                if fiscal_docs:
                    # Pegar o primeiro documento fiscal
                    doc = fiscal_docs[0]
                    return {
                        "has_invoice": True,
                        "source": "seller_uploaded",
                        "fiscal_document_id": doc.get('id'),
                        "xml_url": None,  # Será buscado individualmente se necessário
                        "pdf_url": None
                    }
            
            # 2. Buscar nota fiscal emitida pelo faturador ML (/packs/{pack_id})
            pack_url = f"https://api.mercadolibre.com/packs/{pack_id}"
            pack_response = requests.get(pack_url, headers=headers, timeout=30)
            logger.info(f"🔍 [PACK] /packs -> {pack_response.status_code}")
            
            if pack_response.status_code == 200:
                pack_data = pack_response.json()
                
                # Buscar shipment_id do pack
                shipment = pack_data.get('shipment', {})
                shipment_id = shipment.get('id')
                
                if shipment_id:
                    # 3. Buscar nota fiscal emitida pelo faturador ML usando shipment_id
                    # Primeiro precisamos pegar o user_id (seller_id) do pack
                    seller_id = pack_data.get('seller_id')
                    
                    if seller_id:
                        # Endpoint da documentação: /users/{user_id}/invoices/shipments/{shipment_id}
                        invoice_url = f"https://api.mercadolibre.com/users/{seller_id}/invoices/shipments/{shipment_id}"
                        invoice_response = requests.get(invoice_url, headers=headers, timeout=30)
                        logger.info(f"🔍 [PACK] /users/{seller_id}/invoices/shipments/{shipment_id} -> {invoice_response.status_code}")
                        
                        if invoice_response.status_code == 200:
                            invoice_data = invoice_response.json()
                            
                            # Verificar se a NF está autorizada
                            if invoice_data.get('status') == 'authorized':
                                attributes = invoice_data.get('attributes', {})
                                
                                # Construir URLs completas
                                xml_path = attributes.get('xml_location')
                                pdf_path = attributes.get('danfe_location')
                                
                                xml_url = f"https://api.mercadolibre.com{xml_path}" if xml_path else None
                                pdf_url = f"https://api.mercadolibre.com{pdf_path}" if pdf_path else None
                                
                                return {
                                    "has_invoice": True,
                                    "source": "ml_biller",
                                    "number": invoice_data.get('invoice_number'),
                                    "series": invoice_data.get('invoice_series'),
                                    "key": attributes.get('invoice_key'),
                                    "xml_url": xml_url,
                                    "pdf_url": pdf_url,
                                    "status": invoice_data.get('status')
                                }
            
            return {"has_invoice": False}
        
        except Exception as e:
            logger.warning(f"Erro ao consultar pack {pack_id}: {e}")
            return {"has_invoice": False, "error": str(e)}
    
    def _check_shipment_invoice(
        self,
        shipment_id: str,
        company_id: int,
        access_token: str,
        seller_id: Optional[str] = None,
        ml_account_id: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Verifica se um shipment tem nota fiscal emitida
        Usa endpoint: /users/{user_id}/invoices/shipments/{shipment_id}
        Usado principalmente para pedidos fulfillment
        """
        try:
            import requests
            
            # Definir seller_id prioritariamente a partir dos parâmetros
            if not seller_id:
                # Se não foi informado seller_id, tentar obter via ml_account_id
                if ml_account_id:
                    account = self.db.query(MLAccount).filter(MLAccount.id == ml_account_id).first()
                    if account and account.ml_user_id:
                        seller_id = account.ml_user_id
                
                # Como fallback final, buscar primeiro pedido da empresa para descobrir seller_id
                if not seller_id:
                    ml_order = self.db.query(MLOrder).filter(MLOrder.company_id == company_id).first()
                    if ml_order and ml_order.seller_id:
                        seller_id = ml_order.seller_id
            
            if not seller_id:
                logger.error(f"❌ Não foi possível obter seller_id para company_id {company_id} e shipment {shipment_id}")
                return {"has_invoice": False}
            
            logger.info(f"🔑 Seller ID obtido: {seller_id} para shipment {shipment_id} (company_id: {company_id})")
            
            # Buscar NF no endpoint de invoices por shipment
            headers = {"Authorization": f"Bearer {access_token}"}
            invoice_url = f"https://api.mercadolibre.com/users/{seller_id}/invoices/shipments/{shipment_id}"
            response = requests.get(invoice_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                invoice_data = response.json()
                
                logger.info(f"📄 Resposta do endpoint shipment invoice: {invoice_data}")
                
                # Verificar se a NF está autorizada e tem dados válidos
                if invoice_data.get('status') == 'authorized' and invoice_data.get('invoice_number'):
                    attributes = invoice_data.get('attributes', {})
                    
                    # Construir URLs completas
                    xml_path = attributes.get('xml_location')
                    pdf_path = attributes.get('danfe_location')
                    
                    xml_url = f"https://api.mercadolibre.com{xml_path}" if xml_path else None
                    pdf_url = f"https://api.mercadolibre.com{pdf_path}" if pdf_path else None
                    
                    return {
                        "has_invoice": True,
                        "source": "ml_biller_shipment",
                        "number": invoice_data.get('invoice_number'),
                        "series": invoice_data.get('invoice_series'),
                        "key": attributes.get('invoice_key'),
                        "xml_url": xml_url,
                        "pdf_url": pdf_url,
                        "status": invoice_data.get('status')
                    }
                else:
                    logger.warning(f"⚠️ Shipment {shipment_id} retornou dados inválidos: status={invoice_data.get('status')}, has_invoice_number={bool(invoice_data.get('invoice_number'))}")
            
            return {"has_invoice": False}
        
        except Exception as e:
            logger.warning(f"Erro ao consultar invoice do shipment {shipment_id}: {e}")
            return {"has_invoice": False, "error": str(e)}
    
    def _check_order_invoice(
        self,
        order_id: str,
        company_id: int,
        access_token: str,
        seller_id: Optional[str] = None,
        ml_account_id: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Verifica se um order tem nota fiscal emitida
        Usa endpoint: /users/{seller_id}/invoices/orders/{order_id}
        Documentação: https://developers.mercadolibre.com/pt_br/notas-fiscais
        """
        try:
            import requests
            
            # Se seller_id não foi informado, tentar obter do próprio pedido
            if not seller_id:
                order_id_str = str(order_id)
                ml_order = self.db.query(MLOrder).filter(
                    MLOrder.company_id == company_id,
                    or_(
                        MLOrder.ml_order_id == order_id,
                        MLOrder.ml_order_id == order_id_str,
                        MLOrder.order_id == order_id_str
                    )
                ).first()
                
                if ml_order and ml_order.seller_id:
                    seller_id = ml_order.seller_id
                elif ml_account_id:
                    account = self.db.query(MLAccount).filter(MLAccount.id == ml_account_id).first()
                    seller_id = account.ml_user_id if account else None
                else:
                    fallback_order = self.db.query(MLOrder).filter(
                        MLOrder.company_id == company_id
                    ).first()
                    seller_id = fallback_order.seller_id if fallback_order else None
            
            if not seller_id:
                logger.error(f"❌ Não encontrou seller_id para company_id {company_id} ao consultar order {order_id}")
                return {"has_invoice": False}
            
            logger.info(f"🔑 Buscando NF para order {order_id} pelo seller_id {seller_id}")
            
            # Usar endpoint correto conforme documentação
            headers = {"Authorization": f"Bearer {access_token}"}
            invoice_url = f"https://api.mercadolibre.com/users/{seller_id}/invoices/orders/{order_id}"
            response = requests.get(invoice_url, headers=headers, timeout=30)
            
            logger.info(f"📡 GET {invoice_url} - Status: {response.status_code}")
            
            if response.status_code == 200:
                invoice_data = response.json()
                logger.info(f"📄 Resposta invoice por order: {invoice_data}")
                
                # Verificar se a NF está autorizada e tem dados válidos
                if invoice_data.get('status') == 'authorized' and invoice_data.get('invoice_number'):
                    attributes = invoice_data.get('attributes', {})
                    
                    # Construir URLs completas
                    xml_path = attributes.get('xml_location')
                    pdf_path = attributes.get('danfe_location')
                    
                    xml_url = f"https://api.mercadolibre.com{xml_path}" if xml_path else None
                    pdf_url = f"https://api.mercadolibre.com{pdf_path}" if pdf_path else None
                    
                    logger.info(f"✅ Invoice encontrada para order {order_id}: número={invoice_data.get('invoice_number')}")
                    
                    return {
                        "has_invoice": True,
                        "source": "invoice_order_endpoint",
                        "number": invoice_data.get('invoice_number'),
                        "series": invoice_data.get('invoice_series'),
                        "key": attributes.get('invoice_key'),
                        "xml_url": xml_url,
                        "pdf_url": pdf_url,
                        "status": invoice_data.get('status')
                    }
                else:
                    logger.warning(f"⚠️ Order {order_id} retornou dados inválidos: status={invoice_data.get('status')}, has_invoice_number={bool(invoice_data.get('invoice_number'))}")
            
            return {"has_invoice": False}
        
        except Exception as e:
            logger.warning(f"Erro ao consultar invoice do order {order_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"has_invoice": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Helpers de emissão
    # ------------------------------------------------------------------

    def _ensure_dict(self, value) -> Dict:
        if not value:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                logger.debug(f"⚠️ Não foi possível converter string em JSON: {value[:120]}...")
        return {}

    def _sanitize_document(self, doc: Optional[str]) -> str:
        if not doc:
            return ""
        return "".join(ch for ch in str(doc) if ch.isdigit())

    def _fetch_seller_identification(
        self, 
        seller_id: Optional[str], 
        access_token: str,
        ml_account_id: Optional[int] = None,
        company_id: Optional[int] = None
    ) -> Optional[Dict[str, str]]:
        if not seller_id:
            return None

        url = f"{self.base_url}/users/{seller_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            # Se receber 403, tentar renovar o token e tentar novamente
            if response.status_code == 403 and ml_account_id and company_id:
                logger.info(f"🔄 Token retornou 403, tentando renovar token para conta ML {ml_account_id}")
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
            
            if response.status_code != 200:
                logger.warning(
                    f"⚠️ Não foi possível obter identificação do vendedor {seller_id}. "
                    f"Status HTTP: {response.status_code}"
                )
                return None

            data = response.json()
            identification = data.get("identification") or {}

            doc_number = (
                identification.get("number")
                or identification.get("id_number")
                or data.get("tax_id")
            )
            doc_number = self._sanitize_document(doc_number)

            if not doc_number:
                return None

            doc_type = (
                identification.get("type")
                or identification.get("id_type")
            )
            if not doc_type:
                doc_type = "CNPJ" if len(doc_number) > 11 else "CPF"

            name = (
                data.get("legal_name")
                or data.get("business_name")
                or data.get("corporate_name")
                or identification.get("name")
                or f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
            )

            return {
                "id_type": str(doc_type).upper(),
                "id_number": doc_number,
                "name": name or None
            }

        except Exception as exc:
            logger.warning(f"⚠️ Erro ao buscar identificação do vendedor {seller_id}: {exc}")
            return None

    def _parse_datetime_value(self, value: Optional[object]) -> Optional[datetime]:
        if not value:
            return None

        if isinstance(value, datetime):
            dt = value
        else:
            text = str(value).strip()
            if not text:
                return None
            if text.endswith("Z"):
                text = text.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(text)
            except ValueError:
                try:
                    dt = datetime.strptime(text, "%Y-%m-%d")
                except ValueError:
                    return None

        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _get_invoice_release_datetime(self, shipping_details: Dict) -> Optional[datetime]:
        if not shipping_details:
            return None

        lead_time = shipping_details.get("lead_time") or {}
        shipping_option = shipping_details.get("shipping_option") or {}
        buffering = lead_time.get("buffering") or shipping_option.get("buffering") or {}
        estimated_delivery_time = (
            lead_time.get("estimated_delivery_time")
            or shipping_option.get("estimated_delivery_time")
            or {}
        )
        pickup_promise = lead_time.get("pickup_promise") or {}

        candidates_raw = [
            buffering.get("date"),
            lead_time.get("estimated_schedule_limit", {}).get("date"),
            estimated_delivery_time.get("pay_before"),
            estimated_delivery_time.get("from"),
            pickup_promise.get("from"),
            shipping_option.get("date_available"),
        ]

        candidates: List[datetime] = []
        for candidate in candidates_raw:
            dt = self._parse_datetime_value(candidate)
            if dt:
                candidates.append(dt)

        if not candidates:
            return None

        now_utc = datetime.now(timezone.utc)
        # Só considerar datas futuras que estejam realmente no futuro (com margem de 30 minutos)
        # Se a data já passou ou está muito próxima, a nota provavelmente já está liberada
        future_candidates = [dt for dt in candidates if dt > now_utc + timedelta(minutes=30)]

        if future_candidates:
            # Retornar apenas a menor data futura se ela estiver realmente no futuro
            return min(future_candidates)

        # Se não há datas futuras significativas, considerar que a nota está liberada
        return None

    def _fetch_buyer_identification_from_api(self, order: MLOrder, access_token: str) -> Optional[Dict[str, str]]:
        if not order or not order.order_id:
            return None

        url = f"{self.base_url}/orders/{order.order_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            # Se receber 403, tentar renovar o token e tentar novamente
            if response.status_code == 403 and order.ml_account_id:
                logger.info(f"🔄 Token retornou 403, tentando renovar token para conta ML {order.ml_account_id}")
                from app.services.token_manager import TokenManager
                token_manager = TokenManager(self.db)
                token_record = token_manager.get_token_record_for_account(
                    ml_account_id=order.ml_account_id,
                    company_id=order.company_id
                )
                if token_record and token_record.access_token:
                    access_token = token_record.access_token
                    headers = {"Authorization": f"Bearer {access_token}"}
                    logger.info(f"✅ Token renovado, tentando novamente")
                    response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.warning(
                    f"⚠️ Não foi possível obter dados fiscais do comprador via API para o pedido {order.order_id}. "
                    f"Status HTTP: {response.status_code}"
                )
                return None

            payload = response.json()
            buyer_payload = payload.get("buyer") or {}
            shipping_payload = payload.get("shipping") or {}
            payments_payload = payload.get("payments")

            receiver_address = (
                shipping_payload.get("receiver_address")
                or shipping_payload.get("destination", {}).get("receiver_address")
                or {}
            )

            candidates: List[Dict] = []
            candidates.append(buyer_payload.get("identification") or {})

            billing_info = buyer_payload.get("billing_info") or payload.get("billing_info") or {}
            if isinstance(billing_info, dict):
                candidates.append({
                    "type": billing_info.get("doc_type"),
                    "number": billing_info.get("doc_number")
                })
                candidates.append(billing_info.get("identification") or {})

            if receiver_address and isinstance(receiver_address, dict):
                candidates.append(receiver_address.get("receiver_identification") or {})
                candidates.append(receiver_address.get("identification") or {})

            if payments_payload:
                for payment in payments_payload:
                    if not isinstance(payment, dict):
                        continue
                    payer = payment.get("payer") or {}
                    candidates.append(payer.get("identification") or {})
                    buyer_payment = payment.get("buyer") or {}
                    candidates.append(buyer_payment.get("identification") or {})

            for candidate in candidates:
                if not candidate or not isinstance(candidate, dict):
                    continue
                doc_number = self._sanitize_document(
                    candidate.get("number")
                    or candidate.get("id_number")
                    or candidate.get("identification_number")
                )
                if doc_number:
                    doc_type = (
                        candidate.get("type")
                        or candidate.get("id_type")
                        or ("CNPJ" if len(doc_number) > 11 else "CPF")
                    )

                    try:
                        if receiver_address:
                            order.shipping_address = receiver_address
                        if shipping_payload:
                            order.shipping_details = shipping_payload
                        if payments_payload:
                            order.payments = payments_payload
                        self.db.flush()
                    except Exception as exc_flush:
                        logger.warning(f"⚠️ Não foi possível atualizar o pedido com dados do comprador: {exc_flush}")
                        self.db.rollback()

                    return {
                        "id_type": str(doc_type).upper(),
                        "id_number": doc_number
                    }

            shipping_id = (
                str(shipping_payload.get("id"))
                if isinstance(shipping_payload, dict) and shipping_payload.get("id")
                else order.shipping_id
            )
            if shipping_id and not isinstance(shipping_id, str):
                shipping_id = str(shipping_id)

            if shipping_id:
                try:
                    billing_url = f"{self.base_url}/shipments/{shipping_id}/billing_info"
                    billing_response = requests.get(billing_url, headers=headers, timeout=30)
                    if billing_response.status_code == 200:
                        billing_data = billing_response.json() or {}
                        receiver_info = billing_data.get("receiver") or {}
                        receiver_doc = receiver_info.get("document") or {}
                        doc_number = self._sanitize_document(
                            receiver_doc.get("value")
                            or receiver_doc.get("number")
                            or receiver_doc.get("id_number")
                        )
                        if doc_number:
                            doc_type = receiver_doc.get("id") or receiver_doc.get("type")
                            if not doc_type:
                                doc_type = "CNPJ" if len(doc_number) > 11 else "CPF"

                            try:
                                if receiver_address:
                                    order.shipping_address = receiver_address
                                if shipping_payload and not order.shipping_details:
                                    order.shipping_details = shipping_payload
                                if payments_payload and not order.payments:
                                    order.payments = payments_payload
                                if shipping_id:
                                    order.shipping_id = shipping_id
                                self.db.flush()
                            except Exception as exc_flush:
                                logger.warning(f"⚠️ Não foi possível atualizar o pedido com dados do comprador (billing_info): {exc_flush}")
                                self.db.rollback()

                            return {
                                "id_type": str(doc_type).upper(),
                                "id_number": doc_number
                            }
                    else:
                        logger.warning(
                            f"⚠️ billing_info do shipment {shipping_id} retornou status {billing_response.status_code}"
                        )
                except Exception as exc_billing:
                    logger.warning(f"⚠️ Erro ao buscar billing_info para shipment {shipping_id}: {exc_billing}")

            logger.warning(
                f"⚠️ Pedido {order.order_id} retornado pela API sem identificação fiscal do comprador."
            )
            return None

        except Exception as exc:
            logger.warning(f"⚠️ Erro ao buscar identificação do comprador via API para o pedido {order.order_id}: {exc}")
            return None

    def _ensure_decimal(self, value) -> Decimal:
        try:
            if value is None:
                return Decimal("0")
            if isinstance(value, Decimal):
                return value
            return Decimal(str(value))
        except Exception:
            return Decimal("0")

    def _extract_buyer_identification(self, order: MLOrder) -> Optional[Dict[str, str]]:
        shipping_details = self._ensure_dict(order.shipping_details)
        shipping_address = self._ensure_dict(order.shipping_address)

        candidates = []

        destination = self._ensure_dict(shipping_details.get("destination"))
        candidates.append(self._ensure_dict(destination.get("receiver_identification")))
        destination_receiver = self._ensure_dict(destination.get("receiver"))
        candidates.append(self._ensure_dict(destination_receiver.get("identification")))

        receiver_address = self._ensure_dict(destination.get("receiver_address"))
        if not receiver_address:
            receiver_address = self._ensure_dict(shipping_details.get("receiver_address"))
        if not receiver_address:
            receiver_address = shipping_address

        candidates.append(self._ensure_dict(receiver_address.get("receiver_identification")))
        candidates.append(self._ensure_dict(receiver_address.get("identification")))

        candidates.append(self._ensure_dict(shipping_address.get("receiver_identification")))
        candidates.append(self._ensure_dict(shipping_address.get("identification")))

        payments_data = order.payments
        if payments_data:
            if isinstance(payments_data, str):
                try:
                    payments_data = json.loads(payments_data)
                except Exception:
                    payments_data = []
            if isinstance(payments_data, list):
                for payment in payments_data:
                    payment_dict = self._ensure_dict(payment)
                    payer = self._ensure_dict(payment_dict.get("payer"))
                    candidates.append(self._ensure_dict(payer.get("identification")))
                    buyer = self._ensure_dict(payment_dict.get("buyer"))
                    candidates.append(self._ensure_dict(buyer.get("identification")))

        for candidate in candidates:
            if not candidate:
                continue
            if isinstance(candidate, dict):
                doc_type = candidate.get("type") or candidate.get("id_type") or candidate.get("identification_type")
                doc_number = candidate.get("number") or candidate.get("id_number") or candidate.get("identification_number")
            else:
                doc_type = None
                doc_number = str(candidate)

            doc_number = self._sanitize_document(doc_number)
            if doc_number:
                if not doc_type:
                    doc_type = "CPF" if len(doc_number) <= 11 else "CNPJ"
                return {"id_type": doc_type.upper(), "id_number": doc_number}

        return None

    def _extract_receiver_address(self, order: MLOrder) -> Dict[str, str]:
        shipping_details = self._ensure_dict(order.shipping_details)
        shipping_address = self._ensure_dict(order.shipping_address)

        destination = self._ensure_dict(shipping_details.get("destination"))
        receiver_address = self._ensure_dict(destination.get("receiver_address"))

        if not receiver_address:
            receiver_address = self._ensure_dict(shipping_details.get("receiver_address"))
        if not receiver_address:
            receiver_address = shipping_address

        state = receiver_address.get("state") or shipping_address.get("state") or {}
        city = receiver_address.get("city") or shipping_address.get("city") or {}

        street_name = (
            receiver_address.get("street_name")
            or receiver_address.get("address_line")
            or shipping_address.get("street_name")
            or shipping_address.get("address_line")
        )

        street_number = (
            receiver_address.get("street_number")
            or receiver_address.get("number")
            or shipping_address.get("street_number")
            or shipping_address.get("number")
            or "SN"
        )

        state_name = state
        if isinstance(state, dict):
            state_name = state.get("name") or state.get("id")
        city_name = city
        if isinstance(city, dict):
            city_name = city.get("name") or city.get("id")

        zip_code = (
            receiver_address.get("zip_code")
            or shipping_address.get("zip_code")
            or shipping_address.get("zip_code_prefix")
        )

        if zip_code and isinstance(zip_code, dict):
            zip_code = zip_code.get("id") or zip_code.get("value")

        return {
            "street_name": (street_name or "").strip(),
            "street_number": str(street_number).strip() if street_number else "SN",
            "zip_code": self._sanitize_document(zip_code) if zip_code else "",
            "city": (city_name or "").strip(),
            "state": (state_name or "").strip(),
            "country": (receiver_address.get("country") or shipping_address.get("country") or {}).get("id", "BR")
            if isinstance(receiver_address.get("country") or shipping_address.get("country"), dict)
            else (receiver_address.get("country") or shipping_address.get("country") or "BR")
        }

    def _extract_invoice_items(self, order: MLOrder) -> Tuple[List[Dict], Decimal]:
        items_raw = order.order_items or []
        if isinstance(items_raw, str):
            try:
                items_raw = json.loads(items_raw)
            except Exception:
                items_raw = []

        items: List[Dict] = []
        total = Decimal("0")

        for idx, entry in enumerate(items_raw):
            entry_dict = self._ensure_dict(entry)
            item_data = self._ensure_dict(entry_dict.get("item"))

            quantity = entry_dict.get("quantity") or item_data.get("quantity") or 1
            try:
                quantity = int(quantity)
            except Exception:
                quantity = 1

            unit_price = (
                entry_dict.get("unit_price")
                or item_data.get("unit_price")
                or entry_dict.get("full_unit_price")
                or item_data.get("full_unit_price")
            )
            unit_price = float(unit_price) if unit_price is not None else 0.0

            if unit_price <= 0:
                continue

            total_line = self._ensure_decimal(unit_price) * self._ensure_decimal(quantity)
            total += total_line

            sku = (
                entry_dict.get("seller_sku")
                or entry_dict.get("seller_custom_field")
                or item_data.get("seller_sku")
                or item_data.get("seller_custom_field")
            )

            items.append({
                "code": sku or item_data.get("id") or f"ITEM-{idx + 1}",
                "description": item_data.get("title") or entry_dict.get("title") or "Item",
                "quantity": quantity,
                "unit_price": float(unit_price),
                "total_amount": float(total_line),
                "sku": sku,
                "category_id": item_data.get("category_id")
            })

        return items, total

    def _build_invoice_payload(
        self,
        order: MLOrder,
        items: List[Dict],
        total_amount: float,
        seller_doc: Dict[str, str],
        buyer_ident: Dict[str, str],
        receiver_address: Dict[str, str],
    ) -> Dict:
        receiver_name = (
            receiver_address.get("receiver_name")
            or receiver_address.get("name")
            or self._ensure_dict(order.shipping_address).get("receiver_name")
            or "Cliente Mercado Livre"
        )

        payload = {
            "issuer": {
                "name": seller_doc.get("name"),
                "id_type": seller_doc.get("id_type"),
                "id_number": seller_doc.get("id_number"),
            },
            "receiver": {
                "name": receiver_name,
                "id_type": buyer_ident.get("id_type"),
                "id_number": buyer_ident.get("id_number"),
                "address": {
                    "zip_code": receiver_address.get("zip_code"),
                    "street_name": receiver_address.get("street_name"),
                    "street_number": receiver_address.get("street_number"),
                    "city": receiver_address.get("city"),
                    "state": receiver_address.get("state"),
                    "country": receiver_address.get("country") or "BR",
                },
            },
            "items": [
                {
                    "code": item.get("code"),
                    "description": item.get("description"),
                    "quantity": item.get("quantity"),
                    "unit_price": item.get("unit_price"),
                    "total_amount": item.get("total_amount"),
                    "sku": item.get("sku"),
                    "category_id": item.get("category_id"),
                }
                for item in items
            ],
            "total_amount": total_amount,
            "currency_id": order.currency_id or "BRL",
        }

        # Informações adicionais opcionais
        if order.pack_id:
            payload["pack_id"] = order.pack_id
        if order.shipping_id:
            payload["shipping_id"] = str(order.shipping_id)

        payments_data = order.payments
        payment_methods = []
        if payments_data:
            if isinstance(payments_data, str):
                try:
                    payments_data = json.loads(payments_data)
                except Exception:
                    payments_data = []
            if isinstance(payments_data, list):
                for payment in payments_data:
                    payment_dict = self._ensure_dict(payment)
                    payment_methods.append({
                        "transaction_amount": payment_dict.get("transaction_amount"),
                        "currency_id": payment_dict.get("currency_id"),
                        "payment_method": payment_dict.get("payment_method_id"),
                        "installments": payment_dict.get("installments"),
                    })
        if payment_methods:
            payload["payments"] = payment_methods

        return payload

    def _collect_related_order_ids(self, order: MLOrder, company_id: int) -> List[int]:
        order_ids: List[int] = []

        def _try_add(value):
            try:
                if value is None:
                    return
                numeric = int(str(value))
                if numeric not in order_ids:
                    order_ids.append(numeric)
            except (TypeError, ValueError):
                return

        _try_add(order.ml_order_id)
        _try_add(order.order_id)

        if order.pack_id:
            related_orders = (
                self.db.query(MLOrder)
                .filter(
                    MLOrder.company_id == company_id,
                    MLOrder.pack_id == order.pack_id
                )
                .all()
            )
            for related in related_orders:
                _try_add(related.ml_order_id)
                _try_add(related.order_id)

        return order_ids

    def _extract_release_date_from_error(self, error_data: Dict) -> Optional[datetime]:
        """Extrai a data de liberação de uma resposta de erro da API do ML."""
        if not isinstance(error_data, dict):
            return None
        
        # Procurar por campos comuns que podem conter a data de liberação
        date_fields = [
            "available_after",
            "release_date",
            "available_date",
            "pay_before",
            "buffering_date"
        ]
        
        for field in date_fields:
            date_value = error_data.get(field)
            if date_value:
                dt = self._parse_datetime_value(date_value)
                if dt:
                    return dt
        
        # Procurar em estruturas aninhadas
        if "cause" in error_data and isinstance(error_data["cause"], list):
            for cause_item in error_data["cause"]:
                if isinstance(cause_item, dict):
                    for field in date_fields:
                        date_value = cause_item.get(field)
                        if date_value:
                            dt = self._parse_datetime_value(date_value)
                            if dt:
                                return dt
        
        return None

    def _fetch_invoice_error_description(self, error_code: Optional[str], access_token: str) -> Optional[str]:
        if not error_code:
            return None
        try:
            url = f"{self.base_url}/users/invoices/errors/MLB/{error_code}"
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("display_message") or data.get("message")
            logger.warning(f"⚠️ Não foi possível obter descrição do erro {error_code}: status {response.status_code}")
        except Exception as exc:
            logger.warning(f"⚠️ Falha ao consultar descrição do erro {error_code}: {exc}")
        return None

    def _apply_invoice_to_orders(self, order_ids: List[int], company_id: int, invoice_data: Dict) -> int:
        updated = 0
        for oid in order_ids:
            order_record = (
                self.db.query(MLOrder)
                .filter(
                    MLOrder.company_id == company_id,
                    or_(
                        MLOrder.ml_order_id == str(oid),
                        MLOrder.order_id == str(oid)
                    )
                )
                .first()
            )
            if not order_record:
                continue
            self._apply_invoice_to_order(order_record, invoice_data)
            updated += 1
        return updated

    def _apply_invoice_to_order(self, order: MLOrder, invoice_data: Dict) -> None:
        order.invoice_emitted = True
        order.invoice_emitted_at = datetime.now()
        order.invoice_number = invoice_data.get("number") or order.invoice_number
        order.invoice_series = invoice_data.get("series") or order.invoice_series
        order.invoice_key = invoice_data.get("key") or order.invoice_key
        order.invoice_xml_url = invoice_data.get("xml_url") or order.invoice_xml_url
        order.invoice_pdf_url = invoice_data.get("pdf_url") or order.invoice_pdf_url

