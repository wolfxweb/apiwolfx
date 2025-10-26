"""
Modelos SaaS Multi-tenant para API Mercado Livre
"""
from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, Date, ForeignKey, Enum, JSON, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base
import enum

class CompanyStatus(enum.Enum):
    """Status da empresa"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    TRIAL = "trial"

# SuperAdminRole enum removido - usando strings simples

class UserRole(enum.Enum):
    """Roles de usuário"""
    SUPER_ADMIN = "super_admin"        # Acesso total ao sistema
    COMPANY_ADMIN = "company_admin"    # Admin da empresa
    MANAGER = "manager"                # Gerente de contas ML
    ANALYST = "analyst"                # Analista de dados
    VIEWER = "viewer"                  # Apenas visualização

class MLAccountStatus(enum.Enum):
    """Status da conta do Mercado Livre"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    ERROR = "error"

class Company(Base):
    """Modelo de Empresa (Tenant)"""
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    domain = Column(String(255), unique=True, index=True)
    logo_url = Column(String(500))
    status = Column(Enum(CompanyStatus), default=CompanyStatus.TRIAL, index=True)
    
    # Configurações
    features = Column(JSON)  # Features habilitadas
    ml_orders_as_receivables = Column(Boolean, default=True)  # Considerar pedidos ML como contas a receber
    
    # Plano e Limites
    plan_expires_at = Column(DateTime)  # Data de vencimento do plano
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    trial_ends_at = Column(DateTime)
    
    # Campos de identificação da empresa
    razao_social = Column(String(255))
    nome_fantasia = Column(String(255))
    cnpj = Column(String(20))
    inscricao_estadual = Column(String(50))
    inscricao_municipal = Column(String(50))
    regime_tributario = Column(String(50))
    
    # Campos de endereço
    cep = Column(String(10))
    endereco = Column(String(255))
    numero = Column(String(20))
    complemento = Column(String(100))
    bairro = Column(String(100))
    cidade = Column(String(100))
    estado = Column(String(2))
    pais = Column(String(100))
    
    # Campos de impostos
    aliquota_simples = Column(Numeric(5, 2))
    faturamento_anual = Column(Numeric(15, 2))
    aliquota_ir = Column(Numeric(5, 2))
    aliquota_csll = Column(Numeric(5, 2))
    aliquota_pis = Column(Numeric(5, 2))
    aliquota_cofins = Column(Numeric(5, 2))
    aliquota_icms = Column(Numeric(5, 2))
    aliquota_iss = Column(Numeric(5, 2))
    aliquota_ir_real = Column(Numeric(5, 2))
    aliquota_csll_real = Column(Numeric(5, 2))
    aliquota_pis_real = Column(Numeric(5, 2))
    aliquota_cofins_real = Column(Numeric(5, 2))
    aliquota_icms_real = Column(Numeric(5, 2))
    aliquota_iss_real = Column(Numeric(5, 2))
    
    # Campos de marketing e custos
    percentual_marketing = Column(Numeric(5, 2))  # Percentual de marketing sobre receita
    custo_adicional_por_pedido = Column(Numeric(10, 2))  # Custo adicional por pedido em R$
    
    # Relacionamentos
    users = relationship("User", back_populates="company", cascade="all, delete-orphan")
    ml_accounts = relationship("MLAccount", back_populates="company", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="company", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="company", cascade="all, delete-orphan")
    internal_products = relationship("InternalProduct", back_populates="company", cascade="all, delete-orphan")
    
    # Relacionamentos Financeiros
    financial_accounts = relationship("FinancialAccount", back_populates="company", cascade="all, delete-orphan")
    cost_centers = relationship("CostCenter", back_populates="company", cascade="all, delete-orphan")
    financial_categories = relationship("FinancialCategory", back_populates="company", cascade="all, delete-orphan")
    financial_customers = relationship("FinancialCustomer", back_populates="company", cascade="all, delete-orphan")
    financial_suppliers = relationship("FinancialSupplier", back_populates="company", cascade="all, delete-orphan")
    accounts_receivable = relationship("AccountReceivable", back_populates="company", cascade="all, delete-orphan")
    accounts_payable = relationship("AccountPayable", back_populates="company", cascade="all, delete-orphan")
    financial_transactions = relationship("FinancialTransaction", back_populates="company", cascade="all, delete-orphan")
    financial_goals = relationship("FinancialGoal", back_populates="company", cascade="all, delete-orphan")
    fornecedores = relationship("Fornecedor", back_populates="company", cascade="all, delete-orphan")
    ordens_compra = relationship("OrdemCompra", back_populates="company", cascade="all, delete-orphan")
    financial_alerts = relationship("FinancialAlert", back_populates="company", cascade="all, delete-orphan")

class SuperAdmin(Base):
    """Modelo de SuperAdmin para gerenciamento do sistema"""
    __tablename__ = "super_admins"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(String(50), default="company_manager", index=True)
    is_active = Column(Boolean, default=True, index=True)
    
    # Permissões específicas
    can_manage_companies = Column(Boolean, default=True)
    can_manage_plans = Column(Boolean, default=True)
    can_manage_users = Column(Boolean, default=True)
    can_view_analytics = Column(Boolean, default=True)
    can_access_system_logs = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime)
    
    # Índices
    __table_args__ = (
        Index('ix_super_admins_email_active', 'email', 'is_active'),
        Index('ix_super_admins_role_active', 'role', 'is_active'),
    )

