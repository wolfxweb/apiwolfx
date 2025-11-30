"""
Rotas para Recursos Humanos (RH)
"""
from fastapi import APIRouter, Depends, Request, Cookie, Query, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
import logging

from app.config.database import get_db
from app.controllers.hr_controller import HRController
from app.controllers.auth_controller import AuthController
from app.views.template_renderer import render_template
from app.models.saas_models import UserRole, User, Subscription
from app.models.hr_models import Employee
from sqlalchemy import and_

logger = logging.getLogger(__name__)

# Router para RH
hr_router = APIRouter()


def get_current_user_or_redirect(session_token: Optional[str], db: Session):
    """Helper para obter usuário atual ou redirecionar"""
    if not session_token:
        return None
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return None
    
    return result.get("user")


def check_company_admin(user: dict) -> bool:
    """Verifica se usuário é admin da empresa"""
    if not user:
        return False
    role = user.get("role")
    return role == UserRole.COMPANY_ADMIN.value or role == UserRole.SUPER_ADMIN.value


# ========== PÁGINAS HTML ==========

@hr_router.get("/hr", response_class=HTMLResponse)
async def hr_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página principal de RH"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    if not check_company_admin(user):
        return RedirectResponse(url="/auth/dashboard", status_code=302)
    
    company_id = user.get("company", {}).get("id")
    if not company_id:
        return RedirectResponse(url="/auth/dashboard", status_code=302)
    
    controller = HRController(db)
    employees_result = controller.list_employees(company_id=company_id)
    
    return render_template(
        "hr_employees.html",
        request=request,
        user=user,
        employees=employees_result.get("employees", []) if employees_result.get("success") else []
    )


