"""
Serviço para gerenciamento de SKUs
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.saas_models import SKUManagement, Product, InternalProduct

logger = logging.getLogger(__name__)

class SKUManagementService:
    """Serviço para gerenciar SKUs e evitar duplicação"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_sku_exists(self, sku: str, company_id: int) -> Dict[str, Any]:
        """Verifica se SKU já existe para a empresa"""
        try:
            existing = self.db.query(SKUManagement).filter(
                and_(
                    SKUManagement.sku == sku,
                    SKUManagement.company_id == company_id,
                    SKUManagement.status == "active"
                )
            ).first()
            
            if existing:
                return {
                    "exists": True,
                    "sku_management": {
                        "id": existing.id,
                        "sku": existing.sku,
                        "platform": existing.platform,
                        "platform_item_id": existing.platform_item_id,
                        "product_id": existing.product_id,
                        "internal_product_id": existing.internal_product_id,
                        "status": existing.status
                    }
                }
            
            return {"exists": False}
            
        except Exception as e:
            logger.error(f"Erro ao verificar SKU: {e}")
            return {"error": f"Erro ao verificar SKU: {str(e)}"}
    
    def register_sku(self, sku: str, platform: str, platform_item_id: str, 
                    company_id: int, product_id: Optional[int] = None, 
                    internal_product_id: Optional[int] = None) -> Dict[str, Any]:
        """Registra um novo SKU no sistema ou associa novo anúncio a SKU existente"""
        try:
            # Verificar se já existe registro com este platform_item_id
            existing_by_item = self.db.query(SKUManagement).filter(
                and_(
                    SKUManagement.platform_item_id == platform_item_id,
                    SKUManagement.company_id == company_id,
                    SKUManagement.status == "active"
                )
            ).first()
            
            if existing_by_item:
                return {"error": f"Anúncio '{platform_item_id}' já está registrado para este SKU"}
            
            # Verificar se SKU já existe
            check_result = self.check_sku_exists(sku, company_id)
            
            if check_result.get("exists"):
                # SKU existe, apenas associar novo anúncio
                sku_management = SKUManagement(
                    sku=sku,
                    platform=platform,
                    platform_item_id=platform_item_id,
                    company_id=company_id,
                    product_id=product_id,
                    internal_product_id=internal_product_id,
                    status="active"
                )
                
                self.db.add(sku_management)
                self.db.commit()
                self.db.refresh(sku_management)
                
                return {
                    "success": True,
                    "action": "associated",
                    "message": f"Novo anúncio '{platform_item_id}' associado ao SKU '{sku}' existente",
                    "sku_management": {
                        "id": sku_management.id,
                        "sku": sku_management.sku,
                        "platform": sku_management.platform,
                        "platform_item_id": sku_management.platform_item_id,
                        "product_id": sku_management.product_id,
                        "internal_product_id": sku_management.internal_product_id
                    }
                }
            else:
                # SKU não existe, criar novo registro
                sku_management = SKUManagement(
                    sku=sku,
                    platform=platform,
                    platform_item_id=platform_item_id,
                    company_id=company_id,
                    product_id=product_id,
                    internal_product_id=internal_product_id,
                    status="active"
                )
                
                self.db.add(sku_management)
                self.db.commit()
                self.db.refresh(sku_management)
                
                return {
                    "success": True,
                    "action": "created",
                    "message": f"Novo SKU '{sku}' criado com anúncio '{platform_item_id}'",
                    "sku_management": {
                        "id": sku_management.id,
                        "sku": sku_management.sku,
                        "platform": sku_management.platform,
                        "platform_item_id": sku_management.platform_item_id,
                        "product_id": sku_management.product_id,
                        "internal_product_id": sku_management.internal_product_id
                    }
                }
            
        except Exception as e:
            logger.error(f"Erro ao registrar SKU: {e}")
            self.db.rollback()
            return {"error": f"Erro ao registrar SKU: {str(e)}"}
    
    def update_sku_product(self, sku: str, company_id: int, 
                          product_id: Optional[int] = None,
                          internal_product_id: Optional[int] = None) -> Dict[str, Any]:
        """Atualiza os IDs de produto associados ao SKU"""
        try:
            sku_management = self.db.query(SKUManagement).filter(
                and_(
                    SKUManagement.sku == sku,
                    SKUManagement.company_id == company_id,
                    SKUManagement.status == "active"
                )
            ).first()
            
            if not sku_management:
                return {"error": f"SKU '{sku}' não encontrado"}
            
            if product_id is not None:
                sku_management.product_id = product_id
            if internal_product_id is not None:
                sku_management.internal_product_id = internal_product_id
            
            self.db.commit()
            
            return {
                "success": True,
                "message": f"SKU '{sku}' atualizado com sucesso"
            }
            
        except Exception as e:
            logger.error(f"Erro ao atualizar SKU: {e}")
            self.db.rollback()
            return {"error": f"Erro ao atualizar SKU: {str(e)}"}
    
    def get_sku_history(self, sku: str, company_id: int) -> Dict[str, Any]:
        """Obtém histórico completo do SKU com todos os anúncios associados"""
        try:
            # Buscar todos os registros do SKU
            sku_managements = self.db.query(SKUManagement).filter(
                and_(
                    SKUManagement.sku == sku,
                    SKUManagement.company_id == company_id
                )
            ).order_by(SKUManagement.created_at.desc()).all()
            
            if not sku_managements:
                return {"error": f"SKU '{sku}' não encontrado"}
            
            # Processar cada registro
            announcements = []
            for sku_mgmt in sku_managements:
                announcement = {
                    "id": sku_mgmt.id,
                    "platform_item_id": sku_mgmt.platform_item_id,
                    "platform": sku_mgmt.platform,
                    "status": sku_mgmt.status,
                    "created_at": sku_mgmt.created_at,
                    "updated_at": sku_mgmt.updated_at
                }
                
                # Buscar produto ML associado
                if sku_mgmt.product_id:
                    product = self.db.query(Product).filter(Product.id == sku_mgmt.product_id).first()
                    if product:
                        announcement["product"] = {
                            "id": product.id,
                            "title": product.title,
                            "ml_item_id": product.ml_item_id,
                            "thumbnail": product.thumbnail
                        }
                
                # Buscar produto interno associado
                if sku_mgmt.internal_product_id:
                    internal_product = self.db.query(InternalProduct).filter(
                        InternalProduct.id == sku_mgmt.internal_product_id
                    ).first()
                    if internal_product:
                        announcement["internal_product"] = {
                            "id": internal_product.id,
                            "name": internal_product.name,
                            "internal_sku": internal_product.internal_sku,
                            "cost_price": internal_product.cost_price,
                            "selling_price": internal_product.selling_price
                        }
                
                announcements.append(announcement)
            
            return {
                "success": True,
                "sku": sku,
                "total_announcements": len(announcements),
                "announcements": announcements
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter histórico do SKU: {e}")
            return {"error": f"Erro ao obter histórico do SKU: {str(e)}"}
    
    def deactivate_sku(self, sku: str, company_id: int) -> Dict[str, Any]:
        """Desativa um SKU"""
        try:
            sku_management = self.db.query(SKUManagement).filter(
                and_(
                    SKUManagement.sku == sku,
                    SKUManagement.company_id == company_id,
                    SKUManagement.status == "active"
                )
            ).first()
            
            if not sku_management:
                return {"error": f"SKU '{sku}' não encontrado"}
            
            sku_management.status = "inactive"
            self.db.commit()
            
            return {
                "success": True,
                "message": f"SKU '{sku}' desativado com sucesso"
            }
            
        except Exception as e:
            logger.error(f"Erro ao desativar SKU: {e}")
            self.db.rollback()
            return {"error": f"Erro ao desativar SKU: {str(e)}"}
