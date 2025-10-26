"""
Rotas para expedição e notas fiscais
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Cookie
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import io

from app.config.database import get_db
from app.controllers.shipment_controller import ShipmentController
from app.controllers.auth_controller import AuthController
from app.services.token_manager import TokenManager
from app.views.template_renderer import render_template

router = APIRouter(prefix="/shipments", tags=["Expedição"])

@router.get("/", response_class=HTMLResponse)
async def shipments_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de expedição de produtos"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    return render_template("shipments.html", user=user_data)

@router.get("/pending")
async def list_pending_shipments(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Lista todos os pedidos para expedição"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = ShipmentController(db)
        result = controller.list_pending_shipments(company_id)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@router.post("/sync-invoices")
async def sync_invoice_status(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Sincroniza status das notas fiscais com o Mercado Livre"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        # Buscar token de acesso usando TokenManager
        token_manager = TokenManager(db)
        
        # Buscar um usuário ativo da empresa
        from app.models.saas_models import User
        user_db = db.query(User).filter(
            User.company_id == company_id,
            User.is_active == True
        ).first()
        
        if not user_db:
            return JSONResponse(content={"error": "Nenhum usuário ativo encontrado para esta empresa"}, status_code=404)
        
        access_token = token_manager.get_valid_token(user_db.id)
        
        if not access_token:
            return JSONResponse(content={"error": "Token de acesso inválido ou expirado"}, status_code=401)
        
        controller = ShipmentController(db)
        result = controller.sync_invoices(company_id, access_token)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@router.post("/sync-single-invoice/{order_id}")
async def sync_single_order_invoice(
    order_id: str,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Sincroniza nota fiscal de um pedido específico"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        # Buscar token de acesso usando TokenManager
        token_manager = TokenManager(db)
        
        # Buscar um usuário ativo da empresa
        from app.models.saas_models import User
        user_db = db.query(User).filter(
            User.company_id == company_id,
            User.is_active == True
        ).first()
        
        if not user_db:
            return JSONResponse(content={"error": "Nenhum usuário ativo encontrado para esta empresa"}, status_code=404)
        
        access_token = token_manager.get_valid_token(user_db.id)
        
        if not access_token:
            return JSONResponse(content={"error": "Token de acesso inválido ou expirado"}, status_code=401)
        
        controller = ShipmentController(db)
        result = controller.sync_single_order_invoice(order_id, company_id, access_token)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@router.get("/stats")
async def get_stats(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Retorna estatísticas dos pedidos"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = ShipmentController(db)
        result = controller.get_stats(company_id)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

