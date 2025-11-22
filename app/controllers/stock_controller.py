"""
Controller para gerenciar estoque e depósitos
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.services.stock_service import StockService
from app.services.stock_movement_service import StockMovementService

logger = logging.getLogger(__name__)


class StockController:
    """Controller para gerenciar estoque"""
    
    def __init__(self):
        pass
    
    def create_warehouse(
        self,
        company_id: int,
        name: str,
        type: str,
        address: Optional[str] = None,
        contact_info: Optional[Dict] = None,
        is_shared: bool = False,
        db: Session = None
    ) -> Dict[str, Any]:
        """Cria um novo depósito"""
        try:
            service = StockService(db)
            return service.create_warehouse(
                company_id=company_id,
                name=name,
                type=type,
                address=address,
                contact_info=contact_info,
                is_shared=is_shared
            )
        except Exception as e:
            logger.error(f"❌ Erro no controller ao criar depósito: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao criar depósito: {str(e)}"
            }
    
    def list_warehouses(
        self,
        company_id: int,
        include_shared: bool = True,
        db: Session = None
    ) -> Dict[str, Any]:
        """Lista depósitos da empresa"""
        try:
            service = StockService(db)
            return service.get_warehouses(
                company_id=company_id,
                include_shared=include_shared
            )
        except Exception as e:
            logger.error(f"❌ Erro no controller ao listar depósitos: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao listar depósitos: {str(e)}"
            }
    
    def get_warehouse(
        self,
        warehouse_id: int,
        company_id: int,
        db: Session = None
    ) -> Dict[str, Any]:
        """Obtém um depósito específico"""
        try:
            service = StockService(db)
            return service.get_warehouse(
                warehouse_id=warehouse_id,
                company_id=company_id
            )
        except Exception as e:
            logger.error(f"❌ Erro no controller ao buscar depósito: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao buscar depósito: {str(e)}"
            }
    
    def update_warehouse(
        self,
        warehouse_id: int,
        company_id: int,
        name: Optional[str] = None,
        address: Optional[str] = None,
        contact_info: Optional[Dict] = None,
        status: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Atualiza um depósito"""
        try:
            service = StockService(db)
            return service.update_warehouse(
                warehouse_id=warehouse_id,
                company_id=company_id,
                name=name,
                address=address,
                contact_info=contact_info,
                status=status
            )
        except Exception as e:
            logger.error(f"❌ Erro no controller ao atualizar depósito: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao atualizar depósito: {str(e)}"
            }
    
    def delete_warehouse(
        self,
        warehouse_id: int,
        company_id: int,
        db: Session = None
    ) -> Dict[str, Any]:
        """Remove um depósito"""
        try:
            service = StockService(db)
            return service.delete_warehouse(
                warehouse_id=warehouse_id,
                company_id=company_id
            )
        except Exception as e:
            logger.error(f"❌ Erro no controller ao remover depósito: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao remover depósito: {str(e)}"
            }
    
    def get_stock_by_product(
        self,
        company_id: int,
        internal_product_id: int,
        warehouse_id: Optional[int] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Obtém estoque por produto"""
        try:
            service = StockService(db)
            return service.get_all_stocks_for_product(
                company_id=company_id,
                internal_product_id=internal_product_id
            )
        except Exception as e:
            logger.error(f"❌ Erro no controller ao buscar estoque por produto: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao buscar estoque: {str(e)}"
            }
    
    def list_all_stocks(
        self,
        company_id: int,
        warehouse_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
        db: Session = None
    ) -> Dict[str, Any]:
        """Lista todos os estoques"""
        try:
            service = StockService(db)
            return service.get_product_stock(
                company_id=company_id,
                warehouse_id=warehouse_id,
                limit=limit,
                offset=offset
            )
        except Exception as e:
            logger.error(f"❌ Erro no controller ao listar estoques: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao listar estoques: {str(e)}"
            }
    
    def get_stock_by_announcement(
        self,
        company_id: int,
        ml_item_id: str,
        warehouse_id: Optional[int] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Obtém estoque por anúncio"""
        try:
            service = StockService(db)
            return service.get_stock_by_announcement(
                company_id=company_id,
                ml_item_id=ml_item_id,
                warehouse_id=warehouse_id
            )
        except Exception as e:
            logger.error(f"❌ Erro no controller ao buscar estoque por anúncio: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao buscar estoque: {str(e)}"
            }
    
    def adjust_stock(
        self,
        company_id: int,
        warehouse_id: int,
        quantity: float,
        internal_product_id: Optional[int] = None,
        ml_item_id: Optional[str] = None,
        notes: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Ajuste manual de estoque"""
        try:
            service = StockService(db)
            return service.update_stock(
                company_id=company_id,
                warehouse_id=warehouse_id,
                quantity=quantity,
                internal_product_id=internal_product_id,
                ml_item_id=ml_item_id,
                movement_type="adjustment"
            )
        except Exception as e:
            logger.error(f"❌ Erro no controller ao ajustar estoque: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao ajustar estoque: {str(e)}"
            }
    
    def set_stock_quantity(
        self,
        company_id: int,
        product_stock_id: int,
        new_quantity: float,
        notes: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Define a quantidade absoluta do estoque"""
        try:
            service = StockService(db)
            return service.set_stock_quantity(
                company_id=company_id,
                product_stock_id=product_stock_id,
                new_quantity=new_quantity,
                notes=notes
            )
        except Exception as e:
            logger.error(f"❌ Erro no controller ao definir quantidade de estoque: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao definir quantidade: {str(e)}"
            }
    
    def transfer_stock(
        self,
        company_id: int,
        from_warehouse_id: int,
        to_warehouse_id: int,
        quantity: float,
        internal_product_id: Optional[int] = None,
        ml_item_id: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Transfere estoque entre depósitos"""
        try:
            service = StockService(db)
            return service.transfer_stock(
                company_id=company_id,
                from_warehouse_id=from_warehouse_id,
                to_warehouse_id=to_warehouse_id,
                quantity=quantity,
                internal_product_id=internal_product_id,
                ml_item_id=ml_item_id
            )
        except Exception as e:
            logger.error(f"❌ Erro no controller ao transferir estoque: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao transferir estoque: {str(e)}"
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
        offset: int = 0,
        db: Session = None
    ) -> Dict[str, Any]:
        """Obtém histórico de movimentações"""
        try:
            service = StockMovementService(db)
            return service.get_movement_history(
                company_id=company_id,
                product_stock_id=product_stock_id,
                warehouse_id=warehouse_id,
                internal_product_id=internal_product_id,
                ml_item_id=ml_item_id,
                movement_type=movement_type,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
                offset=offset
            )
        except Exception as e:
            logger.error(f"❌ Erro no controller ao buscar histórico: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao buscar histórico: {str(e)}"
            }
    
    def configure_announcement_warehouse(
        self,
        company_id: int,
        internal_product_id: int,
        ml_item_id: str,
        warehouse_id: int,
        db: Session = None
    ) -> Dict[str, Any]:
        """Configura qual depósito um anúncio específico deve usar"""
        try:
            service = StockService(db)
            return service.configure_announcement_warehouse(
                company_id=company_id,
                internal_product_id=internal_product_id,
                ml_item_id=ml_item_id,
                warehouse_id=warehouse_id
            )
        except Exception as e:
            logger.error(f"❌ Erro no controller ao configurar depósito do anúncio: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao configurar depósito: {str(e)}"
            }
    
    def bulk_configure_announcement_warehouse(
        self,
        company_id: int,
        internal_product_id: int,
        warehouse_id_fulfillment: Optional[int] = None,
        warehouse_id_normal: Optional[int] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Configura depósitos em massa para anúncios de um produto interno"""
        try:
            service = StockService(db)
            return service.bulk_configure_announcement_warehouse(
                company_id=company_id,
                internal_product_id=internal_product_id,
                warehouse_id_fulfillment=warehouse_id_fulfillment,
                warehouse_id_normal=warehouse_id_normal
            )
        except Exception as e:
            logger.error(f"❌ Erro no controller ao configurar depósitos em massa: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao configurar depósitos em massa: {str(e)}"
            }
    
    def bulk_configure_all_announcements_warehouse(
        self,
        company_id: int,
        warehouse_id_fulfillment: Optional[int] = None,
        warehouse_id_normal: Optional[int] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Configura depósitos em massa para TODOS os anúncios da empresa"""
        try:
            service = StockService(db)
            return service.bulk_configure_all_announcements_warehouse(
                company_id=company_id,
                warehouse_id_fulfillment=warehouse_id_fulfillment,
                warehouse_id_normal=warehouse_id_normal
            )
        except Exception as e:
            logger.error(f"❌ Erro no controller ao configurar todos os anúncios em massa: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao configurar depósitos em massa: {str(e)}"
            }
    
    def get_announcement_warehouse_config(
        self,
        company_id: int,
        internal_product_id: int,
        db: Session = None
    ) -> Dict[str, Any]:
        """Lista configurações de estoque por anúncio de um produto interno"""
        try:
            service = StockService(db)
            return service.get_announcement_warehouse_config(
                company_id=company_id,
                internal_product_id=internal_product_id
            )
        except Exception as e:
            logger.error(f"❌ Erro no controller ao buscar configurações: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao buscar configurações: {str(e)}"
            }
    
    def clear_all_stocks(
        self,
        company_id: int,
        db: Session = None
    ) -> Dict[str, Any]:
        """Remove todos os estoques da empresa"""
        try:
            service = StockService(db)
            return service.clear_all_stocks(company_id=company_id)
        except Exception as e:
            logger.error(f"❌ Erro no controller ao limpar todos os estoques: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao limpar estoques: {str(e)}"
            }

