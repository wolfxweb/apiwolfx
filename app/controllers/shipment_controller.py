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
                               page: int = 1, limit: int = 100) -> Dict:
        """
        Lista pedidos para expedição com paginação
        Retorna pedidos paginados (todos os status) para exibir em todas as abas
        """
        try:
            # Buscar TODOS os pedidos (todos os status)
            query = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id
            )
            
            # Aplicar filtro de busca
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    (MLOrder.ml_order_id.cast(String).ilike(search_term)) |
                    (MLOrder.order_id.ilike(search_term)) |
                    (MLOrder.buyer_nickname.ilike(search_term)) |
                    (MLOrder.buyer_first_name.ilike(search_term))
                )
            
            # Aplicar filtro de status da nota fiscal
            if invoice_status == "emitted":
                query = query.filter(MLOrder.invoice_emitted == True)
            elif invoice_status == "pending":
                query = query.filter(MLOrder.invoice_emitted == False)
            
            # Calcular offset
            offset = (page - 1) * limit
            
            # Contar total de registros
            total_count = query.count()
            
            # Buscar com paginação
            orders = query.order_by(MLOrder.date_created.desc()).offset(offset).limit(limit).all()
            
            # Calcular total de páginas
            total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
            
            result = []
            for order in orders:
                # Converter status para string - garantir que seja maiúsculo
                if order.status and hasattr(order.status, 'value'):
                    status_str = str(order.status.value).upper()
                elif order.status:
                    status_str = str(order.status).upper()
                else:
                    status_str = None
                
                result.append({
                    "id": order.id,
                    "order_id": order.order_id,
                    "ml_order_id": order.ml_order_id,
                    "buyer_name": order.buyer_first_name,
                    "buyer_nickname": order.buyer_nickname,
                    "total_amount": float(order.total_amount) if order.total_amount else 0,
                    "status": status_str,
                    "date_created": order.date_created.isoformat() if order.date_created else None,
                    "invoice_emitted": order.invoice_emitted if order.invoice_emitted else False,
                    "invoice_number": order.invoice_number if order.invoice_number else None,
                    "invoice_series": order.invoice_series if order.invoice_series else None,
                    "invoice_key": order.invoice_key if order.invoice_key else None,
                    "invoice_pdf_url": order.invoice_pdf_url if order.invoice_pdf_url else None,
                    "invoice_xml_url": order.invoice_xml_url if order.invoice_xml_url else None,
                        "pack_id": order.pack_id,
                        "shipping_id": order.shipping_id,
                        "shipping_type": order.shipping_type if order.shipping_type else None,
                        "shipping_date": order.shipping_date.isoformat() if order.shipping_date else None,
                        "estimated_delivery_date": order.estimated_delivery_date.isoformat() if order.estimated_delivery_date else None
                })
            
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
