"""
Rotas de autenticação para sistema SaaS
"""
from fastapi import APIRouter, Request, Form, Depends, HTTPException, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.config.database import get_db
from app.controllers.auth_controller import AuthController

# Router para autenticação
auth_router = APIRouter()

# Instância do controller
auth_controller = AuthController()

@auth_router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request, 
    error: str = None, 
    success: str = None,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de login"""
    return auth_controller.get_login_page(error=error, success=success, session_token=session_token, db=db)

@auth_router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    remember: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Processa login do usuário"""
    result = auth_controller.login(email, password, remember, db)
    
    if result.get("error"):
        return auth_controller.get_login_page(error=result["error"])
    
    # Criar resposta de redirecionamento
    response = RedirectResponse(url="/dashboard", status_code=302)
    
    # Definir cookie de sessão
    response.set_cookie(
        key="session_token",
        value=result["session_token"],
        httponly=False,  # Permitir acesso via JavaScript
        secure=False,  # False para desenvolvimento (HTTP)
        samesite="lax",
        max_age=86400 if remember else 3600  # 1 dia ou 1 hora
    )
    
    return response

@auth_router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request, 
    error: str = None, 
    success: str = None,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de cadastro"""
    return auth_controller.get_register_page(error=error, success=success, session_token=session_token, db=db)

@auth_router.post("/register")
async def register(
    request: Request,
    company_name: str = Form(...),
    company_domain: str = Form(""),
    company_description: str = Form(""),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    terms: bool = Form(False),
    newsletter: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Processa cadastro do usuário"""
    # Validações básicas
    if password != confirm_password:
        return auth_controller.get_register_page(error="As senhas não coincidem")
    
    if not terms:
        return auth_controller.get_register_page(error="Você deve aceitar os Termos de Uso")
    
    if len(password) < 8:
        return auth_controller.get_register_page(error="A senha deve ter pelo menos 8 caracteres")
    
    result = auth_controller.register(
        company_name=company_name,
        company_domain=company_domain,
        company_description=company_description,
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=password,
        terms=terms,
        newsletter=newsletter,
        db=db
    )
    
    if result.get("error"):
        return auth_controller.get_register_page(error=result["error"])
    
    # Criar resposta de redirecionamento
    response = RedirectResponse(url="/dashboard", status_code=302)
    
    # Definir cookie de sessão
    response.set_cookie(
        key="session_token",
        value=result["session_token"],
        httponly=False,  # Permitir acesso via JavaScript
        secure=False,  # False para desenvolvimento
        samesite="lax",
        max_age=86400  # 1 dia
    )
    
    return response

@auth_router.get("/logout")
async def logout(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Processa logout do usuário"""
    if session_token:
        auth_controller.logout(session_token, db)
    
    # Redirecionar para login removendo cookie
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("session_token")
    return response

@auth_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Dashboard do usuário"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Buscar contas ML para estatísticas do dashboard
    from app.controllers.ml_controller import MLController
    ml_controller = MLController()
    
    user_data = result["user"]
    user_id = user_data["id"]
    company_id = user_data["company"]["id"]
    
    accounts_result = ml_controller.get_user_ml_accounts(user_id, company_id, db)
    total_accounts = accounts_result.get("total_accounts", 0) if accounts_result.get("success") else 0
    
    from app.views.template_renderer import render_template
    return render_template("dashboard.html", 
                         user=user_data,
                         company=user_data.get("company", {}),
                         total_accounts=total_accounts)

@auth_router.get("/profile", response_class=HTMLResponse)
async def profile(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de perfil do usuário"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    # Buscar informações completas da empresa
    from sqlalchemy import text
    from app.models.saas_models import Company, Subscription, MLAccount
    
    # Informações da empresa
    company_query = text("""
        SELECT c.*, 
               COUNT(DISTINCT u.id) as total_users,
               COUNT(DISTINCT ma.id) as total_ml_accounts
        FROM companies c
        LEFT JOIN users u ON u.company_id = c.id AND u.is_active = true
        LEFT JOIN ml_accounts ma ON ma.company_id = c.id AND ma.status = 'ACTIVE'
        WHERE c.id = :company_id
        GROUP BY c.id
    """)
    
    company_result = db.execute(company_query, {"company_id": company_id}).fetchone()
    company_info = dict(company_result._mapping) if company_result else {}
    
    # Informações da assinatura
    subscription_query = text("""
        SELECT * FROM subscriptions 
        WHERE company_id = :company_id 
        AND status = 'active'
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    
    subscription_result = db.execute(subscription_query, {"company_id": company_id}).fetchone()
    subscription_info = dict(subscription_result._mapping) if subscription_result else {}
    
    from app.views.template_renderer import render_template
    return render_template("profile.html", 
                         user=user_data,
                         company=company_info,
                         subscription=subscription_info)

@auth_router.get("/forgot-password")
async def forgot_password_page(request: Request):
    """Página de recuperação de senha"""
    # TODO: Implementar página de recuperação de senha
    return {"message": "Página de recuperação de senha em desenvolvimento"}

@auth_router.post("/forgot-password")
async def forgot_password(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """Processa recuperação de senha"""
    # TODO: Implementar lógica de recuperação de senha
    return {"message": "Funcionalidade de recuperação de senha em desenvolvimento"}

@auth_router.get("/reset-password")
async def reset_password_page(request: Request, token: str = None):
    """Página de redefinição de senha"""
    # TODO: Implementar página de redefinição de senha
    return {"message": "Página de redefinição de senha em desenvolvimento"}

@auth_router.post("/reset-password")
async def reset_password(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Processa redefinição de senha"""
    # TODO: Implementar lógica de redefinição de senha
    return {"message": "Funcionalidade de redefinição de senha em desenvolvimento"}

# Middleware para verificar autenticação
async def get_current_user(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Dependency para obter usuário atual"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail=result["error"])
    
    return result["user"]