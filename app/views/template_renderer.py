from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
from pathlib import Path
import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

# Configurar templates com Jinja2 nativo
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# Adicionar filtro customizado para formatação de moeda brasileira
def format_brl(value):
    """Formata valor em padrão brasileiro: R$ 1.234,56"""
    if value is None:
        return "R$ 0,00"
    try:
        # Formata com 2 casas decimais
        formatted = "{:,.2f}".format(float(value))
        # Troca ponto por vírgula e vírgula por ponto
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"
    except (ValueError, TypeError):
        return "R$ 0,00"

def tojson(value):
    """Converte valor para JSON string (já retorna como safe/markup)"""
    try:
        from markupsafe import Markup
        return Markup(json.dumps(value, ensure_ascii=False, default=str))
    except ImportError:
        # Fallback se Markup não estiver disponível
        return json.dumps(value, ensure_ascii=False, default=str)

templates.env.filters['brl'] = format_brl
templates.env.filters['tojson'] = tojson

def has_menu_permission(user: Optional[Dict[str, Any]], menu_name: str, submenu_name: Optional[str] = None, request: Optional[Request] = None) -> bool:
    """
    Verifica se o usuário tem permissão para acessar um menu/submenu.
    Se o usuário for company_admin ou super_admin, sempre retorna True.
    Caso contrário, verifica as permissões do funcionário vinculado.
    """
    if not user:
        return False
    
    # Company admin e super admin têm acesso total
    user_role = user.get("role")
    if user_role in ["company_admin", "super_admin"]:
        return True
    
    # Se não tiver request, não pode verificar permissões individuais
    if not request:
        return False
    
    try:
        from app.config.database import get_db
        from app.services.hr_permissions_service import HRPermissionsService
        from app.models.hr_models import Employee
        
        # Obter db do request
        db = next(get_db())
        
        try:
            user_id = user.get("id")
            company_id = user.get("company_id") or (user.get("company", {}).get("id") if isinstance(user.get("company"), dict) else None)
            
            if not user_id or not company_id:
                return False
            
            # Buscar funcionário vinculado ao usuário
            employee = db.query(Employee).filter(
                Employee.user_id == user_id,
                Employee.company_id == company_id,
                Employee.status == "active"
            ).first()
            
            if not employee:
                return False
            
            # Verificar permissão usando o serviço
            permissions_service = HRPermissionsService(db)
            return permissions_service.check_permission(
                employee_id=employee.id,
                company_id=company_id,
                menu_name=menu_name,
                submenu_name=submenu_name
            )
        finally:
            db.close()
    except Exception as e:
        # Em caso de erro, retornar False por segurança
        return False

# Adicionar função global ao ambiente Jinja2
templates.env.globals['has_menu_permission'] = has_menu_permission

def render_template(template_name: str, request: Request = None, **context) -> HTMLResponse:
    """Função de conveniência para renderizar templates usando Jinja2 nativo"""
    if request is None:
        # Criar um request dummy se não fornecido
        from fastapi import Request
        from starlette.requests import Request as StarletteRequest
        request = StarletteRequest({"type": "http", "method": "GET", "url": "/"})
    
    context["request"] = request
    return templates.TemplateResponse(template_name, context)

def render_home() -> HTMLResponse:
    """Renderiza a página home"""
    return render_template("home.html")

def render_login_success(token_data: dict) -> HTMLResponse:
    """Renderiza página de sucesso no login"""
    context = {
        "access_token": token_data.get("access_token", ""),
        "token_type": token_data.get("token_type", ""),
        "expires_in": token_data.get("expires_in", ""),
        "scope": token_data.get("scope", ""),
        "user_id": token_data.get("user_id", ""),
        "refresh_token": token_data.get("refresh_token", "")
    }
    return render_template("login_success.html", **context)

def render_user_info(user_data: dict) -> HTMLResponse:
    """Renderiza página com informações do usuário"""
    context = {
        "user_id": user_data.get("id", ""),
        "nickname": user_data.get("nickname", ""),
        "email": user_data.get("email", ""),
        "first_name": user_data.get("first_name", ""),
        "last_name": user_data.get("last_name", ""),
        "country_id": user_data.get("country_id", ""),
        "site_id": user_data.get("site_id", ""),
        "permalink": user_data.get("permalink", "")
    }
    return render_template("user_info.html", **context)

def render_error(error_message: str, error_type: str = "error") -> HTMLResponse:
    """Renderiza página de erro"""
    context = {
        "error_message": error_message,
        "error_type": error_type
    }
    return render_template("error.html", **context)