"""
Serviço para gerenciar arquitetura SaaS Multi-tenant
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.saas_models import (
    Company, User, MLAccount, UserMLAccount, Token, Product, 
    UserSession, Subscription, CompanyStatus, UserRole, MLAccountStatus
)
from app.models.database_models import ApiLog
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
import secrets
import hashlib

logger = logging.getLogger(__name__)

class SAASService:
    """Serviço para operações SaaS Multi-tenant"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # === EMPRESAS (TENANTS) ===
    def create_company(self, name: str, slug: str, domain: str = None, 
                      max_ml_accounts: int = 5, max_users: int = 10) -> Company:
        """Cria uma nova empresa (tenant)"""
        try:
            company = Company(
                name=name,
                slug=slug,
                domain=domain,
                max_ml_accounts=max_ml_accounts,
                max_users=max_users,
                status=CompanyStatus.TRIAL,
                trial_ends_at=datetime.utcnow() + timedelta(days=14),
                features={
                    "analytics": True,
                    "reports": True,
                    "api_access": True,
                    "webhooks": False,
                    "advanced_analytics": False
                }
            )
            self.db.add(company)
            self.db.commit()
            self.db.refresh(company)
            return company
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Erro ao criar empresa: {e}")
            raise
    
    def get_company_by_slug(self, slug: str) -> Optional[Company]:
        """Busca empresa por slug"""
        return self.db.query(Company).filter(Company.slug == slug).first()
    
    def get_company_by_domain(self, domain: str) -> Optional[Company]:
        """Busca empresa por domínio"""
        return self.db.query(Company).filter(Company.domain == domain).first()
    
    def update_company_features(self, company_id: int, features: Dict[str, Any]):
        """Atualiza features da empresa"""
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if company:
            company.features = features
            self.db.commit()
    
    # === USUÁRIOS ===
    def create_user(self, company_id: int, email: str, first_name: str, 
                   last_name: str, role: UserRole = UserRole.VIEWER) -> User:
        """Cria um novo usuário"""
        try:
            user = User(
                company_id=company_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=role,
                is_active=True
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Erro ao criar usuário: {e}")
            raise
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Busca usuário por email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_company_users(self, company_id: int) -> List[User]:
        """Busca usuários de uma empresa"""
        return self.db.query(User).filter(
            User.company_id == company_id,
            User.is_active == True
        ).all()
    
    def update_user_role(self, user_id: int, role: UserRole):
        """Atualiza role do usuário"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.role = role
            self.db.commit()
    
    # === CONTAS MERCADO LIVRE ===
    def create_ml_account(self, company_id: int, ml_user_id: str, nickname: str,
                         email: str, first_name: str = None, last_name: str = None,
                         country_id: str = None, site_id: str = None) -> MLAccount:
        """Cria uma nova conta do Mercado Livre"""
        try:
            # Verificar se é a primeira conta da empresa
            existing_accounts = self.db.query(MLAccount).filter(
                MLAccount.company_id == company_id
            ).count()
            
            ml_account = MLAccount(
                company_id=company_id,
                ml_user_id=ml_user_id,
                nickname=nickname,
                email=email,
                first_name=first_name,
                last_name=last_name,
                country_id=country_id,
                site_id=site_id,
                is_primary=(existing_accounts == 0),  # Primeira conta é primária
                status=MLAccountStatus.ACTIVE
            )
            self.db.add(ml_account)
            self.db.commit()
            self.db.refresh(ml_account)
            return ml_account
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Erro ao criar conta ML: {e}")
            raise
    
    def get_company_ml_accounts(self, company_id: int) -> List[MLAccount]:
        """Busca contas ML de uma empresa"""
        return self.db.query(MLAccount).filter(
            MLAccount.company_id == company_id,
            MLAccount.status == MLAccountStatus.ACTIVE
        ).all()
    
    def get_user_accessible_ml_accounts(self, user_id: int) -> List[MLAccount]:
        """Busca contas ML acessíveis por um usuário"""
        return self.db.query(MLAccount).join(UserMLAccount).filter(
            UserMLAccount.user_id == user_id,
            MLAccount.status == MLAccountStatus.ACTIVE
        ).all()
    
    # === PERMISSÕES USUÁRIO-CONTA ML ===
    def grant_ml_account_access(self, user_id: int, ml_account_id: int,
                               can_read: bool = True, can_write: bool = False,
                               can_delete: bool = False, can_manage: bool = False):
        """Concede acesso de usuário a uma conta ML"""
        try:
            user_ml_account = UserMLAccount(
                user_id=user_id,
                ml_account_id=ml_account_id,
                can_read=can_read,
                can_write=can_write,
                can_delete=can_delete,
                can_manage=can_manage
            )
            self.db.add(user_ml_account)
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Erro ao conceder acesso: {e}")
            raise
    
    def revoke_ml_account_access(self, user_id: int, ml_account_id: int):
        """Revoga acesso de usuário a uma conta ML"""
        self.db.query(UserMLAccount).filter(
            UserMLAccount.user_id == user_id,
            UserMLAccount.ml_account_id == ml_account_id
        ).delete()
        self.db.commit()
    
    def check_user_ml_account_permission(self, user_id: int, ml_account_id: int, 
                                        permission: str) -> bool:
        """Verifica se usuário tem permissão específica em uma conta ML"""
        user_ml_account = self.db.query(UserMLAccount).filter(
            UserMLAccount.user_id == user_id,
            UserMLAccount.ml_account_id == ml_account_id
        ).first()
        
        if not user_ml_account:
            return False
        
        # Super admin tem todas as permissões
        user = self.db.query(User).filter(User.id == user_id).first()
        if user and user.role == UserRole.SUPER_ADMIN:
            return True
        
        # Verificar permissão específica
        if permission == "read":
            return user_ml_account.can_read
        elif permission == "write":
            return user_ml_account.can_write
        elif permission == "delete":
            return user_ml_account.can_delete
        elif permission == "manage":
            return user_ml_account.can_manage
        
        return False
    
    # === SESSÕES ===
    def create_user_session(self, user_id: int, ip_address: str = None, 
                           user_agent: str = None) -> UserSession:
        """Cria uma nova sessão de usuário"""
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        session = UserSession(
            user_id=user_id,
            session_token=session_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session
    
    def validate_session(self, session_token: str) -> Optional[User]:
        """Valida sessão e retorna usuário"""
        session = self.db.query(UserSession).filter(
            UserSession.session_token == session_token,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.utcnow()
        ).first()
        
        if session:
            session.last_activity = datetime.utcnow()
            self.db.commit()
            return session.user
        
        return None
    
    def invalidate_session(self, session_token: str):
        """Invalida uma sessão"""
        self.db.query(UserSession).filter(
            UserSession.session_token == session_token
        ).update({"is_active": False})
        self.db.commit()
    
    # === TOKENS ===
    def save_token(self, user_id: int, ml_account_id: int, access_token: str,
                   refresh_token: str = None, expires_in: int = 21600) -> Token:
        """Salva token de acesso"""
        try:
            # Desativar tokens anteriores
            self.db.query(Token).filter(
                Token.user_id == user_id,
                Token.ml_account_id == ml_account_id,
                Token.is_active == True
            ).update({"is_active": False})
            
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            token = Token(
                user_id=user_id,
                ml_account_id=ml_account_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in,
                expires_at=expires_at,
                is_active=True
            )
            self.db.add(token)
            self.db.commit()
            self.db.refresh(token)
            return token
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao salvar token: {e}")
            raise
    
    def get_active_token(self, user_id: int, ml_account_id: int) -> Optional[Token]:
        """Busca token ativo"""
        return self.db.query(Token).filter(
            Token.user_id == user_id,
            Token.ml_account_id == ml_account_id,
            Token.is_active == True,
            Token.expires_at > datetime.utcnow()
        ).first()
    
    # === PRODUTOS ===
    def save_product(self, company_id: int, ml_account_id: int, ml_item_id: str,
                    title: str, price: str = None, **kwargs) -> Product:
        """Salva produto"""
        try:
            product = self.db.query(Product).filter(
                Product.ml_item_id == ml_item_id
            ).first()
            
            if product:
                # Atualizar dados
                product.title = title
                product.price = price
                product.updated_at = datetime.utcnow()
                for key, value in kwargs.items():
                    if hasattr(product, key):
                        setattr(product, key, value)
            else:
                # Criar novo produto
                product = Product(
                    company_id=company_id,
                    ml_account_id=ml_account_id,
                    ml_item_id=ml_item_id,
                    title=title,
                    price=price,
                    **kwargs
                )
                self.db.add(product)
            
            self.db.commit()
            self.db.refresh(product)
            return product
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao salvar produto: {e}")
            raise
    
    def get_company_products(self, company_id: int, limit: int = 50) -> List[Product]:
        """Busca produtos de uma empresa"""
        return self.db.query(Product).filter(
            Product.company_id == company_id
        ).limit(limit).all()
    
    def get_user_products(self, user_id: int, limit: int = 50) -> List[Product]:
        """Busca produtos acessíveis por um usuário"""
        return self.db.query(Product).join(MLAccount).join(UserMLAccount).filter(
            UserMLAccount.user_id == user_id,
            UserMLAccount.can_read == True
        ).limit(limit).all()
    
    # === LOGS ===
    def log_api_call(self, company_id: int = None, user_id: int = None,
                    ml_account_id: int = None, endpoint: str = None,
                    method: str = None, status_code: int = None,
                    response_time_ms: int = None, **kwargs):
        """Registra log da API"""
        try:
            log = ApiLog(
                company_id=company_id,
                user_id=user_id,
                ml_account_id=ml_account_id,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time_ms=response_time_ms,
                **kwargs
            )
            self.db.add(log)
            self.db.commit()
        except Exception as e:
            logger.error(f"Erro ao registrar log: {e}")
    
    # === ESTATÍSTICAS ===
    def get_company_stats(self, company_id: int) -> Dict[str, Any]:
        """Busca estatísticas de uma empresa"""
        users_count = self.db.query(User).filter(
            User.company_id == company_id,
            User.is_active == True
        ).count()
        
        ml_accounts_count = self.db.query(MLAccount).filter(
            MLAccount.company_id == company_id,
            MLAccount.status == MLAccountStatus.ACTIVE
        ).count()
        
        products_count = self.db.query(Product).filter(
            Product.company_id == company_id
        ).count()
        
        return {
            "users_count": users_count,
            "ml_accounts_count": ml_accounts_count,
            "products_count": products_count
        }
    
    def get_user_dashboard_data(self, user_id: int) -> Dict[str, Any]:
        """Busca dados para dashboard do usuário"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {}
        
        # Contas ML acessíveis
        ml_accounts = self.get_user_accessible_ml_accounts(user_id)
        
        # Produtos acessíveis
        products = self.get_user_products(user_id, limit=10)
        
        # Estatísticas da empresa
        company_stats = self.get_company_stats(user.company_id)
        
        return {
            "user": {
                "id": user.id,
                "name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "role": user.role.value
            },
            "company": {
                "id": user.company_id,
                "stats": company_stats
            },
            "ml_accounts": [
                {
                    "id": acc.id,
                    "nickname": acc.nickname,
                    "email": acc.email,
                    "is_primary": acc.is_primary
                } for acc in ml_accounts
            ],
            "recent_products": [
                {
                    "id": prod.id,
                    "title": prod.title,
                    "price": prod.price,
                    "status": prod.status
                } for prod in products
            ]
        }

