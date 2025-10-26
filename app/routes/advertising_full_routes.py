"""Rotas completas para publicidade"""
from fastapi import APIRouter, Depends, HTTPException, Request, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.controllers.advertising_full_controller import AdvertisingFullController
from app.controllers.auth_controller import AuthController
from app.models.saas_models import User
from typing import Optional

templates = Jinja2Templates(directory="app/views/templates")

def get_current_user_or_redirect(request: Request, db: Session = Depends(get_db)):
    """Obtém usuário atual ou redireciona para login (para páginas HTML)"""
    session_token = request.cookies.get('session_token')
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    auth_controller = AuthController()
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    return result["user"]

def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Obtém usuário atual da sessão (para APIs JSON)"""
    session_token = request.cookies.get('session_token')
    if not session_token:
        raise HTTPException(status_code=401, detail="Sessão não encontrada")
    
    auth_controller = AuthController()
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail=result["error"])
    
    return result["user"]

router = APIRouter(prefix="/ml/advertising", tags=["Advertising"])

@router.get("", response_class=HTMLResponse)
async def advertising_page(request: Request, db: Session = Depends(get_db)):
    """Página de publicidade"""
    # Verificar autenticação com redirect
    user = get_current_user_or_redirect(request, db)
    
    # Se retornou RedirectResponse, retornar o redirect
    if isinstance(user, RedirectResponse):
        return user
    
    return templates.TemplateResponse("ml_advertising.html", {
        "request": request,
        "user": user
    })

@router.get("/campaigns")
async def get_campaigns(user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lista campanhas locais (rápido)"""
    controller = AdvertisingFullController(db)
    return controller.get_campaigns(user["company"]["id"])

@router.post("/campaigns/sync")
async def sync_campaigns(user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Sincroniza campanhas do Mercado Livre"""
    controller = AdvertisingFullController(db)
    return controller.sync_campaigns(user["company"]["id"])

@router.post("/campaigns")
async def create_campaign(
    campaign_data: dict,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cria campanha"""
    controller = AdvertisingFullController(db)
    return controller.create_campaign(user["company"]["id"], campaign_data)

@router.put("/campaigns/{campaign_id}")
async def update_campaign(
    campaign_id: int,
    updates: dict,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Atualiza campanha"""
    controller = AdvertisingFullController(db)
    return controller.update_campaign(user["company"]["id"], campaign_id, updates)

@router.delete("/campaigns/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deleta campanha"""
    controller = AdvertisingFullController(db)
    return controller.delete_campaign(user["company"]["id"], campaign_id)

@router.get("/metrics")
async def get_metrics(
    date_from: str = None, 
    date_to: str = None,
    status: str = None,
    user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Busca métricas consolidadas de publicidade (com filtro de período e status)"""
    controller = AdvertisingFullController(db)
    return controller.get_metrics_summary(user["company"]["id"], date_from, date_to, status)

@router.get("/alerts")
async def get_alerts(user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Busca alertas de publicidade (budget, performance)"""
    from app.services.advertising_alerts_service import AdvertisingAlertsService
    service = AdvertisingAlertsService(db)
    return {"success": True, "data": service.get_all_alerts(user["company"]["id"])}

@router.get("/campaigns/{campaign_id}/details")
async def campaign_details_page(
    campaign_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Página HTML com detalhes e dashboard da campanha"""
    user_or_redirect = get_current_user_or_redirect(request, db)
    
    if isinstance(user_or_redirect, RedirectResponse):
        return user_or_redirect
    
    user = user_or_redirect
    
    return templates.TemplateResponse("ml_campaign_details.html", {
        "request": request,
        "user": user,
        "campaign_id": campaign_id
    })

@router.get("/campaigns/{campaign_id}")
async def get_campaign_details(
    campaign_id: str,
    date_from: str = None,
    date_to: str = None,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Busca detalhes e métricas de uma campanha específica"""
    controller = AdvertisingFullController(db)
    return controller.get_campaign_details(user["company"]["id"], campaign_id, date_from, date_to)

@router.get("/campaigns/{campaign_id}/ads")
async def get_campaign_ads(
    campaign_id: str,
    date_from: str = None,
    date_to: str = None,
    limit: int = 100,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Busca anúncios/produtos de uma campanha com métricas"""
    controller = AdvertisingFullController(db)
    return controller.get_campaign_ads(user["company"]["id"], campaign_id, date_from, date_to, limit)

@router.get("/campaigns/{campaign_id}/price-evolution")
async def get_campaign_price_evolution(
    campaign_id: str,
    date_from: str = None,
    date_to: str = None,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Busca evolução do preço médio de venda dos produtos da campanha baseado nos pedidos reais"""
    controller = AdvertisingFullController(db)
    return controller.get_campaign_price_evolution(user["company"]["id"], campaign_id, date_from, date_to)
