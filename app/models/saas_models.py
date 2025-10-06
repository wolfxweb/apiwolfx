"""
Modelos SaaS Multi-tenant para API Mercado Livre
"""
from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey, Enum, JSON, Index
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
    max_ml_accounts = Column(Integer, default=5)
    max_users = Column(Integer, default=10)
    features = Column(JSON)  # Features habilitadas
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    trial_ends_at = Column(DateTime)
    
    # Relacionamentos
    users = relationship("User", back_populates="company", cascade="all, delete-orphan")
    ml_accounts = relationship("MLAccount", back_populates="company", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="company", cascade="all, delete-orphan")

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
    products = relationship("Product", back_populates="ml_account", cascade="all, delete-orphan")
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

class Product(Base):
    """Modelo de Produto (atualizado)"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    ml_account_id = Column(Integer, ForeignKey("ml_accounts.id"), nullable=False, index=True)
    
    # Dados do produto
    ml_item_id = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    price = Column(String(50))
    currency_id = Column(String(10))
    condition = Column(String(50))
    permalink = Column(String(500))
    thumbnail = Column(String(500))
    status = Column(String(50), index=True)
    
    # Dados adicionais
    category_id = Column(String(50))
    brand = Column(String(100))
    model = Column(String(100))
    attributes = Column(JSON)  # Atributos específicos
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_sync = Column(DateTime)
    
    # Relacionamentos
    company = relationship("Company")
    ml_account = relationship("MLAccount", back_populates="products")

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
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Dados da assinatura
    plan_name = Column(String(100), nullable=False)
    plan_features = Column(JSON)
    price = Column(String(50))
    currency = Column(String(10), default="BRL")
    
    # Status
    status = Column(String(50), default="active", index=True)
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
    ml_product_id = Column(Integer, ForeignKey("ml_products.id"), nullable=False, index=True)
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

class ApiLog(Base):
    """Modelo de log da API (atualizado)"""
    __tablename__ = "api_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    ml_account_id = Column(Integer, ForeignKey("ml_accounts.id"), nullable=True, index=True)
    
    # Dados da requisição
    endpoint = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer)
    response_time_ms = Column(Integer)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    # Dados adicionais
    request_data = Column(JSON)
    response_data = Column(JSON)
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), index=True)
    
    # Relacionamentos
    company = relationship("Company")
    user = relationship("User")
    ml_account = relationship("MLAccount")

class OrderStatus(enum.Enum):
    """Status do pedido"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

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
    
    # Valores monetários
    total_amount = Column(Integer)  # Em centavos
    paid_amount = Column(Integer)   # Em centavos
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
    shipping_cost = Column(Integer)  # Em centavos
    shipping_method = Column(String(100))
    shipping_status = Column(String(50))
    shipping_address = Column(JSON)  # Endereço de entrega
    shipping_details = Column(JSON)  # Detalhes completos do envio
    
    # === ITENS DO PEDIDO ===
    order_items = Column(JSON)  # Lista completa de itens com detalhes
    
    # === TAXAS E COMISSÕES ===
    total_fees = Column(Integer)      # Total de taxas em centavos
    listing_fees = Column(Integer)    # Taxas de publicação em centavos
    sale_fees = Column(Integer)       # Taxas de venda em centavos
    shipping_fees = Column(Integer)   # Taxas de envio em centavos
    
    # === DESCONTOS E PROMOÇÕES ===
    discounts_applied = Column(JSON)  # Descontos aplicados (/orders/{id}/discounts)
    coupon_amount = Column(Integer)   # Valor do cupom em centavos
    coupon_id = Column(String(50))    # ID do cupom
    
    # === PUBLICIDADE E ANÚNCIOS ===
    is_advertising_sale = Column(Boolean, default=False, index=True)  # Venda por anúncio
    advertising_campaign_id = Column(String(50))  # ID da campanha
    advertising_cost = Column(Integer)  # Custo publicitário em centavos
    advertising_metrics = Column(JSON)  # Métricas de publicidade
    
    # === CONTEXTO DA VENDA ===
    context = Column(JSON)  # Canal, site, flows (/orders/{id})
    pack_id = Column(String(50))  # ID do pack se aplicável
    pickup_id = Column(String(50))  # ID de retirada se aplicável
    
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
    
    # === TIMESTAMPS ===
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # === RELACIONAMENTOS ===
    company = relationship("Company")
    ml_account = relationship("MLAccount")
    
    # === ÍNDICES ===
    __table_args__ = (
        Index('ix_ml_orders_company_ml_account', 'company_id', 'ml_account_id'),
        Index('ix_ml_orders_buyer_id', 'buyer_id'),
        Index('ix_ml_orders_seller_id', 'seller_id'),
        Index('ix_ml_orders_date_created', 'date_created'),
        Index('ix_ml_orders_status', 'status'),
        Index('ix_ml_orders_advertising', 'is_advertising_sale'),
        Index('ix_ml_orders_shipping_id', 'shipping_id'),
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

