"""
Rotas para arquitetura SaaS Multi-tenant
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.controllers.saas_controller import SAASController
from app.middleware.tenant_middleware import get_current_tenant_user, TenantContext
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# Router para rotas SaaS
saas_router = APIRouter(prefix="/saas", tags=["SaaS"])

# === MODELS PYDANTIC ===
class CompanyCreate(BaseModel):
    name: str
    slug: str
    domain: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role: str = "viewer"

class UserRoleUpdate(BaseModel):
    role: str

class MLAccountCreate(BaseModel):
    ml_user_id: str
    nickname: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class MLAccountAccess(BaseModel):
    user_id: int
    ml_account_id: int
    can_read: bool = True
    can_write: bool = False
    can_delete: bool = False
    can_manage: bool = False

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# === ROTAS PÚBLICAS ===
@saas_router.post("/companies", response_model=dict)
async def create_company(
    company_data: CompanyCreate,
    db: Session = Depends(get_db)
):
    """Cria uma nova empresa (tenant)"""
    controller = SAASController(db)
    return controller.create_company(
        name=company_data.name,
        slug=company_data.slug,
        domain=company_data.domain
    )

@saas_router.post("/auth/login", response_model=dict)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Autentica usuário e cria sessão"""
    controller = SAASController(db)
    return controller.login(
        email=login_data.email,
        password=login_data.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

# === ROTAS PROTEGIDAS ===
@saas_router.get("/company", response_model=dict)
async def get_company_info(
    tenant: TenantContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Obtém informações da empresa atual"""
    controller = SAASController(db)
    return controller.get_company_info(tenant)

@saas_router.get("/dashboard", response_model=dict)
async def get_dashboard(
    tenant: TenantContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Obtém dados do dashboard do usuário"""
    controller = SAASController(db)
    return controller.get_dashboard_data(tenant)

# === USUÁRIOS ===
@saas_router.post("/users", response_model=dict)
async def create_user(
    user_data: UserCreate,
    tenant: TenantContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Cria um novo usuário na empresa"""
    controller = SAASController(db)
    return controller.create_user(
        tenant=tenant,
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role
    )

@saas_router.get("/users", response_model=List[dict])
async def get_company_users(
    tenant: TenantContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Lista usuários da empresa"""
    controller = SAASController(db)
    return controller.get_company_users(tenant)

@saas_router.put("/users/{user_id}/role", response_model=dict)
async def update_user_role(
    user_id: int,
    role_data: UserRoleUpdate,
    tenant: TenantContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Atualiza role de um usuário"""
    controller = SAASController(db)
    return controller.update_user_role(tenant, user_id, role_data.role)

# === CONTAS MERCADO LIVRE ===
@saas_router.post("/ml-accounts", response_model=dict)
async def create_ml_account(
    ml_account_data: MLAccountCreate,
    tenant: TenantContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Cria uma nova conta do Mercado Livre"""
    controller = SAASController(db)
    return controller.create_ml_account(
        tenant=tenant,
        ml_user_id=ml_account_data.ml_user_id,
        nickname=ml_account_data.nickname,
        email=ml_account_data.email,
        first_name=ml_account_data.first_name,
        last_name=ml_account_data.last_name
    )

@saas_router.get("/ml-accounts", response_model=List[dict])
async def get_company_ml_accounts(
    tenant: TenantContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Lista contas ML da empresa"""
    controller = SAASController(db)
    return controller.get_company_ml_accounts(tenant)

@saas_router.get("/my-ml-accounts", response_model=List[dict])
async def get_user_ml_accounts(
    tenant: TenantContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Lista contas ML acessíveis pelo usuário"""
    controller = SAASController(db)
    return controller.get_user_ml_accounts(tenant)

# === PERMISSÕES ===
@saas_router.post("/permissions/grant", response_model=dict)
async def grant_ml_account_access(
    access_data: MLAccountAccess,
    tenant: TenantContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Concede acesso de usuário a uma conta ML"""
    controller = SAASController(db)
    return controller.grant_ml_account_access(
        tenant=tenant,
        user_id=access_data.user_id,
        ml_account_id=access_data.ml_account_id,
        can_read=access_data.can_read,
        can_write=access_data.can_write,
        can_delete=access_data.can_delete,
        can_manage=access_data.can_manage
    )

@saas_router.delete("/permissions/revoke", response_model=dict)
async def revoke_ml_account_access(
    user_id: int,
    ml_account_id: int,
    tenant: TenantContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Revoga acesso de usuário a uma conta ML"""
    controller = SAASController(db)
    return controller.revoke_ml_account_access(tenant, user_id, ml_account_id)

# === PRODUTOS ===
@saas_router.get("/products", response_model=List[dict])
async def get_company_products(
    limit: int = 50,
    tenant: TenantContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Lista produtos da empresa"""
    controller = SAASController(db)
    return controller.get_company_products(tenant, limit)

@saas_router.get("/my-products", response_model=List[dict])
async def get_user_products(
    limit: int = 50,
    tenant: TenantContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db)
):
    """Lista produtos acessíveis pelo usuário"""
    controller = SAASController(db)
    return controller.get_user_products(tenant, limit)

# === AUTENTICAÇÃO ===
@saas_router.post("/auth/logout", response_model=dict)
async def logout(
    session_token: str,
    db: Session = Depends(get_db)
):
    """Encerra sessão do usuário"""
    controller = SAASController(db)
    return controller.logout(session_token)

# === ROTAS DE SAÚDE ===
@saas_router.get("/health", response_model=dict)
async def saas_health():
    """Verifica saúde do sistema SaaS"""
    return {
        "status": "healthy",
        "service": "SaaS Multi-tenant",
        "version": "1.0.0"
    }

