"""
Rotas para Fornecedores
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.config.database import get_db
from app.controllers.fornecedores_controller import FornecedoresController
from app.controllers.auth_controller import AuthController
from app.views.template_renderer import render_template

logger = logging.getLogger(__name__)

fornecedores_router = APIRouter()
fornecedores_controller = FornecedoresController()
auth_controller = AuthController()

def get_company_id_from_user(user_data: dict) -> int:
    """Extrair company_id dos dados do usuário"""
    return user_data.get("company_id")

# Rotas HTML
@fornecedores_router.get("/fornecedores", response_class=HTMLResponse)
async def fornecedores_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de fornecedores"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    
    return render_template("fornecedores.html", user=user_data)

# Rotas API
@fornecedores_router.get("/api/fornecedores")
async def get_fornecedores(
    ativo: Optional[bool] = None,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para listar fornecedores"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    fornecedores = fornecedores_controller.get_fornecedores(company_id, db, ativo)
    
    return {
        "success": True,
        "fornecedores": fornecedores,
        "total": len(fornecedores)
    }

@fornecedores_router.get("/api/fornecedores/{fornecedor_id}")
async def get_fornecedor(
    fornecedor_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar fornecedor por ID"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    fornecedor = fornecedores_controller.get_fornecedor_by_id(fornecedor_id, company_id, db)
    
    if not fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    
    return {
        "success": True,
        "fornecedor": fornecedor
    }

@fornecedores_router.post("/api/fornecedores")
async def create_fornecedor(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para criar fornecedor"""
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
    if not body.get('nome'):
        raise HTTPException(status_code=400, detail="Nome é obrigatório")
    
    result = fornecedores_controller.create_fornecedor(body, company_id, db)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao criar fornecedor"))
    
    return result

@fornecedores_router.put("/api/fornecedores/{fornecedor_id}")
async def update_fornecedor(
    fornecedor_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar fornecedor"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    # Obter dados do corpo da requisição
    body = await request.json()
    
    result = fornecedores_controller.update_fornecedor(fornecedor_id, body, company_id, db)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao atualizar fornecedor"))
    
    return result

@fornecedores_router.delete("/api/fornecedores/{fornecedor_id}")
async def delete_fornecedor(
    fornecedor_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para deletar fornecedor"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    result = fornecedores_controller.delete_fornecedor(fornecedor_id, company_id, db)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao deletar fornecedor"))
    
    return result

@fornecedores_router.patch("/api/fornecedores/{fornecedor_id}/toggle-status")
async def toggle_fornecedor_status(
    fornecedor_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para alternar status do fornecedor"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = get_company_id_from_user(user_data)
    
    result = fornecedores_controller.toggle_fornecedor_status(fornecedor_id, company_id, db)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao alterar status do fornecedor"))
    
    return result
