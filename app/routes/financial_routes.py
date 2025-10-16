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

# Dados mockados para centros de custo
mock_cost_centers = [
    {
        "id": 1,
        "code": "CC001",
        "name": "Administração",
        "responsible": "João Silva",
        "responsible_email": "joao@empresa.com",
        "parent_id": None,
        "parent_name": None,
        "monthly_budget": 15000.00,
        "color": "#007bff",
        "description": "Centro de custo para despesas administrativas",
        "is_active": True,
        "created_at": datetime.now(),
        "company_id": None
    },
    {
        "id": 2,
        "code": "CC002",
        "name": "Marketing",
        "responsible": "Maria Santos",
        "responsible_email": "maria@empresa.com",
        "parent_id": None,
        "parent_name": None,
        "monthly_budget": 8000.00,
        "color": "#28a745",
        "description": "Centro de custo para atividades de marketing",
        "is_active": True,
        "created_at": datetime.now(),
        "company_id": None
    },
    {
        "id": 3,
        "code": "CC003",
        "name": "Marketing Digital",
        "responsible": "Carlos Lima",
        "responsible_email": "carlos@empresa.com",
        "parent_id": 2,
        "parent_name": "Marketing",
        "monthly_budget": 5000.00,
        "color": "#17a2b8",
        "description": "Subcentro para marketing digital",
        "is_active": True,
        "created_at": datetime.now(),
        "company_id": None
    }
]

# Contador para IDs únicos de centros de custo
next_cost_center_id = 4

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

@financial_router.get("/financial/cost-centers", response_class=HTMLResponse)
async def financial_cost_centers(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de centros de custo"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    logger.info(f"🔍 DEBUG - user_data: {user_data}")
    
    from app.views.template_renderer import render_template
    return render_template("financial_cost_centers.html", user=user_data)

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

# =====================================================
# ROTAS DE API PARA CENTROS DE CUSTO
# =====================================================

@financial_router.get("/api/financial/cost-centers")
async def get_cost_centers(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter centros de custo"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    # Filtrar centros de custo por company_id (se implementado)
    # Por enquanto, retornar todos os centros de custo mockados
    return mock_cost_centers

@financial_router.post("/api/financial/cost-centers")
async def create_cost_center(
    cost_center_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para criar centro de custo"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    # Validar dados obrigatórios
    if not cost_center_data.get("name"):
        raise HTTPException(status_code=400, detail="Nome é obrigatório")
    if not cost_center_data.get("code"):
        raise HTTPException(status_code=400, detail="Código é obrigatório")
    
    # Criar novo centro de custo
    global next_cost_center_id
    new_cost_center = {
        "id": next_cost_center_id,
        "code": cost_center_data.get("code"),
        "name": cost_center_data.get("name"),
        "responsible": cost_center_data.get("responsible", ""),
        "responsible_email": cost_center_data.get("responsible_email", ""),
        "parent_id": int(cost_center_data.get("parent_id")) if cost_center_data.get("parent_id") else None,
        "parent_name": None,  # Será preenchido se parent_id existir
        "monthly_budget": float(cost_center_data.get("monthly_budget", 0)) if cost_center_data.get("monthly_budget") else None,
        "color": cost_center_data.get("color", "#007bff"),
        "description": cost_center_data.get("description", ""),
        "is_active": cost_center_data.get("is_active", True),
        "created_at": datetime.now(),
        "company_id": company_id
    }
    
    # Preencher parent_name se parent_id existir
    if new_cost_center["parent_id"]:
        parent = next((cc for cc in mock_cost_centers if cc["id"] == new_cost_center["parent_id"]), None)
        if parent:
            new_cost_center["parent_name"] = parent["name"]
    
    mock_cost_centers.append(new_cost_center)
    next_cost_center_id += 1
    
    logger.info(f"✅ Centro de custo criado: {new_cost_center['name']} (ID: {new_cost_center['id']})")
    return {"message": "Centro de custo criado com sucesso", "id": new_cost_center["id"]}

@financial_router.put("/api/financial/cost-centers/{cost_center_id}")
async def update_cost_center(
    cost_center_id: int,
    cost_center_data: dict,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar centro de custo"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    # Buscar centro de custo existente
    cost_center_index = None
    for i, cc in enumerate(mock_cost_centers):
        if cc["id"] == cost_center_id:
            cost_center_index = i
            break
    
    if cost_center_index is None:
        raise HTTPException(status_code=404, detail="Centro de custo não encontrado")
    
    # Atualizar centro de custo
    parent_id = int(cost_center_data.get("parent_id")) if cost_center_data.get("parent_id") else None
    parent_name = None
    
    if parent_id:
        parent = next((cc for cc in mock_cost_centers if cc["id"] == parent_id), None)
        if parent:
            parent_name = parent["name"]
    
    mock_cost_centers[cost_center_index].update({
        "code": cost_center_data.get("code", mock_cost_centers[cost_center_index]["code"]),
        "name": cost_center_data.get("name", mock_cost_centers[cost_center_index]["name"]),
        "responsible": cost_center_data.get("responsible", mock_cost_centers[cost_center_index]["responsible"]),
        "responsible_email": cost_center_data.get("responsible_email", mock_cost_centers[cost_center_index]["responsible_email"]),
        "parent_id": parent_id,
        "parent_name": parent_name,
        "monthly_budget": float(cost_center_data.get("monthly_budget", 0)) if cost_center_data.get("monthly_budget") else None,
        "color": cost_center_data.get("color", mock_cost_centers[cost_center_index]["color"]),
        "description": cost_center_data.get("description", mock_cost_centers[cost_center_index]["description"]),
        "is_active": cost_center_data.get("is_active", mock_cost_centers[cost_center_index]["is_active"]),
        "updated_at": datetime.now()
    })
    
    logger.info(f"✅ Centro de custo atualizado: {mock_cost_centers[cost_center_index]['name']} (ID: {cost_center_id})")
    return {"message": "Centro de custo atualizado com sucesso"}

@financial_router.delete("/api/financial/cost-centers/{cost_center_id}")
async def delete_cost_center(
    cost_center_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para excluir centro de custo"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão necessário")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    # Buscar centro de custo existente
    cost_center_index = None
    cost_center_name = None
    for i, cc in enumerate(mock_cost_centers):
        if cc["id"] == cost_center_id:
            cost_center_index = i
            cost_center_name = cc["name"]
            break
    
    if cost_center_index is None:
        raise HTTPException(status_code=404, detail="Centro de custo não encontrado")
    
    # Verificar se tem centros filhos
    has_children = any(cc["parent_id"] == cost_center_id for cc in mock_cost_centers)
    if has_children:
        raise HTTPException(status_code=400, detail="Não é possível excluir um centro de custo que possui centros filhos")
    
    # Remover centro de custo
    mock_cost_centers.pop(cost_center_index)
    
    logger.info(f"✅ Centro de custo excluído: {cost_center_name} (ID: {cost_center_id})")
    return {"message": "Centro de custo excluído com sucesso"}