@hr_router.get("/hr/employee/{employee_id}", response_class=HTMLResponse)
async def hr_employee_page(
    employee_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de detalhes do funcionário"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    if not check_company_admin(user):
        return RedirectResponse(url="/hr", status_code=302)
    
    company_id = user.get("company", {}).get("id")
    if not company_id:
        return RedirectResponse(url="/hr", status_code=302)
    
    controller = HRController(db)
    employee_result = controller.get_employee(employee_id, company_id)
    
    if not employee_result.get("success"):
        return RedirectResponse(url="/hr", status_code=302)
    
    return render_template(
        "hr_employee_view.html",
        request=request,
        user=user,
        employee=employee_result.get("employee")
    )


# ========== APIs ==========

@hr_router.get("/api/hr/employees", response_class=JSONResponse)
async def list_employees_api(
    request: Request,
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para listar funcionários"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    if not check_company_admin(user):
        return JSONResponse(
            status_code=403,
            content={"success": False, "error": "Acesso negado"}
        )
    
    company_id = user.get("company", {}).get("id")
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Company ID não encontrado"}
        )
    
    controller = HRController(db)
    result = controller.list_employees(
        company_id=company_id,
        status=status,
        search=search
    )
    
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(
            status_code=500,
            content=result
        )


@hr_router.get("/api/hr/users/stats", response_class=JSONResponse)
async def get_users_stats_api(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter estatísticas de usuários do plano"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    if not check_company_admin(user):
        return JSONResponse(
            status_code=403,
            content={"success": False, "error": "Acesso negado"}
        )
    
    company_id = user.get("company", {}).get("id")
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Company ID não encontrado"}
        )
    
    try:
        logger.info(f"🔍 [USERS STATS] Buscando estatísticas para Company ID: {company_id}")
        
        # Buscar TODAS as assinaturas da empresa para debug
        all_subscriptions = db.query(Subscription).filter(
            Subscription.company_id == company_id
        ).order_by(Subscription.created_at.desc()).all()
        logger.info(f"📋 [USERS STATS] Total de assinaturas encontradas para Company ID {company_id}: {len(all_subscriptions)}")
        for sub in all_subscriptions:
            logger.info(f"   - Subscription ID: {sub.id}, Status: {sub.status}, Is Trial: {sub.is_trial}, Plan Name: {sub.plan_name}, Max Users: {sub.max_users}, Created At: {sub.created_at}")
        
        # Buscar assinatura ativa
        subscription = db.query(Subscription).filter(
            Subscription.company_id == company_id,
            (Subscription.status == "active") | (Subscription.is_trial == True)
        ).order_by(Subscription.created_at.desc()).first()
        
        if subscription:
            logger.info(f"✅ [USERS STATS] Assinatura ativa encontrada: ID={subscription.id}, Status={subscription.status}, Is Trial={subscription.is_trial}, Plan Name={subscription.plan_name}, Max Users (assinatura)={subscription.max_users}")
        else:
            logger.warning(f"⚠️ [USERS STATS] Nenhuma assinatura ativa encontrada para Company ID {company_id}")
        
        # Obter max_users do plano
        # SEMPRE buscar do template do plano, pois ele é a fonte da verdade
        # A assinatura pode ter valores antigos
        max_users = None
        if subscription:
            logger.info(f"🔍 [USERS STATS] Max Users da assinatura: {subscription.max_users}")
            
            # SEMPRE buscar do template do plano (fonte da verdade)
            if subscription.plan_name:
                plan_template = db.query(Subscription).filter(
                    Subscription.plan_name == subscription.plan_name,
                    Subscription.status == "template"
                ).first()
                
                if plan_template:
                    logger.info(f"📋 [USERS STATS] Template encontrado: ID={plan_template.id}, Plan Name={plan_template.plan_name}, Max Users={plan_template.max_users}")
                    if plan_template.max_users and plan_template.max_users > 0:
                        max_users = plan_template.max_users
                        logger.info(f"✅ [USERS STATS] Usando max_users do template (fonte da verdade): {max_users}")
                    else:
                        logger.warning(f"⚠️ [USERS STATS] Template encontrado mas sem max_users válido, usando da assinatura")
                        max_users = subscription.max_users
                else:
                    logger.warning(f"⚠️ [USERS STATS] Template do plano '{subscription.plan_name}' não encontrado, usando da assinatura")
                    max_users = subscription.max_users
            else:
                logger.warning(f"⚠️ [USERS STATS] Assinatura sem plan_name, usando max_users da assinatura")
                max_users = subscription.max_users
        
        # Contar TODOS os funcionários ATIVOS (independente de terem conta de usuário)
        active_employees = db.query(Employee).filter(
            and_(
                Employee.company_id == company_id,
                Employee.status == "active"
            )
        ).all()
        active_users_count = len(active_employees)
        
        # Log detalhado dos funcionários ativos
        active_employee_ids = [e.id for e in active_employees]
        active_employee_names = [e.nome_completo for e in active_employees]
        logger.info(f"📊 [USERS STATS] Funcionários ATIVOS para Company ID {company_id}: {active_users_count} funcionários (IDs: {active_employee_ids}, Nomes: {active_employee_names})")
        
        # Contar TODOS os funcionários INATIVOS (independente de terem conta de usuário)
        inactive_employees = db.query(Employee).filter(
            and_(
                Employee.company_id == company_id,
                Employee.status == "inactive"
            )
        ).all()
        inactive_users_count = len(inactive_employees)
        
        # Log detalhado dos funcionários inativos
        inactive_employee_ids = [e.id for e in inactive_employees]
        inactive_employee_names = [e.nome_completo for e in inactive_employees]
        logger.info(f"📊 [USERS STATS] Funcionários INATIVOS para Company ID {company_id}: {inactive_users_count} funcionários (IDs: {inactive_employee_ids}, Nomes: {inactive_employee_names})")
        
        # Contar total de funcionários (para comparação)
        total_employees = db.query(Employee).filter(
            Employee.company_id == company_id
        ).count()
        employees_with_user = db.query(Employee).filter(
            and_(
                Employee.company_id == company_id,
                Employee.user_id.isnot(None)
            )
        ).count()
        employees_without_user = total_employees - employees_with_user
        logger.info(f"📊 [USERS STATS] Total de funcionários: {total_employees}, Com conta de usuário: {employees_with_user}, Sem conta de usuário: {employees_without_user}")
        
        # Verificar se há usuários de outras empresas (para debug)
        total_users_all_companies = db.query(User).count()
        logger.info(f"📊 [USERS STATS] Total de usuários no sistema (todas as empresas): {total_users_all_companies}")
        
        result = {
            "success": True,
            "stats": {
                "max_users": max_users,
                "active_users": active_users_count,
                "inactive_users": inactive_users_count
            }
        }
        logger.info(f"✅ [USERS STATS] Retornando estatísticas: {result}")
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de usuários: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Erro ao obter estatísticas"}
        )


@hr_router.post("/api/hr/employees", response_class=JSONResponse)
async def create_employee_api(
    request: Request,
    employee_data: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para criar funcionário"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    if not check_company_admin(user):
        return JSONResponse(
            status_code=403,
            content={"success": False, "error": "Acesso negado"}
        )
    
    company_id = user.get("company", {}).get("id")
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Company ID não encontrado"}
        )
    
    # Converter data_admissao
    if employee_data.get("data_admissao"):
        employee_data["data_admissao"] = datetime.fromisoformat(employee_data["data_admissao"].replace("Z", "+00:00")).date()
    
    if employee_data.get("data_nascimento"):
        employee_data["data_nascimento"] = datetime.fromisoformat(employee_data["data_nascimento"].replace("Z", "+00:00")).date()
    
    # Converter salario_base
    if employee_data.get("salario_base"):
        employee_data["salario_base"] = Decimal(str(employee_data["salario_base"]))
    
    controller = HRController(db)
    result = controller.create_employee(
        company_id=company_id,
        **employee_data
    )
    
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        # Retornar status 400 para erros de validação (limite, CPF duplicado, etc)
        error_message = result.get("error", "").lower()
        status_code = 400 if any(keyword in error_message for keyword in ["já cadastrado", "limite", "atingido", "e-mail já"]) else 500
        return JSONResponse(
            status_code=status_code,
            content=result
        )


