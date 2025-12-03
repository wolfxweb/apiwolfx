"""
Rotas para Planejamento de Conteúdo
"""
from fastapi import APIRouter, Depends, Request, Cookie, Query, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import logging

from app.config.database import get_db
from app.controllers.content_controller import ContentController
from app.controllers.auth_controller import AuthController
from app.services.briefing_service import BriefingService
from app.views.template_renderer import render_template

logger = logging.getLogger(__name__)

# Router para Content
content_router = APIRouter()


def get_current_user(request: Request, db: Session) -> Optional[dict]:
    """Helper para obter usuário atual (suporta superadmin e usuário normal)"""
    from app.models.saas_models import SuperAdmin
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Primeiro, verificar se é superadmin via cookie
    superadmin_session = request.cookies.get("superadmin_session")
    superadmin_id = request.cookies.get("superadmin_id")
    
    if superadmin_session and superadmin_id:
        try:
            superadmin = db.query(SuperAdmin).filter(
                SuperAdmin.id == int(superadmin_id),
                SuperAdmin.is_active == True
            ).first()
            
            if superadmin:
                logger.info(f"✅ Superadmin autenticado via cookie: {superadmin.email}")
                return {
                    "id": superadmin.id,
                    "email": superadmin.email,
                    "first_name": superadmin.first_name,
                    "last_name": superadmin.last_name,
                    "role": "super_admin",
                    "company_id": None,
                    "company": None
                }
        except (ValueError, TypeError):
            pass
    
    # Fallback: verificar via sessão normal de usuário
    session_token = request.cookies.get("session_token")
    if session_token:
        result = AuthController().get_user_by_session(session_token, db)
        if not result.get("error"):
            user = result.get("user", {})
            logger.info(f"✅ Usuário autenticado: {user.get('email')}")
            return user
    
    return None


def get_company_id_from_user(user_data: dict, request: Request = None, body: dict = None) -> Optional[int]:
    """Extrai company_id do usuário, suportando superadmin"""
    # Tentar pegar do user_data primeiro
    company_id = user_data.get("company", {}).get("id") if user_data.get("company") else None
    
    # Se não tiver e for superadmin, tentar pegar de outras fontes
    if not company_id and user_data.get("role") == "super_admin":
        # Tentar do body primeiro
        if body and body.get("company_id"):
            return int(body.get("company_id"))
        # Tentar do query params
        if request:
            company_id_param = request.query_params.get("company_id")
            if company_id_param:
                return int(company_id_param)
    
    return company_id


def get_current_user_or_redirect(session_token: Optional[str], db: Session):
    """Helper para obter usuário atual ou redirecionar (DEPRECATED - usar get_current_user)"""
    if not session_token:
        return None
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return None
    
    return result.get("user")


# ========== PÁGINAS HTML ==========

@content_router.get("/content/calendar", response_class=HTMLResponse)
async def content_calendar_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """Página de calendário de conteúdo"""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    company_id = user.get("company", {}).get("id") if user.get("company") else None
    if not company_id and user.get("role") != "super_admin":
        return RedirectResponse(url="/auth/dashboard", status_code=302)
    
    return render_template(
        "content_calendar.html",
        request=request,
        user=user
    )


@content_router.get("/content/ideas", response_class=HTMLResponse)
async def content_ideas_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """Página de ideias"""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    company_id = user.get("company", {}).get("id") if user.get("company") else None
    is_superadmin = user.get("role") == "super_admin"
    
    return render_template(
        "content_ideas.html",
        request=request,
        user=user,
        company_id=company_id,
        is_superadmin=is_superadmin
    )


@content_router.get("/content/social", response_class=HTMLResponse)
async def content_social_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """Página de posts sociais"""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    company_id = user.get("company", {}).get("id") if user.get("company") else None
    if not company_id and user.get("role") != "super_admin":
        return RedirectResponse(url="/auth/dashboard", status_code=302)
    
    return render_template(
        "content_social.html",
        request=request,
        user=user
    )


@content_router.get("/content/blog", response_class=HTMLResponse)
async def content_blog_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """Página de posts do blog"""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    company_id = user.get("company", {}).get("id") if user.get("company") else None
    if not company_id and user.get("role") != "super_admin":
        return RedirectResponse(url="/auth/dashboard", status_code=302)
    
    return render_template(
        "content_blog.html",
        request=request,
        user=user
    )


# ========== API - IDEIAS ==========

@content_router.get("/api/content/ideas", response_class=JSONResponse)
async def list_ideas_api(
    request: Request,
    search: Optional[str] = Query(None),
    is_ai_generated: Optional[int] = Query(None),
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """API para listar ideias"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    # Se company_id não foi passado como query param, tentar pegar do usuário
    if company_id is None:
        company_id = get_company_id_from_user(user_data, request)
    
    # Se ainda não tiver company_id e não for superadmin, retornar erro
    if company_id is None and user_data.get("role") != "super_admin":
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.list_ideas(company_id, search, is_ai_generated))


@content_router.post("/api/content/ideas", response_class=JSONResponse)
async def create_idea_api(
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db)
):
    """API para criar ideia"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request, body)
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.create_idea(
        company_id,
        body.get("titulo"),
        body.get("descricao"),
        body.get("tags")
    ))


