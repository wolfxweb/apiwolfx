"""
Controller para gerenciar monitoramento de catálogo
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.services.catalog_monitoring_service import CatalogMonitoringService
from app.models.saas_models import MLCatalogMonitoring, MLCatalogHistory


class CatalogMonitoringController:
    """Controller para ações de monitoramento de catálogo"""
    
    def __init__(self, db: Session):
        self.db = db
        self.service = CatalogMonitoringService(db)
    
    def activate_monitoring(self, company_id: int, catalog_product_id: str, 
                          ml_product_id: Optional[int] = None) -> Dict:
        """
        Ativa monitoramento para um catálogo
        Executa primeira coleta imediatamente
        """
        monitoring = self.service.activate_monitoring(
            company_id=company_id,
            catalog_product_id=catalog_product_id,
            ml_product_id=ml_product_id
        )
        
        return {
            "success": True,
            "message": "Monitoramento ativado com sucesso",
            "monitoring": {
                "id": monitoring.id,
                "catalog_product_id": monitoring.catalog_product_id,
                "is_active": monitoring.is_active,
                "activated_at": monitoring.activated_at.isoformat() if monitoring.activated_at else None,
                "last_check_at": monitoring.last_check_at.isoformat() if monitoring.last_check_at else None
            }
        }
    
    def deactivate_monitoring(self, company_id: int, catalog_product_id: str) -> Dict:
        """Desativa monitoramento de um catálogo"""
        success = self.service.deactivate_monitoring(company_id, catalog_product_id)
        
        if success:
            return {
                "success": True,
                "message": "Monitoramento desativado com sucesso"
            }
        else:
            return {
                "success": False,
                "message": "Monitoramento não encontrado ou já está inativo"
            }
    
    def get_monitoring_status(self, company_id: int, catalog_product_id: str) -> Dict:
        """Busca status do monitoramento"""
        monitoring = self.db.query(MLCatalogMonitoring).filter(
            MLCatalogMonitoring.company_id == company_id,
            MLCatalogMonitoring.catalog_product_id == catalog_product_id
        ).first()
        
        if not monitoring:
            return {
                "is_active": False,
                "message": "Monitoramento não configurado"
            }
        
        return {
            "is_active": monitoring.is_active,
            "activated_at": monitoring.activated_at.isoformat() if monitoring.activated_at else None,
            "deactivated_at": monitoring.deactivated_at.isoformat() if monitoring.deactivated_at else None,
            "last_check_at": monitoring.last_check_at.isoformat() if monitoring.last_check_at else None,
            "catalog_product_id": monitoring.catalog_product_id,
            "ml_product_id": monitoring.ml_product_id
        }
    
    def get_latest_data(self, company_id: int, catalog_product_id: str) -> Optional[Dict]:
        """Busca os dados mais recentes do catálogo"""
        latest = self.service.get_latest_catalog_data(company_id, catalog_product_id)
        
        if not latest:
            return None
        
        return self._format_history_item(latest)
    
    def get_history(self, company_id: int, catalog_product_id: str, 
                   limit: int = 100) -> List[Dict]:
        """Busca histórico de monitoramento"""
        history = self.service.get_catalog_history(company_id, catalog_product_id, limit)
        
        return [self._format_history_item(item) for item in history]
    
    def _format_history_item(self, item: MLCatalogHistory) -> Dict:
        """Formata um item de histórico para retorno"""
        return {
            "id": item.id,
            "collected_at": item.collected_at.isoformat() if item.collected_at else None,
            "catalog_product_id": item.catalog_product_id,
            
            # Dados gerais
            "total_participants": item.total_participants,
            
            # Buy Box
            "buy_box_winner_id": item.buy_box_winner_id,
            "buy_box_winner_price": item.buy_box_winner_price,
            "buy_box_winner_price_brl": f"R$ {item.buy_box_winner_price / 100:.2f}" if item.buy_box_winner_price else None,
            
            # Posição da empresa
            "company_position": item.company_position,
            "company_price": item.company_price,
            "company_price_brl": f"R$ {item.company_price / 100:.2f}" if item.company_price else None,
            "company_has_buy_box": item.company_has_buy_box,
            
            # Estatísticas de preços
            "min_price": item.min_price,
            "min_price_brl": f"R$ {item.min_price / 100:.2f}" if item.min_price else None,
            "max_price": item.max_price,
            "max_price_brl": f"R$ {item.max_price / 100:.2f}" if item.max_price else None,
            "avg_price": item.avg_price,
            "avg_price_brl": f"R$ {item.avg_price / 100:.2f}" if item.avg_price else None,
            "median_price": item.median_price,
            "median_price_brl": f"R$ {item.median_price / 100:.2f}" if item.median_price else None,
            
            # Estatísticas de quantidade
            "total_available_quantity": item.total_available_quantity,
            "total_sold_quantity": item.total_sold_quantity,
            
            # Snapshot dos participantes
            "participants_snapshot": item.participants_snapshot if item.participants_snapshot else []
        }
    
    def delete_history(self, company_id: int, catalog_product_id: str) -> Dict:
        """Remove todo o histórico de monitoramento de um catálogo"""
        deleted_count = self.service.delete_catalog_history(company_id, catalog_product_id)
        
        return {
            "success": True,
            "message": f"Histórico removido com sucesso",
            "deleted_count": deleted_count
        }

