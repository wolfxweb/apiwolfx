"""
Rotas para gerenciamento de dados de publicidade (Product Ads)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.controllers.ml_advertising_controller import MLAdvertisingController
from app.middleware.auth import get_current_user
from app.models.saas_models import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ml/advertising",
    tags=["ML Advertising"]
)

@router.post("/sync-costs")
async def sync_advertising_costs(
    periods: int = 3,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sincroniza custos de Product Ads do Billing API
    
    Args:
        periods: Número de períodos (meses) para sincronizar (padrão: 3)
    """
    try:
        controller = MLAdvertisingController(db)
        result = await controller.sync_advertising_costs(
            company_id=current_user.company_id,
            periods=periods
        )
        
        return {
            "success": True,
            "message": "Custos de publicidade sincronizados com sucesso",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Erro ao sincronizar custos de publicidade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_advertising_summary(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna resumo dos custos de publicidade
    
    Args:
        days: Número de dias para análise (padrão: 30)
    """
    try:
        controller = MLAdvertisingController(db)
        result = controller.get_advertising_summary(
            company_id=current_user.company_id,
            days=days
        )
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar resumo de publicidade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

