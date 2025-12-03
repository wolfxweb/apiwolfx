"""
Rotas para gerenciar Claims (Reclamações e Devoluções) do Mercado Livre
"""
from fastapi import APIRouter, Depends, HTTPException, Cookie, Request, Body, Query
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.config.database import get_db
from app.controllers.auth_controller import AuthController
from app.controllers.ml_claims_controller import MLClaimsController

logger = logging.getLogger(__name__)

ml_claims_router = APIRouter()

@ml_claims_router.get("/claims", response_class=HTMLResponse)
async def claims_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de claims (reclamações e devoluções) do Mercado Livre"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Verificar se plano está inativo e redirecionar para profile
    if result.get("should_redirect_to_profile"):
        return RedirectResponse(url="/auth/profile", status_code=302)
    
    user_data = result["user"]
    
    from app.views.template_renderer import render_template
    return render_template("ml_claims.html", user=user_data)

def get_company_id_from_user(user_data):
    """Extrai company_id dos dados do usuário"""
    return user_data.get("company", {}).get("id")

@ml_claims_router.get("/api/ml/claims")
async def get_claims(
    ml_account_id: Optional[int] = None,
    claim_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Lista claims da empresa do usuário logado
    """
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        if result.get("error"):
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
        
        user_data = result["user"]
        company_id = get_company_id_from_user(user_data)
        user_id = user_data.get("id")
        
        if not company_id:
            raise HTTPException(status_code=400, detail="Company ID não encontrado")
        
        controller = MLClaimsController(db)
        result = controller.get_claims(
            company_id=company_id,
            ml_account_id=ml_account_id,
            claim_type=claim_type,
            status=status,
            limit=limit,
            offset=offset
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Erro ao buscar claims"))
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar claims: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@ml_claims_router.get("/api/ml/claims/{claim_id}")
async def get_claim_details(
    claim_id: int,
    refresh: bool = Query(True, description="Buscar dados atualizados da API do ML"),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Busca detalhes completos de um claim específico
    
    Args:
        claim_id: ID do claim no banco local
        refresh: Se True, busca dados atualizados da API do ML antes de retornar
    """
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        if result.get("error"):
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
        
        user_data = result["user"]
        company_id = get_company_id_from_user(user_data)
        
        if not company_id:
            raise HTTPException(status_code=400, detail="Company ID não encontrado")
        
        controller = MLClaimsController(db)
        result = controller.get_claim_details(claim_id, company_id, refresh_from_api=refresh)
        
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Claim não encontrado"))
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes do claim: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@ml_claims_router.post("/api/ml/claims/sync")
async def sync_claims(
    ml_account_id: Optional[int] = None,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Sincroniza claims do Mercado Livre com o banco de dados
    """
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        if result.get("error"):
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
        
        user_data = result["user"]
        company_id = get_company_id_from_user(user_data)
        user_id = user_data.get("id")
        
        if not company_id:
            raise HTTPException(status_code=400, detail="Company ID não encontrado")
        
        controller = MLClaimsController(db)
        result = controller.sync_claims(company_id, user_id, ml_account_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Erro ao sincronizar claims"))
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao sincronizar claims: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@ml_claims_router.post("/api/ml/claims/{claim_id}/accept")
async def accept_claim(
    claim_id: int,
    body_data: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Aceita um claim
    """
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        if result.get("error"):
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
        
        user_data = result["user"]
        company_id = get_company_id_from_user(user_data)
        user_id = user_data.get("id")
        
        if not company_id:
            raise HTTPException(status_code=400, detail="Company ID não encontrado")
        
        message = body_data.get("message")
        controller = MLClaimsController(db)
        result = controller.accept_claim(claim_id, company_id, user_id, message)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Erro ao aceitar claim"))
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao aceitar claim: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@ml_claims_router.post("/api/ml/claims/{claim_id}/reject")
async def reject_claim(
    claim_id: int,
    body_data: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Rejeita um claim
    """
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        if result.get("error"):
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
        
        user_data = result["user"]
        company_id = get_company_id_from_user(user_data)
        user_id = user_data.get("id")
        
        if not company_id:
            raise HTTPException(status_code=400, detail="Company ID não encontrado")
        
        message = body_data.get("message", "")
        if not message:
            raise HTTPException(status_code=400, detail="Mensagem é obrigatória para rejeitar claim")
        
        controller = MLClaimsController(db)
        result = controller.reject_claim(claim_id, company_id, user_id, message)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Erro ao rejeitar claim"))
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao rejeitar claim: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@ml_claims_router.post("/api/ml/claims/{claim_id}/messages")
async def send_message(
    claim_id: int,
    body_data: dict = Body(...),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Envia mensagem em um claim
    """
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        if result.get("error"):
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
        
        user_data = result["user"]
        company_id = get_company_id_from_user(user_data)
        user_id = user_data.get("id")
        
        if not company_id:
            raise HTTPException(status_code=400, detail="Company ID não encontrado")
        
        message = body_data.get("message", "")
        if not message:
            raise HTTPException(status_code=400, detail="Mensagem é obrigatória")
        
        controller = MLClaimsController(db)
        result = controller.send_message(claim_id, company_id, user_id, message)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Erro ao enviar mensagem"))
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@ml_claims_router.get("/api/ml/claims/accounts")
async def get_ml_accounts(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Lista contas ML do usuário logado para filtro
    """
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        if result.get("error"):
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
        
        user_data = result["user"]
        company_id = get_company_id_from_user(user_data)
        
        if not company_id:
            raise HTTPException(status_code=400, detail="Company ID não encontrado")
        
        from app.models.saas_models import MLAccount, MLAccountStatus
        
        accounts = db.query(MLAccount).filter(
            MLAccount.company_id == company_id,
            MLAccount.status == MLAccountStatus.ACTIVE
        ).order_by(MLAccount.nickname.asc()).all()
        
        accounts_list = [
            {
                "id": acc.id,
                "nickname": acc.nickname,
                "ml_user_id": acc.ml_user_id
            }
            for acc in accounts
        ]
        
        return JSONResponse(content={
            "success": True,
            "accounts": accounts_list
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar contas ML: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

