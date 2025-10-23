"""
Modelos para Planejamento Financeiro
"""
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base

class FinancialPlanning(Base):
    """Planejamento financeiro anual"""
    __tablename__ = "financial_planning"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, index=True)
    year = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relacionamentos
    monthly_plans = relationship("MonthlyPlanning", back_populates="planning", cascade="all, delete-orphan")

class MonthlyPlanning(Base):
    """Planejamento mensal"""
    __tablename__ = "monthly_planning"
    
    id = Column(Integer, primary_key=True, index=True)
    planning_id = Column(Integer, ForeignKey("financial_planning.id"), nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    year = Column(Integer, nullable=False)
    
    # Faturamento esperado
    expected_revenue = Column(Numeric(15, 2), default=0)
    
    # Margem esperada (%)
    expected_margin_percent = Column(Numeric(5, 2), default=0)
    
    # Margem esperada (valor)
    expected_margin_value = Column(Numeric(15, 2), default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relacionamentos
    planning = relationship("FinancialPlanning", back_populates="monthly_plans")
    cost_center_plans = relationship("CostCenterPlanning", back_populates="monthly_planning", cascade="all, delete-orphan")

class CostCenterPlanning(Base):
    """Planejamento por centro de custo"""
    __tablename__ = "cost_center_planning"
    
    id = Column(Integer, primary_key=True, index=True)
    monthly_planning_id = Column(Integer, ForeignKey("monthly_planning.id"), nullable=False)
    cost_center_id = Column(Integer, ForeignKey("cost_centers.id"), nullable=False)
    
    # Valor máximo de gasto
    max_spending = Column(Numeric(15, 2), default=0)
    
    # Observações
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relacionamentos
    monthly_planning = relationship("MonthlyPlanning", back_populates="cost_center_plans")
    cost_center = relationship("CostCenter", backref="planning")
    category_plans = relationship("CategoryPlanning", back_populates="cost_center_planning", cascade="all, delete-orphan")

class CategoryPlanning(Base):
    """Planejamento por categoria dentro do centro de custo"""
    __tablename__ = "category_planning"
    
    id = Column(Integer, primary_key=True, index=True)
    cost_center_planning_id = Column(Integer, ForeignKey("cost_center_planning.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("financial_categories.id"), nullable=False)
    
    # Valor máximo de gasto para esta categoria
    max_spending = Column(Numeric(15, 2), default=0)
    
    # Observações
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relacionamentos
    cost_center_planning = relationship("CostCenterPlanning", back_populates="category_plans")
    category = relationship("FinancialCategory", backref="planning")
