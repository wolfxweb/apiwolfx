"""
Controller para projeções de estoque
"""
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.services.stock_projection_service import StockProjectionService

logger = logging.getLogger(__name__)


class StockProjectionController:
    """Controller para gerenciar projeções de estoque"""
    
    def __init__(self):
        pass
    
    def get_projections(
        self,
        company_id: int,
        internal_product_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Lista projeções de estoque"""
        try:
            from app.models.saas_models import StockProjection, InternalProduct
            
            query = db.query(StockProjection).filter(
                StockProjection.company_id == company_id
            )
            
            if internal_product_id:
                query = query.filter(StockProjection.internal_product_id == internal_product_id)
            
            if warehouse_id:
                query = query.filter(StockProjection.warehouse_id == warehouse_id)
            
            projections = query.all()
            
            result = []
            for proj in projections:
                product = db.query(InternalProduct).filter(
                    InternalProduct.id == proj.internal_product_id
                ).first()
                
                result.append({
                    "id": proj.id,
                    "product_id": proj.internal_product_id,
                    "product_name": product.name if product else None,
                    "product_sku": product.internal_sku if product else None,
                    "warehouse_id": proj.warehouse_id,
                    "warehouse_name": proj.warehouse.name if proj.warehouse else None,
                    "current_stock": float(proj.current_stock),
                    "average_daily_sales": float(proj.average_daily_sales),
                    "days_of_stock": float(proj.days_of_stock) if proj.days_of_stock else None,
                    "turnover_rate": float(proj.turnover_rate) if proj.turnover_rate else None,
                    "projected_stockout_date": proj.projected_stockout_date.isoformat() if proj.projected_stockout_date else None,
                    "recommended_reorder_date": proj.recommended_reorder_date.isoformat() if proj.recommended_reorder_date else None,
                    "recommended_quantity": float(proj.recommended_quantity) if proj.recommended_quantity else None,
                    "last_calculated_at": proj.last_calculated_at.isoformat() if proj.last_calculated_at else None
                })
            
            return {
                "success": True,
                "projections": result,
                "count": len(result)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no controller ao listar projeções: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao listar projeções: {str(e)}"
            }
    
    def get_reorder_recommendations(
        self,
        company_id: int,
        warehouse_id: Optional[int] = None,
        limit: int = 50,
        db: Session = None
    ) -> Dict[str, Any]:
        """Obtém recomendações de compra"""
        try:
            service = StockProjectionService(db)
            return service.get_reorder_recommendations(
                company_id=company_id,
                warehouse_id=warehouse_id,
                limit=limit
            )
        except Exception as e:
            logger.error(f"❌ Erro no controller ao buscar recomendações: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao buscar recomendações: {str(e)}"
            }
    
    def calculate_projection(
        self,
        company_id: int,
        internal_product_id: int,
        warehouse_id: Optional[int] = None,
        period_days: int = 30,
        lead_time_days: int = 7,
        db: Session = None
    ) -> Dict[str, Any]:
        """Calcula projeção específica"""
        try:
            service = StockProjectionService(db)
            return service.update_projection(
                company_id=company_id,
                internal_product_id=internal_product_id,
                warehouse_id=warehouse_id,
                period_days=period_days,
                lead_time_days=lead_time_days
            )
        except Exception as e:
            logger.error(f"❌ Erro no controller ao calcular projeção: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao calcular projeção: {str(e)}"
            }

