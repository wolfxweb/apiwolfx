"""
Rotas para projeções de estoque
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Cookie, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.controllers.auth_controller import get_current_user
from app.controllers.stock_projection_controller import StockProjectionController

logger = logging.getLogger(__name__)

stock_projection_router = APIRouter(prefix="/stock/projections", tags=["Stock Projections"])


@stock_projection_router.get("/")
async def get_projections(
    internal_product_id: Optional[int] = Query(None, description="Filtrar por produto"),
    warehouse_id: Optional[int] = Query(None, description="Filtrar por depósito"),
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Lista projeções de estoque"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    try:
        current_user = get_current_user(session_token)
        company_id = current_user["company_id"]
        
        controller = StockProjectionController()
        result = controller.get_projections(
            company_id=company_id,
            internal_product_id=internal_product_id,
            warehouse_id=warehouse_id,
            db=db
        )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar projeções: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@stock_projection_router.get("/reorder-recommendations")
async def get_reorder_recommendations(
    warehouse_id: Optional[int] = Query(None, description="Filtrar por depósito"),
    limit: int = Query(50, description="Limite de resultados"),
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Obtém recomendações de compra"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    try:
        current_user = get_current_user(session_token)
        company_id = current_user["company_id"]
        
        controller = StockProjectionController()
        result = controller.get_reorder_recommendations(
            company_id=company_id,
            warehouse_id=warehouse_id,
            limit=limit,
            db=db
        )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar recomendações: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@stock_projection_router.post("/calculate")
async def calculate_projection(
    internal_product_id: int = Body(..., description="ID do produto interno"),
    warehouse_id: Optional[int] = Body(None, description="ID do depósito"),
    period_days: int = Body(30, description="Período em dias para cálculo"),
    lead_time_days: int = Body(7, description="Lead time em dias"),
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Calcula projeção específica"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    try:
        current_user = get_current_user(session_token)
        company_id = current_user["company_id"]
        
        controller = StockProjectionController()
        result = controller.calculate_projection(
            company_id=company_id,
            internal_product_id=internal_product_id,
            warehouse_id=warehouse_id,
            period_days=period_days,
            lead_time_days=lead_time_days,
            db=db
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao calcular projeção: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

