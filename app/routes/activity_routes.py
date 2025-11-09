"""
Rotas para fornecer resumos de atividade (perguntas e mensagens) para o front-end
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers.auth_controller import AuthController
from app.models.saas_models import (
    MLMessageThread,
    MLMessageThreadStatus,
    MLQuestion,
    MLQuestionStatus,
)

activity_router = APIRouter()


def _to_iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


@activity_router.get("/api/activity/summary")
async def activity_summary(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db),
):
    """Retorna resumo de novas perguntas e mensagens pós-venda para o usuário logado."""
    if not session_token:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Não autenticado"},
        )

    auth_result = AuthController().get_user_by_session(session_token, db)
    if auth_result.get("error"):
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Sessão inválida"},
        )

    user_data = auth_result["user"]
    company_id = user_data["company"]["id"]

    # Perguntas
    unanswered_count = (
        db.query(func.count(MLQuestion.id))
        .filter(
            MLQuestion.company_id == company_id,
            MLQuestion.status == MLQuestionStatus.UNANSWERED,
        )
        .scalar()
    )

    latest_question = (
        db.query(MLQuestion)
        .filter(MLQuestion.company_id == company_id)
        .order_by(MLQuestion.question_date.desc(), MLQuestion.created_at.desc())
        .first()
    )

    # Mensagens
    open_threads = (
        db.query(func.count(MLMessageThread.id))
        .filter(
            MLMessageThread.company_id == company_id,
            MLMessageThread.status == MLMessageThreadStatus.OPEN,
        )
        .scalar()
    )

    latest_thread = (
        db.query(MLMessageThread)
        .filter(MLMessageThread.company_id == company_id)
        .order_by(
            MLMessageThread.last_message_date.desc().nullslast(),
            MLMessageThread.updated_at.desc(),
        )
        .first()
    )

    summary = {
        "success": True,
        "questions": {
            "unanswered_count": unanswered_count or 0,
            "latest_db_id": latest_question.id if latest_question else None,
            "latest_ml_question_id": latest_question.ml_question_id if latest_question else None,
            "latest_item_title": latest_question.item_title if latest_question else None,
            "latest_buyer": latest_question.buyer_nickname if latest_question else None,
            "latest_question_date": _to_iso(latest_question.question_date) if latest_question else None,
        },
        "messages": {
            "open_threads": open_threads or 0,
            "latest_thread_id": latest_thread.id if latest_thread else None,
            "latest_ml_thread_id": latest_thread.ml_thread_id if latest_thread else None,
            "latest_buyer": latest_thread.buyer_nickname if latest_thread else None,
            "latest_text": latest_thread.last_message_text if latest_thread else None,
            "latest_message_date": _to_iso(latest_thread.last_message_date) if latest_thread else None,
        },
    }

    return JSONResponse(content=summary)


