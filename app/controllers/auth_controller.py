"""
Controller de autenticação para sistema SaaS
"""
from typing import Optional
from fastapi import HTTPException, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import secrets
import string
import logging

logger = logging.getLogger(__name__)

from app.config.database import get_db
from app.models.saas_models import User, Company, UserSession
from app.views.template_renderer import render_template

# Configuração de hash de senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuração JWT
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class AuthController:
    """Controller para autenticação e autorização"""
    
    def __init__(self):
        self.pwd_context = pwd_context
    
    def get_login_page(self, error: str = None, success: str = None, session_token: str = None, db: Session = None, redirect: str = None) -> HTMLResponse:
        """Renderiza página de login"""
        user_data = None
        
        # Se há session_token, verificar se o usuário já está logado
        if session_token and db:
            result = self.get_user_by_session(session_token, db)
            if result.get("success"):
                user_data = result["user"]
        
        return render_template("login.html", 
                             user=user_data,
                             error=error or "", 
                             success=success or "",
                             redirect=redirect or "")
    
    def get_register_page(self, error: str = None, success: str = None, session_token: str = None, selected_plan: int = None, plans: list = None, db: Session = None) -> HTMLResponse:
        """Renderiza página de cadastro"""
        user_data = None
        
        # Se há session_token, verificar se o usuário já está logado
        if session_token and db:
            result = self.get_user_by_session(session_token, db)
            if result.get("success"):
                user_data = result["user"]
        
        return render_template("register.html", 
                             user=user_data,
                             error=error or "", 
                             success=success or "",
                             selected_plan=selected_plan,
                             plans=plans or [])
    
    def login(self, email: str, password: str, remember: bool = False, db: Session = None) -> dict:
        """Processa login do usuário"""
        try:
            # Buscar usuário por email
            user = db.query(User).filter(User.email == email).first()
            
            if not user:
                return {"error": "Email ou senha incorretos"}
            
            # Verificar senha
            if not self.pwd_context.verify(password, user.password_hash):
                return {"error": "Email ou senha incorretos"}
            
            # Verificar se usuário está ativo
            if not user.is_active:
                return {"error": "Conta desativada. Entre em contato com o suporte."}
            
            # Buscar empresa do usuário
            company = db.query(Company).filter(Company.id == user.company_id).first()
            if not company:
                return {"error": "Empresa não encontrada"}
            
            # Criar sessão
            session_token = self._generate_session_token()
            expires_at = datetime.utcnow() + timedelta(days=7 if remember else 1)
            
            session = UserSession(
                user_id=user.id,
                session_token=session_token,
                is_active=True,
                expires_at=expires_at
            )
            db.add(session)
            db.commit()
            
            # Atualizar último login
            user.last_login = datetime.utcnow()
            db.commit()
            
            return {
                "success": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role.value if user.role else None,
                    "company": {
                        "id": company.id,
                        "name": company.name,
                        "slug": company.slug
                    }
                },
                "session_token": session_token
            }
            
        except Exception as e:
            return {"error": f"Erro interno: {str(e)}"}
    
    def register(self, company_name: str, company_domain: str, company_description: str,
                first_name: str, last_name: str, email: str, password: str, 
                plan_id: int = None, terms: bool = False, newsletter: bool = False, db: Session = None) -> dict:
        """Processa cadastro de novo usuário e empresa"""
        try:
            # Verificar se email já existe
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                return {"error": "Email já cadastrado"}
            
            # Verificar se domínio da empresa já existe
            if company_domain:
                existing_company = db.query(Company).filter(Company.domain == company_domain).first()
                if existing_company:
                    return {"error": "Domínio já cadastrado"}
            
            # Criar slug da empresa
            company_slug = self._generate_company_slug(company_name)
            
            # Verificar se slug já existe
            existing_slug = db.query(Company).filter(Company.slug == company_slug).first()
            if existing_slug:
                company_slug = f"{company_slug}-{secrets.randbelow(1000)}"
            
            # Buscar informações do plano ANTES de criar a empresa
            trial_days = 0
            is_trial = False
            plan_template = None
            
            if plan_id:
                from app.models.saas_models import Subscription
                
                # Buscar o template do plano
                plan_template = db.query(Subscription).filter(
                    Subscription.id == plan_id,
                    Subscription.status == "template"
                ).first()
                
                if plan_template:
                    trial_days = plan_template.trial_days if hasattr(plan_template, 'trial_days') else 0
                    is_trial = trial_days > 0
            
            # Criar empresa com status ACTIVE e trial_ends_at baseado no plano
            company_status = "ACTIVE"
            trial_ends_at = datetime.utcnow() + timedelta(days=trial_days) if trial_days > 0 else None
            
            company = Company(
                name=company_name,
                slug=company_slug,
                description=company_description or "",
                domain=company_domain if company_domain else None,
                status=company_status,
                features={"api_access": True, "analytics": True, "reports": True},
                trial_ends_at=trial_ends_at
            )
            db.add(company)
            db.flush()  # Para obter o ID
            
            # Hash da senha
            password_hash = self.get_password_hash(password)
            
            # Criar usuário (admin da empresa)
            user = User(
                company_id=company.id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password_hash=password_hash,
                is_active=True,
                role="COMPANY_ADMIN"
            )
            db.add(user)
            db.flush()  # Para obter o ID
            
            # Criar assinatura do plano selecionado
            if plan_id and plan_template:
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
                db.add(subscription)
            
            # Criar sessão inicial
            session_token = self._generate_session_token()
            session = UserSession(
                user_id=user.id,
                session_token=session_token,
                is_active=True,
                expires_at=datetime.utcnow() + timedelta(days=1)
            )
            db.add(session)
            db.commit()
            
            return {
                "success": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role.value,
                    "company": {
                        "id": company.id,
                        "name": company.name,
                        "slug": company.slug
                    }
                },
                "session_token": session_token
            }
            
        except Exception as e:
            db.rollback()
            return {"error": f"Erro interno: {str(e)}"}
    
    def logout(self, session_token: str, db: Session = None) -> dict:
        """Processa logout do usuário"""
        try:
            # Buscar e desativar sessão
            session = db.query(UserSession).filter(
                UserSession.session_token == session_token,
                UserSession.is_active == True
            ).first()
            
            if session:
                session.is_active = False
                db.commit()
            
            return {"success": True}
            
        except Exception as e:
            return {"error": f"Erro interno: {str(e)}"}
    
    def _cleanup_expired_sessions(self, db: Session = None):
        """Remove sessões expiradas do banco de dados"""
        try:
            if db is None:
                db = next(get_db())
            
            # Deletar sessões expiradas
            expired_count = db.query(UserSession).filter(
                UserSession.expires_at < datetime.utcnow()
            ).delete()
            
            if expired_count > 0:
                db.commit()
                logger.info(f"Removidas {expired_count} sessões expiradas")
                
        except Exception as e:
            logger.error(f"Erro ao limpar sessões expiradas: {e}")
    
    def get_user_by_session(self, session_token: str, db: Session = None) -> dict:
        """Obtém usuário pela sessão"""
        try:
            # Limpar sessões expiradas antes de buscar
            self._cleanup_expired_sessions(db)
            
            session = db.query(UserSession).filter(
                UserSession.session_token == session_token,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            ).first()
            
            if not session:
                return {"error": "Sessão inválida ou expirada"}
            
            user = db.query(User).filter(User.id == session.user_id).first()
            if not user or not user.is_active:
                return {"error": "Usuário não encontrado ou inativo"}
            
            company = db.query(Company).filter(Company.id == user.company_id).first()
            
            return {
                "success": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role.value if user.role else None,
                    "company_id": user.company_id,  # Adicionar company_id diretamente
                    "company": {
                        "id": company.id,
                        "name": company.name,
                        "slug": company.slug
                    } if company else None
                }
            }
            
        except Exception as e:
            return {"error": f"Erro interno: {str(e)}"}
    
    def _generate_session_token(self) -> str:
        """Gera token de sessão seguro"""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(64))
    
    def _generate_company_slug(self, company_name: str) -> str:
        """Gera slug da empresa"""
        import re
        # Converter para minúsculas e remover caracteres especiais
        slug = re.sub(r'[^a-z0-9\s-]', '', company_name.lower())
        # Substituir espaços por hífens
        slug = re.sub(r'\s+', '-', slug)
        # Remover hífens duplicados
        slug = re.sub(r'-+', '-', slug)
        # Remover hífens no início e fim
        return slug.strip('-')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifica senha"""
        # Usar bcrypt diretamente para verificação
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Gera hash da senha"""
        # Usar bcrypt diretamente para hash
        return self.pwd_context.hash(password)
    
    def get_management_dashboard_data(self, company_id: int, db: Session, 
                                      period: str = "30days", 
                                      date_from: Optional[str] = None, 
                                      date_to: Optional[str] = None) -> dict:
        """Busca dados do dashboard de gestão para uma empresa"""
        try:
            from sqlalchemy import func, and_, or_
            from datetime import datetime, timedelta
            from app.models.financial_models import AccountReceivable, AccountPayable
            from app.models.saas_models import MLOrder, OrderStatus, MLAccount, MLAccountStatus, MLQuestion, MLQuestionStatus, Company
            
            # Calcular período baseado no filtro
            today = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            start_date = None
            end_date = today
            
            if period == "custom" and date_from and date_to:
                try:
                    start_date = datetime.strptime(date_from, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999)
                except ValueError:
                    # Se houver erro no parse, usar padrão de 30 dias
                    start_date = (today - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "today":
                start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "7days":
                start_date = (today - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "15days":
                start_date = (today - timedelta(days=15)).replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "30days":
                start_date = (today - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "this_month":
                start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                # Padrão: 30 dias
                start_date = (today - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
            
            logger.info(f"Dashboard: Filtrando dados de {start_date} até {end_date}")
            
            # 1. VALOR A RECEBER (Pendentes)
            # Contas a receber normais pendentes (não filtrar por data, pois são pendentes)
            receivables_pending = db.query(func.sum(AccountReceivable.amount)).filter(
                AccountReceivable.company_id == company_id,
                AccountReceivable.status == 'pending'
            ).scalar() or 0
            
            # Buscar empresa e contas ML
            company = db.query(Company).filter(Company.id == company_id).first()
            accounts = db.query(MLAccount).filter(
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).all()
            
            account_ids = [acc.id for acc in accounts] if accounts else []
            
            # Buscar pedidos ML uma única vez (se houver contas)
            ml_orders = []
            ml_pending_revenue = 0.0
            ml_received_revenue = 0.0
            
            if company and company.ml_orders_as_receivables and account_ids:
                ml_orders_query = db.query(MLOrder).filter(
                    MLOrder.company_id == company_id,
                    MLOrder.ml_account_id.in_(account_ids),
                    MLOrder.status.in_([OrderStatus.PAID, OrderStatus.DELIVERED])
                )
                # Filtrar por data se especificado
                if start_date:
                    ml_orders_query = ml_orders_query.filter(MLOrder.date_created >= start_date)
                if end_date:
                    ml_orders_query = ml_orders_query.filter(MLOrder.date_created <= end_date)
                ml_orders = ml_orders_query.all()
                
                # Processar pedidos ML para calcular pendentes e recebidos
                import json
                for order in ml_orders:
                    gross_amount = float(order.total_amount or 0)
                    is_delivered = (
                        order.status == OrderStatus.DELIVERED or 
                        (order.shipping_status and order.shipping_status.lower() == "delivered")
                    )
                    
                    if is_delivered:
                        delivery_date = None
                        if order.shipping_details:
                            shipping_details = json.loads(order.shipping_details) if isinstance(order.shipping_details, str) else order.shipping_details
                            if isinstance(shipping_details, dict):
                                status_history = shipping_details.get('status_history', {})
                                if status_history and 'date_delivered' in status_history:
                                    try:
                                        delivery_date_str = status_history['date_delivered']
                                        delivery_date = datetime.fromisoformat(delivery_date_str.replace('Z', '+00:00'))
                                    except:
                                        pass
                        
                        if delivery_date:
                            days_since_delivery = (datetime.now() - delivery_date.replace(tzinfo=None)).days
                            if days_since_delivery >= 7:
                                ml_received_revenue += gross_amount
                            else:
                                ml_pending_revenue += gross_amount
                        else:
                            ml_pending_revenue += gross_amount
                    else:
                        ml_pending_revenue += gross_amount
            
            # 1. VALOR A RECEBER (Pendentes)
            total_receivables_pending = float(receivables_pending) + ml_pending_revenue
            
            # 2. VALOR A PAGAR (Pendentes)
            # Não filtrar por data, pois são pendentes
            payables_pending = db.query(func.sum(AccountPayable.amount)).filter(
                AccountPayable.company_id == company_id,
                AccountPayable.status.in_(['pending', 'overdue', 'unpaid'])
            ).scalar() or 0
            
            # 3. VALOR RECEBIDO
            receivables_paid_query = db.query(func.sum(AccountReceivable.paid_amount)).filter(
                AccountReceivable.company_id == company_id,
                AccountReceivable.status.in_(['paid', 'received'])
            )
            # Filtrar por data de pagamento se especificado
            if start_date:
                receivables_paid_query = receivables_paid_query.filter(AccountReceivable.paid_date >= start_date)
            if end_date:
                receivables_paid_query = receivables_paid_query.filter(AccountReceivable.paid_date <= end_date)
            receivables_paid = receivables_paid_query.scalar() or 0
            total_received_revenue = float(receivables_paid) + ml_received_revenue
            
            # 4. QUANTIDADE DE VENDAS
            total_sales_count = 0
            total_sales_value = 0.0
            
            if account_ids:
                sales_orders_query = db.query(MLOrder).filter(
                    MLOrder.company_id == company_id,
                    MLOrder.ml_account_id.in_(account_ids),
                    MLOrder.status.in_([OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DELIVERED])
                )
                # Filtrar por data se especificado
                if start_date:
                    sales_orders_query = sales_orders_query.filter(MLOrder.date_created >= start_date)
                if end_date:
                    sales_orders_query = sales_orders_query.filter(MLOrder.date_created <= end_date)
                sales_orders = sales_orders_query.all()
                
                total_sales_count = len(sales_orders)
                total_sales_value = sum(float(order.total_amount or 0) for order in sales_orders)
            
            # 5. VALOR FATURADO
            if account_ids:
                invoiced_orders_query = db.query(func.sum(MLOrder.total_amount)).filter(
                    MLOrder.company_id == company_id,
                    MLOrder.ml_account_id.in_(account_ids),
                    MLOrder.invoice_emitted == True
                )
                # Filtrar por data se especificado
                if start_date:
                    invoiced_orders_query = invoiced_orders_query.filter(MLOrder.date_created >= start_date)
                if end_date:
                    invoiced_orders_query = invoiced_orders_query.filter(MLOrder.date_created <= end_date)
                invoiced_orders = invoiced_orders_query.scalar() or 0
            else:
                invoiced_orders = 0
            
            # 6. PERGUNTAS ABERTAS
            unanswered_questions = db.query(func.count(MLQuestion.id)).filter(
                MLQuestion.company_id == company_id,
                MLQuestion.status == MLQuestionStatus.UNANSWERED
            ).scalar() or 0
            
            return {
                "success": True,
                "financial": {
                    "receivables_pending": round(total_receivables_pending, 2),
                    "payables_pending": round(float(payables_pending), 2),
                    "received_revenue": round(total_received_revenue, 2),
                    "invoiced_amount": round(float(invoiced_orders), 2)
                },
                "sales": {
                    "total_orders": total_sales_count,
                    "total_sales_value": round(total_sales_value, 2)
                },
                "support": {
                    "unanswered_questions": unanswered_questions
                }
            }
        except Exception as e:
            logger.error(f"Erro ao buscar dados do dashboard: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "financial": {
                    "receivables_pending": 0,
                    "payables_pending": 0,
                    "received_revenue": 0,
                    "invoiced_amount": 0
                },
                "sales": {
                    "total_orders": 0,
                    "total_sales_value": 0
                },
                "support": {
                    "unanswered_questions": 0
                }
            }
    
    def redirect_to_login(self, state: str = None) -> dict:
        """Redireciona para o login do Mercado Livre"""
        from app.config.settings import settings
        
        # Gerar state se não fornecido
        if not state:
            state = self._generate_session_token()
        
        # URL de autorização do ML
        auth_url = (
            f"{settings.ml_auth_url}?"
            f"client_id={settings.ml_app_id}&"
            f"response_type=code&"
            f"redirect_uri={settings.ml_redirect_uri}&"
            f"state={state}"
        )
        
        return {"auth_url": auth_url, "state": state}
    
    async def handle_callback(self, code: str = None, error: str = None, state: str = None) -> dict:
        """Processa callback do Mercado Livre"""
        if error:
            return {"error": f"Erro na autorização: {error}"}
        
        if not code:
            return {"error": "Código de autorização não fornecido"}
        
        # TODO: Implementar troca de code por token
        return {"message": "Callback processado", "code": code, "state": state}
    
    async def get_user_info(self, access_token: str = None) -> dict:
        """Obtém informações do usuário ML"""
        if not access_token:
            return {"error": "Token de acesso não fornecido"}
        
        # TODO: Implementar busca de informações do usuário
        return {"message": "Informações do usuário", "token": access_token}


def get_current_user(session_token: str = None):
    """Dependency para obter usuário atual pela sessão"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    # Obter sessão do banco
    db = next(get_db())
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        
        if "error" in result:
            raise HTTPException(status_code=401, detail=result["error"])
        
        return result["user"]
    finally:
        db.close()