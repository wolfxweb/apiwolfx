"""
Serviço para gerenciar operações do banco de dados
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.database_models import Product, Category, ApiLog
from app.models.saas_models import User, Token
from app.models.mercadolibre_models import MLUser, MLToken, MLItem
from typing import Optional, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    """Serviço para operações do banco de dados"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # === USUÁRIOS ===
    def create_or_update_user(self, ml_user: MLUser) -> User:
        """Cria ou atualiza usuário no banco"""
        try:
            # Buscar usuário existente
            user = self.db.query(User).filter(User.ml_user_id == str(ml_user.id)).first()
            
            if user:
                # Atualizar dados
                user.nickname = ml_user.nickname
                user.email = ml_user.email
                user.first_name = ml_user.first_name
                user.last_name = ml_user.last_name
                user.country_id = ml_user.country_id
                user.site_id = ml_user.site_id
                user.permalink = ml_user.permalink
                user.updated_at = datetime.utcnow()
            else:
                # Criar novo usuário
                user = User(
                    ml_user_id=str(ml_user.id),
                    nickname=ml_user.nickname,
                    email=ml_user.email,
                    first_name=ml_user.first_name,
                    last_name=ml_user.last_name,
                    country_id=ml_user.country_id,
                    site_id=ml_user.site_id,
                    permalink=ml_user.permalink
                )
                self.db.add(user)
            
            self.db.commit()
            self.db.refresh(user)
            return user
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Erro de integridade ao criar/atualizar usuário: {e}")
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar/atualizar usuário: {e}")
            raise
    
    def get_user_by_ml_id(self, ml_user_id: str) -> Optional[User]:
        """Busca usuário por ID do Mercado Livre"""
        return self.db.query(User).filter(User.ml_user_id == ml_user_id).first()
    
    # === TOKENS ===
    def save_token(self, user_id: int, ml_token: MLToken) -> Token:
        """Salva token no banco"""
        try:
            # Desativar tokens anteriores
            self.db.query(Token).filter(
                Token.user_id == user_id,
                Token.is_active == True
            ).update({"is_active": False})
            
            # Calcular data de expiração
            expires_at = datetime.utcnow() + timedelta(seconds=ml_token.expires_in)
            
            # Criar novo token
            token = Token(
                user_id=user_id,
                access_token=ml_token.access_token,
                refresh_token=getattr(ml_token, 'refresh_token', None),
                token_type=ml_token.token_type,
                expires_in=ml_token.expires_in,
                scope=ml_token.scope,
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
    
    def get_active_token(self, user_id: int) -> Optional[Token]:
        """Busca token ativo do usuário"""
        return self.db.query(Token).filter(
            Token.user_id == user_id,
            Token.is_active == True,
            Token.expires_at > datetime.utcnow()
        ).first()
    
    def deactivate_token(self, token_id: int):
        """Desativa token"""
        self.db.query(Token).filter(Token.id == token_id).update({"is_active": False})
        self.db.commit()
    
    # === PRODUTOS ===
    def save_product(self, user_id: int, ml_item: MLItem) -> Product:
        """Salva produto no banco"""
        try:
            # Buscar produto existente
            product = self.db.query(Product).filter(
                Product.ml_item_id == ml_item.id
            ).first()
            
            if product:
                # Atualizar dados
                product.title = ml_item.title
                product.price = ml_item.price
                product.currency_id = ml_item.currency_id
                product.condition = ml_item.condition
                product.permalink = ml_item.permalink
                product.thumbnail = ml_item.thumbnail
                product.status = ml_item.status
                product.updated_at = datetime.utcnow()
            else:
                # Criar novo produto
                product = Product(
                    ml_item_id=ml_item.id,
                    user_id=user_id,
                    title=ml_item.title,
                    price=ml_item.price,
                    currency_id=ml_item.currency_id,
                    condition=ml_item.condition,
                    permalink=ml_item.permalink,
                    thumbnail=ml_item.thumbnail,
                    status=ml_item.status
                )
                self.db.add(product)
            
            self.db.commit()
            self.db.refresh(product)
            return product
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao salvar produto: {e}")
            raise
    
    def get_user_products(self, user_id: int, limit: int = 50) -> List[Product]:
        """Busca produtos do usuário"""
        return self.db.query(Product).filter(
            Product.user_id == user_id
        ).limit(limit).all()
    
    # === CATEGORIAS ===
    def save_category(self, ml_category_id: str, name: str, parent_id: str = None) -> Category:
        """Salva categoria no banco"""
        try:
            category = self.db.query(Category).filter(
                Category.ml_category_id == ml_category_id
            ).first()
            
            if category:
                category.name = name
                category.parent_id = parent_id
                category.updated_at = datetime.utcnow()
            else:
                category = Category(
                    ml_category_id=ml_category_id,
                    name=name,
                    parent_id=parent_id
                )
                self.db.add(category)
            
            self.db.commit()
            self.db.refresh(category)
            return category
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao salvar categoria: {e}")
            raise
    
    def get_categories(self, limit: int = 100) -> List[Category]:
        """Busca categorias"""
        return self.db.query(Category).limit(limit).all()
    
    # === LOGS ===
    def log_api_call(self, user_id: int = None, endpoint: str = None, 
                     method: str = None, status_code: int = None,
                     response_time_ms: int = None, ip_address: str = None,
                     user_agent: str = None):
        """Registra log da API"""
        try:
            log = ApiLog(
                user_id=user_id,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time_ms=response_time_ms,
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db.add(log)
            self.db.commit()
        except Exception as e:
            logger.error(f"Erro ao registrar log: {e}")
    
    def get_api_stats(self, days: int = 7) -> dict:
        """Busca estatísticas da API"""
        from datetime import datetime, timedelta
        start_date = datetime.utcnow() - timedelta(days=days)
        
        total_calls = self.db.query(ApiLog).filter(
            ApiLog.created_at >= start_date
        ).count()
        
        unique_users = self.db.query(ApiLog.user_id).filter(
            ApiLog.created_at >= start_date,
            ApiLog.user_id.isnot(None)
        ).distinct().count()
        
        avg_response_time = self.db.query(func.avg(ApiLog.response_time_ms)).filter(
            ApiLog.created_at >= start_date,
            ApiLog.response_time_ms.isnot(None)
        ).scalar() or 0
        
        return {
            "total_calls": total_calls,
            "unique_users": unique_users,
            "avg_response_time_ms": round(avg_response_time, 2)
        }