class User(Base):
    """Modelo de Usuário (atualizado para SaaS)"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Dados pessoais
    email = Column(String(255), nullable=False, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    avatar_url = Column(String(500))
    
    # Autenticação
    password_hash = Column(String(255))
    is_active = Column(Boolean, default=True, index=True)
    last_login = Column(DateTime)
    
    # Roles e permissões
    role = Column(Enum(UserRole), default=UserRole.VIEWER, index=True)
    permissions = Column(JSON)  # Permissões específicas
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="users")
    user_ml_accounts = relationship("UserMLAccount", back_populates="user", cascade="all, delete-orphan")
    tokens = relationship("Token", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

class MLAccount(Base):
    """Modelo de Conta do Mercado Livre"""
    __tablename__ = "ml_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Dados da conta ML
    ml_user_id = Column(String(50), nullable=False, index=True)
    nickname = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    country_id = Column(String(10))
    site_id = Column(String(10))
    permalink = Column(String(255))
    
    # Status e configurações
    status = Column(Enum(MLAccountStatus), default=MLAccountStatus.ACTIVE, index=True)
    is_primary = Column(Boolean, default=False, index=True)
    settings = Column(JSON)  # Configurações específicas da conta
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_sync = Column(DateTime)
    
    # Relacionamentos
    company = relationship("Company", back_populates="ml_accounts")
    user_ml_accounts = relationship("UserMLAccount", back_populates="ml_account", cascade="all, delete-orphan")
    tokens = relationship("Token", back_populates="ml_account", cascade="all, delete-orphan")
    ml_products = relationship("MLProduct", back_populates="ml_account", cascade="all, delete-orphan")

class UserMLAccount(Base):
    """Associação entre Usuário e Conta ML (permissões)"""
    __tablename__ = "user_ml_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ml_account_id = Column(Integer, ForeignKey("ml_accounts.id"), nullable=False, index=True)
    
    # Permissões específicas para esta conta
    can_read = Column(Boolean, default=True)
    can_write = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    can_manage = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    user = relationship("User", back_populates="user_ml_accounts")
    ml_account = relationship("MLAccount", back_populates="user_ml_accounts")

class Token(Base):
    """Modelo de Token de acesso (atualizado)"""
    __tablename__ = "tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ml_account_id = Column(Integer, ForeignKey("ml_accounts.id"), nullable=False, index=True)
    
    # Token data
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    token_type = Column(String(50), default="bearer")
    expires_in = Column(Integer)
    scope = Column(Text)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    expires_at = Column(DateTime, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    last_used = Column(DateTime)
    
    # Relacionamentos
    user = relationship("User", back_populates="tokens")
    ml_account = relationship("MLAccount", back_populates="tokens")


class UserSession(Base):
    """Sessões de usuário"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Dados da sessão
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    is_active = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, index=True)
    last_activity = Column(DateTime, default=func.now())
    
    # Relacionamentos
    user = relationship("User", back_populates="sessions")

class Subscription(Base):
    """Assinaturas das empresas"""
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)  # Nullable para templates
    
    # Dados da assinatura
    plan_name = Column(String(100), nullable=False)
    description = Column(Text)  # Descrição do plano
    plan_features = Column(JSON)
    price = Column(String(50))
    promotional_price = Column(String(50))  # Preço promocional
    currency = Column(String(10), default="BRL")
    billing_cycle = Column(String(20), default="monthly")  # monthly, quarterly, yearly
    
    # Limites e recursos do plano
    max_users = Column(Integer, default=10)  # Quantidade de usuários
    max_ml_accounts = Column(Integer, default=5)  # Quantidade de contas ML
    
    # Recursos vendidos no plano
    storage_gb = Column(Integer, default=5)  # Espaço de armazenamento em GB
    ai_analysis_monthly = Column(Integer, default=10)  # Análises de IA por mês
    catalog_monitoring_slots = Column(Integer, default=5)  # Slots de monitoramento de catálogo
    product_mining_slots = Column(Integer, default=10)  # Slots de mineração de produto
    product_monitoring_slots = Column(Integer, default=20)  # Slots de monitoramento de produto
    
    trial_days = Column(Integer, default=0)  # Dias de trial gratuito
    
    # Status
    status = Column(String(50), default="active", index=True)  # active, inactive, template
    is_trial = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    starts_at = Column(DateTime, default=func.now())
    ends_at = Column(DateTime)
    trial_ends_at = Column(DateTime)
    
    # Relacionamentos
    company = relationship("Company", back_populates="subscriptions")

class MLProductStatus(enum.Enum):
    """Status do produto ML"""
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    UNDER_REVIEW = "under_review"
    INACTIVE = "inactive"

