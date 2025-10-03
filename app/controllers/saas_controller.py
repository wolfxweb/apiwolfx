"""
Controller para operações SaaS Multi-tenant
"""
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.services.saas_service import SAASService
from app.middleware.tenant_middleware import get_current_tenant_user, TenantContext
from app.models.saas_models import UserRole, CompanyStatus
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class SAASController:
    """Controller para operações SaaS"""
    
    def __init__(self, db: Session):
        self.db = db
        self.saas_service = SAASService(db)
    
    # === EMPRESAS ===
    def create_company(self, name: str, slug: str, domain: str = None) -> Dict[str, Any]:
        """Cria uma nova empresa"""
        try:
            company = self.saas_service.create_company(
                name=name,
                slug=slug,
                domain=domain
            )
            return {
                "id": company.id,
                "name": company.name,
                "slug": company.slug,
                "domain": company.domain,
                "status": company.status.value,
                "trial_ends_at": company.trial_ends_at.isoformat() if company.trial_ends_at else None,
                "features": company.features
            }
        except Exception as e:
            logger.error(f"Erro ao criar empresa: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    def get_company_info(self, tenant: TenantContext) -> Dict[str, Any]:
        """Obtém informações da empresa"""
        company = tenant.company
        stats = self.saas_service.get_company_stats(company.id)
        
        return {
            "id": company.id,
            "name": company.name,
            "slug": company.slug,
            "domain": company.domain,
            "status": company.status.value,
            "features": company.features,
            "stats": stats,
            "trial_ends_at": company.trial_ends_at.isoformat() if company.trial_ends_at else None
        }
    
    # === USUÁRIOS ===
    def create_user(self, tenant: TenantContext, email: str, first_name: str,
                   last_name: str, role: str = "viewer") -> Dict[str, Any]:
        """Cria um novo usuário na empresa"""
        # Verificar se usuário tem permissão
        if tenant.user.role not in [UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN]:
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        
        try:
            user_role = UserRole(role)
            user = self.saas_service.create_user(
                company_id=tenant.company_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=user_role
            )
            return {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role.value,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat()
            }
        except Exception as e:
            logger.error(f"Erro ao criar usuário: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    def get_company_users(self, tenant: TenantContext) -> List[Dict[str, Any]]:
        """Lista usuários da empresa"""
        # Verificar permissão
        if tenant.user.role not in [UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN]:
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        
        users = self.saas_service.get_company_users(tenant.company_id)
        return [
            {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role.value,
                "is_active": user.is_active,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat()
            } for user in users
        ]
    
    def update_user_role(self, tenant: TenantContext, user_id: int, role: str):
        """Atualiza role de um usuário"""
        # Verificar se usuário tem permissão
        if tenant.user.role not in [UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN]:
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        
        try:
            user_role = UserRole(role)
            self.saas_service.update_user_role(user_id, user_role)
            return {"message": "Role atualizado com sucesso"}
        except Exception as e:
            logger.error(f"Erro ao atualizar role: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    # === CONTAS MERCADO LIVRE ===
    def create_ml_account(self, tenant: TenantContext, ml_user_id: str, nickname: str,
                         email: str, first_name: str = None, last_name: str = None) -> Dict[str, Any]:
        """Cria uma nova conta do Mercado Livre"""
        # Verificar se usuário tem permissão
        if tenant.user.role not in [UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.MANAGER]:
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        
        try:
            ml_account = self.saas_service.create_ml_account(
                company_id=tenant.company_id,
                ml_user_id=ml_user_id,
                nickname=nickname,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            return {
                "id": ml_account.id,
                "ml_user_id": ml_account.ml_user_id,
                "nickname": ml_account.nickname,
                "email": ml_account.email,
                "is_primary": ml_account.is_primary,
                "status": ml_account.status.value,
                "created_at": ml_account.created_at.isoformat()
            }
        except Exception as e:
            logger.error(f"Erro ao criar conta ML: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    def get_company_ml_accounts(self, tenant: TenantContext) -> List[Dict[str, Any]]:
        """Lista contas ML da empresa"""
        ml_accounts = self.saas_service.get_company_ml_accounts(tenant.company_id)
        return [
            {
                "id": acc.id,
                "ml_user_id": acc.ml_user_id,
                "nickname": acc.nickname,
                "email": acc.email,
                "is_primary": acc.is_primary,
                "status": acc.status.value,
                "created_at": acc.created_at.isoformat()
            } for acc in ml_accounts
        ]
    
    def get_user_ml_accounts(self, tenant: TenantContext) -> List[Dict[str, Any]]:
        """Lista contas ML acessíveis pelo usuário"""
        ml_accounts = self.saas_service.get_user_accessible_ml_accounts(tenant.user.id)
        return [
            {
                "id": acc.id,
                "ml_user_id": acc.ml_user_id,
                "nickname": acc.nickname,
                "email": acc.email,
                "is_primary": acc.is_primary,
                "status": acc.status.value,
                "permissions": {
                    "can_read": True,  # Se está na lista, pode ler
                    "can_write": False,  # Implementar lógica específica
                    "can_delete": False,
                    "can_manage": False
                }
            } for acc in ml_accounts
        ]
    
    # === PERMISSÕES ===
    def grant_ml_account_access(self, tenant: TenantContext, user_id: int, ml_account_id: int,
                               can_read: bool = True, can_write: bool = False,
                               can_delete: bool = False, can_manage: bool = False):
        """Concede acesso de usuário a uma conta ML"""
        # Verificar se usuário tem permissão
        if tenant.user.role not in [UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN]:
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        
        try:
            self.saas_service.grant_ml_account_access(
                user_id=user_id,
                ml_account_id=ml_account_id,
                can_read=can_read,
                can_write=can_write,
                can_delete=can_delete,
                can_manage=can_manage
            )
            return {"message": "Acesso concedido com sucesso"}
        except Exception as e:
            logger.error(f"Erro ao conceder acesso: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    def revoke_ml_account_access(self, tenant: TenantContext, user_id: int, ml_account_id: int):
        """Revoga acesso de usuário a uma conta ML"""
        # Verificar se usuário tem permissão
        if tenant.user.role not in [UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN]:
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        
        try:
            self.saas_service.revoke_ml_account_access(user_id, ml_account_id)
            return {"message": "Acesso revogado com sucesso"}
        except Exception as e:
            logger.error(f"Erro ao revogar acesso: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    # === DASHBOARD ===
    def get_dashboard_data(self, tenant: TenantContext) -> Dict[str, Any]:
        """Obtém dados para o dashboard"""
        return self.saas_service.get_user_dashboard_data(tenant.user.id)
    
    # === PRODUTOS ===
    def get_company_products(self, tenant: TenantContext, limit: int = 50) -> List[Dict[str, Any]]:
        """Lista produtos da empresa"""
        products = self.saas_service.get_company_products(tenant.company_id, limit)
        return [
            {
                "id": prod.id,
                "ml_item_id": prod.ml_item_id,
                "title": prod.title,
                "price": prod.price,
                "status": prod.status,
                "created_at": prod.created_at.isoformat()
            } for prod in products
        ]
    
    def get_user_products(self, tenant: TenantContext, limit: int = 50) -> List[Dict[str, Any]]:
        """Lista produtos acessíveis pelo usuário"""
        products = self.saas_service.get_user_products(tenant.user.id, limit)
        return [
            {
                "id": prod.id,
                "ml_item_id": prod.ml_item_id,
                "title": prod.title,
                "price": prod.price,
                "status": prod.status,
                "created_at": prod.created_at.isoformat()
            } for prod in products
        ]
    
    # === AUTENTICAÇÃO ===
    def login(self, email: str, password: str, ip_address: str = None, 
              user_agent: str = None) -> Dict[str, Any]:
        """Autentica usuário e cria sessão"""
        try:
            # Buscar usuário
            user = self.saas_service.get_user_by_email(email)
            if not user:
                raise HTTPException(status_code=401, detail="Credenciais inválidas")
            
            # Verificar senha (implementar hash)
            # Por enquanto, apenas verificar se usuário existe
            if not user.is_active:
                raise HTTPException(status_code=403, detail="Usuário inativo")
            
            # Criar sessão
            session = self.saas_service.create_user_session(
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Atualizar último login
            user.last_login = session.created_at
            self.db.commit()
            
            return {
                "session_token": session.session_token,
                "expires_at": session.expires_at.isoformat(),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role.value
                },
                "company": {
                    "id": user.company_id,
                    "slug": user.company.slug if user.company else None
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro no login: {e}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def logout(self, session_token: str):
        """Encerra sessão do usuário"""
        try:
            self.saas_service.invalidate_session(session_token)
            return {"message": "Logout realizado com sucesso"}
        except Exception as e:
            logger.error(f"Erro no logout: {e}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")

