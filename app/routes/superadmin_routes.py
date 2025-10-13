"""
Rotas para SuperAdmin - Painel de administração do sistema
"""
from fastapi import APIRouter, Request, Form, Depends, HTTPException, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.config.database import get_db
from app.controllers.superadmin_controller import SuperAdminController
from app.views.template_renderer import render_template

# Router para superadmin
superadmin_router = APIRouter()

def get_superadmin_session(request: Request, session_token: Optional[str] = Cookie(None)) -> Optional[dict]:
    """Verifica se o usuário está autenticado como superadmin"""
    if not session_token:
        return None
    
    # TODO: Implementar verificação de sessão de superadmin
    # Por enquanto, vamos usar uma verificação simples
    return {"id": 1, "username": "admin", "role": "super_admin"}

@superadmin_router.get("/superadmin", response_class=HTMLResponse)
async def superadmin_login_page(request: Request):
    """Página de login do superadmin"""
    return render_template("superadmin/login.html")

@superadmin_router.post("/superadmin/login")
async def superadmin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Login do superadmin"""
    controller = SuperAdminController(db)
    superadmin = controller.authenticate(username, password)
    
    if not superadmin:
        return render_template("superadmin/login.html", error="Credenciais inválidas")
    
    # TODO: Criar sessão de superadmin
    # Por enquanto, vamos redirecionar direto para o dashboard
    response = RedirectResponse(url="/superadmin/dashboard", status_code=302)
    # TODO: Definir cookie de sessão
    return response

@superadmin_router.get("/superadmin/dashboard", response_class=HTMLResponse)
async def superadmin_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    """Dashboard principal do superadmin"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    overview = controller.get_system_overview()
    
    return render_template("superadmin/dashboard.html", overview=overview, request=request)

@superadmin_router.get("/superadmin/companies", response_class=HTMLResponse)
async def superadmin_companies(
    request: Request,
    page: int = 1,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lista de empresas"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    companies_data = controller.get_companies_list(page=page, status=status)
    
    return render_template("superadmin/companies.html", 
                         companies_data=companies_data,
                         current_status=status)

@superadmin_router.get("/superadmin/companies/{company_id}", response_class=HTMLResponse)
async def superadmin_company_details(
    request: Request,
    company_id: int,
    db: Session = Depends(get_db)
):
    """Detalhes de uma empresa"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    company_details = controller.get_company_details(company_id)
    
    if not company_details:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    
    return render_template("superadmin/company_details.html", 
                         company_details=company_details)

@superadmin_router.post("/superadmin/companies/{company_id}/status")
async def update_company_status(
    request: Request,
    company_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db)
):
    """Atualiza status de uma empresa"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    success = controller.update_company_status(company_id, status)
    
    if not success:
        raise HTTPException(status_code=400, detail="Erro ao atualizar status")
    
    return RedirectResponse(url=f"/superadmin/companies/{company_id}", status_code=302)

@superadmin_router.get("/superadmin/plans", response_class=HTMLResponse)
async def superadmin_plans(
    request: Request,
    db: Session = Depends(get_db)
):
    """Lista de planos"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    plans = controller.get_plans_list()
    
    return render_template("superadmin/plans.html", plans=plans)

@superadmin_router.post("/superadmin/plans/create")
async def create_plan(
    request: Request,
    plan_name: str = Form(...),
    price: str = Form(...),
    currency: str = Form(default="BRL"),
    features: str = Form(default="{}"),
    db: Session = Depends(get_db)
):
    """Cria um novo plano"""
    # TODO: Verificar autenticação de superadmin
    import json
    
    try:
        plan_features = json.loads(features)
    except:
        plan_features = {}
    
    controller = SuperAdminController(db)
    success = controller.create_plan({
        "plan_name": plan_name,
        "price": price,
        "currency": currency,
        "plan_features": plan_features
    })
    
    if not success:
        raise HTTPException(status_code=400, detail="Erro ao criar plano")
    
    return RedirectResponse(url="/superadmin/plans", status_code=302)

@superadmin_router.post("/superadmin/companies/{company_id}/assign-plan")
async def assign_plan_to_company(
    request: Request,
    company_id: int,
    plan_name: str = Form(...),
    duration_months: int = Form(default=1),
    db: Session = Depends(get_db)
):
    """Atribui um plano a uma empresa"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    success = controller.assign_plan_to_company(company_id, plan_name, duration_months)
    
    if not success:
        raise HTTPException(status_code=400, detail="Erro ao atribuir plano")
    
    return RedirectResponse(url=f"/superadmin/companies/{company_id}", status_code=302)