class MLProduct(Base):
    """Modelo de Produto do Mercado Livre"""
    __tablename__ = "ml_products"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    ml_account_id = Column(Integer, ForeignKey("ml_accounts.id"), nullable=False, index=True)
    
    # Identificadores ML
    ml_item_id = Column(String(50), unique=True, nullable=False, index=True)
    user_product_id = Column(String(50), index=True)  # Novo modelo User Products
    family_id = Column(String(50), index=True)        # Novo modelo User Products
    family_name = Column(String(255))                 # Novo modelo User Products
    
    # Dados básicos
    title = Column(String(500), nullable=False)
    subtitle = Column(String(500))
    description = Column(Text)  # Descrição do anúncio
    price = Column(String(50))
    base_price = Column(String(50))
    original_price = Column(String(50))
    currency_id = Column(String(10))
    
    # Quantidades
    available_quantity = Column(Integer, default=0)
    sold_quantity = Column(Integer, default=0)
    initial_quantity = Column(Integer, default=0)
    
    # Categoria e condição
    category_id = Column(String(50), index=True)
    category_name = Column(String(255))  # Nome da categoria
    condition = Column(String(50), index=True)
    listing_type_id = Column(String(50))
    buying_mode = Column(String(50))
    
    # URLs e mídia
    permalink = Column(String(500))
    thumbnail = Column(String(500))
    secure_thumbnail = Column(String(500))
    pictures = Column(JSON)  # Array de URLs das imagens
    
    # Status e timestamps ML
    status = Column(Enum(MLProductStatus), default=MLProductStatus.ACTIVE, index=True)
    sub_status = Column(JSON)  # Array de sub-status
    start_time = Column(DateTime)
    stop_time = Column(DateTime)
    end_time = Column(DateTime)
    
    # Dados do vendedor
    seller_id = Column(String(50), index=True)
    seller_custom_field = Column(String(100))  # SKU personalizado
    seller_sku = Column(String(100))           # SKU do vendedor
    
    # Produto do catálogo
    catalog_product_id = Column(String(50), index=True)
    catalog_listing = Column(Boolean, default=False)
    
    # Atributos e características
    attributes = Column(JSON)  # Atributos do produto
    variations = Column(JSON)  # Variações do produto
    tags = Column(JSON)        # Tags do produto
    
    # Garantia e termos de venda
    sale_terms = Column(JSON)   # Termos de venda (garantia, etc)
    warranty = Column(Text)     # Informações de garantia detalhadas
    
    # Mídia
    video_id = Column(String(100))  # ID do vídeo do YouTube
    
    # Qualidade e saúde do anúncio
    health = Column(JSON)       # Status de saúde do anúncio (exposição, qualidade)
    domain_id = Column(String(100), index=True)  # Domínio do produto
    
    # Envio
    shipping = Column(JSON)    # Configurações de envio
    free_shipping = Column(Boolean, default=False)
    
    # Promoções e preços
    differential_pricing = Column(JSON)
    deal_ids = Column(JSON)
    
    # Timestamps do sistema
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_sync = Column(DateTime, index=True)
    last_ml_update = Column(DateTime)  # Última atualização no ML
    
    # Relacionamentos
    company = relationship("Company")
    ml_account = relationship("MLAccount")
    sync_logs = relationship("MLProductSync", back_populates="ml_product", cascade="all, delete-orphan")
    
    # Índices compostos
    __table_args__ = (
        Index('ix_ml_products_company_account', 'company_id', 'ml_account_id'),
        Index('ix_ml_products_account_status', 'ml_account_id', 'status'),
        Index('ix_ml_products_category_status', 'category_id', 'status'),
    )

class MLProductSync(Base):
    """Log de sincronização de produtos ML"""
    __tablename__ = "ml_product_sync"
    
    id = Column(Integer, primary_key=True, index=True)
    ml_product_id = Column(Integer, ForeignKey("ml_products.id"), nullable=True, index=True)  # Nullable para logs gerais de sincronização
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    ml_account_id = Column(Integer, ForeignKey("ml_accounts.id"), nullable=False, index=True)
    
    # Tipo de sincronização
    sync_type = Column(String(50), nullable=False, index=True)  # full, incremental, manual
    sync_status = Column(String(50), nullable=False, index=True)  # success, error, partial
    
    # Dados da sincronização
    items_processed = Column(Integer, default=0)
    items_created = Column(Integer, default=0)
    items_updated = Column(Integer, default=0)
    items_errors = Column(Integer, default=0)
    
    # Detalhes
    error_message = Column(Text)
    sync_details = Column(JSON)
    
    # Timestamps
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    
    # Relacionamentos
    ml_product = relationship("MLProduct", back_populates="sync_logs")
    company = relationship("Company")
    ml_account = relationship("MLAccount")

class AIProductAnalysis(Base):
    """Análises de produtos feitas com IA"""
    __tablename__ = "ai_product_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    ml_product_id = Column(Integer, ForeignKey("ml_products.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Conteúdo da análise
    analysis_content = Column(Text, nullable=False)  # HTML da análise
    
    # Dados da solicitação
    model_used = Column(String(50), nullable=False)  # gpt-4.1-nano, gpt-5-nano, etc
    prompt_tokens = Column(Integer)  # Tokens usados no prompt/input
    completion_tokens = Column(Integer)  # Tokens usados na resposta/output
    total_tokens = Column(Integer)  # Total de tokens
    
    # Dados enviados para análise (para auditoria)
    request_data = Column(JSON)  # Dados que foram enviados
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), index=True)
    
    # Relacionamentos
    ml_product = relationship("MLProduct")
    company = relationship("Company")
    
    # Índices
    __table_args__ = (
        Index('ix_ai_analysis_product_company', 'ml_product_id', 'company_id'),
        Index('ix_ai_analysis_created', 'created_at'),
    )

