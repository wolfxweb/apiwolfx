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
from app.models.saas_models import UserRole

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
        return JSONResponse(
            status_code=400 if "já cadastrado" in result.get("error", "").lower() else 500,
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
    
    # Extrair campos de usuário
    user_email = employee_data.pop("user_email", None)
    user_password = employee_data.pop("user_password", None)
    user_role = employee_data.pop("user_role", None)
    
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
    
    controller = HRController(db)
    result = controller.update_employee(
        employee_id=employee_id,
        company_id=company_id,
        user_email=user_email,
        user_password=user_password,
        user_role=user_role,
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

