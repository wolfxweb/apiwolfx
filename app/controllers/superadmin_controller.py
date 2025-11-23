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
                "status": company.status.upper() if isinstance(company.status, str) else company.status.value.upper(),
                "created_at": company.created_at,
                "trial_ends_at": company.trial_ends_at,
                "users_count": users_count,
                "ml_accounts_count": ml_accounts_count,
                "has_active_subscription": bool(active_subscription),
                "subscription_plan": active_subscription.plan_name if active_subscription else None,
                # Novos campos de plano
                "plan_expires_at": company.plan_expires_at
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
                "status": company.status,
                "features": company.features,
                "created_at": company.created_at,
                "updated_at": company.updated_at,
                "trial_ends_at": company.trial_ends_at,
                "plan_expires_at": company.plan_expires_at
            },
            "users": users_data,
            "ml_accounts": ml_accounts_data,
            "subscriptions": subscriptions_data
        }
    
    def update_company_status(self, company_id: int, status: str) -> bool:
        """Atualiza status da empresa"""
        try:
            from app.models.saas_models import CompanyStatus
            
            company = self.db.query(Company).filter(Company.id == company_id).first()
            if not company:
                return False
            
            # Converter string para Enum se necessário
            if isinstance(status, str):
                status_upper = status.upper()
                if status_upper == "ACTIVE":
                    company.status = CompanyStatus.ACTIVE
                elif status_upper == "INACTIVE":
                    company.status = CompanyStatus.INACTIVE
                elif status_upper == "SUSPENDED":
                    company.status = CompanyStatus.SUSPENDED
                elif status_upper == "TRIAL":
                    company.status = CompanyStatus.TRIAL
                else:
                    # Tentar usar o valor diretamente
                    try:
                        company.status = CompanyStatus[status_upper]
                    except KeyError:
                        print(f"⚠️ Status inválido: {status}")
                        return False
            elif isinstance(status, CompanyStatus):
                company.status = status
            else:
                print(f"⚠️ Tipo de status inválido: {type(status)}")
                return False
            
            self.db.commit()
            print(f"✅ Status da empresa {company_id} atualizado para: {company.status}")
            return True
        except Exception as e:
            self.db.rollback()
            print(f"❌ Erro ao atualizar status: {e}")
            import traceback
            traceback.print_exc()
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
    
    def create_company(self, company_data: Dict) -> Dict:
        """Cria uma nova empresa"""
        try:
            # Verificar se slug já existe
            existing = self.db.query(Company).filter(Company.slug == company_data["slug"]).first()
            if existing:
                raise ValueError("Slug já existe")
            
            # Verificar se domínio já existe (se fornecido)
            if company_data.get("domain"):
                existing_domain = self.db.query(Company).filter(Company.domain == company_data["domain"]).first()
                if existing_domain:
                    raise ValueError("Domínio já existe")
            
            company = Company(
                name=company_data["name"],
                slug=company_data["slug"],
                domain=company_data.get("domain") if company_data.get("domain") else None,
                description=company_data.get("description"),
                status=company_data["status"],
                # Campos de plano
                plan_expires_at=company_data.get("plan_expires_at")
            )
            
            self.db.add(company)
            self.db.flush()  # Para obter o ID da empresa
            
            # Criar assinatura se plan_id foi fornecido
            if company_data.get("plan_id"):
                plan_template = self.db.query(Subscription).filter(
                    Subscription.id == company_data["plan_id"],
                    Subscription.status == "template"
                ).first()
                
                if plan_template:
                    trial_days = plan_template.trial_days if hasattr(plan_template, 'trial_days') else 0
                    is_trial = trial_days > 0
                    
                    subscription = Subscription(
                        company_id=company.id,
                        plan_name=plan_template.plan_name,
                        description=plan_template.description,
                        price=plan_template.promotional_price if plan_template.promotional_price else plan_template.price,
                        currency=plan_template.currency,
                        billing_cycle=plan_template.billing_cycle,
                        max_users=plan_template.max_users,
                        max_ml_accounts=plan_template.max_ml_accounts,
                        storage_gb=plan_template.storage_gb if hasattr(plan_template, 'storage_gb') else 5,
                        ai_analysis_monthly=plan_template.ai_analysis_monthly if hasattr(plan_template, 'ai_analysis_monthly') else 10,
                        catalog_monitoring_slots=plan_template.catalog_monitoring_slots if hasattr(plan_template, 'catalog_monitoring_slots') else 5,
                        product_mining_slots=plan_template.product_mining_slots if hasattr(plan_template, 'product_mining_slots') else 10,
                        product_monitoring_slots=plan_template.product_monitoring_slots if hasattr(plan_template, 'product_monitoring_slots') else 20,
                        status="active",
                        is_trial=is_trial,
                        starts_at=datetime.utcnow(),
                        ends_at=datetime.utcnow() + timedelta(days=30) if not is_trial else None,
                        trial_ends_at=datetime.utcnow() + timedelta(days=trial_days) if is_trial else None
                    )
                    self.db.add(subscription)
            
            self.db.commit()
            
            return {
                "id": company.id,
                "message": "Empresa criada com sucesso"
            }
        except Exception as e:
            self.db.rollback()
            raise e
    
    def update_company(self, company_id: int, company_data: Dict) -> Dict:
        """Atualiza uma empresa existente"""
        try:
            company = self.db.query(Company).filter(Company.id == company_id).first()
            if not company:
                raise ValueError("Empresa não encontrada")
            
            # Verificar se slug já existe (em outra empresa)
            if company_data.get("slug") and company_data["slug"] != company.slug:
                existing = self.db.query(Company).filter(
                    Company.slug == company_data["slug"],
                    Company.id != company_id
                ).first()
                if existing:
                    raise ValueError("Slug já existe")
            
            # Verificar se domínio já existe (em outra empresa)
            if company_data.get("domain") and company_data["domain"] != company.domain:
                existing_domain = self.db.query(Company).filter(
                    Company.domain == company_data["domain"],
                    Company.id != company_id
                ).first()
                if existing_domain:
                    raise ValueError("Domínio já existe")
            
            # Atualizar campos
            company.name = company_data["name"]
            company.slug = company_data["slug"]
            company.domain = company_data.get("domain") if company_data.get("domain") else None
            company.description = company_data.get("description")
            
            # Converter status string para Enum se necessário
            if "status" in company_data:
                status_value = company_data["status"]
                if isinstance(status_value, str):
                    # Converter string para CompanyStatus enum
                    from app.models.saas_models import CompanyStatus
                    try:
                        # Tentar converter para enum (case insensitive)
                        status_upper = status_value.upper()
                        if status_upper == "ACTIVE":
                            company.status = CompanyStatus.ACTIVE
                        elif status_upper == "INACTIVE":
                            company.status = CompanyStatus.INACTIVE
                        elif status_upper == "SUSPENDED":
                            company.status = CompanyStatus.SUSPENDED
                        elif status_upper == "TRIAL":
                            company.status = CompanyStatus.TRIAL
                        else:
                            # Tentar usar o valor diretamente
                            company.status = CompanyStatus[status_upper]
                    except (KeyError, ValueError):
                        # Se não conseguir converter, manter o valor atual
                        print(f"⚠️ Status inválido: {status_value}, mantendo status atual")
                elif isinstance(status_value, CompanyStatus):
                    company.status = status_value
                else:
                    print(f"⚠️ Tipo de status inválido: {type(status_value)}, mantendo status atual")
            
            # Atualizar campos de plano
            if "plan_expires_at" in company_data:
                plan_expires_at_value = company_data["plan_expires_at"]
                if plan_expires_at_value:
                    # Converter string para datetime se necessário
                    if isinstance(plan_expires_at_value, str):
                        try:
                            # Tentar parsear formato ISO (YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS)
                            if 'T' in plan_expires_at_value:
                                # Formato com hora
                                dt_value = datetime.fromisoformat(plan_expires_at_value.replace('Z', '+00:00'))
                                # Converter para UTC se tiver timezone
                                if dt_value.tzinfo:
                                    dt_value = dt_value.replace(tzinfo=None)
                                company.plan_expires_at = dt_value
                            else:
                                # Apenas data, adicionar hora 23:59:59 em UTC
                                dt_value = datetime.strptime(plan_expires_at_value, '%Y-%m-%d')
                                company.plan_expires_at = dt_value.replace(hour=23, minute=59, second=59)
                        except ValueError:
                            # Tentar outros formatos
                            try:
                                dt_value = datetime.strptime(plan_expires_at_value, '%Y-%m-%d %H:%M:%S')
                                company.plan_expires_at = dt_value
                            except ValueError:
                                raise ValueError(f"Formato de data inválido: {plan_expires_at_value}")
                    elif isinstance(plan_expires_at_value, datetime):
                        # Se já é datetime, usar diretamente (remover timezone se houver)
                        dt_value = plan_expires_at_value
                        if dt_value.tzinfo:
                            dt_value = dt_value.replace(tzinfo=None)
                        company.plan_expires_at = dt_value
                    else:
                        company.plan_expires_at = None
                else:
                    company.plan_expires_at = None
            
            # Buscar subscription ativa existente (se houver)
            active_subscription = self.db.query(Subscription).filter(
                Subscription.company_id == company_id,
                Subscription.status == 'active'
            ).first()
            
            # Atualizar ou criar subscription se plan_id foi fornecido
            if "plan_id" in company_data and company_data.get("plan_id"):
                plan_template_id = company_data["plan_id"]
                
                # Buscar template do plano
                plan_template = self.db.query(Subscription).filter(
                    Subscription.id == plan_template_id,
                    Subscription.status == "template"
                ).first()
                
                if plan_template:
                    if active_subscription:
                        # Atualizar subscription existente com dados do template
                        active_subscription.plan_name = plan_template.plan_name
                        if hasattr(plan_template, 'price'):
                            active_subscription.price = plan_template.price
                        if hasattr(plan_template, 'currency'):
                            active_subscription.currency = plan_template.currency
                        if hasattr(plan_template, 'plan_features'):
                            active_subscription.plan_features = plan_template.plan_features
                        if hasattr(plan_template, 'description'):
                            active_subscription.description = plan_template.description
                        if hasattr(plan_template, 'billing_cycle'):
                            active_subscription.billing_cycle = plan_template.billing_cycle
                        if hasattr(plan_template, 'max_users'):
                            active_subscription.max_users = plan_template.max_users
                        if hasattr(plan_template, 'max_ml_accounts'):
                            active_subscription.max_ml_accounts = plan_template.max_ml_accounts
                        if hasattr(plan_template, 'ai_analysis_monthly'):
                            active_subscription.ai_analysis_monthly = plan_template.ai_analysis_monthly
                        
                        print(f"✅ Subscription {active_subscription.id} atualizada com plano {plan_template.plan_name}")
                    else:
                        # Criar nova subscription
                        # Usar valores do formulário se fornecidos, senão usar padrões
                        subscription_status = company_data.get("subscription_status", "active")
                        subscription_is_trial = company_data.get("subscription_is_trial", False)
                        
                        active_subscription = Subscription(
                            company_id=company_id,
                            plan_name=plan_template.plan_name,
                            status=subscription_status,
                            is_trial=bool(subscription_is_trial),
                            starts_at=datetime.utcnow(),
                            ends_at=company.plan_expires_at if company.plan_expires_at else (datetime.utcnow() + timedelta(days=30))
                        )
                        
                        # Copiar campos do template se existirem
                        if hasattr(plan_template, 'price'):
                            active_subscription.price = plan_template.price
                        if hasattr(plan_template, 'currency'):
                            active_subscription.currency = plan_template.currency or "BRL"
                        if hasattr(plan_template, 'plan_features'):
                            active_subscription.plan_features = plan_template.plan_features
                        if hasattr(plan_template, 'description'):
                            active_subscription.description = plan_template.description
                        if hasattr(plan_template, 'billing_cycle'):
                            active_subscription.billing_cycle = plan_template.billing_cycle
                        if hasattr(plan_template, 'max_users'):
                            active_subscription.max_users = plan_template.max_users
                        if hasattr(plan_template, 'max_ml_accounts'):
                            active_subscription.max_ml_accounts = plan_template.max_ml_accounts
                        if hasattr(plan_template, 'ai_analysis_monthly'):
                            active_subscription.ai_analysis_monthly = plan_template.ai_analysis_monthly
                        
                        self.db.add(active_subscription)
                        print(f"✅ Nova subscription criada com plano {plan_template.plan_name}")
                else:
                    print(f"⚠️ Template de plano {plan_template_id} não encontrado")
            
            # Atualizar campos da subscription se fornecidos (sempre, independente de plan_id)
            if active_subscription:
                # Atualizar ends_at se plan_expires_at foi definido
                if company.plan_expires_at:
                    active_subscription.ends_at = company.plan_expires_at
                    print(f"✅ Subscription {active_subscription.id} - ends_at atualizado para: {active_subscription.ends_at}")
                
                # Atualizar is_trial se fornecido
                if "subscription_is_trial" in company_data:
                    active_subscription.is_trial = bool(company_data["subscription_is_trial"])
                    print(f"✅ Subscription {active_subscription.id} - is_trial atualizado para: {active_subscription.is_trial}")
                
                # Atualizar status se fornecido
                if "subscription_status" in company_data:
                    active_subscription.status = company_data["subscription_status"]
                    print(f"✅ Subscription {active_subscription.id} - status atualizado para: {active_subscription.status}")
            elif company.plan_expires_at or "subscription_is_trial" in company_data or "subscription_status" in company_data:
                # Se não há subscription mas há campos para atualizar, apenas logar
                print(f"⚠️ Não há subscription ativa para atualizar. Campos ignorados: plan_expires_at, subscription_is_trial, subscription_status")
            
            # Log para debug
            print(f"✅ Empresa {company_id} atualizada:")
            print(f"   plan_expires_at = {company.plan_expires_at}")
            print(f"   status = {company.status} (tipo: {type(company.status)})")
            
            self.db.commit()
            
            # Recarregar a empresa do banco para garantir que foi salva
            self.db.refresh(company)
            print(f"✅ Empresa recarregada do banco:")
            print(f"   plan_expires_at = {company.plan_expires_at}")
            print(f"   status = {company.status} (tipo: {type(company.status)})")
            
            return {
                "id": company.id,
                "message": "Empresa atualizada com sucesso",
                "plan_expires_at": company.plan_expires_at.isoformat() if company.plan_expires_at else None,
                "status": company.status.value if hasattr(company.status, 'value') else str(company.status)
            }
        except Exception as e:
            self.db.rollback()
            raise e
    
    def delete_company(self, company_id: int) -> Dict:
        """Exclui uma empresa e todos os seus registros associados"""
        from sqlalchemy import text
        import traceback
        import sys
        
        # Buscar empresa
        try:
            company = self.db.query(Company).filter(Company.id == company_id).first()
            if not company:
                raise ValueError("Empresa não encontrada")
            company_name = company.name
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Erro ao buscar empresa: {str(e)}")
        
        print(f"\n{'='*80}")
        print(f"🗑️  DELETANDO EMPRESA: {company_name} (ID: {company_id})")
        print(f"{'='*80}\n")
        
        try:
            # Rollback de qualquer transação anterior
            self.db.rollback()
            
            # ============================================================
            # ESTRATÉGIA DE EXCLUSÃO BASEADA EM ORDEM TOPOLÓGICA DE FKs
            # ============================================================
            # Ordenação baseada nas dependências de Foreign Keys:
            # Nível 1: Tabelas folha (dependem de outras, não são dependidas)
            # Nível 2: Tabelas intermediárias (dependem de outras e são dependidas)
            # Nível 3: Tabelas que dependem de companies + outras tabelas
            # Nível 4: Tabelas que dependem apenas de companies
            # Nível 5: companies (deletada por último)
            # ============================================================
            
            # NÍVEL 1: Tabelas folha (dependem de outras, não são dependidas)
            # Nota: ordem_compra_item e ordem_compra_link não têm company_id direto,
            # então serão deletadas via subquery
            level_1 = [
                "ml_campaign_metrics",           # FK: ml_campaigns
                "ml_campaign_products",          # FK: ml_campaigns, ml_products
                "category_planning",             # FK: cost_center_planning, financial_categories
                "cost_center_planning",          # FK: monthly_planning, cost_centers
                "ml_product_attributes",         # FK: ml_products
                "ai_product_analysis",           # FK: ml_products
                "ml_catalog_history",           # FK: ml_catalog_monitoring, ml_products
                "ml_messages",                  # FK: ml_message_threads
            ]
            
            # Tabelas sem company_id direto (deletadas via subquery)
            level_1_special = [
                ("ordem_compra_item", "ordem_compra_id", "ordem_compra"),      # FK: ordem_compra
                ("ordem_compra_link", "ordem_compra_id", "ordem_compra"),      # FK: ordem_compra
            ]
            
            # NÍVEL 2: Tabelas intermediárias (dependem de outras e são dependidas)
            # IMPORTANTE: tokens e user_ml_accounts devem ser deletados ANTES de users e ml_accounts
            level_2 = [
                "monthly_planning",              # FK: financial_planning
                "ml_product_sync",               # FK: ml_products, ml_accounts
                "accounts_receivable",           # FK: accounts_receivable (self), financial_accounts, financial_categories, cost_centers
                "accounts_payable",              # FK: fornecedores, ordem_compra, accounts_payable (self), financial_accounts, financial_categories, cost_centers
                "financial_transactions",        # FK: financial_accounts, financial_categories, cost_centers, financial_customers, financial_suppliers
                "ml_orders",                     # FK: ml_accounts, financial_accounts
                "ml_questions",                 # FK: ml_accounts
                "ml_message_threads",           # FK: ml_accounts
                "tokens",                        # FK: users, ml_accounts (deletar ANTES de users e ml_accounts)
                "user_ml_accounts",             # FK: users, ml_accounts (deletar ANTES de users e ml_accounts)
                "user_sessions",                # FK: users
                "api_logs",                     # FK: users
            ]
            
            # NÍVEL 3: Tabelas que dependem de companies + outras tabelas
            level_3 = [
                "ml_campaigns",                  # FK: ml_accounts
                "ml_catalog_monitoring",        # FK: ml_products
                "sku_management",               # FK: products, internal_products
                "internal_products",            # FK: products
                "ml_products",                  # FK: ml_accounts
            ]
            
            # NÍVEL 4: Tabelas que dependem apenas de companies
            # IMPORTANTE: users e ml_accounts devem ser deletados DEPOIS de todas as suas dependências
            level_4 = [
                "financial_accounts",           # FK: companies
                "financial_categories",         # FK: companies
                "cost_centers",                 # FK: companies
                "financial_customers",          # FK: companies
                "financial_suppliers",          # FK: companies
                "financial_goals",              # FK: companies
                "financial_alerts",             # FK: companies
                "financial_planning",           # FK: companies
                "fornecedores",                 # FK: companies
                "ordem_compra",                 # FK: companies, fornecedores
                "products",                     # FK: companies
                "subscriptions",                # FK: companies
                "catalog_participants",         # FK: companies
                "payment_methods",              # FK: companies (se existir)
                "payments",                     # FK: subscriptions (se existir)
                "ml_billing_charges",           # FK: companies (se existir)
                "ml_billing_periods",           # FK: companies (se existir)
                "notification_logs",            # FK: companies (se existir)
                "ml_accounts",                   # FK: companies (deletar DEPOIS de tokens, user_ml_accounts, ml_products, etc)
                "users",                        # FK: companies (deletar DEPOIS de tokens, user_ml_accounts, user_sessions, etc)
            ]
            
            # Combinar todos os níveis em ordem
            tables_by_level = [level_1, level_2, level_3, level_4]
            
            print("🔄 Deletando registros por nível de dependência...")
            deleted_count = 0
            
            # Deletar por nível, garantindo que dependências sejam resolvidas
            for level_num, level_tables in enumerate(tables_by_level, 1):
                print(f"\n📊 Nível {level_num}: {len(level_tables)} tabela(s)")
                deleted_in_level = 0
                
                # Deletar tabelas normais (com company_id)
                for table in level_tables:
                    try:
                        try:
                            self.db.rollback()
                        except Exception:
                            pass

                        result = self.db.execute(
                            text(f"DELETE FROM {table} WHERE company_id = :company_id"),
                            {"company_id": company_id}
                        )
                        count = result.rowcount if hasattr(result, 'rowcount') else 0

                        if count > 0:
                            self.db.commit()
                            deleted_count += count
                            deleted_in_level += count
                            print(f"  ✅ {table}: {count} registro(s) deletado(s)")

                    except Exception as e:
                        error_str = str(e).lower()
                        try:
                            self.db.rollback()
                        except Exception:
                            pass

                        if "does not exist" not in error_str and "undefinedtable" not in error_str:
                            if "foreign key" in error_str or "violates" in error_str:
                                print(f"  ⚠️  {table}: bloqueada por FK (será tentada novamente)")
                            else:
                                print(f"  ⏭️  {table}: {str(e)[:80]}")

                # Deletar tabelas especiais (sem company_id direto) no nível 1
                if level_num == 1:
                    for table_name, fk_column, parent_table in level_1_special:
                        try:
                            try:
                                self.db.rollback()
                            except Exception:
                                pass

                            result = self.db.execute(
                                text(f"""
                                    DELETE FROM {table_name}
                                    WHERE {fk_column} IN (
                                        SELECT id FROM {parent_table} WHERE company_id = :company_id
                                    )
                                """),
                                {"company_id": company_id}
                            )
                            count = result.rowcount if hasattr(result, 'rowcount') else 0

                            if count > 0:
                                self.db.commit()
                                deleted_count += count
                                deleted_in_level += count
                                print(f"  ✅ {table_name}: {count} registro(s) deletado(s)")

                        except Exception as e:
                            error_str = str(e).lower()
                            try:
                                self.db.rollback()
                            except Exception:
                                pass

                            if "does not exist" not in error_str and "undefinedtable" not in error_str:
                                if "foreign key" in error_str or "violates" in error_str:
                                    print(f"  ⚠️  {table_name}: bloqueada por FK (será tentada novamente)")
                                else:
                                    print(f"  ⏭️  {table_name}: {str(e)[:80]}")
                
                if deleted_in_level > 0:
                    print(f"   Total deletado no nível {level_num}: {deleted_in_level}")
            
            # Fazer passadas adicionais para pegar tabelas que falharam por FK
            print(f"\n🔄 Passadas adicionais para resolver FKs restantes...")
            max_additional_passes = 5  # Aumentar para 5 passadas
            for pass_num in range(max_additional_passes):
                deleted_in_pass = 0
                all_tables = level_1 + level_2 + level_3 + level_4
                
                print(f"\n  🔄 Passada adicional {pass_num + 1}/{max_additional_passes}:")
                
                for table in all_tables:
                    try:
                        try:
                            self.db.rollback()
                        except:
                            pass
                        
                        result = self.db.execute(
                            text(f"DELETE FROM {table} WHERE company_id = :company_id"),
                            {"company_id": company_id}
                        )
                        count = result.rowcount if hasattr(result, 'rowcount') else 0
                        
                        if count > 0:
                            self.db.commit()
                            deleted_count += count
                            deleted_in_pass += count
                            print(f"    ✅ {table}: {count} registro(s) deletado(s)")
                        
                    except Exception as e:
                        error_str = str(e).lower()
                        try:
                            self.db.rollback()
                        except:
                            pass
                        
                        if "does not exist" not in error_str and "undefinedtable" not in error_str:
                            if "foreign key" not in error_str and "violates" not in error_str:
                                print(f"    ⏭️  {table}: {str(e)[:80]}")
                
                if deleted_in_pass == 0:
                    print(f"  ✅ Nenhum registro restante nas passadas adicionais")
                    break
                else:
                    print(f"  📊 Total deletado na passada {pass_num + 1}: {deleted_in_pass}")
            
            # Verificação final: garantir que ml_accounts foi deletada
            print(f"\n🔍 Verificação final antes de deletar empresa...")
            try:
                self.db.rollback()
            except:
                pass
            
            # Verificar se ainda há ml_accounts
            ml_accounts_check = self.db.execute(
                text("SELECT COUNT(*) FROM ml_accounts WHERE company_id = :company_id"),
                {"company_id": company_id}
            ).scalar()
            
            if ml_accounts_check > 0:
                print(f"  ⚠️  Ainda há {ml_accounts_check} conta(s) ML. Tentando deletar forçadamente...")

                ml_account_ids = self.db.execute(
                    text("SELECT id FROM ml_accounts WHERE company_id = :company_id"),
                    {"company_id": company_id}
                ).fetchall()

                if ml_account_ids:
                    ml_account_ids_list = [row[0] for row in ml_account_ids]
                    print(f"  🔍 Encontradas {len(ml_account_ids_list)} conta(s) ML: {ml_account_ids_list}")

                    dependent_tables = [
                        ("ml_campaign_metrics", "campaign_id", "ml_campaigns", "ml_account_id"),
                        ("ml_campaign_products", "campaign_id", "ml_campaigns", "ml_account_id"),
                        ("ml_product_attributes", "ml_product_id", "ml_products", "ml_account_id"),
                        ("ai_product_analysis", "ml_product_id", "ml_products", "ml_account_id"),
                        ("ml_catalog_history", "monitoring_id", "ml_catalog_monitoring", "ml_account_id"),
                        ("ml_messages", "thread_id", "ml_message_threads", "ml_account_id"),
                        ("tokens", "ml_account_id", None, None),
                        ("ml_products", "ml_account_id", None, None),
                        ("ml_orders", "ml_account_id", None, None),
                        ("ml_questions", "ml_account_id", None, None),
                        ("ml_message_threads", "ml_account_id", None, None),
                        ("ml_campaigns", "ml_account_id", None, None),
                        ("ml_product_sync", "ml_account_id", None, None),
                        ("ml_catalog_monitoring", "ml_account_id", None, None),
                        ("user_ml_accounts", "ml_account_id", None, None),
                    ]

                    max_force_passes = 5
                    for force_pass in range(max_force_passes):
                        deleted_in_pass = 0
                        print(f"    🔄 Passada forçada {force_pass + 1}/{max_force_passes}:")

                        for dep_info in dependent_tables:
                            if len(dep_info) == 4:
                                dep_table, fk_column, parent_table, parent_fk = dep_info
                            else:
                                dep_table, fk_column = dep_info[:2]
                                parent_table, parent_fk = None, None

                            try:
                                self.db.rollback()
                            except Exception:
                                pass

                            try:
                                placeholders = ','.join([':id' + str(i) for i in range(len(ml_account_ids_list))])
                                params = {f'id{i}': ml_id for i, ml_id in enumerate(ml_account_ids_list)}

                                if parent_table and parent_fk:
                                    query = text(f"""
                                        DELETE FROM {dep_table}
                                        WHERE {fk_column} IN (
                                            SELECT id FROM {parent_table}
                                            WHERE {parent_fk} IN ({placeholders})
                                        )
                                    """)
                                else:
                                    query = text(f"DELETE FROM {dep_table} WHERE {fk_column} IN ({placeholders})")

                                result = self.db.execute(query, params)
                                count = result.rowcount if hasattr(result, 'rowcount') else 0
                                if count and count > 0:
                                    self.db.commit()
                                    deleted_count += count
                                    deleted_in_pass += count
                                    print(f"      ✅ {dep_table}: {count} registro(s) deletado(s)")

                            except Exception as e:
                                error_str = str(e).lower()
                                try:
                                    self.db.rollback()
                                except Exception:
                                    pass

                                if "does not exist" not in error_str and "undefinedtable" not in error_str:
                                    if "foreign key" in error_str or "violates" in error_str:
                                        pass
                                    else:
                                        print(f"      ⚠️  {dep_table}: {str(e)[:60]}")

                        if deleted_in_pass == 0:
                            break

                    print(f"    🔍 Verificando dependências restantes...")
                    remaining_deps = []
                    for dep_info in dependent_tables:
                        dep_table = dep_info[0]
                        fk_column = dep_info[1] if len(dep_info) > 1 else "ml_account_id"
                        try:
                            placeholders = ','.join([':id' + str(i) for i in range(len(ml_account_ids_list))])
                            params = {f'id{i}': ml_id for i, ml_id in enumerate(ml_account_ids_list)}
                            count = self.db.execute(
                                text(f"SELECT COUNT(*) FROM {dep_table} WHERE {fk_column} IN ({placeholders})"),
                                params
                            ).scalar()
                            if count and count > 0:
                                remaining_deps.append(f"{dep_table}: {count}")
                        except Exception:
                            pass

                    if remaining_deps:
                        print(f"    ⚠️  Dependências restantes: {', '.join(remaining_deps)}")
                        print(f"    🔧 Tentando deletar ml_accounts mesmo assim...")
                    else:
                        print(f"    ✅ Nenhuma dependência restante")

                    try:
                        self.db.rollback()
                    except Exception:
                        pass

                    try:
                        result = self.db.execute(
                            text("DELETE FROM ml_accounts WHERE company_id = :company_id"),
                            {"company_id": company_id}
                        )
                        count = result.rowcount if hasattr(result, 'rowcount') else 0
                        if count and count > 0:
                            self.db.commit()
                            deleted_count += count
                            print(f"    ✅ ml_accounts: {count} conta(s) deletada(s) (forçado)")
                        else:
                            print(f"    ⚠️  ml_accounts: nenhum registro deletado (já estava vazio?)")
                    except Exception as e:
                        error_msg = str(e)
                        print(f"    ❌ Erro ao deletar ml_accounts: {error_msg[:150]}")
                        try:
                            self.db.rollback()
                        except Exception:
                            pass

                        for ml_acc_id in ml_account_ids_list:
                            try:
                                self.db.execute(
                                    text("DELETE FROM ml_accounts WHERE id = :id"),
                                    {"id": ml_acc_id}
                                )
                                self.db.commit()
                                print(f"    ✅ ml_accounts ID {ml_acc_id}: deletado individualmente")
                            except Exception as inner_exc:
                                self.db.rollback()
                                print(f"    ⚠️  Erro ao deletar ml_account {ml_acc_id}: {str(inner_exc)[:150]}")

            # Verificar se ainda há usuários vinculados a esta empresa
            try:
                remaining_users = self.db.execute(
                    text("SELECT id FROM users WHERE company_id = :company_id"),
                    {"company_id": company_id}
                ).fetchall()
            except Exception as e:
                remaining_users = []
                print(f"  ⚠️  Erro ao verificar usuários restantes: {str(e)[:120]}")

            if remaining_users:
                user_ids = [row[0] for row in remaining_users]
                print(f"  🔧 Usuários restantes vinculados à empresa: {user_ids}")
                deleted_users = 0
                for user_id in user_ids:
                    try:
                        self.db.rollback()
                    except:
                        pass

                    try:
                        # Remover sessões vinculadas ao usuário
                        self.db.execute(
                            text("DELETE FROM user_sessions WHERE user_id = :user_id"),
                            {"user_id": user_id}
                        )
                        self.db.commit()
                    except Exception as e:
                        print(f"  ⚠️  Erro ao remover sessões do usuário {user_id}: {str(e)[:150]}")
                        try:
                            self.db.rollback()
                        except:
                            pass

                    try:
                        result = self.db.execute(
                            text("DELETE FROM users WHERE id = :user_id"),
                            {"user_id": user_id}
                        )
                        deleted = result.rowcount if hasattr(result, 'rowcount') else 0
                        if deleted > 0:
                            self.db.commit()
                            deleted_users += deleted
                            print(f"  ✅ users: usuário {user_id} removido (forçado)")
                    except Exception as e:
                        print(f"  ❌ Erro ao remover usuário {user_id}: {str(e)[:150]}")
                        try:
                            self.db.rollback()
                        except Exception:
                            pass

                if deleted_users > 0:
                    deleted_count += deleted_users
            
            # Verificar outras tabelas críticas
            critical_tables = ["users", "ml_accounts", "subscriptions"]
            for table in critical_tables:
                try:
                    count = self.db.execute(
                        text(f"SELECT COUNT(*) FROM {table} WHERE company_id = :company_id"),
                        {"company_id": company_id}
                    ).scalar()
                    if count > 0:
                        print(f"  ⚠️  Ainda há {count} registro(s) em {table}")
                except:
                    pass  # Tabela pode não existir
            
            # Deletar a empresa
            print(f"\n🔧 Deletando empresa {company_id}...")
            try:
                try:
                    self.db.rollback()
                except Exception:
                    pass

                self.db.execute(
                    text("DELETE FROM companies WHERE id = :company_id"),
                    {"company_id": company_id}
                )
            except Exception as e:
                self.db.rollback()
                raise
            
            # COMMIT final
            print(f"\n💾 Salvando exclusão da empresa...")
            self.db.commit()
            print(f"\n{'='*80}")
            print(f"✅ EMPRESA DELETADA COM SUCESSO!")
            print(f"   Total de registros relacionados deletados: {deleted_count}")
            print(f"{'='*80}\n")
            
            return {
                "success": True,
                "message": f"Empresa '{company_name}' excluída com sucesso",
                "deleted_records": deleted_count
            }
            
        except Exception as e:
            self.db.rollback()
            error_msg = str(e)
            print(f"\n{'='*80}")
            print(f"❌ ERRO AO DELETAR EMPRESA")
            print(f"   Erro: {error_msg[:200]}")
            print(f"{'='*80}\n")
            traceback.print_exc()
            raise Exception(f"Erro ao excluir empresa: {error_msg}")
    
    # ==================== MÉTODOS PARA PLANOS ====================
    
    
    def get_plans_overview(self) -> Dict:
        """Retorna visão geral dos planos"""
        try:
            # Total de planos (templates)
            total_plans = self.db.query(Subscription).filter(
                Subscription.status == "template"
            ).count()
            
            # Planos ativos (templates ativos)
            active_plans = self.db.query(Subscription).filter(
                Subscription.status == "template"
            ).count()
            
            # Assinaturas trial
            trial_plans = self.db.query(Subscription).filter(
                Subscription.is_trial == True,
                Subscription.status == "active"
            ).count()
            
            # Empresas com planos ativos
            companies_with_plans = self.db.query(Subscription).filter(
                Subscription.status == "active",
                Subscription.company_id.isnot(None)
            ).distinct(Subscription.company_id).count()
            
            # Lista de todos os planos
            plans = self.db.query(Subscription).filter(
                Subscription.status == "template"
            ).all()
            
            plans_data = []
            for plan in plans:
                # Contar assinaturas ativas deste plano
                active_subscriptions = self.db.query(Subscription).filter(
                    Subscription.plan_name == plan.plan_name,
                    Subscription.status == "active",
                    Subscription.company_id.isnot(None)
                ).count()
                
                plans_data.append({
                    "id": plan.id,
                    "plan_name": plan.plan_name,
                    "description": plan.description if hasattr(plan, 'description') else None,
                    "price": float(plan.price) if plan.price else 0,
                    "promotional_price": float(plan.promotional_price) if hasattr(plan, 'promotional_price') and plan.promotional_price else None,
                    "currency": plan.currency,
                    "billing_cycle": plan.billing_cycle if hasattr(plan, 'billing_cycle') else "monthly",
                    "status": "active",  # Templates são sempre ativos
                    
                    # Limites básicos
                    "max_users": plan.max_users if hasattr(plan, 'max_users') else 10,
                    "max_ml_accounts": plan.max_ml_accounts if hasattr(plan, 'max_ml_accounts') else 5,
                    
                    # Recursos vendidos
                    "storage_gb": plan.storage_gb if hasattr(plan, 'storage_gb') else 5,
                    "ai_analysis_monthly": plan.ai_analysis_monthly if hasattr(plan, 'ai_analysis_monthly') else 10,
                    "catalog_monitoring_slots": plan.catalog_monitoring_slots if hasattr(plan, 'catalog_monitoring_slots') else 5,
                    "product_mining_slots": plan.product_mining_slots if hasattr(plan, 'product_mining_slots') else 10,
                    "product_monitoring_slots": plan.product_monitoring_slots if hasattr(plan, 'product_monitoring_slots') else 20,
                    
                    "trial_days": plan.trial_days if hasattr(plan, 'trial_days') else 0,
                    "active_subscriptions": active_subscriptions,
                    "created_at": plan.created_at
                })
            
            return {
                "total": total_plans,
                "active_plans": active_plans,
                "trial_plans": trial_plans,
                "companies_with_plans": companies_with_plans,
                "plans": plans_data
            }
        except Exception as e:
            print(f"Erro ao buscar planos: {e}")
            return {
                "total": 0,
                "active_plans": 0,
                "trial_plans": 0,
                "companies_with_plans": 0,
                "plans": []
            }
    
    def create_plan_template(self, plan_data: Dict) -> Dict:
        """Cria um template de plano"""
        try:
            # Verificar se já existe plano com este nome
            existing = self.db.query(Subscription).filter(
                Subscription.plan_name == plan_data["plan_name"],
                Subscription.status == "template"
            ).first()
            
            if existing:
                raise ValueError("Já existe um plano com este nome")
            
            plan = Subscription(
                company_id=None,  # Template não pertence a nenhuma empresa
                plan_name=plan_data["plan_name"],
                description=plan_data.get("description"),
                price=str(plan_data.get("price", 0)),
                promotional_price=str(plan_data.get("promotional_price")) if plan_data.get("promotional_price") else None,
                currency=plan_data.get("currency", "BRL"),
                billing_cycle=plan_data.get("billing_cycle", "monthly"),
                status="template",
                is_trial=False,
                
                # Limites básicos
                max_users=plan_data.get("max_users", 10),
                max_ml_accounts=plan_data.get("max_ml_accounts", 5),
                
                # Recursos vendidos
                storage_gb=plan_data.get("storage_gb", 5),
                ai_analysis_monthly=plan_data.get("ai_analysis_monthly", 10),
                catalog_monitoring_slots=plan_data.get("catalog_monitoring_slots", 5),
                product_mining_slots=plan_data.get("product_mining_slots", 10),
                product_monitoring_slots=plan_data.get("product_monitoring_slots", 20),
                
                trial_days=plan_data.get("trial_days", 0)
            )
            
            self.db.add(plan)
            self.db.commit()
            
            return {
                "id": plan.id,
                "message": "Plano criado com sucesso"
            }
        except Exception as e:
            self.db.rollback()
            raise e
    
    def update_plan_template(self, plan_id: int, plan_data: Dict) -> Dict:
        """Atualiza um template de plano"""
        try:
            plan = self.db.query(Subscription).filter(
                Subscription.id == plan_id,
                Subscription.status == "template"
            ).first()
            
            if not plan:
                raise ValueError("Plano não encontrado")
            
            # Verificar se o novo nome já existe (em outro plano)
            if plan_data.get("plan_name") and plan_data["plan_name"] != plan.plan_name:
                existing = self.db.query(Subscription).filter(
                    Subscription.plan_name == plan_data["plan_name"],
                    Subscription.status == "template",
                    Subscription.id != plan_id
                ).first()
                
                if existing:
                    raise ValueError("Já existe um plano com este nome")
            
            # Atualizar campos
            plan.plan_name = plan_data.get("plan_name", plan.plan_name)
            plan.description = plan_data.get("description", plan.description)
            plan.price = str(plan_data.get("price", plan.price))
            plan.promotional_price = str(plan_data.get("promotional_price")) if plan_data.get("promotional_price") else None
            plan.currency = plan_data.get("currency", plan.currency)
            plan.billing_cycle = plan_data.get("billing_cycle", plan.billing_cycle)
            
            # Limites básicos
            plan.max_users = plan_data.get("max_users", plan.max_users)
            plan.max_ml_accounts = plan_data.get("max_ml_accounts", plan.max_ml_accounts)
            
            # Recursos vendidos
            plan.storage_gb = plan_data.get("storage_gb", plan.storage_gb if hasattr(plan, 'storage_gb') else 5)
            plan.ai_analysis_monthly = plan_data.get("ai_analysis_monthly", plan.ai_analysis_monthly if hasattr(plan, 'ai_analysis_monthly') else 10)
            plan.catalog_monitoring_slots = plan_data.get("catalog_monitoring_slots", plan.catalog_monitoring_slots if hasattr(plan, 'catalog_monitoring_slots') else 5)
            plan.product_mining_slots = plan_data.get("product_mining_slots", plan.product_mining_slots if hasattr(plan, 'product_mining_slots') else 10)
            plan.product_monitoring_slots = plan_data.get("product_monitoring_slots", plan.product_monitoring_slots if hasattr(plan, 'product_monitoring_slots') else 20)
            
            plan.trial_days = plan_data.get("trial_days", plan.trial_days)
            
            self.db.commit()
            
            return {
                "id": plan.id,
                "message": "Plano atualizado com sucesso"
            }
        except Exception as e:
            self.db.rollback()
            raise e
    
    def delete_plan_template(self, plan_id: int) -> Dict:
        """Exclui um template de plano"""
        try:
            plan = self.db.query(Subscription).filter(
                Subscription.id == plan_id,
                Subscription.status == "template"
            ).first()
            
            if not plan:
                raise ValueError("Plano não encontrado")
            
            # Verificar se há assinaturas ativas usando este plano
            active_subscriptions = self.db.query(Subscription).filter(
                Subscription.plan_name == plan.plan_name,
                Subscription.status == "active",
                Subscription.company_id.isnot(None)
            ).count()
            
            if active_subscriptions > 0:
                raise ValueError(f"Não é possível excluir plano com {active_subscriptions} assinatura(s) ativa(s)")
            
            self.db.delete(plan)
            self.db.commit()
            
            return {
                "message": "Plano excluído com sucesso"
            }
        except Exception as e:
            self.db.rollback()
            raise e
