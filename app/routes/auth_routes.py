"""
Rotas de autenticação para sistema SaaS
"""
from fastapi import APIRouter, Request, Form, Depends, HTTPException, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.config.database import get_db
from app.controllers.auth_controller import AuthController
from app.config.settings import Settings

# Router para autenticação
auth_router = APIRouter()

# Instância do controller e settings
auth_controller = AuthController()
settings = Settings()

@auth_router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request, 
    error: str = None, 
    success: str = None,
    redirect: str = None,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de login"""
    return auth_controller.get_login_page(error=error, success=success, session_token=session_token, db=db, redirect=redirect)

@auth_router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    remember: bool = Form(False),
    redirect: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Processa login do usuário"""
    result = auth_controller.login(email, password, remember, db)
    
    if result.get("error"):
        return auth_controller.get_login_page(error=result["error"], redirect=redirect)
    
    # Redirecionar para a URL especificada ou dashboard por padrão
    redirect_url = redirect if redirect else "/dashboard"
    response = RedirectResponse(url=redirect_url, status_code=302)
    
    # Definir cookie de sessão (secure=True em produção HTTPS)
    response.set_cookie(
        key="session_token",
        value=result["session_token"],
        httponly=False,  # Permitir acesso via JavaScript
        secure=settings.is_production,  # True em produção (HTTPS), False em dev (HTTP)
        samesite="lax",
        max_age=86400 if remember else 3600  # 1 dia ou 1 hora
    )
    
    return response

@auth_router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request, 
    plan: int = None,
    error: str = None, 
    success: str = None,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de cadastro"""
    from app.models.saas_models import Subscription
    
    # Buscar planos disponíveis
    plans = db.query(Subscription).filter(
        Subscription.status == "template"
    ).order_by(Subscription.price).all()
    
    plans_data = []
    for p in plans:
        plans_data.append({
            "id": p.id,
            "plan_name": p.plan_name,
            "price": float(p.price) if p.price else 0,
            "promotional_price": float(p.promotional_price) if p.promotional_price else None
        })
    
    return auth_controller.get_register_page(
        error=error, 
        success=success, 
        session_token=session_token, 
        selected_plan=plan,
        plans=plans_data,
        db=db
    )

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
    plan_id: int = Form(None),
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
        plan_id=plan_id,
        terms=terms,
        newsletter=newsletter,
        db=db
    )
    
    if result.get("error"):
        return auth_controller.get_register_page(error=result["error"])
    
    # Criar resposta de redirecionamento
    response = RedirectResponse(url="/dashboard", status_code=302)
    
    # Definir cookie de sessão (secure=True em produção HTTPS)
    response.set_cookie(
        key="session_token",
        value=result["session_token"],
        httponly=False,  # Permitir acesso via JavaScript
        secure=settings.is_production,  # True em produção (HTTPS), False em dev (HTTP)
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
    """Dashboard de gestão do usuário"""
    from app.views.template_renderer import render_template
    from fastapi.responses import RedirectResponse
    
    # Verificar autenticação
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result.get("user")
    company_id = user_data.get("company_id") if user_data else None
    
    if not company_id:
        return render_template("dashboard_simple.html", request=request, user=user_data)
    
    return render_template("auth_dashboard.html", request=request, user=user_data)

@auth_router.get("/api/dashboard/data")
async def get_dashboard_data(
    request: Request,
    period: Optional[str] = "30days",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter dados do dashboard de gestão"""
    from fastapi.responses import JSONResponse
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Debug: verificar se o cookie está sendo recebido
    if not session_token:
        # Tentar pegar do header também
        session_token = request.cookies.get("session_token")
        logger.warning(f"Dashboard API: Cookie não encontrado no parâmetro, tentando do request.cookies: {session_token is not None}")
    
    if not session_token:
        logger.error("Dashboard API: Nenhum token de sessão encontrado")
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        logger.error(f"Dashboard API: Erro ao validar sessão: {result.get('error')}")
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Sessão inválida"}
        )
    
    user_data = result.get("user")
    # Tentar pegar company_id diretamente ou do objeto company
    company_id = user_data.get("company_id") if user_data else None
    if not company_id and user_data and user_data.get("company"):
        company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        logger.error(f"Dashboard API: Empresa não encontrada. user_data keys: {list(user_data.keys()) if user_data else 'None'}")
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Empresa não encontrada"}
        )
    
    logger.info(f"Dashboard API: Buscando dados para company_id={company_id}, período={period}, de {date_from} até {date_to}")
    dashboard_data = auth_controller.get_management_dashboard_data(
        company_id, 
        db, 
        period=period,
        date_from=date_from,
        date_to=date_to
    )
    logger.info(f"Dashboard API: Dados retornados com sucesso: {dashboard_data.get('success', False)}")
    return JSONResponse(content=dashboard_data)

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
    
    # Informações da assinatura (incluindo trial)
    subscription_query = text("""
        SELECT * FROM subscriptions 
        WHERE company_id = :company_id 
        AND (status = 'active' OR is_trial = true)
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



@auth_router.get("/plans", response_class=HTMLResponse)
async def plans_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de planos e assinaturas"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    # Buscar assinatura atual
    from sqlalchemy import text
    
    subscription_query = text("""
        SELECT * FROM subscriptions 
        WHERE company_id = :company_id 
        AND (status = 'active' OR is_trial = true)
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    
    subscription_result = db.execute(subscription_query, {"company_id": company_id}).fetchone()
    subscription_info = dict(subscription_result._mapping) if subscription_result else None
    
    # Buscar planos disponíveis do banco de dados
    plans_query = text("""
        SELECT * FROM mp_plans 
        WHERE is_active = true
        ORDER BY price ASC
    """)
    
    plans_result = db.execute(plans_query).fetchall()
    available_plans = [dict(plan._mapping) for plan in plans_result]
    
    from app.views.template_renderer import render_template
    return render_template("plans.html", 
                         user=user_data,
                         subscription=subscription_info,
                         plans=available_plans)

@auth_router.get("/payments", response_class=HTMLResponse)
async def payments_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de pagamentos do usuário"""
    try:
        # Obter usuário da sessão
        auth_controller = AuthController()
        user_result = auth_controller.get_user_by_session(session_token, db)
        
        if user_result.get("error"):
            return RedirectResponse(url="/auth/login", status_code=302)
        
        user_data = user_result["user"]
        company_id = user_data["company_id"]
        
        from app.views.template_renderer import render_template
        return render_template("payments.html", 
                             user=user_data)
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar página de pagamentos: {e}")
        return RedirectResponse(url="/auth/login", status_code=302)

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
