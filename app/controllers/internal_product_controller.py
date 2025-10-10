"""
Controller para produtos internos/customizados
"""
import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.services.internal_product_service import InternalProductService

logger = logging.getLogger(__name__)


class InternalProductController:
    """Controller para gerenciar produtos internos"""
    
    def __init__(self):
        pass
    
    def create_internal_product(
        self,
        company_id: int,
        name: str,
        internal_sku: str,
        base_product_id: Optional[int] = None,
        description: Optional[str] = None,
        cost_price: Optional[float] = None,
        selling_price: Optional[float] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        supplier: Optional[str] = None,
        db: Session = Depends(get_db),
        **kwargs
    ) -> Dict[str, Any]:
        """Cria um novo produto interno"""
        try:
            service = InternalProductService(db)
            result = service.create_internal_product(
                company_id=company_id,
                name=name,
                internal_sku=internal_sku,
                base_product_id=base_product_id,
                description=description,
                cost_price=cost_price,
                selling_price=selling_price,
                category=category,
                brand=brand,
                supplier=supplier,
                **kwargs
            )
            
            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro no controller ao criar produto interno: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def get_internal_products(
        self,
        company_id: int,
        status: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Lista produtos internos da empresa"""
        try:
            service = InternalProductService(db)
            result = service.get_internal_products(
                company_id=company_id,
                status=status,
                category=category,
                search=search,
                limit=limit,
                offset=offset
            )
            
            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro no controller ao listar produtos internos: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def get_internal_product(
        self,
        product_id: int,
        company_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Obtém um produto interno específico"""
        try:
            service = InternalProductService(db)
            result = service.get_internal_product(
                product_id=product_id,
                company_id=company_id
            )
            
            if "error" in result:
                raise HTTPException(status_code=404, detail=result["error"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro no controller ao obter produto interno: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def update_internal_product(
        self,
        product_id: int,
        company_id: int,
        update_data: Dict[str, Any],
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Atualiza um produto interno"""
        try:
            service = InternalProductService(db)
            result = service.update_internal_product(
                product_id=product_id,
                company_id=company_id,
                **update_data
            )
            
            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro no controller ao atualizar produto interno: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def delete_internal_product(
        self,
        product_id: int,
        company_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Remove um produto interno"""
        try:
            service = InternalProductService(db)
            result = service.delete_internal_product(
                product_id=product_id,
                company_id=company_id
            )
            
            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro no controller ao remover produto interno: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def get_base_products(
        self,
        company_id: int,
        search: Optional[str] = None,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Lista produtos do ML que podem ser usados como base"""
        try:
            service = InternalProductService(db)
            result = service.get_base_products(
                company_id=company_id,
                search=search
            )
            
            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro no controller ao listar produtos base: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def bulk_delete_internal_products(
        self,
        product_ids: list,
        company_id: int,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Exclui múltiplos produtos internos"""
        try:
            service = InternalProductService(db)
            result = service.bulk_delete_internal_products(
                product_ids=product_ids,
                company_id=company_id
            )
            
            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro no controller ao excluir produtos em massa: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def bulk_update_internal_products(
        self,
        company_id: int,
        cost_price: Optional[float] = None,
        tax_rate: Optional[float] = None,
        marketing_cost: Optional[float] = None,
        other_costs: Optional[float] = None,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Atualiza valores em massa em todos os produtos internos"""
        try:
            service = InternalProductService(db)
            result = service.bulk_update_internal_products(
                company_id=company_id,
                cost_price=cost_price,
                tax_rate=tax_rate,
                marketing_cost=marketing_cost,
                other_costs=other_costs
            )
            
            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro no controller ao atualizar produtos em massa: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")