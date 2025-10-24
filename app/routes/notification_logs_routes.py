"""
Rotas para visualizar logs de notificações do Mercado Livre
"""
from fastapi import APIRouter, Depends, HTTPException, Cookie
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.config.database import get_db
from app.controllers.auth_controller import AuthController
from app.utils.notification_logger import notification_logger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notification-logs", tags=["notification-logs"])

def get_company_id_from_user(session_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)) -> int:
    """Obtém company_id do usuário autenticado"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    
    auth_controller = AuthController()
    result = auth_controller.get_user_by_session(session_token, db)
    
    if result.get("error"):
        raise HTTPException(status_code=401, detail=result["error"])
    
    user_data = result["user"]
    return user_data.get("company_id")

@router.get("/company/{company_id}")
async def get_company_logs(
    company_id: int,
    limit: int = 100,
    current_company_id: int = Depends(get_company_id_from_user)
):
    """Recupera logs de notificações de uma empresa específica"""
    try:
        # Verificar se o usuário tem acesso à empresa
        if current_company_id != company_id:
            raise HTTPException(status_code=403, detail="Acesso negado a esta empresa")
        
        logs = notification_logger.get_company_logs(company_id, limit)
        
        return {
            "company_id": company_id,
            "total_logs": len(logs),
            "logs": logs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao recuperar logs da empresa {company_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/company/{company_id}/stats")
async def get_company_stats(
    company_id: int,
    days: int = 7,
    current_company_id: int = Depends(get_company_id_from_user)
):
    """Recupera estatísticas de notificações de uma empresa"""
    try:
        # Verificar se o usuário tem acesso à empresa
        if current_company_id != company_id:
            raise HTTPException(status_code=403, detail="Acesso negado a esta empresa")
        
        stats = notification_logger.get_notification_stats(company_id, days)
        
        return {
            "company_id": company_id,
            "period_days": days,
            "statistics": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao recuperar estatísticas da empresa {company_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/my-company")
async def get_my_company_logs(
    limit: int = 100,
    company_id: int = Depends(get_company_id_from_user)
):
    """Recupera logs da empresa do usuário logado"""
    try:
        logs = notification_logger.get_company_logs(company_id, limit)
        
        return {
            "company_id": company_id,
            "total_logs": len(logs),
            "logs": logs
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao recuperar logs da empresa {company_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/my-company/stats")
async def get_my_company_stats(
    days: int = 7,
    company_id: int = Depends(get_company_id_from_user)
):
    """Recupera estatísticas da empresa do usuário logado"""
    try:
        stats = notification_logger.get_notification_stats(company_id, days)
        
        return {
            "company_id": company_id,
            "period_days": days,
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao recuperar estatísticas da empresa {company_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
