"""
Modelos de Recursos Humanos (RH)
"""
from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, Date, ForeignKey, Enum, JSON, Index, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base
import enum
import logging

logger = logging.getLogger(__name__)


class EmployeeStatus(enum.Enum):
    """Status do funcionário"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"  # Afastado
    TERMINATED = "terminated"  # Demitido


class ContractType(enum.Enum):
    """Tipo de contrato"""
    CLT = "clt"
    PJ = "pj"
    ESTAGIO = "estagio"
    TEMPORARIO = "temporario"


class PayrollStatus(enum.Enum):
    """Status da folha de pagamento"""
    DRAFT = "draft"  # Rascunho
    PROCESSED = "processed"  # Processada
    PAID = "paid"  # Paga


class VacationStatus(enum.Enum):
    """Status das férias"""
    SCHEDULED = "scheduled"  # Agendada
    IN_PROGRESS = "in_progress"  # Em andamento
    COMPLETED = "completed"  # Concluída


class BenefitType(enum.Enum):
    """Tipo de benefício"""
    VALE_TRANSPORTE = "vale_transporte"
    VALE_REFEICAO = "vale_refeicao"
    VALE_ALIMENTACAO = "vale_alimentacao"
    PLANO_SAUDE = "plano_saude"
    PLANO_ODONTO = "plano_odonto"
    OUTRO = "outro"


class Employee(Base):
    """Modelo de Funcionário"""
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Opcional - se vinculado a usuário do sistema
    
    # Dados pessoais
    cpf = Column(String(14), nullable=False, index=True)
    rg = Column(String(20))
    nome_completo = Column(String(255), nullable=False)
    data_nascimento = Column(Date)
    telefone = Column(String(20))
    email = Column(String(255), index=True)
    endereco = Column(Text)
    cidade = Column(String(100))
    estado = Column(String(2))
    cep = Column(String(10))
    
    # Dados profissionais
    cargo = Column(String(100))
    departamento = Column(String(100))
    data_admissao = Column(Date, nullable=False, index=True)
    data_demissao = Column(Date, nullable=True)
    status = Column(String(20), default=EmployeeStatus.ACTIVE.value, nullable=False, index=True)
    
    # Dados contratuais
    salario_base = Column(Numeric(10, 2), nullable=False)
    tipo_contrato = Column(String(20), default=ContractType.CLT.value)
    carga_horaria = Column(Integer, default=220)  # Horas mensais padrão
    
    # Integração Financeira
    financial_category_id = Column(Integer, ForeignKey("financial_categories.id"), nullable=True, index=True)
    cost_center_id = Column(Integer, ForeignKey("cost_centers.id"), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company")
    user = relationship("User", foreign_keys=[user_id])
    financial_category = relationship("FinancialCategory")
    cost_center = relationship("CostCenter")
    payrolls = relationship("Payroll", back_populates="employee", cascade="all, delete-orphan")
    vacations = relationship("EmployeeVacation", back_populates="employee", cascade="all, delete-orphan")
    benefits = relationship("EmployeeBenefit", back_populates="employee", cascade="all, delete-orphan")
    permissions = relationship("EmployeePermission", back_populates="employee", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_employees_company_cpf', 'company_id', 'cpf', unique=True),
        Index('ix_employees_company_status', 'company_id', 'status'),
    )


class Payroll(Base):
    """Modelo de Folha de Pagamento"""
    __tablename__ = "payroll"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Período de referência
    mes_referencia = Column(Integer, nullable=False)  # 1-12
    ano_referencia = Column(Integer, nullable=False, index=True)
    
    # Valores
    salario_bruto = Column(Numeric(10, 2), nullable=False)
    descontos = Column(Numeric(10, 2), default=0)
    adicionais = Column(Numeric(10, 2), default=0)
    
    # Cálculos automáticos
    inss = Column(Numeric(10, 2), default=0)
    irrf = Column(Numeric(10, 2), default=0)
    fgts = Column(Numeric(10, 2), default=0)
    
    # Total líquido
    salario_liquido = Column(Numeric(10, 2), nullable=False)
    
    # Status
    status = Column(String(20), default=PayrollStatus.DRAFT.value, nullable=False, index=True)
    
    # Observações
    observacoes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relacionamentos
    employee = relationship("Employee", back_populates="payrolls")
    company = relationship("Company")
    items = relationship("PayrollItem", back_populates="payroll", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_payroll_employee_period', 'employee_id', 'mes_referencia', 'ano_referencia', unique=True),
        Index('ix_payroll_company_period', 'company_id', 'mes_referencia', 'ano_referencia'),
    )


class PayrollItem(Base):
    """Itens da Folha de Pagamento (descontos e adicionais)"""
    __tablename__ = "payroll_items"
    
    id = Column(Integer, primary_key=True, index=True)
    payroll_id = Column(Integer, ForeignKey("payroll.id"), nullable=False, index=True)
    
    # Tipo de item
    tipo = Column(String(20), nullable=False)  # 'desconto' ou 'adicional'
    descricao = Column(String(255), nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    
    # Código de referência (para INSS, IRRF, etc.)
    codigo_referencia = Column(String(50))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamentos
    payroll = relationship("Payroll", back_populates="items")
    
    __table_args__ = (
        Index('ix_payroll_items_payroll', 'payroll_id'),
    )


class EmployeeVacation(Base):
    """Modelo de Férias do Funcionário"""
    __tablename__ = "employee_vacations"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    
    # Período aquisitivo
    periodo_aquisitivo_inicio = Column(Date, nullable=False)
    periodo_aquisitivo_fim = Column(Date, nullable=False)
    
    # Período de gozo
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=False)
    dias = Column(Integer, nullable=False, default=30)
    
    # Status
    status = Column(String(20), default=VacationStatus.SCHEDULED.value, nullable=False, index=True)
    
    # Observações
    observacoes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    employee = relationship("Employee", back_populates="vacations")
    
    __table_args__ = (
        Index('ix_employee_vacations_employee', 'employee_id'),
        Index('ix_employee_vacations_status', 'status'),
    )


class EmployeeBenefit(Base):
    """Modelo de Benefícios do Funcionário"""
    __tablename__ = "employee_benefits"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    
    # Tipo e descrição
    tipo_beneficio = Column(String(50), nullable=False, index=True)
    descricao = Column(String(255), nullable=False)
    
    # Valores e período
    valor = Column(Numeric(10, 2), nullable=False)
    data_inicio = Column(Date, nullable=False, index=True)
    data_fim = Column(Date, nullable=True)
    
    # Status
    status = Column(String(20), default="active", nullable=False, index=True)  # active, inactive
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    employee = relationship("Employee", back_populates="benefits")
    
    __table_args__ = (
        Index('ix_employee_benefits_employee', 'employee_id'),
        Index('ix_employee_benefits_status', 'status'),
    )


class EmployeePermission(Base):
    """Permissões Individuais de Acesso aos Menus"""
    __tablename__ = "employee_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Menu e submenu
    menu_name = Column(String(50), nullable=False, index=True)  # ex: 'cadastros', 'ml', 'financeiro'
    submenu_name = Column(String(50), nullable=True, index=True)  # ex: 'produtos', 'estoque', 'dashboard'
    
    # Permissão
    has_access = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    employee = relationship("Employee", back_populates="permissions")
    company = relationship("Company")
    
    __table_args__ = (
        Index('ix_employee_permissions_employee_menu', 'employee_id', 'menu_name', 'submenu_name', unique=True),
        Index('ix_employee_permissions_company', 'company_id'),
    )

