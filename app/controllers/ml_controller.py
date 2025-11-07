"""
Controller para integração com Mercado Livre
"""
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import requests
import secrets
import string
import logging

from app.config.settings import settings
from app.models.saas_models import MLAccount, UserMLAccount, Token, User, Company
from app.models.saas_models import MLAccountStatus

logger = logging.getLogger(__name__)

class MLController:
    """Controller para integração com Mercado Livre"""
    
    def __init__(self):
        self.client_id = settings.ml_app_id
        self.client_secret = settings.ml_client_secret
        self.redirect_uri = settings.ml_redirect_uri
        self.base_url = settings.ml_api_base_url
    
    def start_oauth_flow(self, user_id: int, company_id: int, db: Session) -> dict:
        """Inicia o fluxo OAuth do Mercado Livre"""
        try:
            # Gerar state para segurança
            state = self._generate_state()
            
            # Salvar state na sessão (pode usar cache/redis em produção)
            # Por enquanto, vamos usar o state como identificador
            
            # URL de autorização do ML
            auth_url = (
                f"{self.base_url}/oauth/authorize?"
                f"client_id={self.client_id}&"
                f"response_type=code&"
                f"redirect_uri={self.redirect_uri}&"
                f"state={state}"
            )
            
            return {
                "success": True,
                "auth_url": auth_url,
                "state": state
            }
            
        except Exception as e:
            return {"error": f"Erro ao iniciar OAuth: {str(e)}"}
    
    def handle_oauth_callback(self, code: str, state: str, user_id: int, company_id: int, db: Session) -> dict:
        """Processa o callback do OAuth do Mercado Livre"""
        try:
            # Trocar code por access_token
            token_data = self._exchange_code_for_token(code)
            if token_data.get("error"):
                return token_data
            
            # Obter informações do usuário ML
            user_info = self._get_ml_user_info(token_data["access_token"])
            if user_info.get("error"):
                return user_info
            
            # Verificar se a conta ML já existe
            existing_account = db.query(MLAccount).filter(
                MLAccount.ml_user_id == str(user_info["id"]),  # Converter para string para garantir correspondência
                MLAccount.company_id == company_id
            ).first()
            
            if existing_account:
                # Atualizar tokens existentes
                self._update_tokens(existing_account.id, token_data, db)
                ml_account = existing_account
            else:
                # Criar nova conta ML
                ml_account = self._create_ml_account(user_info, company_id, db)
                if ml_account.get("error"):
                    return ml_account
                ml_account = ml_account["account"]
                
                # Salvar tokens
                self._save_tokens(ml_account.id, token_data, db)
            
            # Associar usuário à conta ML
            self._associate_user_to_account(user_id, ml_account.id, db)
            
            return {
                "success": True,
                "message": "Conta conectada com sucesso!",
                "account": {
                    "id": ml_account.id,
                    "nickname": ml_account.nickname,
                    "email": ml_account.email,
                    "site_id": ml_account.site_id
                }
            }
            
        except Exception as e:
            return {"error": f"Erro ao processar callback: {str(e)}"}
    
    def get_user_ml_accounts(self, user_id: int, company_id: int, db: Session) -> dict:
        """Obtém contas ML do usuário"""
        try:
            logger.info(f"🔍 get_user_ml_accounts - Buscando contas ML para company_id: {company_id}")
            
            # Buscar contas ML da empresa (sem JOIN com UserMLAccount)
            accounts = db.query(MLAccount).filter(
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).all()
            
            logger.info(f"🔍 Encontradas {len(accounts)} contas ML para company_id {company_id}")
            
            accounts_data = []
            for account in accounts:
                logger.info(f"  - Conta ML ID: {account.id}, Nickname: {account.nickname}, ml_user_id: {account.ml_user_id}, company_id: {account.company_id}")
                
                # Validação adicional: verificar se realmente pertence ao company
                if account.company_id != company_id:
                    logger.error(f"❌ ATENÇÃO: Conta ML {account.id} tem company_id {account.company_id} mas foi buscada para company_id {company_id}!")
                    continue  # Pular esta conta
                
                # Formatar data de criação
                created_at_formatted = account.created_at.strftime('%d/%m/%Y') if account.created_at else 'N/A'
                
                accounts_data.append({
                    "id": account.id,
                    "nickname": account.nickname,
                    "email": account.email,
                    "country_id": account.country_id,
                    "site_id": account.site_id,
                    "is_primary": account.is_primary,
                    "status": account.status.value if hasattr(account.status, 'value') else str(account.status),
                    "last_sync": account.last_sync,
                    "created_at": created_at_formatted
                })
            
            return {
                "success": True,
                "accounts": accounts_data,
                "total_accounts": len(accounts_data)
            }
            
        except Exception as e:
            return {"error": f"Erro ao buscar contas: {str(e)}"}
    
    def disconnect_account(self, account_id: int, user_id: int, company_id: int, db: Session) -> dict:
        """Desconecta uma conta ML"""
        try:
            # Verificar se o usuário tem permissão para esta conta
            user_account = db.query(UserMLAccount).join(MLAccount).filter(
                UserMLAccount.user_id == user_id,
                MLAccount.id == account_id,
                MLAccount.company_id == company_id
            ).first()
            
            if not user_account:
                return {"error": "Conta não encontrada ou sem permissão"}
            
            # Desativar conta ML
            ml_account = db.query(MLAccount).filter(MLAccount.id == account_id).first()
            if ml_account:
                ml_account.status = MLAccountStatus.INACTIVE
                db.commit()
            
            return {
                "success": True,
                "message": "Conta desconectada com sucesso"
            }
            
        except Exception as e:
            return {"error": f"Erro ao desconectar conta: {str(e)}"}
    
    def _generate_state(self) -> str:
        """Gera state seguro para OAuth"""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    
    def _exchange_code_for_token(self, code: str) -> dict:
        """Troca code por access_token"""
        try:
            url = f"{self.base_url}/oauth/token"
            data = {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri
            }
            
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            return {"error": f"Erro ao trocar code por token: {str(e)}"}
    
    def _get_ml_user_info(self, access_token: str) -> dict:
        """Obtém informações do usuário ML"""
        try:
            url = f"{self.base_url}/users/me"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            return {"error": f"Erro ao obter informações do usuário: {str(e)}"}
    
    def _create_ml_account(self, user_info: dict, company_id: int, db: Session) -> dict:
        """Cria nova conta ML"""
        try:
            ml_account = MLAccount(
                company_id=company_id,
                ml_user_id=str(user_info["id"]),  # IMPORTANTE: Sempre salvar como string
                nickname=user_info["nickname"],
                email=user_info.get("email", ""),
                first_name=user_info.get("first_name", ""),
                last_name=user_info.get("last_name", ""),
                country_id=user_info.get("country_id", ""),
                site_id=user_info.get("site_id", ""),
                permalink=user_info.get("permalink", ""),
                status=MLAccountStatus.ACTIVE,
                is_primary=False,  # Primeira conta será primária
                settings={}
            )
            
            db.add(ml_account)
            db.flush()  # Para obter o ID
            
            return {"account": ml_account}
            
        except Exception as e:
            return {"error": f"Erro ao criar conta ML: {str(e)}"}
    
    def _save_tokens(self, ml_account_id: int, token_data: dict, db: Session):
        """Salva tokens de acesso"""
        try:
            # Access Token
            access_token = Token(
                ml_account_id=ml_account_id,
                token_type="access",
                token_value=token_data["access_token"],
                expires_at=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 21600)),
                scope=token_data.get("scope", ""),
                is_active=True
            )
            db.add(access_token)
            
            # Refresh Token (se disponível)
            if "refresh_token" in token_data:
                refresh_token = Token(
                    ml_account_id=ml_account_id,
                    token_type="refresh",
                    token_value=token_data["refresh_token"],
                    expires_at=datetime.utcnow() + timedelta(days=30),  # Refresh tokens duram mais
                    scope=token_data.get("scope", ""),
                    is_active=True
                )
                db.add(refresh_token)
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            raise e
    
    def _update_tokens(self, ml_account_id: int, token_data: dict, db: Session):
        """Atualiza tokens existentes"""
        try:
            # Desativar tokens antigos
            db.query(Token).filter(
                Token.ml_account_id == ml_account_id,
                Token.is_active == True
            ).update({"is_active": False})
            
            # Salvar novos tokens
            self._save_tokens(ml_account_id, token_data, db)
            
        except Exception as e:
            db.rollback()
            raise e
    
    def _associate_user_to_account(self, user_id: int, ml_account_id: int, db: Session):
        """Associa usuário à conta ML"""
        try:
            # Verificar se associação já existe
            existing = db.query(UserMLAccount).filter(
                UserMLAccount.user_id == user_id,
                UserMLAccount.ml_account_id == ml_account_id
            ).first()
            
            if not existing:
                user_ml_account = UserMLAccount(
                    user_id=user_id,
                    ml_account_id=ml_account_id,
                    can_read=True,
                    can_write=True,
                    can_delete=False,
                    can_manage=True  # Usuário que conectou pode gerenciar
                )
                db.add(user_ml_account)
                db.commit()
            
        except Exception as e:
            db.rollback()
            raise e
