"""
Rotas para integração com Mercado Livre
"""
from fastapi import APIRouter, Request, Depends, HTTPException, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta

from app.config.database import get_db
from app.controllers.auth_controller import AuthController
from app.controllers.ml_controller import MLController

# Router para Mercado Livre
ml_router = APIRouter()

# Instâncias dos controllers
auth_controller = AuthController()
ml_controller = MLController()

@ml_router.get("/accounts", response_class=HTMLResponse)
async def ml_accounts(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    success: str = None,
    error: str = None,
    db: Session = Depends(get_db)
):
    """Página de contas do Mercado Livre"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    user_id = user_data["id"]
    company_id = user_data["company"]["id"]
    
    # Buscar contas ML do usuário
    accounts_result = ml_controller.get_user_ml_accounts(user_id, company_id, db)
    accounts = accounts_result.get("accounts", []) if accounts_result.get("success") else []
    total_accounts = accounts_result.get("total_accounts", 0) if accounts_result.get("success") else 0
    
    from app.views.template_renderer import render_template
    return render_template("ml_accounts.html", 
                         user=user_data,
                         company=user_data.get("company", {}),
                         accounts=accounts,
                         total_accounts=total_accounts,
                         success=success or "",
                         error=error or "")

@ml_router.get("/connect")
async def ml_connect(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Inicia processo de conexão com Mercado Livre"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Usar a mesma lógica que funcionava antes
    from app.config.settings import settings
    import secrets
    import string
    
    # Gerar state para segurança
    state = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    
    # URL de autorização do ML
    auth_url = (
        f"{settings.ml_auth_url}?"
        f"client_id={settings.ml_app_id}&"
        f"response_type=code&"
        f"redirect_uri={settings.ml_redirect_uri}&"
        f"state={state}"
    )
    
    # Redirecionar para autorização do ML
    return RedirectResponse(url=auth_url, status_code=302)

@ml_router.get("/callback")
async def ml_callback(
    request: Request,
    code: str = None,
    state: str = None,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Callback do OAuth do Mercado Livre"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    if not code:
        return RedirectResponse(url="/ml/accounts?error=no_code", status_code=302)
    
    user_data = result["user"]
    user_id = user_data["id"]
    company_id = user_data["company"]["id"]
    
    try:
        # Trocar code por access_token
        token_data = await _exchange_code_for_token(code)
        if token_data.get("error"):
            return RedirectResponse(url=f"/ml/accounts?error={token_data['error']}", status_code=302)
        
        # Obter informações do usuário ML
        user_info = await _get_ml_user_info(token_data["access_token"])
        if user_info.get("error"):
            return RedirectResponse(url=f"/ml/accounts?error={user_info['error']}", status_code=302)
        
        # Verificar se a conta ML já existe
        from app.models.saas_models import MLAccount, UserMLAccount, Token, MLAccountStatus
        from datetime import datetime, timedelta
        
        existing_account = db.query(MLAccount).filter(
            MLAccount.ml_user_id == user_info["id"],
            MLAccount.company_id == company_id
        ).first()
        
        if existing_account:
            # ATUALIZAR conta existente
            existing_account.nickname = user_info["nickname"]
            existing_account.email = user_info.get("email", existing_account.email)
            existing_account.first_name = user_info.get("first_name", existing_account.first_name)
            existing_account.last_name = user_info.get("last_name", existing_account.last_name)
            existing_account.country_id = user_info.get("country_id", existing_account.country_id)
            existing_account.site_id = user_info.get("site_id", existing_account.site_id)
            existing_account.permalink = user_info.get("permalink", existing_account.permalink)
            existing_account.status = MLAccountStatus.ACTIVE
            existing_account.updated_at = datetime.utcnow()
            
            # Desativar tokens antigos
            db.query(Token).filter(
                Token.ml_account_id == existing_account.id,
                Token.is_active == True
            ).update({"is_active": False})
            
            # Salvar novos tokens
            await _save_tokens(existing_account.id, token_data, db)
            
            ml_account = existing_account
            action = "atualizada"
        else:
            # CRIAR nova conta ML
            ml_account = MLAccount(
                company_id=company_id,
                ml_user_id=user_info["id"],
                nickname=user_info["nickname"],
                email=user_info.get("email", ""),
                first_name=user_info.get("first_name", ""),
                last_name=user_info.get("last_name", ""),
                country_id=user_info.get("country_id", ""),
                site_id=user_info.get("site_id", ""),
                permalink=user_info.get("permalink", ""),
                status=MLAccountStatus.ACTIVE,
                is_primary=False,
                settings={}
            )
            db.add(ml_account)
            db.flush()  # Para obter o ID
            
            # Salvar tokens
            await _save_tokens(ml_account.id, token_data, db)
            
            action = "conectada"
        
        # Associar usuário à conta ML (se não existir)
        existing_association = db.query(UserMLAccount).filter(
            UserMLAccount.user_id == user_id,
            UserMLAccount.ml_account_id == ml_account.id
        ).first()
        
        if not existing_association:
            user_ml_account = UserMLAccount(
                user_id=user_id,
                ml_account_id=ml_account.id,
                can_read=True,
                can_write=True,
                can_delete=False,
                can_manage=True
            )
            db.add(user_ml_account)
        
        db.commit()
        
        # Redirecionar para página de contas com sucesso
        return RedirectResponse(url=f"/ml/accounts?success={action}", status_code=302)
        
    except Exception as e:
        db.rollback()
        return RedirectResponse(url=f"/ml/accounts?error=Erro interno: {str(e)}", status_code=302)

@ml_router.get("/sync/{account_id}")
async def ml_sync(
    account_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Refresh token de uma conta do Mercado Livre"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    user_id = user_data["id"]
    company_id = user_data["company"]["id"]
    
    try:
        # Buscar conta ML
        from app.models.saas_models import MLAccount, Token
        
        ml_account = db.query(MLAccount).filter(
            MLAccount.id == account_id,
            MLAccount.company_id == company_id
        ).first()
        
        if not ml_account:
            return RedirectResponse(url="/ml/accounts?error=Conta não encontrada", status_code=302)
        
        # Buscar refresh token ativo
        refresh_token = db.query(Token).filter(
            Token.ml_account_id == account_id,
            Token.token_type == "refresh",
            Token.is_active == True,
            Token.expires_at > datetime.utcnow()
        ).first()
        
        if not refresh_token:
            # Se não tem refresh token, precisa reconectar
            return RedirectResponse(url="/ml/connect?error=Reconexão necessária", status_code=302)
        
        # Usar o serviço para refresh token
        from app.services.mercadolibre_service import MercadoLivreService
        
        ml_service = MercadoLivreService()
        new_token = await ml_service.refresh_token(refresh_token.token_value)
        
        if not new_token:
            return RedirectResponse(url="/ml/accounts?error=Erro ao renovar token", status_code=302)
        
        # Desativar tokens antigos
        db.query(Token).filter(
            Token.ml_account_id == account_id,
            Token.is_active == True
        ).update({"is_active": False})
        
        # Salvar novo access token
        access_token = Token(
            ml_account_id=account_id,
            token_type="access",
            token_value=new_token.access_token,
            expires_at=datetime.utcnow() + timedelta(seconds=new_token.expires_in),
            scope=new_token.scope,
            is_active=True
        )
        db.add(access_token)
        
        # Salvar novo refresh token se disponível
        if hasattr(new_token, 'refresh_token') and new_token.refresh_token:
            new_refresh_token = Token(
                ml_account_id=account_id,
                token_type="refresh",
                token_value=new_token.refresh_token,
                expires_at=datetime.utcnow() + timedelta(days=30),
                scope=new_token.scope,
                is_active=True
            )
            db.add(new_refresh_token)
        
        db.commit()
        
        return RedirectResponse(url="/ml/accounts?success=token_updated", status_code=302)
        
    except Exception as e:
        db.rollback()
        return RedirectResponse(url=f"/ml/accounts?error=Erro interno: {str(e)}", status_code=302)

@ml_router.post("/disconnect/{account_id}")
async def ml_disconnect(
    account_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Desconecta uma conta do Mercado Livre"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    user_id = user_data["id"]
    company_id = user_data["company"]["id"]
    
    # Desconectar conta
    disconnect_result = ml_controller.disconnect_account(account_id, user_id, company_id, db)
    
    if disconnect_result.get("error"):
        return RedirectResponse(url=f"/ml/accounts?error={disconnect_result['error']}", status_code=302)
    
    return RedirectResponse(url="/ml/accounts?success=disconnected", status_code=302)

# Funções auxiliares para OAuth
async def _exchange_code_for_token(code: str) -> dict:
    """Troca code por access_token"""
    try:
        from app.config.settings import settings
        import requests
        
        url = f"{settings.ml_token_url}"
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.ml_app_id,
            "client_secret": settings.ml_client_secret,
            "code": code,
            "redirect_uri": settings.ml_redirect_uri
        }
        
        response = requests.post(url, data=data)
        response.raise_for_status()
        
        return response.json()
        
    except Exception as e:
        return {"error": f"Erro ao trocar code por token: {str(e)}"}

async def _get_ml_user_info(access_token: str) -> dict:
    """Obtém informações do usuário ML"""
    try:
        import requests
        
        url = "https://api.mercadolibre.com/users/me"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()
        
    except Exception as e:
        return {"error": f"Erro ao obter informações do usuário: {str(e)}"}

async def _save_tokens(ml_account_id: int, token_data: dict, db: Session):
    """Salva tokens de acesso"""
    try:
        from app.models.saas_models import Token
        from datetime import datetime, timedelta
        
        # Access Token
        access_token = Token(
            user_id=user_id,
            ml_account_id=ml_account_id,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_type="bearer",
            expires_in=token_data.get("expires_in", 21600),
            scope=token_data.get("scope", ""),
            expires_at=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 21600)),
            is_active=True
        )
        db.add(access_token)
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        raise e
