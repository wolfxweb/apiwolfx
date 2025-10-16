"""
Rotas para o módulo financeiro SaaS
Seguindo o padrão do sistema
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Cookie
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from app.config.database import get_db
from app.controllers.auth_controller import AuthController

# Configurar logging
logger = logging.getLogger(__name__)

# Criar router
financial_router = APIRouter()

# Instanciar controller
auth_controller = AuthController()

# Dados mockados em memória (temporário para demonstração)
mock_categories = [
    {
        "id": 1,
        "code": "REC001",
        "name": "Receitas de Vendas",
        "type": "revenue",
        "monthly_limit": 50000.00,
        "description": "Receitas provenientes de vendas de produtos",
        "is_active": True,
        "created_at": datetime.now(),
        "company_id": None
    },
    {
        "id": 2,
        "code": "EXP001", 
        "name": "Marketing",
        "type": "expense",
        "monthly_limit": 5000.00,
        "description": "Gastos com marketing e publicidade",
        "is_active": True,
        "created_at": datetime.now(),
        "company_id": None
    },
    {
        "id": 3,
        "code": "INV001",
        "name": "Equipamentos",
        "type": "investment",
        "monthly_limit": 10000.00,
        "description": "Investimentos em equipamentos",
        "is_active": True,
        "created_at": datetime.now(),
        "company_id": None
    }
]

# Contador para IDs únicos
next_category_id = 4

# =====================================================
# ROTAS DE INTERFACE (TEMPLATES)
# =====================================================

@financial_router.get("/financial/categories", response_class=HTMLResponse)
async def financial_categories(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de categorias financeiras"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    logger.info(f"🔍 DEBUG - user_data: {user_data}")
    logger.info(f"🔍 DEBUG - user_data keys: {list(user_data.keys()) if user_data else 'None'}")
    
    from app.views.template_renderer import render_template
    return render_template("financial_categories.html", user=user_data)

# =====================================================
# ROTAS DE API
# =====================================================

@financial_router.get("/api/financial/categories")
async def get_financial_categories(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter categorias financeiras"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    # Filtrar categorias por company_id (se implementado)
    # Por enquanto, retornar todas as categorias mockadas
    return mock_categories

@financial_router.post("/api/financial/categories")
async def create_financial_category(
    category_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para criar categoria financeira"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    # Validar dados obrigatórios
    if not category_data.get("name"):
        raise HTTPException(status_code=400, detail="Nome é obrigatório")
    if not category_data.get("type"):
        raise HTTPException(status_code=400, detail="Tipo é obrigatório")
    
    # Criar nova categoria
    global next_category_id
    new_category = {
        "id": next_category_id,
        "code": category_data.get("code", f"CAT{next_category_id:03d}"),
        "name": category_data.get("name"),
        "type": category_data.get("type"),
        "monthly_limit": float(category_data.get("monthly_limit", 0)) if category_data.get("monthly_limit") else None,
        "description": category_data.get("description", ""),
        "is_active": category_data.get("is_active", True),
        "created_at": datetime.now(),
        "company_id": company_id
    }
    
    mock_categories.append(new_category)
    next_category_id += 1
    
    logger.info(f"✅ Categoria criada: {new_category['name']} (ID: {new_category['id']})")
    return {"message": "Categoria criada com sucesso", "id": new_category["id"]}

@financial_router.put("/api/financial/categories/{category_id}")
async def update_financial_category(
    category_id: int,
    category_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar categoria financeira"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    # Buscar categoria existente
    category_index = None
    for i, cat in enumerate(mock_categories):
        if cat["id"] == category_id:
            category_index = i
            break
    
    if category_index is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    # Atualizar categoria
    mock_categories[category_index].update({
        "code": category_data.get("code", mock_categories[category_index]["code"]),
        "name": category_data.get("name", mock_categories[category_index]["name"]),
        "type": category_data.get("type", mock_categories[category_index]["type"]),
        "monthly_limit": float(category_data.get("monthly_limit", 0)) if category_data.get("monthly_limit") else None,
        "description": category_data.get("description", mock_categories[category_index]["description"]),
        "is_active": category_data.get("is_active", mock_categories[category_index]["is_active"]),
        "updated_at": datetime.now()
    })
    
    logger.info(f"✅ Categoria atualizada: {mock_categories[category_index]['name']} (ID: {category_id})")
    return {"message": "Categoria atualizada com sucesso"}

@financial_router.delete("/api/financial/categories/{category_id}")
async def delete_financial_category(
    category_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para excluir categoria financeira"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    # Buscar categoria existente
    category_index = None
    category_name = None
    for i, cat in enumerate(mock_categories):
        if cat["id"] == category_id:
            category_index = i
            category_name = cat["name"]
            break
    
    if category_index is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    # Remover categoria
    mock_categories.pop(category_index)
    
    logger.info(f"✅ Categoria excluída: {category_name} (ID: {category_id})")
    return {"message": "Categoria excluída com sucesso"}