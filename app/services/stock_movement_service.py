"""
Serviço para gerenciar movimentações de estoque
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime, timedelta
from app.models.saas_models import (
    StockMovement, StockMovementType, ProductStock, Warehouse, WarehouseType
)

logger = logging.getLogger(__name__)


class StockMovementService:
    """Serviço para gerenciar movimentações de estoque"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_movement(
        self,
        company_id: int,
        warehouse_id: int,
        product_stock_id: int,
        movement_type: str,
        quantity: float,
        previous_quantity: float,
        new_quantity: float,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        ml_order_id: Optional[int] = None,
        notes: Optional[str] = None,
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """Registra uma movimentação de estoque"""
        try:
            # Verificar se product_stock pertence à empresa
            product_stock = self.db.query(ProductStock).filter(
                and_(
                    ProductStock.id == product_stock_id,
                    ProductStock.company_id == company_id
                )
            ).first()
            
            if not product_stock:
                return {
                    "success": False,
                    "error": "Estoque não encontrado"
                }
            
            movement = StockMovement(
                company_id=company_id,
                warehouse_id=warehouse_id,
                product_stock_id=product_stock_id,
                movement_type=StockMovementType(movement_type),
                quantity=quantity,
                previous_quantity=previous_quantity,
                new_quantity=new_quantity,
                reference_type=reference_type,
                reference_id=reference_id,
                ml_order_id=ml_order_id,
                notes=notes,
                created_by=created_by
            )
            
            self.db.add(movement)
            self.db.commit()
            self.db.refresh(movement)
            
            logger.info(f"✅ Movimentação registrada: {movement_type} - {quantity} unidades (Stock ID: {product_stock_id})")
            
            return {
                "success": True,
                "movement": {
                    "id": movement.id,
                    "type": movement.movement_type.value,
                    "quantity": float(movement.quantity),
                    "created_at": movement.created_at.isoformat() if movement.created_at else None
                }
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao registrar movimentação: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao registrar movimentação: {str(e)}"
            }
    
    def get_movement_history(
        self,
        company_id: int,
        product_stock_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        internal_product_id: Optional[int] = None,
        ml_item_id: Optional[str] = None,
        movement_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Obtém histórico de movimentações"""
        try:
            query = self.db.query(StockMovement).filter(
                StockMovement.company_id == company_id
            )
            
            if product_stock_id:
                query = query.filter(StockMovement.product_stock_id == product_stock_id)
            
            if warehouse_id:
                query = query.filter(StockMovement.warehouse_id == warehouse_id)
            
            if movement_type:
                query = query.filter(StockMovement.movement_type == StockMovementType(movement_type))
            
            if date_from:
                query = query.filter(StockMovement.created_at >= date_from)
            
            if date_to:
                query = query.filter(StockMovement.created_at <= date_to)
            
            # Se buscar por produto, precisa filtrar via product_stock
            if internal_product_id or ml_item_id:
                product_stock_query = self.db.query(ProductStock.id).filter(
                    ProductStock.company_id == company_id
                )
                
                if internal_product_id:
                    product_stock_query = product_stock_query.filter(
                        ProductStock.internal_product_id == internal_product_id
                    )
                
                if ml_item_id:
                    product_stock_query = product_stock_query.filter(
                        ProductStock.ml_item_id == ml_item_id
                    )
                
                product_stock_ids = [ps[0] for ps in product_stock_query.all()]
                query = query.filter(StockMovement.product_stock_id.in_(product_stock_ids))
            
            total = query.count()
            
            movements = query.order_by(desc(StockMovement.created_at)).limit(limit).offset(offset).all()
            
            return {
                "success": True,
                "movements": [
                    {
                        "id": m.id,
                        "warehouse_id": m.warehouse_id,
                        "warehouse_name": m.warehouse.name if m.warehouse else None,
                        "movement_type": m.movement_type.value,
                        "quantity": float(m.quantity),
                        "previous_quantity": float(m.previous_quantity),
                        "new_quantity": float(m.new_quantity),
                        "reference_type": m.reference_type,
                        "reference_id": m.reference_id,
                        "ml_order_id": m.ml_order_id,
                        "notes": m.notes,
                        "created_by": m.created_by,
                        "created_at": m.created_at.isoformat() if m.created_at else None
                    }
                    for m in movements
                ],
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar histórico de movimentações: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao buscar histórico: {str(e)}"
            }
    
    def sync_sale_to_stock(
        self,
        company_id: int,
        ml_order_id: int,
        ml_item_id: str,
        quantity: int,
        warehouse_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Sincroniza venda com estoque (quando pedido é confirmado)"""
        try:
            from app.models.saas_models import MLOrder
            from app.services.stock_service import StockService
            
            # Verificar se pedido existe e pertence à empresa
            order = self.db.query(MLOrder).filter(
                and_(
                    MLOrder.id == ml_order_id,
                    MLOrder.company_id == company_id
                )
            ).first()
            
            if not order:
                return {
                    "success": False,
                    "error": "Pedido não encontrado"
                }
            
            # Se não especificou warehouse, tentar encontrar por ml_item_id
            if not warehouse_id:
                # Buscar estoque específico do anúncio
                product_stock = self.db.query(ProductStock).filter(
                    and_(
                        ProductStock.company_id == company_id,
                        ProductStock.ml_item_id == ml_item_id
                    )
                ).first()
                
                if product_stock:
                    warehouse_id = product_stock.warehouse_id
                else:
                    # Buscar fulfillment (compartilhado)
                    fulfillment_warehouse = self.db.query(Warehouse).filter(
                        and_(
                            Warehouse.type == WarehouseType.FULFILLMENT,
                            Warehouse.is_shared == True
                        )
                    ).first()
                    
                    if fulfillment_warehouse:
                        warehouse_id = fulfillment_warehouse.id
            
            if not warehouse_id:
                return {
                    "success": False,
                    "error": "Depósito não encontrado para este anúncio"
                }
            
            # Atualizar estoque
            stock_service = StockService(self.db)
            result = stock_service.update_stock(
                company_id=company_id,
                warehouse_id=warehouse_id,
                quantity=-quantity,  # Negativo para saída
                ml_item_id=ml_item_id,
                movement_type="sale"
            )
            
            if not result.get("success"):
                return result
            
            # Registrar movimentação
            product_stock = self.db.query(ProductStock).filter(
                and_(
                    ProductStock.company_id == company_id,
                    ProductStock.warehouse_id == warehouse_id,
                    ProductStock.ml_item_id == ml_item_id
                )
            ).first()
            
            if product_stock:
                self.record_movement(
                    company_id=company_id,
                    warehouse_id=warehouse_id,
                    product_stock_id=product_stock.id,
                    movement_type="sale",
                    quantity=-quantity,
                    previous_quantity=float(product_stock.quantity) + quantity,
                    new_quantity=float(product_stock.quantity),
                    reference_type="order",
                    reference_id=ml_order_id,
                    ml_order_id=ml_order_id,
                    notes=f"Venda do pedido {order.order_id}"
                )
            
            logger.info(f"✅ Venda sincronizada com estoque: {quantity} unidades do item {ml_item_id}")
            
            return {
                "success": True,
                "message": "Venda sincronizada com estoque"
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao sincronizar venda com estoque: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao sincronizar venda: {str(e)}"
            }
    
    def get_sales_by_period(
        self,
        company_id: int,
        internal_product_id: Optional[int] = None,
        ml_item_id: Optional[str] = None,
        warehouse_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Obtém vendas (movimentações tipo 'sale') por período"""
        try:
            date_from = datetime.utcnow() - timedelta(days=days)
            
            return self.get_movement_history(
                company_id=company_id,
                warehouse_id=warehouse_id,
                internal_product_id=internal_product_id,
                ml_item_id=ml_item_id,
                movement_type="sale",
                date_from=date_from,
                limit=1000
            )
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar vendas por período: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao buscar vendas: {str(e)}"
            }

