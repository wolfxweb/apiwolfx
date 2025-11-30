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
from app.views.template_renderer import render_template

logger = logging.getLogger(__name__)

# Router para Content
content_router = APIRouter()


def get_current_user_or_redirect(session_token: Optional[str], db: Session):
    """Helper para obter usuário atual ou redirecionar"""
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
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de calendário de conteúdo"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    company_id = user.get("company", {}).get("id")
    if not company_id:
        return RedirectResponse(url="/auth/dashboard", status_code=302)
    
    return render_template(
        "content_calendar.html",
        request=request,
        user=user
    )


@content_router.get("/content/ideas", response_class=HTMLResponse)
async def content_ideas_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de ideias"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    company_id = user.get("company", {}).get("id")
    if not company_id:
        return RedirectResponse(url="/auth/dashboard", status_code=302)
    
    return render_template(
        "content_ideas.html",
        request=request,
        user=user
    )


@content_router.get("/content/social", response_class=HTMLResponse)
async def content_social_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de posts sociais"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    company_id = user.get("company", {}).get("id")
    if not company_id:
        return RedirectResponse(url="/auth/dashboard", status_code=302)
    
    return render_template(
        "content_social.html",
        request=request,
        user=user
    )


@content_router.get("/content/blog", response_class=HTMLResponse)
async def content_blog_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de posts do blog"""
    user = get_current_user_or_redirect(session_token, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    company_id = user.get("company", {}).get("id")
    if not company_id:
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
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para listar ideias"""
    if not session_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessão inválida"})
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID não encontrado"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.list_ideas(company_id, search, is_ai_generated))


@content_router.post("/api/content/ideas", response_class=JSONResponse)
async def create_idea_api(
    request: Request,
    body: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para criar ideia"""
    if not session_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessão inválida"})
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID não encontrado"})
    
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
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter ideia"""
    if not session_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessão inválida"})
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID não encontrado"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.get_idea(idea_id, company_id))


@content_router.patch("/api/content/ideas/{idea_id}", response_class=JSONResponse)
async def update_idea_api(
    idea_id: int,
    request: Request,
    body: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar ideia"""
    if not session_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessão inválida"})
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID não encontrado"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.update_idea(idea_id, company_id, **body))


@content_router.delete("/api/content/ideas/{idea_id}", response_class=JSONResponse)
async def delete_idea_api(
    idea_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para excluir ideia"""
    if not session_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessão inválida"})
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID não encontrado"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.delete_idea(idea_id, company_id))


@content_router.post("/api/content/ideas/{idea_id}/convert-social", response_class=JSONResponse)
async def convert_idea_to_social_api(
    idea_id: int,
    request: Request,
    body: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para converter ideia em post social"""
    if not session_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessão inválida"})
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID não encontrado"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.convert_idea_to_social(idea_id, company_id, **body))


@content_router.post("/api/content/ideas/{idea_id}/convert-blog", response_class=JSONResponse)
async def convert_idea_to_blog_api(
    idea_id: int,
    request: Request,
    body: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para converter ideia em post de blog"""
    if not session_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessão inválida"})
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID não encontrado"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.convert_idea_to_blog(idea_id, company_id, **body))


# ========== API - SOCIAL ==========

@content_router.get("/api/content/social", response_class=JSONResponse)
async def list_social_posts_api(
    request: Request,
    status: Optional[str] = Query(None),
    canal: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para listar posts sociais"""
    if not session_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessão inválida"})
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID não encontrado"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.list_social_posts(company_id, status, canal, search))


@content_router.post("/api/content/social", response_class=JSONResponse)
async def create_social_post_api(
    request: Request,
    body: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para criar post social"""
    if not session_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessão inválida"})
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID não encontrado"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.create_social_post(company_id, **body))


@content_router.get("/api/content/social/{post_id}", response_class=JSONResponse)
async def get_social_post_api(
    post_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter post social"""
    if not session_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessão inválida"})
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID não encontrado"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.get_social_post(post_id, company_id))


@content_router.patch("/api/content/social/{post_id}", response_class=JSONResponse)
async def update_social_post_api(
    post_id: int,
    request: Request,
    body: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar post social"""
    if not session_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessão inválida"})
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID não encontrado"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.update_social_post(post_id, company_id, **body))


@content_router.delete("/api/content/social/{post_id}", response_class=JSONResponse)
async def delete_social_post_api(
    post_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para excluir post social"""
    if not session_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessão inválida"})
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID não encontrado"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.delete_social_post(post_id, company_id))


# ========== API - BLOG ==========

@content_router.get("/api/content/blog", response_class=JSONResponse)
async def list_blog_posts_api(
    request: Request,
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para listar posts do blog"""
    if not session_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessão inválida"})
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID não encontrado"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.list_blog_posts(company_id, status, search))


@content_router.post("/api/content/blog", response_class=JSONResponse)
async def create_blog_post_api(
    request: Request,
    body: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para criar post de blog"""
    if not session_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessão inválida"})
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID não encontrado"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.create_blog_post(company_id, **body))


@content_router.get("/api/content/blog/{post_id}", response_class=JSONResponse)
async def get_blog_post_api(
    post_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter post de blog"""
    if not session_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessão inválida"})
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID não encontrado"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.get_blog_post(post_id, company_id))


@content_router.patch("/api/content/blog/{post_id}", response_class=JSONResponse)
async def update_blog_post_api(
    post_id: int,
    request: Request,
    body: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para atualizar post de blog"""
    if not session_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessão inválida"})
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID não encontrado"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.update_blog_post(post_id, company_id, **body))


@content_router.delete("/api/content/blog/{post_id}", response_class=JSONResponse)
async def delete_blog_post_api(
    post_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para excluir post de blog"""
    if not session_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessão inválida"})
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID não encontrado"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.delete_blog_post(post_id, company_id))


# ========== API - CALENDÁRIO ==========

@content_router.get("/api/content/calendar", response_class=JSONResponse)
async def get_calendar_events_api(
    request: Request,
    mes: str = Query(...),
    ano: str = Query(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter eventos do calendário"""
    if not session_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessão inválida"})
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID não encontrado"})
    
    controller = ContentController(db)
    return JSONResponse(content=controller.get_calendar_events(company_id, mes, ano))


@content_router.patch("/api/content/calendar/{calendar_id}/move-date", response_class=JSONResponse)
async def move_event_date_api(
    calendar_id: int,
    request: Request,
    body: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para mover data de publicação de um evento"""
    if not session_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autenticado"})
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessão inválida"})
    
    user_data = result["user"]
    company_id = user_data.get("company", {}).get("id")
    
    if not company_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "Company ID não encontrado"})
    
    nova_data = datetime.fromisoformat(body.get("nova_data"))
    
    controller = ContentController(db)
    return JSONResponse(content=controller.move_event_date(calendar_id, company_id, nova_data))

