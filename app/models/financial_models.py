"""
Modelos SQLAlchemy para o módulo financeiro
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, ForeignKey, Enum, Numeric, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base
import enum

class AccountType(enum.Enum):
    """Tipos de conta bancária"""
    checking = "checking"
    savings = "savings"
    investment = "investment"
    credit = "credit"

class CategoryType(enum.Enum):
    """Tipos de categoria financeira"""
    revenue = "revenue"
    expense = "expense"
    investment = "investment"
    transfer = "transfer"

class PaymentStatus(enum.Enum):
    """Status de pagamento"""
    pending = "pending"
    paid = "paid"
    overdue = "overdue"
    cancelled = "cancelled"

class TransactionType(enum.Enum):
    """Tipos de transação"""
    income = "income"
    expense = "expense"
    transfer = "transfer"

class FinancialTransactionType(enum.Enum):
    """Tipos de transação financeira"""
    credit = "credit"
    debit = "debit"

class RecurringFrequency(enum.Enum):
    """Frequência de recorrência"""
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"

# =====================================================
# MODELOS FINANCEIROS
# =====================================================

class FinancialAccount(Base):
    """Contas Bancárias"""
    __tablename__ = "financial_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Dados bancários (apenas colunas que existem no banco)
    bank_name = Column(String(255), nullable=False)
    account_name = Column(String(255), nullable=False)
    account_type = Column(String(50), nullable=False)  # Não é enum no banco
    agency = Column(String(50))
    account_number = Column(String(50))
    
    # Informações financeiras
    initial_balance = Column(Numeric(15, 2), default=0)
    current_balance = Column(Numeric(15, 2), default=0)
    
    # Configurações
    description = Column(Text)
    is_active = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="financial_accounts")
    transactions = relationship("FinancialTransaction", back_populates="account")
    
    __table_args__ = (
        Index('ix_financial_accounts_company_active', 'company_id', 'is_active'),
    )

class FinancialCategory(Base):
    """Categorias Financeiras"""
    __tablename__ = "financial_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Dados da categoria
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(Enum(CategoryType), nullable=False)
    description = Column(Text)
    
    # Configurações
    monthly_limit = Column(Numeric(15, 2))
    is_active = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="financial_categories")
    
    __table_args__ = (
        Index('ix_financial_categories_company_type', 'company_id', 'type'),
    )

class CostCenter(Base):
    """Centros de Custo"""
    __tablename__ = "cost_centers"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Dados do centro de custo (apenas colunas que existem no banco)
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="cost_centers")
    
    __table_args__ = (
        Index('ix_cost_centers_company_active', 'company_id', 'is_active'),
    )

class FinancialCustomer(Base):
    """Clientes Financeiros"""
    __tablename__ = "financial_customers"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Dados do cliente
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    document = Column(String(50))  # CPF/CNPJ
    
    # Endereço
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    
    # Configurações
    is_active = Column(Boolean, default=True, index=True)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="financial_customers")
    
    __table_args__ = (
        Index('ix_financial_customers_company_active', 'company_id', 'is_active'),
    )

class AccountReceivable(Base):
    """Contas a Receber"""
    __tablename__ = "accounts_receivable"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Relacionamentos (apenas colunas que existem no banco)
    customer_name = Column(String(255))  # Campo texto livre (não é FK)
    category_id = Column(Integer)
    cost_center_id = Column(Integer)
    account_id = Column(Integer)
    
    # Dados da conta
    invoice_number = Column(String(100))
    description = Column(Text, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    
    # Pagamento
    paid_date = Column(Date)
    paid_amount = Column(Numeric(15, 2))
    status = Column(String(50), default="pending", index=True)
    
    # Parcelamento
    installment_number = Column(Integer)
    total_installments = Column(Integer)
    parent_receivable_id = Column(Integer, ForeignKey("accounts_receivable.id"))
    
    # Recorrência
    is_recurring = Column(Boolean, default=False)
    recurring_frequency = Column(String(50))
    recurring_end_date = Column(Date)
    
    # Observações
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="accounts_receivable")
    parent = relationship("AccountReceivable", remote_side=[id])
    installments = relationship("AccountReceivable", overlaps="parent")
    
    __table_args__ = (
        Index('ix_accounts_receivable_company_status', 'company_id', 'status'),
        Index('ix_accounts_receivable_due_date', 'due_date'),
        Index('ix_accounts_receivable_customer', 'customer_name'),
    )

class AccountPayable(Base):
    """Contas a Pagar"""
    __tablename__ = "accounts_payable"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Relacionamentos (apenas colunas que existem no banco)
    supplier_name = Column(String(255))  # Campo texto livre (não é FK)
    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id"), nullable=True, index=True)  # FK para fornecedores
    ordem_compra_id = Column(Integer, ForeignKey("ordem_compra.id"), nullable=True, index=True)  # FK para ordens de compra
    category_id = Column(Integer)
    cost_center_id = Column(Integer)
    account_id = Column(Integer)
    payment_method_id = Column(Integer)
    
    # Dados da conta
    invoice_number = Column(String(100))
    description = Column(Text, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    
    # Pagamento
    paid_date = Column(Date)
    paid_amount = Column(Numeric(15, 2))
    status = Column(String(50), default="pending", index=True)
    
    # Parcelamento
    installment_number = Column(Integer)
    total_installments = Column(Integer)
    parent_payable_id = Column(Integer, ForeignKey("accounts_payable.id"))
    
    # Recorrência
    is_recurring = Column(Boolean, default=False)
    recurring_frequency = Column(String(50))
    recurring_end_date = Column(Date)
    
    # Tipo de custo
    is_fixed = Column(Boolean, default=False, index=True)
    
    # Observações
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="accounts_payable")
    fornecedor = relationship("Fornecedor", back_populates="accounts_payable")
    
    __table_args__ = (
        Index('ix_accounts_payable_company_status', 'company_id', 'status'),
        Index('ix_accounts_payable_due_date', 'due_date'),
        Index('ix_accounts_payable_supplier', 'supplier_name'),
    )

class FinancialSupplier(Base):
    """Fornecedores Financeiros"""
    __tablename__ = "financial_suppliers"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Dados do fornecedor
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    document = Column(String(50))  # CPF/CNPJ
    
    # Endereço
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    
    # Configurações
    is_active = Column(Boolean, default=True, index=True)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="financial_suppliers")
    
    __table_args__ = (
        Index('ix_financial_suppliers_company_active', 'company_id', 'is_active'),
    )

class FinancialTransaction(Base):
    """Transações Financeiras"""
    __tablename__ = "financial_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Dados da transação
    description = Column(Text, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    transaction_date = Column(Date, nullable=False)
    transaction_type = Column(String(50), nullable=False)  # Usar varchar como no banco
    
    # Relacionamentos (apenas colunas que existem no banco)
    account_id = Column(Integer, ForeignKey("financial_accounts.id"))
    category_id = Column(Integer, ForeignKey("financial_categories.id"))
    cost_center_id = Column(Integer, ForeignKey("cost_centers.id"))
    customer_id = Column(Integer, ForeignKey("financial_customers.id"))
    supplier_id = Column(Integer, ForeignKey("financial_suppliers.id"))
    payment_method_id = Column(Integer)
    
    # Referências
    reference_id = Column(String(100))  # Mudança para String para suportar IDs do ML
    reference_type = Column(String(50))
    
    # Observações
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="financial_transactions")
    account = relationship("FinancialAccount")
    category = relationship("FinancialCategory")
    cost_center = relationship("CostCenter")
    customer = relationship("FinancialCustomer")
    supplier = relationship("FinancialSupplier")
    
    __table_args__ = (
        Index('ix_financial_transactions_company_date', 'company_id', 'transaction_date'),
        Index('ix_financial_transactions_type', 'transaction_type'),
    )

class FinancialGoal(Base):
    """Metas Financeiras"""
    __tablename__ = "financial_goals"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Dados da meta
    name = Column(String(255), nullable=False)
    description = Column(Text)
    target_amount = Column(Numeric(15, 2), nullable=False)
    current_amount = Column(Numeric(15, 2), default=0)
    
    # Período
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Configurações
    is_active = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="financial_goals")
    
    __table_args__ = (
        Index('ix_financial_goals_company_active', 'company_id', 'is_active'),
    )

class FinancialAlert(Base):
    """Alertas Financeiros"""
    __tablename__ = "financial_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Dados do alerta
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=False)  # info, warning, error
    
    # Configurações
    is_read = Column(Boolean, default=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="financial_alerts")
    
    __table_args__ = (
        Index('ix_financial_alerts_company_active', 'company_id', 'is_active'),
        Index('ix_financial_alerts_read', 'is_read'),
    )

