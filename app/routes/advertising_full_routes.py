"""Rotas completas para publicidade"""
from fastapi import APIRouter, Depends, HTTPException, Request, Cookie
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.controllers.advertising_full_controller import AdvertisingFullController
from app.controllers.auth_controller import AuthController
from app.models.saas_models import User
from app.views.template_renderer import render_template
from typing import Optional

def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Obtém usuário atual da sessão"""
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
async def advertising_page(request: Request, db: Session = Depends(get_db), user = Depends(get_current_user)):
    """Página de publicidade"""
    return render_template("ml_advertising.html", {"user": user})

@router.get("/campaigns")
async def get_campaigns(user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lista campanhas"""
    controller = AdvertisingFullController(db)
    return controller.get_campaigns(user["company"]["id"])

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
