"""
Controller para SuperAdmin - Gerenciamento do sistema SaaS
"""
from sqlalchemy.orm import Session
from sqlalchemy import text, func, desc
from passlib.context import CryptContext
from datetime import datetime
from typing import Dict, List, Optional
import secrets
import string

from app.models.saas_models import SuperAdmin, Company, User, Subscription, MLAccount

# Configuração para hash de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SuperAdminController:
    """Controller para operações de SuperAdmin"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """Autentica superadmin"""
        superadmin = self.db.query(SuperAdmin).filter(
            SuperAdmin.username == username,
            SuperAdmin.is_active == True
        ).first()
        
        if not superadmin or not pwd_context.verify(password, superadmin.password_hash):
            return None
        
        # Atualizar último login
        superadmin.last_login = datetime.utcnow()
        self.db.commit()
        
        return {
            "id": superadmin.id,
            "username": superadmin.username,
            "email": superadmin.email,
            "first_name": superadmin.first_name,
            "last_name": superadmin.last_name,
            "role": superadmin.role,
            "permissions": {
                "can_manage_companies": superadmin.can_manage_companies,
                "can_manage_plans": superadmin.can_manage_plans,
                "can_manage_users": superadmin.can_manage_users,
                "can_view_analytics": superadmin.can_view_analytics,
                "can_access_system_logs": superadmin.can_access_system_logs
            }
        }
    
    def get_system_overview(self) -> Dict:
        """Obtém visão geral do sistema"""
        # Estatísticas gerais
        stats_query = text("""
            SELECT 
                (SELECT COUNT(*) FROM companies WHERE status = 'ACTIVE') as active_companies,
                (SELECT COUNT(*) FROM companies WHERE status = 'TRIAL') as trial_companies,
                (SELECT COUNT(*) FROM companies WHERE status = 'INACTIVE') as inactive_companies,
                (SELECT COUNT(*) FROM users WHERE is_active = true) as active_users,
                (SELECT COUNT(*) FROM ml_accounts WHERE status = 'ACTIVE') as active_ml_accounts,
                (SELECT COUNT(*) FROM subscriptions WHERE status = 'active') as active_subscriptions
        """)
        
        stats = self.db.execute(stats_query).fetchone()
        
        # Receita mensal (simulado)
        revenue_query = text("""
            SELECT 
                COUNT(*) as total_subscriptions,
                SUM(CASE WHEN price ~ '^[0-9]+\.?[0-9]*$' THEN CAST(price AS DECIMAL) ELSE 0 END) as total_revenue
            FROM subscriptions 
            WHERE status = 'active' AND created_at >= DATE_TRUNC('month', CURRENT_DATE)
        """)
        
        revenue = self.db.execute(revenue_query).fetchone()
        
        return {
            "companies": {
                "active": stats.active_companies,
                "trial": stats.trial_companies,
                "inactive": stats.inactive_companies,
                "total": stats.active_companies + stats.trial_companies + stats.inactive_companies
            },
            "users": {
                "active": stats.active_users,
                "total": self.db.query(User).count()
            },
            "ml_accounts": {
                "active": stats.active_ml_accounts,
                "total": self.db.query(MLAccount).count()
            },
            "subscriptions": {
                "active": stats.active_subscriptions,
                "total": self.db.query(Subscription).count()
            },
            "revenue": {
                "monthly_subscriptions": revenue.total_subscriptions,
                "monthly_revenue": float(revenue.total_revenue) if revenue.total_revenue else 0
            }
        }
    
    def get_companies_list(self, page: int = 1, per_page: int = 20, status: Optional[str] = None) -> Dict:
        """Lista empresas com paginação"""
        query = self.db.query(Company)
        
        if status:
            query = query.filter(Company.status == status)
        
        # Contar total
        total = query.count()
        
        # Paginar
        offset = (page - 1) * per_page
        companies = query.order_by(desc(Company.created_at)).offset(offset).limit(per_page).all()
        
        # Adicionar estatísticas para cada empresa
        companies_data = []
        for company in companies:
            users_count = self.db.query(User).filter(
                User.company_id == company.id,
                User.is_active == True
            ).count()
            
            ml_accounts_count = self.db.query(MLAccount).filter(
                MLAccount.company_id == company.id,
                MLAccount.status == 'ACTIVE'
            ).count()
            
            active_subscription = self.db.query(Subscription).filter(
                Subscription.company_id == company.id,
                Subscription.status == 'active'
            ).first()
            
            companies_data.append({
                "id": company.id,
                "name": company.name,
                "slug": company.slug,
                "status": company.status.value,
                "created_at": company.created_at,
                "trial_ends_at": company.trial_ends_at,
                "max_users": company.max_users,
                "max_ml_accounts": company.max_ml_accounts,
                "users_count": users_count,
                "ml_accounts_count": ml_accounts_count,
                "has_active_subscription": bool(active_subscription),
                "subscription_plan": active_subscription.plan_name if active_subscription else None
            })
        
        return {
            "companies": companies_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        }
    
    def get_company_details(self, company_id: int) -> Optional[Dict]:
        """Obtém detalhes completos de uma empresa"""
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return None
        
        # Usuários da empresa
        users = self.db.query(User).filter(User.company_id == company_id).all()
        users_data = []
        for user in users:
            users_data.append({
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role.value,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "last_login": user.last_login
            })
        
        # Contas ML da empresa
        ml_accounts = self.db.query(MLAccount).filter(MLAccount.company_id == company_id).all()
        ml_accounts_data = []
        for account in ml_accounts:
            ml_accounts_data.append({
                "id": account.id,
                "ml_user_id": account.ml_user_id,
                "nickname": account.nickname,
                "status": account.status.value,
                "is_primary": account.is_primary,
                "created_at": account.created_at,
                "last_sync": account.last_sync
            })
        
        # Assinaturas da empresa
        subscriptions = self.db.query(Subscription).filter(Subscription.company_id == company_id).all()
        subscriptions_data = []
        for sub in subscriptions:
            subscriptions_data.append({
                "id": sub.id,
                "plan_name": sub.plan_name,
                "price": sub.price,
                "currency": sub.currency,
                "status": sub.status,
                "is_trial": sub.is_trial,
                "starts_at": sub.starts_at,
                "ends_at": sub.ends_at,
                "trial_ends_at": sub.trial_ends_at,
                "created_at": sub.created_at
            })
        
        return {
            "company": {
                "id": company.id,
                "name": company.name,
                "slug": company.slug,
                "description": company.description,
                "domain": company.domain,
                "logo_url": company.logo_url,
                "status": company.status.value,
                "max_users": company.max_users,
                "max_ml_accounts": company.max_ml_accounts,
                "features": company.features,
                "created_at": company.created_at,
                "updated_at": company.updated_at,
                "trial_ends_at": company.trial_ends_at
            },
            "users": users_data,
            "ml_accounts": ml_accounts_data,
            "subscriptions": subscriptions_data
        }
    
    def update_company_status(self, company_id: int, status: str) -> bool:
        """Atualiza status da empresa"""
        try:
            company = self.db.query(Company).filter(Company.id == company_id).first()
            if not company:
                return False
            
            company.status = status
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False
    
    def create_plan(self, plan_data: Dict) -> bool:
        """Cria um novo plano"""
        try:
            subscription = Subscription(
                company_id=None,  # Plano template
                plan_name=plan_data["plan_name"],
                plan_features=plan_data.get("plan_features", {}),
                price=plan_data.get("price", "0"),
                currency=plan_data.get("currency", "BRL"),
                status="template",
                is_trial=False
            )
            
            self.db.add(subscription)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False
    
    def get_plans_list(self) -> List[Dict]:
        """Lista todos os planos disponíveis"""
        plans = self.db.query(Subscription).filter(
            Subscription.status == "template"
        ).all()
        
        plans_data = []
        for plan in plans:
            # Contar quantas empresas estão usando este plano
            active_subscriptions = self.db.query(Subscription).filter(
                Subscription.plan_name == plan.plan_name,
                Subscription.status == "active"
            ).count()
            
            plans_data.append({
                "id": plan.id,
                "plan_name": plan.plan_name,
                "plan_features": plan.plan_features,
                "price": plan.price,
                "currency": plan.currency,
                "active_subscriptions": active_subscriptions,
                "created_at": plan.created_at
            })
        
        return plans_data
    
    def assign_plan_to_company(self, company_id: int, plan_name: str, duration_months: int = 1) -> bool:
        """Atribui um plano a uma empresa"""
        try:
            # Desativar assinaturas atuais
            current_subscriptions = self.db.query(Subscription).filter(
                Subscription.company_id == company_id,
                Subscription.status == "active"
            ).all()
            
            for sub in current_subscriptions:
                sub.status = "inactive"
            
            # Criar nova assinatura
            from datetime import datetime, timedelta
            
            new_subscription = Subscription(
                company_id=company_id,
                plan_name=plan_name,
                status="active",
                is_trial=False,
                starts_at=datetime.utcnow(),
                ends_at=datetime.utcnow() + timedelta(days=30 * duration_months)
            )
            
            self.db.add(new_subscription)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False
    
    def create_superadmin(self, superadmin_data: Dict) -> bool:
        """Cria um novo superadmin"""
        try:
            # Verificar se já existe
            existing = self.db.query(SuperAdmin).filter(
                SuperAdmin.email == superadmin_data["email"]
            ).first()
            
            if existing:
                return False
            
            # Hash da senha
            password_hash = pwd_context.hash(superadmin_data["password"])
            
            superadmin = SuperAdmin(
                email=superadmin_data["email"],
                username=superadmin_data["username"],
                password_hash=password_hash,
                first_name=superadmin_data["first_name"],
                last_name=superadmin_data["last_name"],
                role=superadmin_data.get("role", "company_manager"),
                can_manage_companies=superadmin_data.get("can_manage_companies", True),
                can_manage_plans=superadmin_data.get("can_manage_plans", True),
                can_manage_users=superadmin_data.get("can_manage_users", True),
                can_view_analytics=superadmin_data.get("can_view_analytics", True),
                can_access_system_logs=superadmin_data.get("can_access_system_logs", False)
            )
            
            self.db.add(superadmin)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False
