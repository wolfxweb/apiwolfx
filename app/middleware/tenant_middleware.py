"""
Middleware para isolamento de tenants (empresas)
"""
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.services.saas_service import SAASService
from app.models.saas_models import User, Company
from typing import Optional
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()

class TenantContext:
    """Contexto do tenant atual"""
    def __init__(self, company: Company, user: User = None):
        self.company = company
        self.user = user
        self.company_id = company.id
        self.user_id = user.id if user else None

def get_tenant_from_domain(request: Request) -> Optional[str]:
    """Extrai tenant do domínio da requisição"""
    host = request.headers.get("host", "")
    
    # Se for localhost, usar header X-Tenant
    if "localhost" in host or "127.0.0.1" in host:
        return request.headers.get("X-Tenant")
    
    # Extrair tenant do subdomínio (ex: empresa.api.com)
    parts = host.split(".")
    if len(parts) >= 3:
        return parts[0]
    
    return None

def get_tenant_from_header(request: Request) -> Optional[str]:
    """Extrai tenant do header X-Tenant"""
    return request.headers.get("X-Tenant")

async def get_current_tenant(
    request: Request,
    db: Session = Depends(get_db)
) -> TenantContext:
    """Obtém o contexto do tenant atual"""
    saas_service = SAASService(db)
    
    # Tentar obter tenant do domínio
    tenant_slug = get_tenant_from_domain(request)
    
    # Se não encontrou, tentar do header
    if not tenant_slug:
        tenant_slug = get_tenant_from_header(request)
    
    if not tenant_slug:
        # Usar empresa padrão se não conseguir identificar o tenant
        tenant_slug = "default-company"
    
    # Buscar empresa
    company = saas_service.get_company_by_slug(tenant_slug)
    if not company:
        raise HTTPException(
            status_code=404,
            detail=f"Empresa '{tenant_slug}' não encontrada"
        )
    
    if company.status.value == "inactive":
        raise HTTPException(
            status_code=403,
            detail="Empresa inativa"
        )
    
    return TenantContext(company=company)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Obtém o usuário atual autenticado"""
    saas_service = SAASService(db)
    
    # Validar sessão
    user = saas_service.validate_session(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Sessão inválida ou expirada"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Usuário inativo"
        )
    
    return user

async def get_current_tenant_user(
    tenant: TenantContext = Depends(get_current_tenant),
    user: User = Depends(get_current_user)
) -> TenantContext:
    """Obtém tenant e usuário atual"""
    # Verificar se usuário pertence à empresa
    if user.company_id != tenant.company_id:
        raise HTTPException(
            status_code=403,
            detail="Usuário não pertence a esta empresa"
        )
    
    tenant.user = user
    return tenant

def require_permission(permission: str):
    """Decorator para verificar permissões"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Implementar verificação de permissões
            # Por enquanto, apenas um placeholder
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(required_roles: list):
    """Decorator para verificar roles"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Implementar verificação de roles
            # Por enquanto, apenas um placeholder
            return await func(*args, **kwargs)
        return wrapper
    return decorator

class TenantIsolation:
    """Classe para isolamento de dados por tenant"""
    
    @staticmethod
    def filter_by_tenant(query, tenant_id: int):
        """Filtra query por tenant"""
        # Implementar filtros específicos por modelo
        return query
    
    @staticmethod
    def ensure_tenant_access(user: User, resource_company_id: int):
        """Garante que usuário tem acesso ao recurso"""
        if user.company_id != resource_company_id:
            raise HTTPException(
                status_code=403,
                detail="Acesso negado: recurso não pertence à sua empresa"
            )

