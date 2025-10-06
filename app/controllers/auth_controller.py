"""
Controller de autenticação para sistema SaaS
"""
from fastapi import HTTPException, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import secrets
import string

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
    
    def get_login_page(self, error: str = None, success: str = None, session_token: str = None, db: Session = None) -> HTMLResponse:
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
                             success=success or "")
    
    def get_register_page(self, error: str = None, success: str = None, session_token: str = None, db: Session = None) -> HTMLResponse:
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
                             success=success or "")
    
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
                terms: bool, newsletter: bool = False, db: Session = None) -> dict:
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
            
            # Criar empresa
            company = Company(
                name=company_name,
                slug=company_slug,
                description=company_description or "",
                domain=company_domain if company_domain else None,  # Usar None se vazio
                status="TRIAL",
                max_ml_accounts=5,
                max_users=10,
                features={"api_access": True, "analytics": True, "reports": True},
                trial_ends_at=datetime.utcnow() + timedelta(days=14)
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
    
    def get_user_by_session(self, session_token: str, db: Session = None) -> dict:
        """Obtém usuário pela sessão"""
        try:
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


def get_current_user(session_token: str = None, db: Session = Depends(get_db)):
    """Dependency para obter usuário atual pela sessão"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    auth_controller = AuthController()
    result = auth_controller.get_user_by_session(session_token, db)
    
    if "error" in result:
        raise HTTPException(status_code=401, detail=result["error"])
    
    return result["user"]