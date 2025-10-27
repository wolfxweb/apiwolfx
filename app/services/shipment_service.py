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
            
            for order in orders:
                try:
                    order_updated = False
                    
                    # 1. SINCRONIZAR STATUS DO PEDIDO
                    try:
                        order_url = f"{self.base_url}/orders/{order.ml_order_id}"
                        headers = {"Authorization": f"Bearer {access_token}"}
                        response = requests.get(order_url, headers=headers, timeout=30)
                        
                        if response.status_code == 200:
                            order_data = response.json()
                            
                            # Mapear e atualizar status
                            status_mapping = {
                                "confirmed": OrderStatus.CONFIRMED,
                                "payment_required": OrderStatus.PENDING,
                                "payment_in_process": OrderStatus.PENDING,
                                "paid": OrderStatus.PAID,
                                "ready_to_ship": OrderStatus.PAID,
                                "shipped": OrderStatus.SHIPPED,
                                "delivered": OrderStatus.DELIVERED,
                                "cancelled": OrderStatus.CANCELLED,
                                "refunded": OrderStatus.REFUNDED
                            }
                            
                            api_status = order_data.get("status", "pending")
                            new_status = status_mapping.get(api_status, OrderStatus.PENDING)
                            
                            if order.status != new_status:
                                order.status = new_status
                                order_updated = True
                                status_updated += 1
                                logger.info(f"✅ Status do pedido {order.order_id} atualizado: {order.status} -> {new_status}")
                            
                            # Atualizar shipping info
                            shipping = order_data.get("shipping", {})
                            if shipping:
                                order.shipping_status = shipping.get("status")
                                order.shipping_id = str(shipping.get("id", order.shipping_id))
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
            
            # Commit das alterações
            if updated > 0:
                self.db.commit()
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
        Sincroniza nota fiscal E STATUS de um pedido específico
        """
        try:
            # Buscar o pedido específico
            order = self.db.query(MLOrder).filter(
                MLOrder.ml_order_id == order_id,
                MLOrder.company_id == company_id
            ).first()
            
            if not order:
                return {
                    "success": False,
                    "error": f"Pedido {order_id} não encontrado"
                }
            
            # 1. SINCRONIZAR STATUS DO PEDIDO
            status_updated = False
            try:
                import requests
                order_url = f"{self.base_url}/orders/{order_id}"
                headers = {"Authorization": f"Bearer {access_token}"}
                response = requests.get(order_url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    order_data = response.json()
                    
                    # Mapear status
                    status_mapping = {
                        "confirmed": OrderStatus.CONFIRMED,
                        "payment_required": OrderStatus.PENDING,
                        "payment_in_process": OrderStatus.PENDING,
                        "paid": OrderStatus.PAID,
                        "ready_to_ship": OrderStatus.PAID,
                        "shipped": OrderStatus.SHIPPED,
                        "delivered": OrderStatus.DELIVERED,
                        "cancelled": OrderStatus.CANCELLED,
                        "refunded": OrderStatus.REFUNDED
                    }
                    
                    api_status = order_data.get("status", "pending")
                    new_status = status_mapping.get(api_status, OrderStatus.PENDING)
                    
                    if order.status != new_status:
                        order.status = new_status
                        status_updated = True
                        logger.info(f"✅ Status do pedido {order_id} atualizado: {order.status} -> {new_status}")
                    
                            # Atualizar shipping status também
                    shipping = order_data.get("shipping", {})
                    if shipping:
                        order.shipping_status = shipping.get("status")
                        order.shipping_id = str(shipping.get("id", order.shipping_id))
                        order.last_updated = datetime.utcnow()
                        status_updated = True
                        
                        # Se tem shipping_id, buscar dados completos do shipment
                        shipment_id = shipping.get("id")
                        if shipment_id:
                            try:
                                shipment_url = f"{self.base_url}/shipments/{shipment_id}"
                                shipment_headers = {
                                    **headers,
                                    "x-format-new": "true"  # Necessário para novo formato
                                }
                                shipment_response = requests.get(shipment_url, headers=shipment_headers, timeout=30)
                                
                                if shipment_response.status_code == 200:
                                    shipment_data = shipment_response.json()
                                    
                                    # Capturar substatus (importante para fulfillment)
                                    substatus = shipment_data.get("substatus")
                                    if substatus:
                                        logger.info(f"📦 Shipment {shipment_id} - Substatus: {substatus}")
                                    
                                    # Identificar tipo de logística
                                    logistic = shipment_data.get("logistic", {})
                                    logistic_type = logistic.get("type")  # fulfillment, cross_docking, etc
                                    logistic_mode = logistic.get("mode")  # me2
                                    
                                    if logistic_type == "fulfillment":
                                        logger.info(f"✅ Pedido {order_id} é FULFILLMENT - Processando no CD do ML")
                                        logger.info(f"   Mode: {logistic_mode}, Type: {logistic_type}, Substatus: {substatus}")
                                    
                                    # Atualizar método de envio
                                    order.shipping_method = logistic_type or order.shipping_method
                                    
                                    # ATUALIZAR STATUS BASEADO NO SUBSTATUS (fulfillment)
                                    if substatus:
                                        substatus_mapping = {
                                            "in_warehouse": OrderStatus.PAID,  # Processando no centro de distribuição
                                            "ready_to_print": OrderStatus.PAID,
                                            "printed": OrderStatus.PAID,
                                            "ready_to_pack": OrderStatus.PAID,
                                            "ready_to_ship": OrderStatus.PAID,
                                            "shipped": OrderStatus.SHIPPED,
                                            "in_transit": OrderStatus.SHIPPED,
                                            "delivered": OrderStatus.DELIVERED,
                                            "lost": OrderStatus.CANCELLED,
                                            "damaged": OrderStatus.CANCELLED
                                        }
                                        
                                        substatus_status = substatus_mapping.get(substatus)
                                        if substatus_status and order.status != substatus_status:
                                            logger.info(f"🔄 [STATUS] Atualizando status baseado no substatus: {order.status} -> {substatus_status} (substatus: {substatus})")
                                            order.status = substatus_status
                                            status_updated = True
                                    
                            except Exception as e:
                                logger.warning(f"Erro ao buscar detalhes do shipment {shipment_id}: {e}")
                
            except Exception as e:
                logger.warning(f"Erro ao sincronizar status do pedido {order_id}: {e}")
            
            # 2. SINCRONIZAR NOTA FISCAL
            invoice_updated = False
            
            # Tentar buscar NF usando pack_id OU shipment_id (para fulfillment)
            invoice_data = None
            
            if order.pack_id:
                # Buscar NF pelo pack_id
                try:
                    invoice_data = self._check_pack_invoice(order.pack_id, access_token)
                except Exception as e:
                    logger.warning(f"Erro ao buscar NF pelo pack_id: {e}")
            
            # Se não encontrou pelo pack_id e tem shipment_id, tentar pelo shipment_id (fulfillment)
            if not invoice_data and order.shipping_id:
                try:
                    logger.info(f"🔍 Buscando NF pelo shipment_id {order.shipping_id} para pedido {order_id}")
                    logger.info(f"   Company ID: {order.company_id}, Pack ID: {order.pack_id}")
                    invoice_data = self._check_shipment_invoice(order.shipping_id, order.company_id, access_token)
                    logger.info(f"📄 Resultado busca NF: has_invoice={invoice_data.get('has_invoice') if invoice_data else False}")
                except Exception as e:
                    logger.error(f"❌ Erro ao buscar NF pelo shipment_id: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            
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
                    logger.info(f"✅ NF do pedido {order_id} sincronizada - Fonte: {invoice_data.get('source')}")
                except Exception as e:
                    logger.warning(f"Erro ao atualizar dados da NF no pedido {order_id}: {e}")
            
            # Commit se houver alterações
            if status_updated or invoice_updated:
                self.db.commit()
                return {
                    "success": True,
                    "message": f"Pedido {order_id} sincronizado com sucesso",
                    "status_updated": status_updated,
                    "invoice_updated": invoice_updated
                }
            else:
                return {
                    "success": True,
                    "message": f"Pedido {order_id} já está atualizado",
                    "status_updated": False,
                    "invoice_updated": False
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
                        "source": "ml_biller_shipment",
                        "number": invoice_data.get('invoice_number'),
                        "series": invoice_data.get('invoice_series'),
                        "key": attributes.get('invoice_key'),
                        "xml_url": xml_url,
                        "pdf_url": pdf_url,
                        "status": invoice_data.get('status')
                    }
            
            return {"has_invoice": False}
        
        except Exception as e:
            logger.warning(f"Erro ao consultar invoice do shipment {shipment_id}: {e}")
            return {"has_invoice": False, "error": str(e)}

