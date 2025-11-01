"""
Controller para análises de mais vendidos do Mercado Livre
"""
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.services.highlights_service import HighlightsService

logger = logging.getLogger(__name__)

class HighlightsController:
    """Controller para análises de mais vendidos"""
    
    def __init__(self, db: Session):
        self.db = db
        self.highlights_service = HighlightsService(db)
    
    def get_category_highlights(self, category_id: str, user_id: int,
                               attribute: Optional[str] = None,
                               attribute_value: Optional[str] = None) -> Dict:
        """Busca os mais vendidos de uma categoria"""
        try:
            return self.highlights_service.get_category_highlights(
                category_id, user_id, attribute, attribute_value
            )
        except Exception as e:
            logger.error(f"Erro ao buscar mais vendidos: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_product_position(self, product_id: str, user_id: int) -> Dict:
        """Busca posicionamento de um produto"""
        try:
            return self.highlights_service.get_product_position(product_id, user_id)
        except Exception as e:
            logger.error(f"Erro ao buscar posicionamento do produto: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_item_position(self, item_id: str, user_id: int) -> Dict:
        """Busca posicionamento de um item"""
        try:
            return self.highlights_service.get_item_position(item_id, user_id)
        except Exception as e:
            logger.error(f"Erro ao buscar posicionamento do item: {e}")
            return {
                "success": False,
                "error": str(e)
            }

