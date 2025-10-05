from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
from pathlib import Path

# Configurar templates com Jinja2 nativo
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

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