@content_router.get("/api/content/ideas/{idea_id}", response_class=JSONResponse)
async def get_idea_api(
    idea_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """API para obter ideia"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request)
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.get_idea(idea_id, company_id))


@content_router.patch("/api/content/ideas/{idea_id}", response_class=JSONResponse)
async def update_idea_api(
    idea_id: int,
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db)
):
    """API para atualizar ideia"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request, body)
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.update_idea(idea_id, company_id, **body))


@content_router.delete("/api/content/ideas/{idea_id}", response_class=JSONResponse)
async def delete_idea_api(
    idea_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """API para excluir ideia"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request)
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.delete_idea(idea_id, company_id))


@content_router.post("/api/content/ideas/{idea_id}/convert-social", response_class=JSONResponse)
async def convert_idea_to_social_api(
    idea_id: int,
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db)
):
    """API para converter ideia em post social"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request, body)
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.convert_idea_to_social(idea_id, company_id, **body))


@content_router.post("/api/content/ideas/{idea_id}/convert-blog", response_class=JSONResponse)
async def convert_idea_to_blog_api(
    idea_id: int,
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db)
):
    """API para converter ideia em post de blog"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request, body)
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.convert_idea_to_blog(idea_id, company_id, **body))


# ========== API - SOCIAL ==========

@content_router.get("/api/content/social", response_class=JSONResponse)
async def list_social_posts_api(
    request: Request,
    status: Optional[str] = Query(None),
    canal: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """API para listar posts sociais"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request)
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.list_social_posts(company_id, status, canal, search))


@content_router.post("/api/content/social", response_class=JSONResponse)
async def create_social_post_api(
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db)
):
    """API para criar post social"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request, body)
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.create_social_post(company_id, **body))


@content_router.get("/api/content/social/{post_id}", response_class=JSONResponse)
async def get_social_post_api(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """API para obter post social"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request)
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.get_social_post(post_id, company_id))


@content_router.patch("/api/content/social/{post_id}", response_class=JSONResponse)
async def update_social_post_api(
    post_id: int,
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db)
):
    """API para atualizar post social"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request, body)
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.update_social_post(post_id, company_id, **body))


@content_router.delete("/api/content/social/{post_id}", response_class=JSONResponse)
async def delete_social_post_api(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """API para excluir post social"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request)
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.delete_social_post(post_id, company_id))


# ========== API - BLOG ==========

@content_router.get("/api/content/blog", response_class=JSONResponse)
async def list_blog_posts_api(
    request: Request,
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """API para listar posts do blog"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request)
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.list_blog_posts(company_id, status, search))


@content_router.post("/api/content/blog", response_class=JSONResponse)
async def create_blog_post_api(
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db)
):
    """API para criar post de blog"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request, body)
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.create_blog_post(company_id, **body))


@content_router.get("/api/content/blog/{post_id}", response_class=JSONResponse)
async def get_blog_post_api(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """API para obter post de blog"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request)
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.get_blog_post(post_id, company_id))


@content_router.patch("/api/content/blog/{post_id}", response_class=JSONResponse)
async def update_blog_post_api(
    post_id: int,
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db)
):
    """API para atualizar post de blog"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request, body)
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.update_blog_post(post_id, company_id, **body))


@content_router.delete("/api/content/blog/{post_id}", response_class=JSONResponse)
async def delete_blog_post_api(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """API para excluir post de blog"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request)
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.delete_blog_post(post_id, company_id))


# ========== API - CALENDÁRIO ==========

@content_router.get("/api/content/calendar", response_class=JSONResponse)
async def get_calendar_events_api(
    request: Request,
    mes: str = Query(...),
    ano: str = Query(...),
    db: Session = Depends(get_db)
):
    """API para obter eventos do calendário"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request)
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.get_calendar_events(company_id, mes, ano))