class MLProductAttribute(Base):
    """Atributos específicos de produtos ML"""
    __tablename__ = "ml_product_attributes"
    
    id = Column(Integer, primary_key=True, index=True)
    ml_product_id = Column(Integer, ForeignKey("ml_products.id"), nullable=False, index=True)
    
    # Dados do atributo
    attribute_id = Column(String(100), nullable=False, index=True)
    attribute_name = Column(String(255), nullable=False)
    value_id = Column(String(100))
    value_name = Column(String(255))
    value_struct = Column(JSON)
    
    # Metadados
    attribute_group_id = Column(String(100))
    attribute_group_name = Column(String(255))
    source = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    ml_product = relationship("MLProduct")
    
    # Índices
    __table_args__ = (
        Index('ix_ml_product_attributes_product_id', 'ml_product_id'),
        Index('ix_ml_product_attributes_attribute_id', 'attribute_id'),
    )

# ApiLog removido - já definido em database_models.py

class OrderStatus(enum.Enum):
    """Status do pedido"""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"

class MLOrder(Base):
    """Modelo de Pedidos do Mercado Libre - Completo"""
    __tablename__ = "ml_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    ml_account_id = Column(Integer, ForeignKey("ml_accounts.id"), nullable=False, index=True)
    
    # === DADOS BÁSICOS DO PEDIDO ===
    ml_order_id = Column(BigInteger, unique=True, nullable=False, index=True)
    order_id = Column(String(50), nullable=False, index=True)
    
    # Status e datas
    status = Column(Enum(OrderStatus), nullable=False, index=True)
    status_detail = Column(String(100))
    date_created = Column(DateTime, index=True)
    date_closed = Column(DateTime, index=True)
    last_updated = Column(DateTime, index=True)
    
    # Valores monetários (valores diretos da API em reais, SEM conversão)
    total_amount = Column(Numeric(10, 2))  # Valor em reais (ex: 95.50)
    paid_amount = Column(Numeric(10, 2))   # Valor em reais (ex: 95.50)
    currency_id = Column(String(10))
    
    # === DADOS DO COMPRADOR ===
    buyer_id = Column(String(50), nullable=False, index=True)
    buyer_nickname = Column(String(255))
    buyer_email = Column(String(255))
    buyer_first_name = Column(String(255))
    buyer_last_name = Column(String(255))
    buyer_phone = Column(JSON)  # Dados de telefone do comprador
    
    # === DADOS DO VENDEDOR ===
    seller_id = Column(String(50), index=True)
    seller_nickname = Column(String(255))
    seller_phone = Column(JSON)  # Dados de telefone do vendedor
    
    # === PAGAMENTOS ===
    payments = Column(JSON)  # Array completo de pagamentos
    payment_method_id = Column(String(50))  # Método principal
    payment_type_id = Column(String(50))    # Tipo principal
    payment_status = Column(String(50))     # Status principal
    
    # === ENVIO E LOGÍSTICA ===
    shipping_id = Column(String(50), index=True)  # ID do envio para buscar detalhes
    shipping_cost = Column(Numeric(10, 2))  # Valor em reais (direto da API)
    shipping_method = Column(String(100))
    shipping_status = Column(String(50))
    shipping_address = Column(JSON)  # Endereço de entrega
    shipping_details = Column(JSON)  # Detalhes completos do envio
    
    # === ITENS DO PEDIDO ===
    order_items = Column(JSON)  # Lista completa de itens com detalhes
    
    # === TAXAS E COMISSÕES (valores em reais, direto da API - SEM conversão) ===
    total_fees = Column(Numeric(10, 2))      # Total de taxas em reais
    listing_fees = Column(Numeric(10, 2))    # Taxas de publicação em reais
    sale_fees = Column(Numeric(10, 2))       # Taxas de venda em reais
    shipping_fees = Column(Numeric(10, 2))   # Taxas de envio em reais
    
    # === BREAKDOWN DE COMISSÕES (Billing) ===
    financing_fee = Column(Numeric(10, 2))           # Taxa de parcelamento em reais
    financing_transfer_total = Column(Numeric(10, 2)) # Valor total pago pelo cliente em reais
    sale_fee_breakdown = Column(JSON)         # Breakdown detalhado da taxa de venda
    billing_details = Column(JSON)            # Detalhes completos de billing
    marketplace_fee_breakdown = Column(JSON)  # Breakdown das taxas do marketplace
    
    # === DESCONTOS E PROMOÇÕES ===
    discounts_applied = Column(JSON)  # Descontos aplicados (/orders/{id}/discounts)
    coupon_amount = Column(Numeric(10, 2))   # Valor do cupom em reais (direto da API)
    coupon_id = Column(String(50))    # ID do cupom
    
    # === PUBLICIDADE E ANÚNCIOS ===
    is_advertising_sale = Column(Boolean, default=False, index=True)  # Venda por anúncio
    advertising_campaign_id = Column(String(50))  # ID da campanha
    advertising_cost = Column(Numeric(10, 2))  # Custo publicitário em reais (direto da API)
    advertising_metrics = Column(JSON)  # Métricas de publicidade
    
    # === CONTEXTO DA VENDA ===
    context = Column(JSON)  # Canal, site, flows (/orders/{id})
    pack_id = Column(String(50))  # ID do pack se aplicável
    pickup_id = Column(String(50))  # ID de retirada se aplicável
    has_catalog_products = Column(Boolean, default=False, index=True)  # Se tem produtos de catálogo
    catalog_products_count = Column(Integer, default=0)  # Quantidade de produtos de catálogo
    catalog_products = Column(JSON)  # Lista de produtos de catálogo
    
    # === MEDIAÇÕES E DISPUTAS ===
    mediations = Column(JSON)  # Mediações e disputas
    order_request = Column(JSON)  # Solicitações de troca/devolução
    
    # === FEEDBACK ===
    feedback = Column(JSON)  # Feedback completo (comprador e vendedor)
    
    # === TAGS E METADADOS ===
    tags = Column(JSON)  # Tags do pedido
    fulfilled = Column(Boolean)  # Se foi cumprido
    comment = Column(Text)  # Comentário do pedido
    
    # === IMPOSTOS ===
    taxes = Column(JSON)  # Impostos aplicados
    
    # === DETALHES DE CANCELAMENTO ===
    cancel_detail = Column(JSON)  # Detalhes se cancelado
    
    # === CONTROLE DE CAIXA ===
    cash_entry_created = Column(Boolean, default=False, index=True)  # Se já foi lançado no caixa
    cash_entry_date = Column(DateTime)  # Data do lançamento no caixa
    cash_entry_amount = Column(Numeric(10, 2))  # Valor lançado no caixa
    cash_entry_account_id = Column(Integer, ForeignKey("financial_accounts.id"))  # Conta onde foi lançado
    
    # === NOTA FISCAL ===
    invoice_emitted = Column(Boolean, default=False, index=True)  # Se a NF foi emitida
    invoice_emitted_at = Column(DateTime)  # Data de emissão da NF
    invoice_number = Column(String(50))  # Número da NF
    invoice_series = Column(String(10))  # Série da NF
    invoice_key = Column(String(44))  # Chave de acesso da NF
    invoice_xml_url = Column(String(500))  # URL do XML da NF
    invoice_pdf_url = Column(String(500))  # URL do PDF da NF (DANFE)
    
    # === TIMESTAMPS ===
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # === RELACIONAMENTOS ===
    company = relationship("Company")
    ml_account = relationship("MLAccount")
    cash_entry_account = relationship("FinancialAccount")
    
    # === ÍNDICES ===
    __table_args__ = (
        Index('ix_ml_orders_company_ml_account', 'company_id', 'ml_account_id'),
        Index('ix_ml_orders_buyer_id', 'buyer_id'),
        Index('ix_ml_orders_seller_id', 'seller_id'),
        Index('ix_ml_orders_date_created', 'date_created'),
        Index('ix_ml_orders_status', 'status'),
        Index('ix_ml_orders_advertising', 'is_advertising_sale'),
        Index('ix_ml_orders_shipping_id', 'shipping_id'),
        Index('ix_ml_orders_cash_entry', 'cash_entry_created'),
    )

