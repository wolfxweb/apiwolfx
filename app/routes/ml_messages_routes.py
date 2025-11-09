"""
Rotas para gerenciar mensagens pós-venda do Mercado Livre
"""
from fastapi import APIRouter, Depends, Request, Cookie, Query, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.config.database import get_db
from app.controllers.ml_messages_controller import MLMessagesController
from app.controllers.auth_controller import AuthController

logger = logging.getLogger(__name__)

# Router para mensagens pós-venda
ml_messages_router = APIRouter()

@ml_messages_router.get("/messages", response_class=HTMLResponse)
async def messages_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de mensagens pós-venda do Mercado Livre"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    
    from app.views.template_renderer import render_template
    return render_template("ml_messages.html", user=user_data)

@ml_messages_router.get("/ml/messages", response_class=HTMLResponse)
async def messages_page_with_prefix(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Alias com prefixo /ml para compatibilidade"""
    return await messages_page(request, session_token=session_token, db=db)

@ml_messages_router.get("/api/messages")
async def get_threads_api(
    request: Request,
    status: Optional[str] = Query(None, description="Status: open, closed"),
    ml_account_id: Optional[int] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para listar conversas/threads"""
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
    
    controller = MLMessagesController(db)
    result = controller.get_threads(company_id, ml_account_id, status)
    
    return JSONResponse(content=result)

@ml_messages_router.get("/api/messages/{thread_id}")
async def get_thread_api(
    thread_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter detalhes de uma conversa/thread"""
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
    
    controller = MLMessagesController(db)
    result = controller.get_thread(thread_id, company_id)
    
    return JSONResponse(content=result)

@ml_messages_router.post("/api/messages/create")
async def create_message_api(
    request: Request,
    body: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para criar uma nova mensagem pós-venda"""
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
    
    package_id = body.get("package_id")
    reason = body.get("reason")
    message_text = body.get("message_text")
    
    if not all([package_id, reason, message_text]):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "package_id, reason e message_text são obrigatórios"}
        )
    
    controller = MLMessagesController(db)
    result = controller.create_message(package_id, reason, message_text, company_id, user_id)
    
    return JSONResponse(content=result)

@ml_messages_router.post("/api/messages/{thread_id}/send")
async def send_message_api(
    thread_id: int,
    request: Request,
    body: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para enviar mensagem em conversa existente"""
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
    
    message_text = body.get("message_text")
    if not message_text:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "message_text é obrigatório"}
        )
    
    controller = MLMessagesController(db)
    result = controller.send_message(thread_id, message_text, company_id, user_id)
    
    return JSONResponse(content=result)

@ml_messages_router.post("/api/messages/sync")
async def sync_messages_api(
    request: Request,
    body: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para sincronizar mensagens pós-venda"""
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
    date_from = body.get("date_from")  # Formato: YYYY-MM-DD ou YYYY-MM-DDTHH:mm:ss
    date_to = body.get("date_to")      # Formato: YYYY-MM-DD ou YYYY-MM-DDTHH:mm:ss
    fetch_all = body.get("fetch_all", True)  # Por padrão busca todas as páginas
    
    controller = MLMessagesController(db)
    result = controller.sync_messages(
        company_id, 
        user_id, 
        ml_account_id,
        date_from=date_from,
        date_to=date_to,
        fetch_all=fetch_all
    )
    
    return JSONResponse(content=result)

@ml_messages_router.get("/api/messages/reasons")
async def get_reasons_api(
    request: Request,
    ml_account_id: Optional[int] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para obter motivos disponíveis para iniciar comunicação"""
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
    user_id = user_data["id"]
    
    controller = MLMessagesController(db)
    result = controller.get_reasons(user_id, ml_account_id)
    
    return JSONResponse(content=result)

@ml_messages_router.get("/api/messages/accounts")
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
    company_id = user_data["company"]["id"]
    user_id = user_data["id"]
    
    from app.models.saas_models import MLAccount, MLAccountStatus, UserMLAccount
    
    accounts_query = (
        db.query(MLAccount)
        .join(UserMLAccount, UserMLAccount.ml_account_id == MLAccount.id)
        .filter(
            MLAccount.company_id == company_id,
            UserMLAccount.user_id == user_id,
            MLAccount.status == MLAccountStatus.ACTIVE,
        )
        .order_by(MLAccount.nickname.asc(), MLAccount.id.asc())
    )
    
    ml_accounts = accounts_query.all()
    
    # Se o usuário não tiver contas vinculadas explicitamente, retornar todas da empresa
    if not ml_accounts:
        ml_accounts = (
            db.query(MLAccount)
            .filter(
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE,
            )
            .order_by(MLAccount.nickname.asc(), MLAccount.id.asc())
            .all()
        )
    
    accounts_list = [
        {
            "id": acc.id,
            "nickname": acc.nickname,
            "ml_user_id": acc.ml_user_id,
            "site_id": acc.site_id,
        }
        for acc in ml_accounts
    ]
    
    return JSONResponse(
        content={
            "success": True,
            "accounts": accounts_list,
        }
    )

