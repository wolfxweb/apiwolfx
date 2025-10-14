"""
Modelos do banco de dados usando SQLAlchemy
"""
from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base

# NOTA: Modelos User e Token movidos para app.models.saas_models

class Product(Base):
    """Modelo de produto"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    ml_item_id = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    price = Column(Numeric(10, 2))
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