@content_router.patch("/api/content/calendar/{calendar_id}/move-date", response_class=JSONResponse)
async def move_event_date_api(
    calendar_id: int,
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db)
):
    """API para mover data de publicação de um evento"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request, body)
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    nova_data = datetime.fromisoformat(body.get("nova_data"))
    
    controller = ContentController(db)
    return JSONResponse(content=controller.move_event_date(calendar_id, company_id, nova_data))


# ========== API - BRIEFINGS ==========

@content_router.get("/content/briefing", response_class=HTMLResponse)
async def content_briefing_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """Página de briefing de marketing"""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    company_id = user.get("company", {}).get("id") if user.get("company") else None
    is_superadmin = user.get("role") == "super_admin"
    
    return render_template(
        "content_briefing.html",
        request=request,
        user=user,
        company_id=company_id,
        is_superadmin=is_superadmin
    )


@content_router.post("/api/content/briefings/generate-from-name", response_class=JSONResponse)
async def generate_briefing_from_name_api(
    request: Request,
    db: Session = Depends(get_db)
):
    """API para gerar briefing completo a partir apenas do nome da empresa/produto"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    # Para superadmin, company_id pode ser None
    company_id = get_company_id_from_user(user_data, request)
    is_superadmin = user_data.get("role") == "super_admin"
    
    # Apenas usuários do SaaS precisam de company_id
    if not company_id and not is_superadmin:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    body = await request.json()
    nome_empresa_produto = body.get("nome_empresa_produto", "").strip()
    
    if not nome_empresa_produto:
        return JSONResponse(status_code=400, content={"success": False, "error": "Nome da empresa/produto é obrigatório"})
    
    service = BriefingService(db)
    user_id = user_data.get("id")
    
    result = service.generate_briefing_from_name(
        company_id=company_id,
        user_id=user_id,
        nome_empresa_produto=nome_empresa_produto,
        user=user_data
    )
    
    return JSONResponse(content=result)


@content_router.post("/api/content/briefings", response_class=JSONResponse)
async def create_briefing_api(
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db)
):
    """API para criar briefing"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request, body)
    user_id = user_data.get("id")
    is_superadmin = user_data.get("role") == "super_admin"
    
    # Apenas usuários do SaaS precisam de company_id
    if not company_id and not is_superadmin:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    service = BriefingService(db)
    return JSONResponse(content=service.create_briefing(company_id, user_id, body))


@content_router.get("/api/content/briefings", response_class=JSONResponse)
async def list_briefings_api(
    request: Request,
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """API para listar briefings"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request)
    is_superadmin = user_data.get("role") == "super_admin"
    
    # Para superadmin, pode listar todos os briefings (company_id=None)
    # Para usuários do SaaS, precisa de company_id
    if not company_id and not is_superadmin:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    service = BriefingService(db)
    return JSONResponse(content=service.list_briefings(company_id, status))


@content_router.get("/api/content/briefings/{briefing_id}", response_class=JSONResponse)
async def get_briefing_api(
    briefing_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """API para obter briefing"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request)
    is_superadmin = user_data.get("role") == "super_admin"
    
    # Para superadmin, pode acessar qualquer briefing (company_id=None)
    # Para usuários do SaaS, precisa de company_id
    if not company_id and not is_superadmin:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    service = BriefingService(db)
    return JSONResponse(content=service.get_briefing(briefing_id, company_id))


@content_router.post("/api/content/briefings/{briefing_id}/research", response_class=JSONResponse)
async def execute_research_api(
    briefing_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """API para executar pesquisa Perplexity"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request)
    is_superadmin = user_data.get("role") == "super_admin"
    
    # Para superadmin, pode executar pesquisa sem company_id
    # Para usuários do SaaS, precisa de company_id
    if not company_id and not is_superadmin:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    service = BriefingService(db)
    return JSONResponse(content=service.execute_research(briefing_id, company_id, user_data))


@content_router.post("/api/content/briefings/{briefing_id}/identify-agents", response_class=JSONResponse)
async def identify_agents_api(
    briefing_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """API para identificar agentes necessários"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request)
    is_superadmin = user_data.get("role") == "super_admin"
    
    # Para superadmin, pode identificar agentes sem company_id
    # Para usuários do SaaS, precisa de company_id
    if not company_id and not is_superadmin:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    service = BriefingService(db)
    return JSONResponse(content=service.identify_agents(briefing_id, company_id, user_data))


@content_router.post("/api/content/briefings/{briefing_id}/generate", response_class=JSONResponse)
async def generate_content_api(
    briefing_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """API para gerar conteúdo completo (pesquisa + identificação + execução de agentes)"""
    user_data = get_current_user(request, db)
    if not user_data:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    company_id = get_company_id_from_user(user_data, request)
    is_superadmin = user_data.get("role") == "super_admin"
    
    # Para superadmin, pode executar pesquisa sem company_id
    # Para usuários do SaaS, precisa de company_id
    if not company_id and not is_superadmin:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID necessário"})
    
    service = BriefingService(db)
    
    # 1. Executar pesquisa
    research_result = service.execute_research(briefing_id, company_id, user_data)
    if not research_result.get("success"):
        return JSONResponse(content=research_result)
    
    # 2. Identificar agentes
    identify_result = service.identify_agents(briefing_id, company_id, user_data)
    if not identify_result.get("success"):
        return JSONResponse(content=identify_result)
    
    # 3. Executar agentes encadeadamente
    generate_result = service.execute_agents_chain(briefing_id, company_id, user_data)
    
    return JSONResponse(content=generate_result)

