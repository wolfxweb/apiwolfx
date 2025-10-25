"""
Rotas para gerenciamento de custos de marketing (Product Ads)
do Mercado Livre.

Endpoints disponíveis:
- POST /marketing/sync-costs: Sincronizar custos de marketing
- GET /marketing/summary: Resumo de custos de marketing
- GET /marketing/period: Custos por período específico
- GET /marketing/account/{id}: Custos por conta ML
- GET /marketing/metrics: Métricas para dashboards
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.config.database import get_db
from app.controllers.marketing_costs_controller import MarketingCostsController
from app.controllers.auth_controller import AuthController

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/marketing",
    tags=["Marketing Costs"]
)

@router.post("/sync-costs")
async def sync_marketing_costs(
    months: int = Query(3, description="Número de meses para sincronizar (máximo 12)"),
    session_token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Sincroniza custos de marketing da Billing API do Mercado Livre
    
    Args:
        months: Número de meses para sincronizar (padrão: 3, máximo 12)
        session_token: Token de sessão do usuário
        
    Returns:
        Resultado da sincronização com totais e estatísticas
    """
    try:
        # Validar autenticação
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        auth_result = AuthController().get_user_by_session(session_token, db)
        if auth_result.get("error"):
            raise HTTPException(status_code=401, detail="Sessão inválida")
        
        user_data = auth_result["user"]
        company_id = user_data["company"]["id"]
        
        # Validar parâmetros
        if months < 1 or months > 12:
            raise HTTPException(status_code=400, detail="Número de meses deve estar entre 1 e 12")
        
        # Sincronizar custos
        controller = MarketingCostsController(db)
        result = controller.sync_marketing_costs(company_id, months)
        
        if result["success"]:
            return JSONResponse(content={
                "success": True,
                "message": result["message"],
                "data": {
                    "total_cost": result["total_cost"],
                    "orders_updated": result["orders_updated"],
                    "accounts_processed": result["accounts_processed"],
                    "accounts_data": result["accounts_data"]
                }
            })
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Erro na sincronização"))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint sync-costs: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/summary")
async def get_marketing_summary(
    months: int = Query(3, description="Número de meses para analisar"),
    session_token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Busca resumo de custos de marketing
    
    Args:
        months: Número de meses para analisar (padrão: 3)
        session_token: Token de sessão do usuário
        
    Returns:
        Resumo de custos de marketing com breakdown mensal
    """
    try:
        # Validar autenticação
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        auth_result = AuthController().get_user_by_session(session_token, db)
        if auth_result.get("error"):
            raise HTTPException(status_code=401, detail="Sessão inválida")
        
        user_data = auth_result["user"]
        company_id = user_data["company"]["id"]
        
        # Buscar resumo
        controller = MarketingCostsController(db)
        result = controller.get_marketing_summary(company_id, months)
        
        if result["success"]:
            return JSONResponse(content={
                "success": True,
                "data": result
            })
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Erro ao buscar resumo"))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint summary: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/period")
async def get_marketing_by_period(
    date_from: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    date_to: str = Query(..., description="Data final (YYYY-MM-DD)"),
    session_token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Busca custos de marketing de um período específico
    
    Args:
        date_from: Data inicial no formato YYYY-MM-DD
        date_to: Data final no formato YYYY-MM-DD
        session_token: Token de sessão do usuário
        
    Returns:
        Custos de marketing do período com breakdown por conta e dia
    """
    try:
        # Validar autenticação
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        auth_result = AuthController().get_user_by_session(session_token, db)
        if auth_result.get("error"):
            raise HTTPException(status_code=401, detail="Sessão inválida")
        
        user_data = auth_result["user"]
        company_id = user_data["company"]["id"]
        
        # Validar formato das datas
        try:
            from datetime import datetime
            datetime.strptime(date_from, "%Y-%m-%d")
            datetime.strptime(date_to, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD")
        
        # Buscar custos do período
        controller = MarketingCostsController(db)
        result = controller.get_marketing_by_period(company_id, date_from, date_to)
        
        if result["success"]:
            return JSONResponse(content={
                "success": True,
                "data": result
            })
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Erro ao buscar custos do período"))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint period: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/account/{ml_account_id}")
async def get_marketing_by_account(
    ml_account_id: int,
    months: int = Query(3, description="Número de meses para analisar"),
    session_token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Busca custos de marketing de uma conta ML específica
    
    Args:
        ml_account_id: ID da conta ML
        months: Número de meses para analisar (padrão: 3)
        session_token: Token de sessão do usuário
        
    Returns:
        Custos de marketing da conta com breakdown mensal
    """
    try:
        # Validar autenticação
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        auth_result = AuthController().get_user_by_session(session_token, db)
        if auth_result.get("error"):
            raise HTTPException(status_code=401, detail="Sessão inválida")
        
        user_data = auth_result["user"]
        company_id = user_data["company"]["id"]
        
        # Buscar custos da conta
        controller = MarketingCostsController(db)
        result = controller.get_marketing_by_account(company_id, ml_account_id, months)
        
        if result["success"]:
            return JSONResponse(content={
                "success": True,
                "data": result
            })
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Erro ao buscar custos da conta"))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint account: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/metrics")
async def get_marketing_metrics(
    months: int = Query(3, description="Número de meses para analisar"),
    session_token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Busca métricas de marketing para dashboards
    
    Args:
        months: Número de meses para analisar (padrão: 3)
        session_token: Token de sessão do usuário
        
    Returns:
        Métricas de marketing com tendências e breakdowns
    """
    try:
        # Validar autenticação
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        auth_result = AuthController().get_user_by_session(session_token, db)
        if auth_result.get("error"):
            raise HTTPException(status_code=401, detail="Sessão inválida")
        
        user_data = auth_result["user"]
        company_id = user_data["company"]["id"]
        
        # Buscar métricas
        controller = MarketingCostsController(db)
        result = controller.get_marketing_metrics(company_id, months)
        
        if result["success"]:
            return JSONResponse(content={
                "success": True,
                "data": result["metrics"]
            })
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Erro ao buscar métricas"))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no endpoint metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/health")
async def health_check():
    """
    Verifica se o serviço de custos de marketing está funcionando
    
    Returns:
        Status do serviço
    """
    return JSONResponse(content={
        "success": True,
        "service": "Marketing Costs API",
        "status": "healthy",
        "version": "1.0.0"
    })
