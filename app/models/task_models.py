"""
Modelos para sistema de Tarefas e Atividades
"""
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base
import enum


class TaskStatus(enum.Enum):
    """Status das tarefas"""
    PENDING = "pending"          # Pendente
    IN_PROGRESS = "in_progress"   # Em Andamento
    WAITING = "waiting"           # Aguardando
    COMPLETED = "completed"      # Concluída
    CANCELLED = "cancelled"      # Cancelada


class TaskPriority(enum.Enum):
    """Prioridade das tarefas"""
    LOW = "low"          # Baixa
    MEDIUM = "medium"    # Média
    HIGH = "high"        # Alta
    URGENT = "urgent"    # Urgente


class TaskCategory(enum.Enum):
    """Categorias de tarefas"""
    VENDAS = "vendas"
    SUPORTE = "suporte"
    DESENVOLVIMENTO = "desenvolvimento"
    MARKETING = "marketing"
    FINANCEIRO = "financeiro"
    RH = "rh"
    OPERACIONAL = "operacional"
    OUTRO = "outro"


class Task(Base):
    """Modelo de Tarefa/Atividade"""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # Quem criou
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Usuário atribuído
    
    # Dados da tarefa
    title = Column(String(500), nullable=False)  # Nome/título da tarefa
    description = Column(Text)  # O que deve ser feito
    status = Column(String(20), default="pending", nullable=False, index=True)  # Status
    priority = Column(String(20), default="medium")  # Prioridade
    category = Column(String(50))  # Categoria da tarefa
    
    # Datas
    due_date = Column(Date, nullable=False, index=True)  # Data que deve ser feito
    completed_at = Column(DateTime(timezone=True), nullable=True)  # Data de conclusão
    
    # Associação opcional com produto
    product_id = Column(Integer, ForeignKey("internal_products.id"), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company")
    creator = relationship("User", foreign_keys=[created_by])
    assignee = relationship("User", foreign_keys=[assigned_to])
    product = relationship("InternalProduct", foreign_keys=[product_id])
    
    # Índices
    __table_args__ = (
        Index('ix_tasks_company_status', 'company_id', 'status'),
        Index('ix_tasks_assigned_to', 'assigned_to'),
        Index('ix_tasks_due_date', 'due_date'),
        Index('ix_tasks_category', 'category'),
    )

