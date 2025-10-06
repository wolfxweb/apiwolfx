"""
Rotas para gerenciamento de SKUs
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.controllers.auth_controller import get_current_user
from app.services.sku_management_service import SKUManagementService

logger = logging.getLogger(__name__)

sku_management_router = APIRouter()

@sku_management_router.get("/check-sku")
async def check_sku_exists(
    sku: str = Query(..., description="SKU para verificar"),
    session_token: str = Query(..., description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Verifica se SKU já existe"""
    try:
        current_user = get_current_user(session_token)
        company_id = current_user["company_id"]
        
        service = SKUManagementService(db)
        result = service.check_sku_exists(sku, company_id)
        
        return JSONResponse(content=result)
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro ao verificar SKU: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@sku_management_router.post("/register-sku")
async def register_sku(
    sku: str = Query(..., description="SKU para registrar"),
    platform: str = Query("mercadolivre", description="Plataforma"),
    platform_item_id: str = Query(..., description="ID do item na plataforma"),
    product_id: Optional[int] = Query(None, description="ID do produto ML"),
    internal_product_id: Optional[int] = Query(None, description="ID do produto interno"),
    session_token: str = Query(..., description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Registra um novo SKU"""
    try:
        current_user = get_current_user(session_token)
        company_id = current_user["company_id"]
        
        service = SKUManagementService(db)
        result = service.register_sku(
            sku=sku,
            platform=platform,
            platform_item_id=platform_item_id,
            company_id=company_id,
            product_id=product_id,
            internal_product_id=internal_product_id
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return JSONResponse(content=result)
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro ao registrar SKU: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@sku_management_router.get("/sku-history")
async def get_sku_history(
    sku: str = Query(..., description="SKU para consultar histórico"),
    session_token: str = Query(..., description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Obtém histórico de um SKU"""
    try:
        current_user = get_current_user(session_token)
        company_id = current_user["company_id"]
        
        service = SKUManagementService(db)
        result = service.get_sku_history(sku, company_id)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return JSONResponse(content=result)
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro ao obter histórico do SKU: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@sku_management_router.put("/deactivate-sku")
async def deactivate_sku(
    sku: str = Query(..., description="SKU para desativar"),
    session_token: str = Query(..., description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Desativa um SKU"""
    try:
        current_user = get_current_user(session_token)
        company_id = current_user["company_id"]
        
        service = SKUManagementService(db)
        result = service.deactivate_sku(sku, company_id)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return JSONResponse(content=result)
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro ao desativar SKU: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

