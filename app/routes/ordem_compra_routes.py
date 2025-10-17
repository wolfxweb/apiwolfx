"""
Rotas para Ordens de Compra
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.config.database import get_db
from app.controllers.ordem_compra_controller import OrdemCompraController
from app.controllers.auth_controller import AuthController
from app.views.template_renderer import render_template

logger = logging.getLogger(__name__)

ordem_compra_router = APIRouter()
ordem_compra_controller = OrdemCompraController()
auth_controller = AuthController()

def get_company_id_from_user(user_data: dict) -> int:
    """Extrair company_id dos dados do usuário"""
    return user_data.get("company_id")

# Rotas HTML
@ordem_compra_router.get("/ordem-compra", response_class=HTMLResponse)
async def ordem_compra_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de ordens de compra"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    
    return render_template("ordem_compra.html", user=user_data)

@ordem_compra_router.get("/ordem-compra/nova", response_class=HTMLResponse)
async def nova_ordem_compra_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de nova ordem de compra"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    
    return render_template("nova_ordem_compra.html", user=user_data)

# Rotas API
@ordem_compra_router.get("/api/ordem-compra")
async def get_ordens_compra(
    status: Optional[str] = None,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para listar ordens de compra"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    ordens = ordem_compra_controller.get_ordens_compra(company_id, db, status)
    
    return {
        "success": True,
        "ordens": ordens,
        "total": len(ordens)
    }

@ordem_compra_router.get("/api/ordem-compra/{ordem_id}")
async def get_ordem_compra(
    ordem_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar ordem de compra por ID"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    ordem = ordem_compra_controller.get_ordem_compra_by_id(ordem_id, company_id, db)
    
    if not ordem:
        raise HTTPException(status_code=404, detail="Ordem de compra não encontrada")
    
    return {
        "success": True,
        "ordem": ordem
    }

@ordem_compra_router.post("/api/ordem-compra")
async def create_ordem_compra(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para criar ordem de compra"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Obter dados do corpo da requisição
    body = await request.json()
    
    # Validações básicas
    if not body.get('numero_ordem') and not body.get('itens'):
        raise HTTPException(status_code=400, detail="Número da ordem ou itens são obrigatórios")
    
    result = ordem_compra_controller.create_ordem_compra(body, company_id, db)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao criar ordem de compra"))
    
    return result

@ordem_compra_router.put("/api/ordem-compra/{ordem_id}")
async def update_ordem_compra(
    ordem_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar ordem de compra"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Obter dados do corpo da requisição
    body = await request.json()
    
    result = ordem_compra_controller.update_ordem_compra(ordem_id, body, company_id, db)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao atualizar ordem de compra"))
    
    return result

@ordem_compra_router.delete("/api/ordem-compra/{ordem_id}")
async def delete_ordem_compra(
    ordem_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para deletar ordem de compra"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    result = ordem_compra_controller.delete_ordem_compra(ordem_id, company_id, db)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao deletar ordem de compra"))
    
    return result

@ordem_compra_router.patch("/api/ordem-compra/{ordem_id}/status")
async def update_status_ordem(
    ordem_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para alterar status da ordem de compra"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Obter dados do corpo da requisição
    body = await request.json()
    status = body.get("status")
    
    if not status:
        raise HTTPException(status_code=400, detail="Status é obrigatório")
    
    result = ordem_compra_controller.update_status_ordem(ordem_id, status, company_id, db)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao alterar status da ordem"))
    
    return result
