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
        httponly=True,
        secure=True,
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
        httponly=True,
        secure=True,
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
    
    from app.views.template_renderer import render_template
    # Passar os dados do usuário e empresa para o template
    user_data = result["user"]
    return render_template("dashboard.html", 
                         user=user_data,
                         company=user_data.get("company", {}))

@auth_router.get("/profile")
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
    
    # TODO: Implementar página de perfil
    return {"message": "Página de perfil em desenvolvimento", "user": result["user"]}

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