class CatalogParticipant(Base):
    """Modelo de Participante do Catálogo"""
    __tablename__ = "catalog_participants"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    catalog_product_id = Column(String(50), nullable=False, index=True)
    ml_item_id = Column(String(50), nullable=False, unique=True, index=True)
    seller_id = Column(String(50), nullable=False, index=True)
    
    # Informações do produto
    title = Column(String(500), nullable=False)
    price = Column(Integer, nullable=False)  # Em centavos
    currency_id = Column(String(10), default="BRL")
    status = Column(String(20), default="active")
    
    # Quantidades
    available_quantity = Column(Integer, default=0)
    sold_quantity = Column(Integer, default=0)
    
    # URLs e mídia
    permalink = Column(String(500))
    thumbnail = Column(String(500))
    
    # Detalhes do produto
    condition = Column(String(20), default="new")
    listing_type_id = Column(String(50))
    official_store_id = Column(String(50))
    accepts_mercadopago = Column(Boolean, default=False)
    original_price = Column(Integer)  # Em centavos
    category_id = Column(String(50))
    logistic_type = Column(String(50), default="default")
    buy_box_winner = Column(Boolean, default=False)
    
    # Informações detalhadas do vendedor
    seller_name = Column(String(255))
    seller_nickname = Column(String(255))
    seller_country = Column(String(10))
    seller_city = Column(String(100))
    seller_state = Column(String(100))
    seller_registration_date = Column(String(50))
    seller_experience = Column(String(50))
    seller_power_seller = Column(Boolean, default=False)
    seller_power_seller_status = Column(String(50))
    seller_reputation_level = Column(String(20))
    seller_transactions_total = Column(Integer, default=0)
    seller_ratings_positive = Column(Integer, default=0)
    seller_ratings_negative = Column(Integer, default=0)
    seller_ratings_neutral = Column(Integer, default=0)
    seller_mercadopago_accepted = Column(Boolean, default=False)
    seller_mercadoenvios = Column(String(50))
    seller_user_type = Column(String(50))
    seller_tags = Column(JSON)
    
    # Informações detalhadas de envio
    shipping_free = Column(Boolean, default=False)
    shipping_method = Column(String(50))
    shipping_tags = Column(JSON)
    shipping_paid_by = Column(String(50), default="Comprador")
    
    # Posição no catálogo
    position = Column(Integer, default=0)
    
    # Timestamps
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, default=func.now())
    
    # === RELACIONAMENTOS ===
    company = relationship("Company")
    
    # === ÍNDICES ===
    __table_args__ = (
        Index('ix_catalog_participants_company', 'company_id'),
        Index('ix_catalog_participants_catalog_product', 'catalog_product_id'),
        Index('ix_catalog_participants_seller', 'seller_id'),
        Index('ix_catalog_participants_price', 'price'),
        Index('ix_catalog_participants_status', 'status'),
        Index('ix_catalog_participants_last_updated', 'last_updated'),
        Index('ix_catalog_participants_company_catalog', 'company_id', 'catalog_product_id'),
    )


