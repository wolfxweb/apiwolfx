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

@superadmin_router.get("/superadmin/assistants", response_class=HTMLResponse)
async def superadmin_assistants(
    request: Request,
    db: Session = Depends(get_db)
):
    """Gerenciar agentes OpenAI"""
    # TODO: Verificar autenticação de superadmin
    return render_template("superadmin/assistants.html", request=request)

@superadmin_router.get("/superadmin/assistants/new", response_class=HTMLResponse)
async def superadmin_assistants_new(
    request: Request,
    db: Session = Depends(get_db)
):
    """Criar novo agente OpenAI"""
    # TODO: Verificar autenticação de superadmin
    return render_template("superadmin/assistants_form.html", request=request, assistant_id=None)

@superadmin_router.get("/superadmin/assistants/{assistant_id}/edit", response_class=HTMLResponse)
async def superadmin_assistants_edit(
    request: Request,
    assistant_id: int,
    db: Session = Depends(get_db)
):
    """Editar agente OpenAI"""
    # TODO: Verificar autenticação de superadmin
    return render_template("superadmin/assistants_form.html", request=request, assistant_id=assistant_id)

@superadmin_router.get("/superadmin/assistants/usage", response_class=HTMLResponse)
async def superadmin_assistants_usage(
    request: Request,
    db: Session = Depends(get_db)
):
    """Monitorar uso de tokens dos agentes"""
    # TODO: Verificar autenticação de superadmin
    return render_template("superadmin/assistants_usage.html", request=request)

@superadmin_router.get("/superadmin/plans", response_class=HTMLResponse)
async def superadmin_plans(
    request: Request,
    db: Session = Depends(get_db)
):
    """Lista de planos"""
    # TODO: Verificar autenticação de superadmin
    return render_template("superadmin/plans.html")

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

# ==================== API REST PARA EMPRESAS ====================

@superadmin_router.get("/api/superadmin/companies")
async def api_get_companies(
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """API: Lista empresas com paginação"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    companies_data = controller.get_companies_list(page=page, per_page=per_page, status=status)
    return companies_data

@superadmin_router.get("/api/superadmin/companies/{company_id}")
async def api_get_company(
    company_id: int,
    db: Session = Depends(get_db)
):
    """API: Obtém detalhes de uma empresa"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    company_details = controller.get_company_details(company_id)
    
    if not company_details:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    
    return company_details

@superadmin_router.post("/api/superadmin/companies")
async def api_create_company(
    company_data: dict,
    db: Session = Depends(get_db)
):
    """API: Cria uma nova empresa"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    
    try:
        result = controller.create_company(company_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@superadmin_router.put("/api/superadmin/companies/{company_id}")
async def api_update_company(
    company_id: int,
    company_data: dict,
    db: Session = Depends(get_db)
):
    """API: Atualiza uma empresa existente"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    
    try:
        result = controller.update_company(company_id, company_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@superadmin_router.delete("/api/superadmin/companies/{company_id}")
async def api_delete_company(
    company_id: int,
    db: Session = Depends(get_db)
):
    """API: Exclui uma empresa"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    
    try:
        result = controller.delete_company(company_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = str(e)
        # Se for erro do banco, extrair informação relevante
        if hasattr(e, 'orig') and e.orig:
            error_detail = str(e.orig)
        elif hasattr(e, 'args') and e.args:
            error_detail = str(e.args[0]) if isinstance(e.args[0], str) else str(e)
        
        # Log detalhado
        print(f"❌ Erro ao excluir empresa {company_id} via API: {error_detail}")
        print(traceback.format_exc())
        
        raise HTTPException(status_code=500, detail=f"Erro interno: {error_detail}")

@superadmin_router.get("/api/superadmin/companies/{company_id}/subscription")
async def api_get_company_subscription(
    company_id: int,
    db: Session = Depends(get_db)
):
    """API: Busca assinatura ativa da empresa"""
    # TODO: Verificar autenticação de superadmin
    from app.models.saas_models import Subscription
    
    try:
        # Buscar assinatura ativa da empresa
        subscription = db.query(Subscription).filter(
            Subscription.company_id == company_id,
            Subscription.status == "active"
        ).first()
        
        if not subscription:
            return {"subscription": None, "plan_template_id": None}
        
        # Buscar o template do plano com o mesmo nome
        plan_template = db.query(Subscription).filter(
            Subscription.plan_name == subscription.plan_name,
            Subscription.status == "template"
        ).first()
        
        return {
            "subscription": {
                "id": subscription.id,
                "plan_name": subscription.plan_name,
                "price": subscription.price,
                "status": subscription.status
            },
            "plan_template_id": plan_template.id if plan_template else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# ==================== API REST PARA PLANOS ====================

@superadmin_router.get("/api/superadmin/plans")
async def api_get_plans(db: Session = Depends(get_db)):
    """API: Lista todos os planos"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    return controller.get_plans_overview()

@superadmin_router.post("/api/superadmin/plans")
async def api_create_plan(
    request: Request,
    db: Session = Depends(get_db)
):
    """API: Cria um novo plano"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    
    try:
        plan_data = await request.json()
        result = controller.create_plan_template(plan_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@superadmin_router.put("/api/superadmin/plans/{plan_id}")
async def api_update_plan(
    plan_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """API: Atualiza um plano existente"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    
    try:
        plan_data = await request.json()
        result = controller.update_plan_template(plan_id, plan_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@superadmin_router.delete("/api/superadmin/plans/{plan_id}")
async def api_delete_plan(
    plan_id: int,
    db: Session = Depends(get_db)
):
    """API: Exclui um plano"""
    # TODO: Verificar autenticação de superadmin
    controller = SuperAdminController(db)
    
    try:
        result = controller.delete_plan_template(plan_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
