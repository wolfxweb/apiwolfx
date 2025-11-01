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
                    from datetime import datetime, timedelta
                    
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
            company.status = company_data["status"]
            # Atualizar campos de plano
            if "plan_expires_at" in company_data:
                company.plan_expires_at = company_data["plan_expires_at"]
            
            self.db.commit()
            
            return {
                "id": company.id,
                "message": "Empresa atualizada com sucesso"
            }
        except Exception as e:
            self.db.rollback()
            raise e
    
    def delete_company(self, company_id: int) -> Dict:
        """Exclui uma empresa e todos os seus registros associados"""
        from sqlalchemy import text
        import traceback
        import sys
        
        # Buscar empresa sem carregar relacionamentos que podem ter problemas
        try:
            company = self.db.query(Company).filter(Company.id == company_id).first()
            if not company:
                raise ValueError("Empresa não encontrada")
            company_name = company.name
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Erro ao buscar empresa: {str(e)}")
        
        # Função helper para deletar com tratamento de erro isolado
        def safe_delete(table_name: str, description: str = "", use_subquery: bool = False, subquery_table: str = "", subquery_field: str = "id"):
            """Deleta de uma tabela com tratamento de erro isolado"""
            def build_query():
                if use_subquery and subquery_table:
                    return f"""
                        DELETE FROM {table_name} 
                        WHERE {subquery_field} IN (
                            SELECT {subquery_field} FROM {subquery_table} WHERE company_id = :company_id
                        )
                    """
                else:
                    return f"DELETE FROM {table_name} WHERE company_id = :company_id"
            
            error_str = ""
            max_retries = 2
            
            for attempt in range(max_retries):
                try:
                    query = build_query()
                    self.db.execute(text(query), {"company_id": company_id})
                    self.db.flush()
                    return True
                except Exception as e:
                    error_str = str(e).lower()
                    
                    # Erros aceitáveis (tabela ou coluna não existe)
                    if any(x in error_str for x in ["does not exist", "undefinedtable", "undefinedcolumn"]):
                        if description:
                            print(f"ℹ️  {description}: Tabela/coluna não existe, ignorando")
                        return True  # Considera sucesso pois não há dados para deletar
                    
                    # Se transação abortada ou outro erro, fazer rollback e tentar novamente
                    if attempt < max_retries - 1:
                        try:
                            self.db.rollback()
                        except:
                            pass
                        continue
                    else:
                        # Última tentativa falhou
                        if description:
                            print(f"⚠️  {description}: {str(e)[:150]}")
                        return False
            
            return False
        
        try:
            # IMPORTANTE: Deletar financial_goals PRIMEIRO (antes de qualquer cascade)
            safe_delete("financial_goals", "Aviso ao deletar financial_goals")
            
            # Excluir TODOS os registros associados em ordem (respeitando foreign keys)
            
            # 1. Tabelas financeiras (dependem de company_id mas podem ter relacionamentos internos)
            #    Transações primeiro (podem referenciar customers, suppliers, accounts, etc)
            safe_delete("financial_transactions", "Aviso ao deletar financial_transactions")
            safe_delete("accounts_receivable", "Aviso ao deletar accounts_receivable")
            safe_delete("accounts_payable", "Aviso ao deletar accounts_payable")
            safe_delete("financial_customers", "Aviso ao deletar financial_customers")
            safe_delete("financial_suppliers", "Aviso ao deletar financial_suppliers")
            safe_delete("financial_accounts", "Aviso ao deletar financial_accounts")
            safe_delete("financial_categories", "Aviso ao deletar financial_categories")
            safe_delete("cost_centers", "Aviso ao deletar cost_centers")
            
            # Planejamento financeiro (filhos primeiro)
            safe_delete("monthly_planning", "Aviso ao deletar monthly_planning", 
                       use_subquery=True, subquery_table="financial_planning", subquery_field="planning_id")
            safe_delete("financial_planning", "Aviso ao deletar financial_planning")
            
            # 2. Campanhas e produtos de campanha (filhos primeiro)
            safe_delete("ml_campaign_products", use_subquery=True, 
                       subquery_table="ml_campaigns", subquery_field="campaign_id")
            safe_delete("ml_campaign_metrics", use_subquery=True, 
                       subquery_table="ml_campaigns", subquery_field="campaign_id")
            safe_delete("ml_campaigns")
            
            # 3. Catálogo ML (filhos primeiro)
            safe_delete("ml_catalog_history", use_subquery=True, 
                       subquery_table="ml_catalog_monitoring", subquery_field="monitoring_id")
            safe_delete("ml_catalog_monitoring")
            safe_delete("catalog_participants")
            
            # 4. Produtos ML
            safe_delete("ml_product_sync")
            safe_delete("ml_products")
            
            # 5. Billing ML (filhos primeiro)
            safe_delete("ml_billing_charges", use_subquery=True, 
                       subquery_table="ml_billing_periods", subquery_field="period_id")
            safe_delete("ml_billing_periods")
            
            # 6. Pedidos e Contas ML
            safe_delete("ml_orders", "Erro crítico ao deletar ml_orders")
            safe_delete("ml_accounts", "Erro crítico ao deletar ml_accounts")
            
            # 7. Payments (filhos primeiro) - ANTES de subscriptions porque payment_transactions pode referenciar subscriptions
            safe_delete("payment_transactions", "Erro crítico ao deletar payment_transactions")
            safe_delete("payments", "Erro crítico ao deletar payments")
            safe_delete("payment_methods")
            
            # 8. Assinaturas (após payments porque payment_transactions pode ter subscription_id)
            # IMPORTANTE: subscriptions precisa ser deletada com força se necessário
            subscriptions_deleted = safe_delete("subscriptions", "Erro crítico ao deletar subscriptions")
            if not subscriptions_deleted:
                # Tentar deletar novamente com query direta
                try:
                    self.db.execute(text("DELETE FROM subscriptions WHERE company_id = :company_id"), 
                                  {"company_id": company_id})
                    self.db.flush()
                    print(f"✅ Subscriptions deletadas via query direta")
                except Exception as sub_err:
                    print(f"⚠️  Aviso ao deletar subscriptions via query direta: {sub_err}")
            
            # 9. Produtos
            safe_delete("internal_products")
            safe_delete("products", "Erro crítico ao deletar products")
            
            # 9. Ordens de compra (itens primeiro)
            safe_delete("ordem_compra_item", use_subquery=True, 
                       subquery_table="ordem_compra", subquery_field="ordem_compra_id")
            safe_delete("ordem_compra_link")
            safe_delete("ordem_compra")
            safe_delete("fornecedores")
            
            # 10. Outras tabelas financeiras
            safe_delete("reconciliation_items", use_subquery=True, 
                       subquery_table="bank_reconciliation", subquery_field="reconciliation_id")
            safe_delete("bank_reconciliation")
            safe_delete("chart_of_accounts")
            safe_delete("financial_alerts")
            safe_delete("ai_product_analysis")
            safe_delete("sku_management")
            safe_delete("api_logs")
            
            # 11. Tabelas relacionadas a usuários (antes de deletar usuários)
            safe_delete("user_sessions", use_subquery=True, 
                       subquery_table="users", subquery_field="user_id")
            safe_delete("user_ml_accounts", use_subquery=True, 
                       subquery_table="users", subquery_field="user_id")
            safe_delete("tokens", use_subquery=True, 
                       subquery_table="users", subquery_field="user_id")
            
            # 12. Usuários (depois de deletar relacionamentos)
            safe_delete("users", "Erro crítico ao deletar users")
            
            # VERIFICAÇÃO CRÍTICA: Garantir que subscriptions foi deletada
            # Se falhar, tentar novamente com query direta e forçar commit
            try:
                # Verificar se ainda existem subscriptions
                result = self.db.execute(
                    text("SELECT COUNT(*) as count FROM subscriptions WHERE company_id = :company_id"),
                    {"company_id": company_id}
                ).scalar()
                
                if result and result > 0:
                    print(f"⚠️  Ainda existem {result} subscriptions, tentando deletar novamente...")
                    # Tentar deletar novamente com força
                    self.db.execute(text("DELETE FROM subscriptions WHERE company_id = :company_id"), 
                                  {"company_id": company_id})
                    self.db.flush()
                    # Verificar novamente
                    result = self.db.execute(
                        text("SELECT COUNT(*) FROM subscriptions WHERE company_id = :company_id"),
                        {"company_id": company_id}
                    ).scalar()
                    if result and result > 0:
                        raise Exception(f"Não foi possível deletar {result} subscriptions. Verifique foreign keys.")
                    else:
                        print(f"✅ Subscriptions deletadas com sucesso na segunda tentativa")
            except Exception as e:
                print(f"⚠️  Erro ao verificar/deletar subscriptions: {e}")
                try:
                    self.db.rollback()
                except:
                    pass
                # Tentar deletar subscriptions de qualquer forma antes de continuar
                try:
                    self.db.execute(text("DELETE FROM subscriptions WHERE company_id = :company_id"), 
                                  {"company_id": company_id})
                    self.db.flush()
                except:
                    pass
            
            # Commit parcial: garantir que tudo até aqui foi deletado antes de deletar company
            # Isso evita que erro na deleção de company reverta tudo
            try:
                self.db.commit()
                print(f"✅ Todas as tabelas relacionadas deletadas para company_id {company_id}")
                
                # VERIFICAÇÃO FINAL: Confirmar que subscriptions realmente foi deletada
                from app.config.database import SessionLocal
                verify_db = SessionLocal()
                try:
                    remaining = verify_db.execute(
                        text("SELECT COUNT(*) FROM subscriptions WHERE company_id = :company_id"),
                        {"company_id": company_id}
                    ).scalar()
                    if remaining and remaining > 0:
                        print(f"❌ ATENÇÃO: Ainda existem {remaining} subscriptions após commit!")
                        # Tentar deletar com nova sessão
                        verify_db.execute(text("DELETE FROM subscriptions WHERE company_id = :company_id"), 
                                        {"company_id": company_id})
                        verify_db.commit()
                        print(f"✅ Subscriptions deletadas em sessão separada")
                finally:
                    verify_db.close()
                    
            except Exception as e:
                print(f"⚠️  Aviso ao fazer commit parcial: {e}")
                try:
                    self.db.rollback()
                except:
                    pass
            
            # 13. Finalmente, excluir a empresa via SQL direto em uma nova transação
            # IMPORTANTE: Deletar subscriptions novamente na nova sessão se ainda existirem
            from app.config.database import SessionLocal
            final_db = SessionLocal()
            try:
                # Verificar e deletar subscriptions na nova sessão (se ainda existirem)
                remaining_subs = final_db.execute(
                    text("SELECT COUNT(*) FROM subscriptions WHERE company_id = :company_id"),
                    {"company_id": company_id}
                ).scalar()
                
                if remaining_subs and remaining_subs > 0:
                    print(f"⚠️  Encontradas {remaining_subs} subscriptions na nova sessão, deletando...")
                    try:
                        # Verificar se há foreign keys que impedem
                        # Primeiro tentar deletar qualquer dependência de subscriptions
                        final_db.execute(text("DELETE FROM subscriptions WHERE company_id = :company_id"), 
                                      {"company_id": company_id})
                        final_db.commit()
                        print(f"✅ {remaining_subs} subscriptions deletadas na nova sessão")
                    except Exception as sub_err:
                        print(f"⚠️  Erro ao deletar subscriptions: {sub_err}")
                        final_db.rollback()
                        # Tentar descobrir qual foreign key está bloqueando
                        error_str = str(sub_err).lower()
                        if "foreign key" in error_str or "violates" in error_str:
                            raise Exception(f"Não foi possível deletar subscriptions. Foreign key constraint: {str(sub_err)[:200]}")
                        raise
                
                # Agora deletar a empresa
                max_company_retries = 3
                for attempt in range(max_company_retries):
                    try:
                        final_db.execute(text("DELETE FROM companies WHERE id = :company_id"), 
                                      {"company_id": company_id})
                        final_db.commit()
                        print(f"✅ Empresa {company_id} deletada com sucesso")
                        break
                    except Exception as e:
                        error_str = str(e).lower()
                        # Se for erro de foreign key, tentar deletar subscriptions novamente
                        if ("foreign key" in error_str or "violates" in error_str) and "subscriptions" in error_str:
                            print(f"⚠️  Foreign key error com subscriptions, tentando deletar novamente...")
                            try:
                                final_db.rollback()
                                final_db.execute(text("DELETE FROM subscriptions WHERE company_id = :company_id"), 
                                              {"company_id": company_id})
                                final_db.commit()
                                print(f"✅ Subscriptions deletadas, tentando deletar empresa novamente...")
                                continue  # Tentar deletar empresa novamente
                            except Exception as sub_err2:
                                print(f"❌ Erro ao deletar subscriptions: {sub_err2}")
                                raise Exception(f"Não foi possível deletar subscriptions antes de deletar empresa: {str(sub_err2)[:200]}")
                        
                        if attempt < max_company_retries - 1:
                            try:
                                final_db.rollback()
                            except:
                                pass
                            continue
                        else:
                            final_db.rollback()
                            raise Exception(f"Erro ao deletar empresa após {max_company_retries} tentativas: {error_str[:200]}")
            finally:
                final_db.close()
            
            return {
                "message": f"Empresa '{company_name}' e todos os seus registros foram excluídos com sucesso"
            }
        except Exception as e:
            self.db.rollback()
            import traceback
            import sys
            error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            print(f"❌ Erro ao excluir empresa {company_id}: {error_detail}", file=sys.stderr)
            # Log completo do erro
            error_msg = str(e)
            if hasattr(e, '__class__'):
                error_msg = f"{e.__class__.__name__}: {error_msg}"
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
