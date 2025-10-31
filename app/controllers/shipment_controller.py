"""
Controller para expedição e notas fiscais
"""
import logging
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import String

from app.services.shipment_service import ShipmentService
from app.models.saas_models import MLOrder, OrderStatus

logger = logging.getLogger(__name__)

class ShipmentController:
    def __init__(self, db: Session):
        self.db = db
        self.service = ShipmentService(db)

    def list_pending_shipments(self, company_id: int, search: str = "", invoice_status: str = "", 
                               status: str = "", page: int = 1, limit: int = 100, 
                               start_date: str = None, end_date: str = None) -> Dict:
        """
        Lista pedidos para expedição com paginação
        Retorna pedidos paginados (todos os status) para exibir em todas as abas
        """
        try:
            from sqlalchemy import text
            from datetime import datetime
            
            # Construir query SQL com filtros dinâmicos
            sql = """
                SELECT 
                    ml_orders.*,
                    ml_orders.ml_order_id,
                    ml_orders.order_id,
                    ml_orders.buyer_first_name,
                    ml_orders.buyer_nickname,
                    ml_orders.total_amount,
                    ml_orders.status,
                    ml_orders.date_created,
                    ml_orders.invoice_emitted,
                    ml_orders.invoice_number,
                    ml_orders.invoice_series,
                    ml_orders.invoice_key,
                    ml_orders.invoice_pdf_url,
                    ml_orders.invoice_xml_url,
                    ml_orders.pack_id,
                    ml_orders.shipping_type,
                    ml_orders.shipping_details,
                    ml_orders.payments,
                    ml_orders.order_items,
                    ml_orders.shipping_address,
                    ml_orders.shipping_id,
                    ml_orders.shipping_status,
                    ml_orders.shipping_method,
                    ml_orders.shipping_date,
                    ml_orders.estimated_delivery_date
                FROM ml_orders
                WHERE ml_orders.company_id = :company_id
            """
            
            params = {"company_id": company_id}
            
            # Aplicar filtro de busca
            if search:
                sql += """
                    AND (
                        CAST(ml_order_id AS VARCHAR) ILIKE :search
                        OR order_id ILIKE :search
                        OR buyer_nickname ILIKE :search
                        OR buyer_first_name ILIKE :search
                    )
                """
                params["search"] = f"%{search}%"
            
            # Aplicar filtro de data inicial
            if start_date:
                sql += " AND ml_orders.date_created >= CAST(:start_date AS DATE)"
                params["start_date"] = start_date
            
            # Aplicar filtro de data final
            if end_date:
                sql += " AND ml_orders.date_created <= CAST(:end_date AS DATE)"
                params["end_date"] = end_date
            
            # Aplicar filtro de status da nota fiscal
            if invoice_status == "emitted":
                sql += " AND invoice_emitted = true"
            elif invoice_status == "pending":
                sql += " AND invoice_emitted = false"
            
            # Aplicar filtro de status do pedido
            if status:
                if status == "READY_TO_PREPARE":
                    sql += " AND status = 'READY_TO_PREPARE'"
                else:
                    sql += f" AND status = :status_filter"
                    params["status_filter"] = status
            
            # Contar total
            count_sql = f"SELECT COUNT(*) as total FROM ({sql}) as filtered_orders"
            count_result = self.db.execute(text(count_sql), params).first()
            total_count = count_result[0] if count_result else 0
            
            # Aplicar paginação
            offset = (page - 1) * limit
            sql += " ORDER BY date_created DESC OFFSET :offset LIMIT :limit"
            params["offset"] = offset
            params["limit"] = limit
            
            # Calcular total de páginas
            total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
            
            # Executar query
            results = self.db.execute(text(sql), params)
            
            result = []
            for row in results:
                # Converter status para string - garantir que seja maiúsculo
                status_value = row.status
                if status_value:
                    status_str = str(status_value).upper()
                else:
                    status_str = None
                
                # Converter datetime para ISO string
                date_created = row.date_created
                if date_created and hasattr(date_created, 'isoformat'):
                    date_created_str = date_created.isoformat()
                else:
                    date_created_str = str(date_created) if date_created else None
                
                # Converter shipping_details para dict se necessário
                shipping_details_data = None
                if row.shipping_details:
                    import json
                    if isinstance(row.shipping_details, dict):
                        shipping_details_data = row.shipping_details
                    elif isinstance(row.shipping_details, str):
                        try:
                            shipping_details_data = json.loads(row.shipping_details)
                        except:
                            shipping_details_data = row.shipping_details
                
                order_dict = {
                    "id": row.id,
                    "order_id": row.order_id,
                    "ml_order_id": row.ml_order_id,
                    "buyer_name": row.buyer_first_name,
                    "buyer_nickname": row.buyer_nickname,
                    "total_amount": float(row.total_amount) if row.total_amount else 0,
                    "paid_amount": float(row.paid_amount) if row.paid_amount else 0,
                    "status": status_str,
                    "date_created": date_created_str,
                    "invoice_emitted": row.invoice_emitted if row.invoice_emitted else False,
                    "invoice_number": row.invoice_number if row.invoice_number else None,
                    "invoice_series": row.invoice_series if row.invoice_series else None,
                    "invoice_key": row.invoice_key if row.invoice_key else None,
                    "invoice_pdf_url": row.invoice_pdf_url if row.invoice_pdf_url else None,
                    "invoice_xml_url": row.invoice_xml_url if row.invoice_xml_url else None,
                    "pack_id": row.pack_id if row.pack_id else None,
                    # Campos JSON completos (shipping_details já tem todas as informações de envio)
                    "shipping_details": shipping_details_data,
                    "payments": row.payments if row.payments else None,
                    "order_items": row.order_items if row.order_items else None,
                    "shipping_address": row.shipping_address if row.shipping_address else None
                }
                
                result.append(order_dict)
            
            return {
                "success": True,
                "count": len(result),
                "total_count": total_count,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "orders": result
            }
        
        except Exception as e:
            logger.error(f"Erro ao listar pedidos para expedição: {e}")
            return {
                "success": False,
                "error": str(e),
                "count": 0,
                "orders": []
            }

    def sync_invoices(self, company_id: int, access_token: str) -> Dict:
        """
        Sincroniza status das notas fiscais com o Mercado Livre
        """
        try:
            result = self.service.sync_invoice_status(company_id, access_token)
            return result
        
        except Exception as e:
            logger.error(f"Erro ao sincronizar notas fiscais: {e}")
            return {
                "success": False,
                "error": str(e),
                "updated": 0
            }

    def sync_single_order_invoice(self, order_id: str, company_id: int, access_token: str) -> Dict:
        """
        Sincroniza nota fiscal de um pedido específico
        """
        try:
            result = self.service.sync_single_order_invoice(order_id, company_id, access_token)
            return result
        
        except Exception as e:
            logger.error(f"Erro ao sincronizar NF do pedido {order_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_stats(self, company_id: int) -> Dict:
        """
        Retorna estatísticas dos pedidos para expedição
        """
        try:
            # Total de pedidos pagos
            total_paid = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id,
                MLOrder.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED])
            ).count()
            
            # Pedidos com NF emitida
            with_invoice = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id,
                MLOrder.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED]),
                MLOrder.invoice_emitted == True
            ).count()
            
            # Pedidos sem NF (pendentes de expedição)
            pending = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id,
                MLOrder.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED]),
                MLOrder.invoice_emitted == False
            ).count()
            
            # Calcular porcentagem
            percentage = round((with_invoice / total_paid * 100) if total_paid > 0 else 0, 1)
            
            return {
                "success": True,
                "total_orders": total_paid,
                "orders_with_invoice": with_invoice,
                "orders_without_invoice": pending,
                "invoice_percentage": percentage
            }
        
        except Exception as e:
            logger.error(f"Erro ao buscar estatísticas: {e}")
            return {
                "success": False,
                "error": str(e),
                "stats": {
                    "total_paid": 0,
                    "with_invoice": 0,
                    "pending_invoice": 0
                }
            }
    
    def get_tab_counts(self, company_id: int) -> Dict:
        """
        Retorna contadores de pedidos por status para as abas
        Considera shipping_status e substatus, não apenas status
        """
        from sqlalchemy import or_, func
        
        try:
            from app.models.saas_models import MLOrder, OrderStatus
            import json
            
            # Buscar todos os pedidos da empresa
            all_orders = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id
            ).all()
            
            # Contadores
            counts = {
                "PENDING": 0,
                "CONFIRMED": 0,
                "READY_TO_PREPARE": 0,
                "WAITING_SHIPMENT": 0,
                "SHIPPED": 0,
                "DELIVERED": 0,
                "CANCELLED": 0,
                "REFUNDED": 0
            }

            # Contadores de debug para entender exclusões em READY_TO_PREPARE
            debug_excludes = {
                "total_paid": 0,
                "has_tracking": 0,
                "has_shipping_date": 0,
                "in_transit": 0,
                "delivered": 0,
                "pending": 0,
                "status_shipped": 0,
                "ready_to_ship": 0,
            }
            
            logger.info(f"📊 Total de pedidos na empresa: {len(all_orders)}")
            
            count = 0
            for order in all_orders:
                count += 1
                # Parse shipping_details se existir
                shipping_details = None
                if order.shipping_details:
                    if isinstance(order.shipping_details, str):
                        try:
                            shipping_details = json.loads(order.shipping_details)
                        except:
                            shipping_details = {}
                    else:
                        shipping_details = order.shipping_details
                
                shipping_status = shipping_details.get('status') if shipping_details else order.shipping_status
                substatus = shipping_details.get('substatus') if shipping_details else None

                # Normalizar status do pedido (enum/string) e shipping_status
                try:
                    status_str = getattr(order.status, 'value', order.status)
                except Exception:
                    status_str = order.status
                status_str = str(status_str).upper() if status_str is not None else None
                shipping_status_norm = str(shipping_status).lower() if shipping_status else None
                substatus_norm = str(substatus).lower() if substatus else None
                
                # Log apenas os primeiros 5 pedidos para debug
                if count <= 5:
                    logger.debug(f"📋 Order {order.order_id}: status={status_str}, shipping_status={shipping_status_norm}, substatus={substatus_norm}")
                
                # 1. PENDING: status = PENDING OR (status = PAID AND shipping_status = pending)
                if status_str == 'PENDING':
                    counts["PENDING"] += 1
                elif status_str == 'PAID' and (shipping_status_norm == 'pending' or not shipping_status_norm):
                    counts["PENDING"] += 1
                
                # 2. CONFIRMED
                if status_str == 'CONFIRMED':
                    counts["CONFIRMED"] += 1
                
                # 3. READY_TO_PREPARE: status = PAID AND não enviado/entregue/pendente/ready_to_ship (não-Fulfillment)
                if status_str == 'PAID':
                    has_tracking = (shipping_status_norm == 'shipped')
                    has_shipping_date = order.shipping_date is not None
                    
                    # Verificar substatus de ready_to_ship ANTES das exclusões
                    is_ready_to_ship = substatus_norm in ['ready_to_ship', 'ready_to_print', 'printed', 'ready_to_pack', 'packed', 'ready_for_pickup', 'ready_for_dropoff']
                    
                    # Verificar se deve excluir
                    exclude = False
                    debug_excludes["total_paid"] += 1
                    
                    # Excluir se já foi enviado
                    if has_tracking or has_shipping_date:
                        exclude = True
                        if has_tracking:
                            debug_excludes["has_tracking"] += 1
                        if has_shipping_date:
                            debug_excludes["has_shipping_date"] += 1
                    
                    # Excluir se está em trânsito
                    if shipping_status_norm in ['shipped', 'in_transit', 'out_for_delivery', 'soon_deliver']:
                        exclude = True
                        debug_excludes["in_transit"] += 1
                    
                # Excluir se substatus indica em trânsito ou que já foi coletado (mesmo com status ready_to_ship)
                if substatus_norm in ['in_transit', 'picked_up', 'dropped_off', 'in_hub']:
                    exclude = True
                    debug_excludes["in_transit"] += 1
                    
                    # Excluir se foi entregue
                    if shipping_status_norm in ['delivered', 'inferred'] or status_str == 'DELIVERED':
                        exclude = True
                        debug_excludes["delivered"] += 1
                    
                    # Excluir se está pendente
                    if shipping_status_norm == 'pending' or status_str == 'PENDING':
                        exclude = True
                        debug_excludes["pending"] += 1
                    
                    # Excluir se status do pedido é SHIPPED
                    if status_str == 'SHIPPED':
                        exclude = True
                        debug_excludes["status_shipped"] += 1
                    
                    # Excluir se está pronto para envio (vai para "Aguardando Envio")
                    if is_ready_to_ship:
                        exclude = True
                        debug_excludes["ready_to_ship"] += 1

                    # Excluir Fulfillment (não-Fulfillment na aba)
                    try:
                        logistic_type = None
                        details = shipping_details if 'shipping_details' in locals() and shipping_details else {}
                        if isinstance(details, dict):
                            logistic_type = details.get('logistic_type') or (details.get('logistic', {}) or {}).get('type')
                        shipping_type = getattr(order, 'shipping_type', None)
                        if (shipping_type == 'fulfillment') or (str(logistic_type).lower() == 'fulfillment'):
                            exclude = True
                    except Exception:
                        pass

                    if not exclude:
                        counts["READY_TO_PREPARE"] += 1
                    else:
                        # Se excluiu de READY_TO_PREPARE por estar pronto para envio, vai para WAITING_SHIPMENT
                        # WAITING_SHIPMENT: apenas quando substatus indicar pronto para envio (igual à tela)
                        if is_ready_to_ship:
                            counts["WAITING_SHIPMENT"] += 1
                
                # 5. SHIPPED: status = SHIPPED OR shipping_status em trânsito
                if status_str == 'SHIPPED':
                    counts["SHIPPED"] += 1
                elif shipping_status_norm in ['shipped', 'in_transit', 'out_for_delivery', 'soon_deliver']:
                    counts["SHIPPED"] += 1
                elif substatus_norm == 'in_transit':
                    counts["SHIPPED"] += 1
                
                # 6. DELIVERED: status = DELIVERED OR shipping_status = delivered/inferred
                if status_str == 'DELIVERED':
                    counts["DELIVERED"] += 1
                elif shipping_status_norm in ['delivered', 'inferred']:
                    counts["DELIVERED"] += 1
                
                # 7. CANCELLED
                if status_str in ['CANCELLED', 'PENDING_CANCEL']:
                    counts["CANCELLED"] += 1
                
                # 8. REFUNDED
                if status_str in ['REFUNDED', 'PARTIALLY_REFUNDED']:
                    counts["REFUNDED"] += 1
            
            logger.info(f"📊 Contadores calculados: {counts}")
            logger.info(f"🧪 READY_TO_PREPARE debug: {debug_excludes}")
            
            return {
                "success": True,
                "counts": counts
            }
        
        except Exception as e:
            logger.error(f"Erro ao buscar contadores das abas: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "counts": {
                    "PENDING": 0,
                    "CONFIRMED": 0,
                    "READY_TO_PREPARE": 0,
                    "WAITING_SHIPMENT": 0,
                    "SHIPPED": 0,
                    "DELIVERED": 0,
                    "CANCELLED": 0,
                    "REFUNDED": 0
                }
            }
