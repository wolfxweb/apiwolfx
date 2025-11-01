"""
Rotas para gerenciar perguntas do Mercado Livre
"""
from fastapi import APIRouter, Depends, Request, Cookie, Query, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.config.database import get_db
from app.controllers.ml_questions_controller import MLQuestionsController
from app.controllers.auth_controller import AuthController

logger = logging.getLogger(__name__)

# Router para perguntas
ml_questions_router = APIRouter()

@ml_questions_router.get("/questions", response_class=HTMLResponse)
async def questions_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de perguntas do Mercado Livre"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    
    from app.views.template_renderer import render_template
    return render_template("ml_questions.html", user=user_data)

@ml_questions_router.get("/api/questions")
async def get_questions_api(
    request: Request,
    status: Optional[str] = Query(None, description="Status: UNANSWERED, ANSWERED, CLOSED_UNANSWERED"),
    ml_account_id: Optional[int] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para listar perguntas"""
    if not session_token:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Sessão inválida"}
        )
    
    user_data = result["user"]
    company_id = user_data["company"]["id"]
    
    controller = MLQuestionsController(db)
    result = controller.get_questions(company_id, ml_account_id, status)
    
    return JSONResponse(content=result)

@ml_questions_router.get("/api/questions/{question_id}")
async def get_question_api(
    question_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter detalhes de uma pergunta"""
    if not session_token:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Sessão inválida"}
        )
    
    user_data = result["user"]
    company_id = user_data["company"]["id"]
    
    controller = MLQuestionsController(db)
    result = controller.get_question(question_id, company_id)
    
    return JSONResponse(content=result)

@ml_questions_router.post("/api/questions/{question_id}/answer")
async def answer_question_api(
    question_id: int,
    request: Request,
    body: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para responder uma pergunta"""
    if not session_token:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Sessão inválida"}
        )
    
    user_data = result["user"]
    company_id = user_data["company"]["id"]
    user_id = user_data["id"]
    
    answer_text = body.get("text", "").strip()
    if not answer_text:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Texto da resposta é obrigatório"}
        )
    
    controller = MLQuestionsController(db)
    result = controller.answer_question(question_id, answer_text, company_id, user_id)
    
    return JSONResponse(content=result)

@ml_questions_router.post("/api/questions/sync")
async def sync_questions_api(
    request: Request,
    body: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para sincronizar perguntas com o Mercado Livre"""
    if not session_token:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"}
        )
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Sessão inválida"}
        )
    
    user_data = result["user"]
    company_id = user_data["company"]["id"]
    user_id = user_data["id"]
    
    ml_account_id = body.get("ml_account_id")
    status = body.get("status")
    
    if not ml_account_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "ml_account_id é obrigatório"}
        )
    
    controller = MLQuestionsController(db)
    result = controller.sync_questions(company_id, ml_account_id, user_id, status)
    
    return JSONResponse(content=result)

