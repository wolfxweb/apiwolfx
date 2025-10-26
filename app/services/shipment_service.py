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
        Sincroniza status das notas fiscais do Mercado Livre
        
        Busca TODOS os pedidos pagos e verifica se têm nota fiscal no ML
        Atualiza os campos de invoice para pedidos que já têm NF emitida
        """
        try:
            # Buscar TODOS os pedidos pagos que tenham pack_id (não apenas os sem NF)
            orders = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id,
                MLOrder.status.in_([OrderStatus.PAID, OrderStatus.CONFIRMED]),
                MLOrder.pack_id.isnot(None)
            ).all()
            
            logger.info(f"Sincronizando notas fiscais para {len(orders)} pedido(s)")
            
            updated = 0
            already_synced = 0
            errors = []
            
            for order in orders:
                try:
                    # Consultar pack no ML para verificar se tem NF
                    invoice_data = self._check_pack_invoice(order.pack_id, access_token)
                    
                    if invoice_data and invoice_data.get('has_invoice'):
                        # Verificar se já está sincronizado
                        if not order.invoice_emitted:
                            # Atualizar ordem com dados da NF
                            order.invoice_emitted = True
                            order.invoice_emitted_at = datetime.now()
                            order.invoice_number = invoice_data.get('number')
                            order.invoice_series = invoice_data.get('series')
                            order.invoice_key = invoice_data.get('key')
                            order.invoice_xml_url = invoice_data.get('xml_url')
                            order.invoice_pdf_url = invoice_data.get('pdf_url')
                            
                            updated += 1
                            logger.info(f"✅ NF sincronizada para pedido {order.order_id}")
                        else:
                            already_synced += 1
                            logger.debug(f"📋 NF já sincronizada para pedido {order.order_id}")
                    else:
                        # Se não tem NF no ML, garantir que está marcado como False
                        if order.invoice_emitted:
                            order.invoice_emitted = False
                            order.invoice_emitted_at = None
                            order.invoice_number = None
                            order.invoice_series = None
                            order.invoice_key = None
                            order.invoice_xml_url = None
                            order.invoice_pdf_url = None
                            updated += 1
                            logger.info(f"🔄 Status NF atualizado para pedido {order.order_id}")
                
                except Exception as e:
                    error_msg = f"Erro ao sincronizar pedido {order.order_id}: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
            
            # Commit das alterações
            if updated > 0:
                self.db.commit()
                logger.info(f"✅ {updated} nota(s) fiscal(is) sincronizada(s)")
            
            return {
                "success": True,
                "updated": updated,
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
        Sincroniza nota fiscal de um pedido específico
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
            
            if not order.pack_id:
                return {
                    "success": False,
                    "error": f"Pedido {order_id} não tem pack_id"
                }
            
            # Verificar NF no ML
            invoice_data = self._check_pack_invoice(order.pack_id, access_token)
            
            if invoice_data and invoice_data.get('has_invoice'):
                # Atualizar pedido com dados da NF
                order.invoice_emitted = True
                order.invoice_emitted_at = datetime.now()
                order.invoice_number = invoice_data.get('number')
                order.invoice_series = invoice_data.get('series')
                order.invoice_key = invoice_data.get('key')
                order.invoice_xml_url = invoice_data.get('xml_url')
                order.invoice_pdf_url = invoice_data.get('pdf_url')
                
                self.db.commit()
                
                return {
                    "success": True,
                    "message": f"Nota fiscal sincronizada para pedido {order_id}",
                    "invoice_data": {
                        "number": invoice_data.get('number'),
                        "series": invoice_data.get('series'),
                        "key": invoice_data.get('key')
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"Nenhuma nota fiscal encontrada para pedido {order_id}"
                }
        
        except Exception as e:
            logger.error(f"Erro ao sincronizar NF do pedido {order_id}: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    def _check_pack_invoice(self, pack_id: str, access_token: str) -> Optional[Dict]:
        """
        Verifica se um pack tem nota fiscal emitida
        Usa endpoint correto da documentação: /users/{user_id}/invoices/shipments/{shipment_id}
        """
        try:
            import requests
            
            # Primeiro tentar buscar no pack
            url = f"https://api.mercadolibre.com/packs/{pack_id}"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                pack_data = response.json()
                
                # Verificar se tem fiscal_document no pack
                fiscal_doc = pack_data.get('fiscal_document', {})
                if fiscal_doc:
                    return {
                        "has_invoice": True,
                        "number": fiscal_doc.get('number'),
                        "series": fiscal_doc.get('series'),
                        "key": fiscal_doc.get('key'),
                        "xml_url": fiscal_doc.get('xml_url'),
                        "pdf_url": fiscal_doc.get('danfe_url')
                    }
                
                # Se não tem no pack, buscar no shipment associado
                shipment = pack_data.get('shipment', {})
                shipment_id = shipment.get('id')
                
                if shipment_id:
                    # Usar endpoint correto da documentação para consultar nota fiscal no shipment
                    invoice_url = f"https://api.mercadolibre.com/users/1979794691/invoices/shipments/{shipment_id}"
                    invoice_response = requests.get(invoice_url, headers=headers, timeout=30)
                    
                    if invoice_response.status_code == 200:
                        invoice_data = invoice_response.json()
                        
                        return {
                            "has_invoice": True,
                            "number": invoice_data.get('invoice_number'),
                            "series": invoice_data.get('invoice_series'),
                            "key": invoice_data.get('attributes', {}).get('invoice_key'),
                            "xml_url": invoice_data.get('attributes', {}).get('xml_location'),
                            "pdf_url": invoice_data.get('attributes', {}).get('danfe_location')
                        }
            
            return {"has_invoice": False}
        
        except Exception as e:
            logger.warning(f"Erro ao consultar pack {pack_id}: {e}")
            return {"has_invoice": False, "error": str(e)}

