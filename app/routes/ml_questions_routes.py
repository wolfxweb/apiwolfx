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

@ml_questions_router.get("/ml/questions", response_class=HTMLResponse)
async def questions_page_with_prefix(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Alias com prefixo /ml para compatibilidade"""
    return await questions_page(request, session_token=session_token, db=db)

@ml_questions_router.get("/ml/questions/{question_id}", response_class=HTMLResponse)
async def question_detail_page_with_prefix(
    question_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Alias com prefixo /ml para página de detalhes de pergunta"""
    return await question_detail_page(question_id, request, session_token=session_token, db=db)

@ml_questions_router.get("/questions/{question_id}", response_class=HTMLResponse)
async def question_detail_page(
    question_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de detalhes de uma pergunta específica"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    company_id = user_data["company"]["id"]
    
    controller = MLQuestionsController(db)
    question_result = controller.get_question(question_id, company_id)
    
    if not question_result.get("success"):
        return RedirectResponse(url="/ml/questions?error=not_found", status_code=302)
    
    from app.views.template_renderer import render_template
    return render_template(
        "ml_question_detail.html",
        user=user_data,
        question=question_result["question"]
    )

@ml_questions_router.get("/api/questions")
async def get_questions_api(
    request: Request,
    status: Optional[str] = Query(None, description="Status: UNANSWERED, ANSWERED, CLOSED_UNANSWERED"),
    limit: int = Query(50, ge=1, le=500),
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
    result = controller.get_questions(company_id, ml_account_id, status, limit)
    
    return JSONResponse(content=result)

@ml_questions_router.get("/api/accounts")
async def get_ml_accounts_api(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para listar contas ML do usuário logado"""
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
    company_id = user_data["company"]["id"]  # Garantir que sempre usa o company_id do usuário logado
    
    # Buscar contas ML da empresa (filtradas pelo company_id do usuário logado)
    from app.models.saas_models import MLAccount, MLAccountStatus
    
    ml_accounts = db.query(MLAccount).filter(
        MLAccount.company_id == company_id,  # Filtro por company_id do usuário logado
        MLAccount.status == MLAccountStatus.ACTIVE
    ).all()
    
    accounts_list = []
    for acc in ml_accounts:
        accounts_list.append({
            "id": acc.id,
            "nickname": acc.nickname,
            "email": acc.email,
            "ml_user_id": acc.ml_user_id
        })
    
    return JSONResponse(content=accounts_list)

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
    
    ml_account_id = body.get("ml_account_id")  # Opcional - se None, sincroniza todas as contas
    status = body.get("status")  # Opcional - se None, busca todas as perguntas
    
    controller = MLQuestionsController(db)
    result = controller.sync_questions(company_id, user_id, ml_account_id, status)
    
    return JSONResponse(content=result)

