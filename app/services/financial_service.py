"""
Serviço para operações financeiras
"""

from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging

from app.models.financial_models import CostCenter, FinancialCategory

logger = logging.getLogger(__name__)

class FinancialService:
    """Serviço para operações financeiras"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_cost_centers(self, company_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """Lista centros de custo da empresa"""
        try:
            query = self.db.query(CostCenter).filter(CostCenter.company_id == company_id)
            
            if active_only:
                query = query.filter(CostCenter.is_active == True)
            
            cost_centers = query.all()
            
            return [
                {
                    "id": cc.id,
                    "name": cc.name,
                    "description": cc.description,
                    "is_active": cc.is_active,
                    "created_at": cc.created_at.isoformat() if cc.created_at else None
                }
                for cc in cost_centers
            ]
            
        except Exception as e:
            logger.error(f"Erro ao buscar centros de custo: {e}")
            return []
    
    def get_categories(self, company_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """Lista categorias financeiras da empresa"""
        try:
            query = self.db.query(FinancialCategory).filter(FinancialCategory.company_id == company_id)
            
            if active_only:
                query = query.filter(FinancialCategory.is_active == True)
            
            categories = query.all()
            
            return [
                {
                    "id": cat.id,
                    "name": cat.name,
                    "description": cat.description,
                    "category_type": cat.type.value if cat.type else None,
                    "is_active": cat.is_active,
                    "created_at": cat.created_at.isoformat() if cat.created_at else None
                }
                for cat in categories
            ]
            
        except Exception as e:
            logger.error(f"Erro ao buscar categorias: {e}")
            return []
    
    def get_financial_categories(self, company_id: int, category_type: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
        """Lista categorias financeiras da empresa (alias para get_categories)"""
        return self.get_categories(company_id, active_only)