class Product(Base):
    """Produtos importados do Mercado Livre"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    ml_item_id = Column(String(50), nullable=False, index=True)  # ID do produto no ML
    title = Column(String(500), nullable=False)  # Nome do produto
    thumbnail = Column(String(1000))  # URL da imagem
    sku = Column(String(100), index=True)  # SKU do produto
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Campos de custos e preços (para preenchimento posterior)
    cost_price = Column(String(20))  # Preço de custo
    tax_rate = Column(String(10))  # Taxa de imposto (%)
    marketing_cost = Column(String(20))  # Custo de marketing
    other_costs = Column(String(20))  # Outros custos
    notes = Column(Text)  # Observações
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="products")
    
    # Índices
    __table_args__ = (
        Index('ix_products_company', 'company_id'),
        Index('ix_products_ml_item', 'ml_item_id'),
        Index('ix_products_sku', 'sku'),
        Index('ix_products_company_sku', 'company_id', 'sku'),
    )


class InternalProduct(Base):
    """Produtos internos/customizados criados pela empresa"""
    __tablename__ = "internal_products"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    base_product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)  # Produto base do ML (opcional)
    
    # Dados do produto interno
    name = Column(String(500), nullable=False)  # Nome customizado
    description = Column(Text)  # Descrição customizada
    internal_sku = Column(String(100), nullable=False, index=True)  # SKU interno
    barcode = Column(String(100), index=True)  # Código de barras
    
    # Preços e custos
    cost_price = Column(Numeric(10, 2))  # Preço de custo
    selling_price = Column(Numeric(10, 2))  # Preço de venda
    tax_rate = Column(Numeric(5, 2), default=0.0)  # Taxa de imposto (%)
    marketing_cost = Column(Numeric(10, 2), default=0.0)  # Custo de marketing
    other_costs = Column(Numeric(10, 2), default=0.0)  # Outros custos
    expected_profit_margin = Column(Numeric(5, 2), default=0.0)  # Margem de lucro esperada (%)
    
    # Categorização interna
    category = Column(String(100))  # Categoria interna
    brand = Column(String(100))  # Marca
    model = Column(String(100))  # Modelo
    supplier = Column(String(200))  # Fornecedor
    
    # Status e controle
    status = Column(String(50), default="active", index=True)  # active, inactive, discontinued
    is_featured = Column(Boolean, default=False)  # Produto em destaque
    min_stock = Column(Integer, default=0)  # Estoque mínimo
    current_stock = Column(Integer, default=0)  # Estoque atual
    
    # Imagens e mídia
    main_image = Column(String(1000))  # Imagem principal
    additional_images = Column(JSON)  # Array de URLs de imagens adicionais
    
    # Observações e notas
    notes = Column(Text)  # Observações gerais
    internal_notes = Column(Text)  # Notas internas
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="internal_products")
    base_product = relationship("Product", foreign_keys=[base_product_id])
    
    # Índices
    __table_args__ = (
        Index('ix_internal_products_company', 'company_id'),
        Index('ix_internal_products_base', 'base_product_id'),
        Index('ix_internal_products_sku', 'internal_sku'),
        Index('ix_internal_products_status', 'status'),
        Index('ix_internal_products_category', 'category'),
        Index('ix_internal_products_created', 'created_at'),
    )


class SKUManagement(Base):
    """Gerenciamento de SKUs para evitar duplicação"""
    __tablename__ = "sku_management"
    
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), nullable=False, index=True)  # SKU único
    platform = Column(String(50), nullable=False, default="mercadolivre")  # Plataforma (ML, Amazon, etc.)
    platform_item_id = Column(String(100), nullable=False)  # ID do item na plataforma
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)  # Produto ML
    internal_product_id = Column(Integer, ForeignKey("internal_products.id"), nullable=True)  # Produto interno
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    status = Column(String(50), default="active", index=True)  # active, inactive, archived
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company")
    product = relationship("Product", foreign_keys=[product_id])
    internal_product = relationship("InternalProduct", foreign_keys=[internal_product_id])
    
    # Índices
    __table_args__ = (
        Index('ix_sku_management_sku', 'sku'),
        Index('ix_sku_management_platform', 'platform'),
        Index('ix_sku_management_platform_item', 'platform_item_id'),
        Index('ix_sku_management_company', 'company_id'),
        Index('ix_sku_management_status', 'status'),
    )


class MLCatalogMonitoring(Base):
    """Controle de ativação do monitoramento de catálogo"""
    __tablename__ = "ml_catalog_monitoring"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    catalog_product_id = Column(String(50), nullable=False, index=True)  # ID do produto no catálogo ML
    ml_product_id = Column(Integer, ForeignKey("ml_products.id"), nullable=True, index=True)  # Produto ML da empresa (opcional)
    
    # Controle de ativação
    is_active = Column(Boolean, default=True, nullable=False, index=True)  # Se o monitoramento está ativo
    
    # Timestamps
    activated_at = Column(DateTime(timezone=True), server_default=func.now())
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    last_check_at = Column(DateTime(timezone=True), nullable=True)  # Última vez que foi verificado
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company")
    ml_product = relationship("MLProduct", foreign_keys=[ml_product_id])
    
    # Índices e constraints
    __table_args__ = (
        Index('ix_catalog_monitoring_company', 'company_id'),
        Index('ix_catalog_monitoring_catalog_product', 'catalog_product_id'),
        Index('ix_catalog_monitoring_is_active', 'is_active'),
        Index('ix_catalog_monitoring_company_catalog', 'company_id', 'catalog_product_id'),
        Index('ix_catalog_monitoring_active', 'company_id', 'is_active'),
        # Constraint: Um catálogo só pode ser monitorado uma vez por empresa
        {'extend_existing': True}
    )


class MLCatalogHistory(Base):
    """Histórico de monitoramento do catálogo do Mercado Livre"""
    __tablename__ = "ml_catalog_history"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    catalog_product_id = Column(String(50), nullable=False, index=True)  # ID do produto no catálogo ML
    ml_product_id = Column(Integer, ForeignKey("ml_products.id"), nullable=True, index=True)  # Produto ML da empresa
    monitoring_id = Column(Integer, ForeignKey("ml_catalog_monitoring.id"), nullable=True, index=True)  # Referência ao monitoramento
    
    # Dados do catálogo no momento da coleta
    total_participants = Column(Integer, default=0)  # Total de participantes/vendedores
    buy_box_winner_id = Column(String(50))  # ID do vendedor que ganhou a buy box
    buy_box_winner_price = Column(Integer)  # Preço do vencedor da buy box (em centavos)
    
    # Posição do produto da empresa
    company_position = Column(Integer)  # Posição do produto da empresa no catálogo
    company_price = Column(Integer)  # Preço do produto da empresa (em centavos)
    company_has_buy_box = Column(Boolean, default=False)  # Se a empresa ganhou a buy box
    
    # Estatísticas de preços
    min_price = Column(Integer)  # Menor preço no catálogo (em centavos)
    max_price = Column(Integer)  # Maior preço no catálogo (em centavos)
    avg_price = Column(Integer)  # Preço médio no catálogo (em centavos)
    median_price = Column(Integer)  # Preço mediano no catálogo (em centavos)
    
    # Estatísticas de quantidade
    total_available_quantity = Column(Integer, default=0)  # Total disponível no catálogo
    total_sold_quantity = Column(Integer, default=0)  # Total vendido no catálogo
    
    # Dados completos em JSON (para análises futuras)
    participants_snapshot = Column(JSON)  # Snapshot de todos os participantes
    
    # Timestamps
    collected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamentos
    company = relationship("Company")
    ml_product = relationship("MLProduct", foreign_keys=[ml_product_id])
    monitoring = relationship("MLCatalogMonitoring", foreign_keys=[monitoring_id])
    
    # Índices
    __table_args__ = (
        Index('ix_catalog_history_company', 'company_id'),
        Index('ix_catalog_history_catalog_product', 'catalog_product_id'),
        Index('ix_catalog_history_ml_product', 'ml_product_id'),
        Index('ix_catalog_history_monitoring', 'monitoring_id'),
        Index('ix_catalog_history_collected_at', 'collected_at'),
        Index('ix_catalog_history_company_catalog', 'company_id', 'catalog_product_id'),
        Index('ix_catalog_history_company_collected', 'company_id', 'collected_at'),
    )

class Fornecedor(Base):
    """Tabela de Fornecedores"""
    __tablename__ = "fornecedores"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Dados básicos
    nome = Column(String(255), nullable=False)
    nome_fantasia = Column(String(255))
    cnpj = Column(String(18), index=True)
    inscricao_estadual = Column(String(50))
    inscricao_municipal = Column(String(50))
    
    # Contato
    contato_nome = Column(String(255))
    email = Column(String(255))
    telefone = Column(String(20))
    celular = Column(String(20))
    site = Column(String(255))
    
    # Endereço
    cep = Column(String(10))
    endereco = Column(String(255))
    numero = Column(String(20))
    complemento = Column(String(100))
    bairro = Column(String(100))
    cidade = Column(String(100))
    estado = Column(String(2))
    pais = Column(String(50), default="Brasil")
    
    # Dados bancários
    banco = Column(String(100))
    agencia = Column(String(20))
    conta = Column(String(20))
    tipo_conta = Column(String(20))  # corrente, poupança, etc.
    pix = Column(String(255))
    
    # Observações
    observacoes = Column(Text)
    ativo = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="fornecedores")
    accounts_payable = relationship("AccountPayable", back_populates="fornecedor")
    ordens_compra = relationship("OrdemCompra", back_populates="fornecedor", foreign_keys="OrdemCompra.fornecedor_id")
    ordens_compra_transportadora = relationship("OrdemCompra", back_populates="transportadora", foreign_keys="OrdemCompra.transportadora_id")
    
    # Índices
    __table_args__ = (
        Index('ix_fornecedores_company_ativo', 'company_id', 'ativo'),
        Index('ix_fornecedores_cnpj', 'cnpj'),
    )

class OrdemCompra(Base):
    """Tabela de Ordens de Compra"""
    __tablename__ = "ordem_compra"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id"), nullable=True, index=True)
    transportadora_id = Column(Integer, ForeignKey("fornecedores.id"), nullable=True, index=True)
    
    # Dados da ordem
    numero_ordem = Column(String(50), nullable=False, index=True)
    data_ordem = Column(Date, nullable=False)
    data_entrega_prevista = Column(Date)
    data_entrega_real = Column(Date)
    
    # Status
    status = Column(String(50), default="pendente", index=True)  # pendente, em_cotacao, aprovada, rejeitada, em_andamento, entregue, cancelada
    
    # Valores
    valor_total = Column(Numeric(15, 2), default=0)
    desconto = Column(Numeric(15, 2), default=0)
    valor_final = Column(Numeric(15, 2), default=0)
    
    # Moeda
    moeda = Column(String(10), default="BRL", nullable=False)  # BRL, USD, CNY
    cotacao_moeda = Column(Numeric(10, 4), default=1.0)  # Taxa de câmbio para conversão
    
    # Tipo de ordem
    tipo_ordem = Column(String(20), default="nacional")  # nacional, internacional
    
    # Campos para ordens internacionais
    comissao_agente = Column(Numeric(15, 2), default=0)  # Valor calculado da comissão do agente
    percentual_comissao = Column(Numeric(5, 2), default=0)  # Percentual da comissão do agente
    valor_transporte = Column(Numeric(15, 2), default=0)  # Valor do transporte
    percentual_importacao = Column(Numeric(5, 2), default=0)  # Percentual de impostos de importação
    taxas_adicionais = Column(Numeric(15, 2), default=0)  # Taxas adicionais de importação
    valor_impostos = Column(Numeric(15, 2), default=0)  # Valor calculado dos impostos
    
    # Observações
    observacoes = Column(Text)
    condicoes_pagamento = Column(String(255))
    prazo_entrega = Column(String(100))
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="ordens_compra")
    fornecedor = relationship("Fornecedor", back_populates="ordens_compra", foreign_keys=[fornecedor_id])
    transportadora = relationship("Fornecedor", back_populates="ordens_compra_transportadora", foreign_keys=[transportadora_id])
    itens = relationship("OrdemCompraItem", back_populates="ordem_compra", cascade="all, delete-orphan")
    links = relationship("OrdemCompraLink", back_populates="ordem_compra", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        Index('ix_ordem_compra_company_status', 'company_id', 'status'),
        Index('ix_ordem_compra_data', 'data_ordem'),
        Index('ix_ordem_compra_numero', 'numero_ordem'),
    )

class OrdemCompraItem(Base):
    """Itens da Ordem de Compra"""
    __tablename__ = "ordem_compra_item"
    
    id = Column(Integer, primary_key=True, index=True)
    ordem_compra_id = Column(Integer, ForeignKey("ordem_compra.id"), nullable=False, index=True)
    
    # Dados do produto
    produto_id = Column(Integer, nullable=True)  # FK para produtos internos (opcional)
    produto_nome = Column(String(255), nullable=False)
    produto_descricao = Column(Text)
    produto_codigo = Column(String(100))
    produto_imagem = Column(String(500))  # URL da imagem do produto
    descricao_fornecedor = Column(Text)  # Descrição específica do fornecedor
    
    # Quantidades e valores
    quantidade = Column(Numeric(10, 3), nullable=False)
    valor_unitario = Column(Numeric(15, 2), nullable=False)
    valor_total = Column(Numeric(15, 2), nullable=False)
    
    # URL do produto
    url = Column(String(500))
    
    # Observações do item
    observacoes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    ordem_compra = relationship("OrdemCompra", back_populates="itens")
    
    # Índices
    __table_args__ = (
        Index('ix_ordem_compra_item_ordem', 'ordem_compra_id'),
        Index('ix_ordem_compra_item_produto', 'produto_id'),
    )


class OrdemCompraLink(Base):
    """Links Externos das Ordens de Compra"""
    __tablename__ = "ordem_compra_link"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    ordem_compra_id = Column(Integer, ForeignKey("ordem_compra.id"), nullable=False, index=True)
    nome = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    descricao = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company")
    ordem_compra = relationship("OrdemCompra", back_populates="links")
    
    # Índices
    __table_args__ = (
        Index('ix_ordem_compra_link_company', 'company_id'),
        Index('ix_ordem_compra_link_ordem', 'ordem_compra_id'),
    )