@hr_router.patch("/api/hr/employees/{employee_id}", response_class=JSONResponse)
async def update_employee_api(
    employee_id: int,
    request: Request,
    employee_data: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar funcionário"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    if not check_company_admin(user):
        return JSONResponse(
            status_code=403,
            content={"success": False, "error": "Acesso negado"}
        )
    
    company_id = user.get("company", {}).get("id")
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Company ID não encontrado"}
        )
    
    # Extrair campos de usuário e status
    user_email = employee_data.pop("user_email", None)
    user_password = employee_data.pop("user_password", None)
    user_role = employee_data.pop("user_role", None)
    status = employee_data.pop("status", None)
    
    # Converter datas se fornecidas
    if employee_data.get("data_admissao"):
        employee_data["data_admissao"] = datetime.fromisoformat(employee_data["data_admissao"].replace("Z", "+00:00")).date()
    
    if employee_data.get("data_nascimento"):
        employee_data["data_nascimento"] = datetime.fromisoformat(employee_data["data_nascimento"].replace("Z", "+00:00")).date()
    
    if employee_data.get("data_demissao"):
        employee_data["data_demissao"] = datetime.fromisoformat(employee_data["data_demissao"].replace("Z", "+00:00")).date()
    
    # Converter salario_base
    if employee_data.get("salario_base"):
        employee_data["salario_base"] = Decimal(str(employee_data["salario_base"]))
    
    # Converter financial_category_id e cost_center_id (strings vazias para None)
    if employee_data.get("financial_category_id") == "" or employee_data.get("financial_category_id") is None:
        employee_data["financial_category_id"] = None
    elif employee_data.get("financial_category_id"):
        employee_data["financial_category_id"] = int(employee_data["financial_category_id"])
    
    if employee_data.get("cost_center_id") == "" or employee_data.get("cost_center_id") is None:
        employee_data["cost_center_id"] = None
    elif employee_data.get("cost_center_id"):
        employee_data["cost_center_id"] = int(employee_data["cost_center_id"])
    
    controller = HRController(db)
    result = controller.update_employee(
        employee_id=employee_id,
        company_id=company_id,
        user_email=user_email,
        user_password=user_password,
        user_role=user_role,
        status=status,
        **employee_data
    )
    
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(
            status_code=404 if "não encontrado" in result.get("error", "").lower() else 500,
            content=result
        )


@hr_router.delete("/api/hr/employees/{employee_id}", response_class=JSONResponse)
async def delete_employee_api(
    employee_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para desativar funcionário"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    if not check_company_admin(user):
        return JSONResponse(
            status_code=403,
            content={"success": False, "error": "Acesso negado"}
        )
    
    company_id = user.get("company", {}).get("id")
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Company ID não encontrado"}
        )
    
    controller = HRController(db)
    result = controller.delete_employee(employee_id, company_id)
    
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(
            status_code=404 if "não encontrado" in result.get("error", "").lower() else 500,
            content=result
        )


@hr_router.post("/api/hr/employees/{employee_id}/permissions", response_class=JSONResponse)
async def set_permissions_api(
    employee_id: int,
    request: Request,
    permissions_data: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para definir permissões de um funcionário"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    if not check_company_admin(user):
        return JSONResponse(
            status_code=403,
            content={"success": False, "error": "Acesso negado"}
        )
    
    company_id = user.get("company", {}).get("id")
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Company ID não encontrado"}
        )
    
    permissions = permissions_data.get("permissions", [])
    if not isinstance(permissions, list):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Permissões devem ser uma lista"}
        )
    
    controller = HRController(db)
    result = controller.set_permissions(
        employee_id=employee_id,
        company_id=company_id,
        permissions=permissions
    )
    
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(
            status_code=404 if "não encontrado" in result.get("error", "").lower() else 500,
            content=result
        )


@hr_router.get("/api/hr/employees/{employee_id}/permissions", response_class=JSONResponse)
async def get_permissions_api(
    employee_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter permissões de um funcionário"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    if not check_company_admin(user):
        return JSONResponse(
            status_code=403,
            content={"success": False, "error": "Acesso negado"}
        )
    
    company_id = user.get("company", {}).get("id")
    if not company_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Company ID não encontrado"}
        )
    
    controller = HRController(db)
    result = controller.get_permissions(employee_id, company_id)
    
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(
            status_code=500,
            content=result
        )

