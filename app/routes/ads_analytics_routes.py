from fastapi import APIRouter, Depends, Request, Cookie, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.config.database import get_db
from app.controllers.ads_analytics_controller import AdsAnalyticsController
from app.controllers.analytics_controller import AnalyticsController
from app.controllers.auth_controller import AuthController


ads_analytics_router = APIRouter()

@ads_analytics_router.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Dashboard principal de Analytics & Performance"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    
    from app.views.template_renderer import render_template
    return render_template("ads_analytics_dashboard.html", user=user_data)

@ads_analytics_router.get("/api/analytics/sales-dashboard")
async def get_sales_dashboard_data(
    ml_account_id: Optional[int] = Query(None),
    period: Optional[str] = Query("30"),
    search: Optional[str] = Query(None),
    current_month: Optional[bool] = Query(False),
    last_month: Optional[bool] = Query(False),
    current_year: Optional[bool] = Query(False),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar dados do dashboard de vendas"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        # Converter period para int se não for um período especial
        period_days = 30  # padrão
        if period == "last_30_days":
            period_days = 30  # Últimos 30 dias
        elif period.isdigit():
            period_days = int(period)
        
        controller = AnalyticsController(db)
        data = controller.get_sales_dashboard(
            company_id=company_id,
            user_id=user_data["id"],
            ml_account_id=ml_account_id,
            period_days=period_days,
            search=search,
            current_month=current_month,
            last_month=last_month,
            current_year=current_year,
            date_from=date_from,
            date_to=date_to,
            specific_month=month,
            specific_year=year
        )
        
        return JSONResponse(content=data)
        
    except Exception as e:
        logging.error(f"Erro no endpoint sales dashboard: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ads_analytics_router.get("/api/analytics/top-products")
async def get_top_products_data(
    ml_account_id: Optional[int] = Query(None),
    limit: Optional[int] = Query(10),
    period: Optional[int] = Query(30),
    search: Optional[str] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar top produtos"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = AnalyticsController(db)
        data = controller.get_top_products(
            company_id=company_id,
            user_id=user_data["id"],
            ml_account_id=ml_account_id,
            limit=limit,
            period_days=period,
            search=search
        )
        
        return JSONResponse(content=data)
        
    except Exception as e:
        logging.error(f"Erro no endpoint top products: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ads_analytics_router.get("/api/analytics/accounts-summary")
async def get_accounts_summary_data(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar resumo de contas"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = AnalyticsController(db)
        data = controller.get_accounts_summary(company_id=company_id)
        
        return JSONResponse(content=data)
        
    except Exception as e:
        logging.error(f"Erro no endpoint accounts summary: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ads_analytics_router.get("/api/analytics/dashboard")
async def get_dashboard_data(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar dados do dashboard principal"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = AdsAnalyticsController(db)
        data = controller.get_dashboard_data(company_id, date_from, date_to)
        
        return JSONResponse(content=data)
        
    except Exception as e:
        logging.error(f"Erro no endpoint dashboard: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ads_analytics_router.get("/api/analytics/account/{ml_account_id}")
async def get_account_analytics(
    ml_account_id: int,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar analytics de uma conta específica"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = AdsAnalyticsController(db)
        data = controller.get_account_analytics(company_id, ml_account_id, date_from, date_to)
        
        return JSONResponse(content=data)
        
    except Exception as e:
        logging.error(f"Erro no endpoint account analytics: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ads_analytics_router.get("/api/analytics/products/{ml_account_id}/{advertiser_id}")
async def get_product_performance(
    ml_account_id: int,
    advertiser_id: str,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar performance de produtos de um advertiser"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = AdsAnalyticsController(db)
        data = controller.get_product_performance(company_id, ml_account_id, advertiser_id, date_from, date_to)
        
        return JSONResponse(content=data)
        
    except Exception as e:
        logging.error(f"Erro no endpoint product performance: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)


