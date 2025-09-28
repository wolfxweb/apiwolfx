"""
Modelos do banco de dados usando SQLAlchemy
"""
from sqlalchemy import Column, Integer, String, Text, Decimal, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base

class User(Base):
    """Modelo de usuário"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    ml_user_id = Column(String(50), unique=True, nullable=False, index=True)
    nickname = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    country_id = Column(String(10))
    site_id = Column(String(10))
    permalink = Column(String(255))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    tokens = relationship("Token", back_populates="user", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="user", cascade="all, delete-orphan")

class Token(Base):
    """Modelo de token de acesso"""
    __tablename__ = "tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    token_type = Column(String(50), default="bearer")
    expires_in = Column(Integer)
    scope = Column(Text)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, index=True)
    is_active = Column(Boolean, default=True, index=True)
    
    # Relacionamentos
    user = relationship("User", back_populates="tokens")

class Product(Base):
    """Modelo de produto"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    ml_item_id = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    price = Column(Decimal(10, 2))
    currency_id = Column(String(10))
    condition = Column(String(50))
    permalink = Column(String(500))
    thumbnail = Column(String(500))
    status = Column(String(50), index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    user = relationship("User", back_populates="products")

class Category(Base):
    """Modelo de categoria"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    ml_category_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    parent_id = Column(String(50), index=True)
    path_from_root = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class ApiLog(Base):
    """Modelo de log da API"""
    __tablename__ = "api_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    endpoint = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer)
    response_time_ms = Column(Integer)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=func.now(), index=True)
    
    # Relacionamentos
    user = relationship("User")
