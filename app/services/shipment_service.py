"""
Serviço para gerenciar expedição e notas fiscais
"""
import requests
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.saas_models import MLOrder, OrderStatus

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
                            invoice_data = self._check_shipment_invoice(order.shipping_id, company_id, access_token)
                        
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
            
            # Buscar o pedido específico - tentar múltiplos campos
            # O order_id pode ser: ml_order_id, order_id, sale_id ou pack_id
            order = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id,
                or_(
                    MLOrder.ml_order_id == order_id,
                    MLOrder.order_id == order_id,
                    MLOrder.sale_id == order_id,
                    MLOrder.pack_id == order_id
                )
            ).first()
            
            if not order:
                return {
                    "success": False,
                    "error": f"Pedido {order_id} não encontrado (busca por ml_order_id, order_id, sale_id ou pack_id)"
                }
            
            # Usar order_id para buscar na API do Mercado Livre
            # O order_id é o ID que o ML espera (normalmente igual ao ml_order_id)
            api_order_id = str(order.order_id)
            
            # Para logs, usar o order_id
            order_id_for_logs = str(order.order_id)
            
            # 1. SINCRONIZAR STATUS DO PEDIDO
            status_updated = False
            try:
                import requests
                order_url = f"{self.base_url}/orders/{api_order_id}"
                headers = {"Authorization": f"Bearer {access_token}"}
                response = requests.get(order_url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    order_data = response.json()
                    
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
                            from datetime import datetime
                            parsed_date = datetime.fromisoformat(date_created.replace('Z', '+00:00'))
                            if parsed_date != order.date_created:
                                order.date_created = parsed_date
                                status_updated = True
                        except:
                            pass
                    
                    date_closed = order_data.get("date_closed")
                    if date_closed:
                        try:
                            from datetime import datetime
                            parsed_date = datetime.fromisoformat(date_closed.replace('Z', '+00:00'))
                            if parsed_date != order.date_closed:
                                order.date_closed = parsed_date
                                status_updated = True
                        except:
                            pass
                    
                    last_updated = order_data.get("last_updated")
                    if last_updated:
                        try:
                            from datetime import datetime
                            parsed_date = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                            if parsed_date != order.last_updated:
                                order.last_updated = parsed_date
                                status_updated = True
                        except:
                            pass
                    
                    # 6. Atualizar sale_id (número da venda real)
                    # O sale_id pode estar em diferentes lugares na resposta
                    sale_id = order_data.get("sale_id") or order_data.get("id")
                    if sale_id and str(sale_id) != str(order.sale_id):
                        order.sale_id = str(sale_id)
                        status_updated = True
                        logger.info(f"🆔 Sale ID atualizado: {order.sale_id} -> {sale_id}")
                    
                    # 7. Atualizar status_detail
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
                        
                        # Se não identificamos como fulfillment pelo pack_id, tentar outras formas
                        if not order.shipping_type:
                            # Tentar extrair shipping_type básico se não há shipment_id
                            if not shipping_id_from_api:
                                # Verificar se há informações de logística no shipping básico
                                logistic_type = shipping.get("logistic_type")
                                if logistic_type:
                                    order.shipping_type = logistic_type
                                    logger.info(f"✅ Pedido {order_id_for_logs} shipping_type atualizado do shipping: {logistic_type}")
                                    if logistic_type == "fulfillment":
                                        logger.info(f"✅ Pedido {order_id_for_logs} identificado como FULFILLMENT (shipping.logistic_type)")
                            else:
                                # Se tem shipping_id, buscar dados completos do shipment
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
                                        try:
                                            order.shipping_details = shipment_data
                                        except Exception:
                                            pass
                                        
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
                                        
                                        # Status history: definir marcos importantes (DEVE VIR ANTES de shipping_date)
                                        status_history = shipment_data.get("status_history") or {}
                                        date_shipped = status_history.get("date_shipped")
                                        date_delivered = status_history.get("date_delivered")
                                        date_ready_to_ship = status_history.get("date_ready_to_ship")
                                        
                                        # Atualizar shipping_date usando date_shipped do status_history (mais preciso)
                                        if date_shipped:
                                            try:
                                                from datetime import datetime
                                                order.shipping_date = datetime.fromisoformat(date_shipped.replace('Z', '+00:00'))
                                                logger.info(f"✅ Shipping date atualizado do status_history: {date_shipped}")
                                            except:
                                                pass
                                        else:
                                            # Fallback: usar date_created se não tiver date_shipped
                                            shipping_date = shipment_data.get("date_created")
                                            if shipping_date:
                                                try:
                                                    from datetime import datetime
                                                    order.shipping_date = datetime.fromisoformat(shipping_date.replace('Z', '+00:00'))
                                                except:
                                                    pass
                                        
                                        # Atualizar data estimada de entrega
                                        shipping_option = shipment_data.get("shipping_option", {})
                                        estimated_delivery = shipping_option.get("estimated_delivery_final", {})
                                        estimated_date = estimated_delivery.get("date")
                                        if estimated_date:
                                            try:
                                                from datetime import datetime
                                                order.estimated_delivery_date = datetime.fromisoformat(estimated_date.replace('Z', '+00:00'))
                                            except:
                                                pass
                                        
                                        # Ajustar status do pedido com base no shipment (prioridade alta)
                                        # NOTA: date_shipped, date_delivered, date_ready_to_ship já foram extraídos acima
                                        if date_delivered or shipment_status == "delivered":
                                            target_status = OrderStatus.DELIVERED
                                        elif shipment_status == "shipped" or date_shipped:
                                            target_status = OrderStatus.SHIPPED
                                        elif shipment_status == "ready_to_ship" or date_ready_to_ship:
                                            target_status = OrderStatus.PAID
                                        else:
                                            target_status = None
                                        
                                        if target_status and order.status != target_status:
                                            if self.should_update_status(order.status, target_status, order.status_manual):
                                                logger.info(f"🔄 [STATUS] Atualizando por shipment.status/history: {order.status} -> {target_status}")
                                                order.status = target_status
                                                if order.status_manual:
                                                    order.status_manual = False
                                                    order.status_manual_date = None
                                                status_updated = True
                                        
                                        # ATUALIZAR STATUS BASEADO NO SUBSTATUS (fulfillment)
                                        # Baseado na documentação oficial do Mercado Livre
                                        if substatus:
                                            substatus_mapping = {
                                                # Substatus de fulfillment - ready_to_ship
                                                "in_warehouse": OrderStatus.PAID,  # Processando no centro de distribuição
                                                "ready_to_print": OrderStatus.PAID,
                                                "printed": OrderStatus.PAID,
                                                "ready_to_pack": OrderStatus.PAID,
                                                "ready_to_ship": OrderStatus.PAID,
                                                "in_pickup_list": OrderStatus.PAID,
                                                "ready_for_pickup": OrderStatus.PAID,
                                                "ready_for_dropoff": OrderStatus.PAID,
                                                "picked_up": OrderStatus.PAID,
                                                "dropped_off": OrderStatus.PAID,
                                                "in_hub": OrderStatus.PAID,
                                                "packed": OrderStatus.PAID,
                                                "on_hold": OrderStatus.PAID,
                                                "rejected_in_hub": OrderStatus.CANCELLED,
                                                
                                                # Substatus de shipped
                                                "shipped": OrderStatus.SHIPPED,
                                                "in_transit": OrderStatus.SHIPPED,
                                                "out_for_delivery": OrderStatus.SHIPPED,
                                                "soon_deliver": OrderStatus.SHIPPED,
                                                "at_customs": OrderStatus.SHIPPED,
                                                "delayed_at_customs": OrderStatus.SHIPPED,
                                                "left_customs": OrderStatus.SHIPPED,
                                                
                                                # Substatus de delivered
                                                "delivered": OrderStatus.DELIVERED,
                                                "inferred": OrderStatus.DELIVERED,
                                                
                                                # Substatus de not_delivered / cancelled
                                                "lost": OrderStatus.CANCELLED,
                                                "damaged": OrderStatus.CANCELLED,
                                                "returning_to_sender": OrderStatus.CANCELLED,
                                                "returned": OrderStatus.CANCELLED,
                                                "destroyed": OrderStatus.CANCELLED,
                                                "stolen": OrderStatus.CANCELLED,
                                                "confiscated": OrderStatus.CANCELLED,
                                                "cancelled_measurement_exceeded": OrderStatus.CANCELLED,
                                                "closed_by_user": OrderStatus.CANCELLED,
                                                "pack_splitted": OrderStatus.CANCELLED
                                            }
                                            
                                            substatus_status = substatus_mapping.get(substatus)
                                            if substatus_status and order.status != substatus_status:
                                                # Verificar se deve atualizar o status (respeitando status manual)
                                                if self.should_update_status(order.status, substatus_status, order.status_manual):
                                                    logger.info(f"🔄 [STATUS] Atualizando status baseado no substatus: {order.status} -> {substatus_status} (substatus: {substatus})")
                                                    order.status = substatus_status
                                                    # Se atualizar via API, remover flag manual
                                                    if order.status_manual:
                                                        order.status_manual = False
                                                        order.status_manual_date = None
                                                        logger.info(f"🔄 Status manual removido (atualizado via substatus)")
                                                    status_updated = True
                                                else:
                                                    logger.info(f"⏸️ Status manual preservado: {order.status} (substatus sugeriria {substatus_status})")
                                    
                                except Exception as e:
                                    logger.warning(f"Erro ao buscar detalhes do shipment {shipping_id_from_api}: {e}")
                            
                            # Se ainda não identificamos shipping_type, buscar do produto
                            if not order.shipping_type and order_items:
                                try:
                                    # Pegar o primeiro item do pedido
                                    first_item = order_items[0].get("item", {})
                                    item_id = first_item.get("id")
                                    
                                    if item_id:
                                        logger.info(f"🔍 Buscando informações do produto {item_id} para verificar shipping_type")
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
            invoice_updated = False
            
            logger.info(f"========== [INICIO] Buscando NF para pedido {order_id_for_logs} ==========")
            logger.info(f"Pack ID: {order.pack_id}")
            logger.info(f"Shipping ID: {order.shipping_id}")
            
            # Tentar buscar NF usando pack_id OU shipment_id OU sale_id
            invoice_data = None
            
            if order.pack_id:
                logger.info(f"📦 Tentando buscar NF pelo pack_id: {order.pack_id}")
                # Buscar NF pelo pack_id
                try:
                    invoice_data = self._check_pack_invoice(order.pack_id, access_token)
                    logger.info(f"Resultado pack_id: has_invoice={invoice_data.get('has_invoice') if invoice_data else False}")
                except Exception as e:
                    logger.warning(f"ERRO ao buscar NF pelo pack_id: {e}")
            
            # Se não encontrou pelo pack_id e tem shipment_id, tentar pelo shipment_id (fulfillment)
            if (not invoice_data or not invoice_data.get('has_invoice')) and order.shipping_id:
                logger.info(f"🔍 Buscando NF pelo shipment_id {order.shipping_id} para pedido {order_id_for_logs}")
                logger.info(f"   Company ID: {order.company_id}, Pack ID: {order.pack_id}")
                try:
                    invoice_data = self._check_shipment_invoice(order.shipping_id, order.company_id, access_token)
                    logger.info(f"📄 Resultado busca NF: has_invoice={invoice_data.get('has_invoice') if invoice_data else False}")
                except Exception as e:
                    logger.error(f"❌ Erro ao buscar NF pelo shipment_id: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Se ainda não encontrou, tentar buscar pelo sale_id (número da venda real)
            if not invoice_data or not invoice_data.get('has_invoice'):
                if hasattr(order, 'sale_id') and order.sale_id:
                    try:
                        logger.info(f"🔍 Buscando NF pelo sale_id {order.sale_id} (número da venda real)")
                        invoice_data = self._check_order_invoice(order.sale_id, company_id, access_token)
                        logger.info(f"📄 Resultado busca NF por sale_id: has_invoice={invoice_data.get('has_invoice') if invoice_data else False}")
                    except Exception as e:
                        logger.error(f"❌ Erro ao buscar NF pelo sale_id: {e}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Se ainda não encontrou, tentar buscar pelo order_id diretamente (documentação ML)
            if not invoice_data or not invoice_data.get('has_invoice'):
                try:
                    logger.info(f"🔍 Buscando NF pelo order_id {api_order_id} (método direto)")
                    invoice_data = self._check_order_invoice(api_order_id, company_id, access_token)
                    logger.info(f"📄 Resultado busca NF por order_id: has_invoice={invoice_data.get('has_invoice') if invoice_data else False}")
                except Exception as e:
                    logger.error(f"❌ Erro ao buscar NF pelo order_id: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Log para debug se não encontrou NF
            if not invoice_data or not invoice_data.get('has_invoice'):
                logger.warning(f"⚠️ Pedido {order_id_for_logs} não tem NF disponível - Pack ID: {order.pack_id}, Shipping ID: {order.shipping_id}")
            
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
                    logger.info(f"✅ NF do pedido {order_id_for_logs} sincronizada - Fonte: {invoice_data.get('source')}")
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

    def _check_pack_invoice(self, pack_id: str, access_token: str) -> Optional[Dict]:
        """
        Verifica se um pack tem nota fiscal emitida
        Busca tanto notas fiscais carregadas pelo vendedor quanto emitidas pelo faturador do ML
        """
        try:
            import requests
            
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # 1. Primeiro verificar notas fiscais carregadas no pack (/packs/{pack_id}/fiscal_documents)
            fiscal_docs_url = f"https://api.mercadolibre.com/packs/{pack_id}/fiscal_documents"
            fiscal_response = requests.get(fiscal_docs_url, headers=headers, timeout=30)
            
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
    
    def _check_shipment_invoice(self, shipment_id: str, company_id: int, access_token: str) -> Optional[Dict]:
        """
        Verifica se um shipment tem nota fiscal emitida
        Usa endpoint: /users/{user_id}/invoices/shipments/{shipment_id}
        Usado principalmente para pedidos fulfillment
        """
        try:
            import requests
            
            # Buscar seller_id da empresa - filtrar por company_id específico
            ml_account = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id
            ).first()
            
            if not ml_account:
                logger.error(f"❌ Não encontrou MLOrder para company_id {company_id}")
                return {"has_invoice": False}
            
            # Verificar se tem seller_id
            if not ml_account.seller_id:
                logger.error(f"❌ MLOrder para company_id {company_id} não tem seller_id")
                return {"has_invoice": False}
            
            seller_id = ml_account.seller_id
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
    
    def _check_order_invoice(self, order_id: str, company_id: int, access_token: str) -> Optional[Dict]:
        """
        Verifica se um order tem nota fiscal emitida
        Usa endpoint: /users/{seller_id}/invoices/orders/{order_id}
        Documentação: https://developers.mercadolibre.com/pt_br/notas-fiscais
        """
        try:
            import requests
            
            # Buscar seller_id da empresa - filtrar por company_id específico
            ml_account = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id
            ).first()
            
            if not ml_account or not ml_account.seller_id:
                logger.error(f"❌ Não encontrou seller_id para company_id {company_id}")
                return {"has_invoice": False}
            
            seller_id = ml_account.seller_id
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

