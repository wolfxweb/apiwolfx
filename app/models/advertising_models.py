"""
Modelos de dados para Publicidade (Product Ads)
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.saas_models import Base


class MLCampaign(Base):
    """Campanhas de publicidade do Mercado Livre"""
    __tablename__ = "ml_campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    ml_account_id = Column(Integer, ForeignKey("ml_accounts.id"), nullable=False, index=True)
    
    # Dados da campanha
    campaign_id = Column(String(100), unique=True, nullable=False, index=True)  # ID do ML
    advertiser_id = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, index=True)  # active, paused, deleted
    
    # Orçamento
    daily_budget = Column(Float, default=0)
    total_budget = Column(Float, default=0)
    
    # Métricas acumuladas
    total_spent = Column(Float, default=0)
    total_impressions = Column(Integer, default=0)
    total_clicks = Column(Integer, default=0)
    total_conversions = Column(Integer, default=0)
    total_revenue = Column(Float, default=0)
    
    # Métricas calculadas
    ctr = Column(Float, default=0)  # Click-through rate
    cpc = Column(Float, default=0)  # Cost per click
    roas = Column(Float, default=0)  # Return on ad spend
    
    # Configurações
    bidding_strategy = Column(String(50))  # manual, automatic
    optimization_goal = Column(String(50))  # clicks, conversions
    
    # Dados adicionais
    campaign_data = Column(JSON)  # Dados completos da campanha
    
    # Timestamps
    campaign_created_at = Column(DateTime)  # Data de criação no ML
    campaign_updated_at = Column(DateTime)  # Última atualização no ML
    last_sync_at = Column(DateTime, default=func.now())  # Última sincronização
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company")
    ml_account = relationship("MLAccount")
    
    # Índices
    __table_args__ = (
        Index('ix_ml_campaigns_company_status', 'company_id', 'status'),
        Index('ix_ml_campaigns_account_status', 'ml_account_id', 'status'),
        Index('ix_ml_campaigns_last_sync', 'last_sync_at'),
    )


class MLCampaignProduct(Base):
    """Produtos associados a campanhas"""
    __tablename__ = "ml_campaign_products"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("ml_campaigns.id"), nullable=False, index=True)
    ml_product_id = Column(Integer, ForeignKey("ml_products.id"), nullable=False, index=True)
    
    # Status do produto na campanha
    status = Column(String(50), nullable=False)  # active, paused, removed
    
    # Métricas do produto
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    spent = Column(Float, default=0)
    revenue = Column(Float, default=0)
    
    # Timestamps
    added_at = Column(DateTime, default=func.now())
    last_sync_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    campaign = relationship("MLCampaign")
    ml_product = relationship("MLProduct")
    
    # Índices
    __table_args__ = (
        Index('ix_campaign_products_campaign', 'campaign_id'),
        Index('ix_campaign_products_product', 'ml_product_id'),
    )


class MLCampaignMetrics(Base):
    """Métricas diárias das campanhas - COMPLETO conforme API ML"""
    __tablename__ = "ml_campaign_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("ml_campaigns.id"), nullable=False, index=True)
    
    # Data das métricas
    metric_date = Column(DateTime, nullable=False, index=True)
    
    # Métricas básicas de performance
    impressions = Column(Integer, default=0)  # prints na API
    clicks = Column(Integer, default=0)
    spent = Column(Float, default=0)  # cost na API
    ctr = Column(Float, default=0)  # taxa de cliques (%)
    cpc = Column(Float, default=0)  # custo por clique
    
    # Vendas por Publicidade - DIRETAS
    direct_items_quantity = Column(Integer, default=0)  # vendas diretas (qtd)
    direct_units_quantity = Column(Integer, default=0)  # unidades vendidas diretas
    direct_amount = Column(Float, default=0)  # receita vendas diretas (R$)
    
    # Vendas por Publicidade - INDIRETAS
    indirect_items_quantity = Column(Integer, default=0)  # vendas indiretas (qtd)
    indirect_units_quantity = Column(Integer, default=0)  # unidades vendidas indiretas
    indirect_amount = Column(Float, default=0)  # receita vendas indiretas (R$)
    
    # Vendas por Publicidade - TOTAIS
    advertising_items_quantity = Column(Integer, default=0)  # total vendas por ads
    units_quantity = Column(Integer, default=0)  # total unidades vendidas
    total_amount = Column(Float, default=0)  # receita total (R$)
    
    # Vendas Orgânicas (sem publicidade)
    organic_items_quantity = Column(Integer, default=0)  # vendas orgânicas (qtd)
    organic_units_quantity = Column(Integer, default=0)  # unidades orgânicas
    organic_units_amount = Column(Float, default=0)  # receita orgânica (R$)
    
    # Métricas Avançadas
    acos = Column(Float, default=0)  # custo de publicidade de vendas (%)
    cvr = Column(Float, default=0)  # taxa de conversão (%)
    roas = Column(Float, default=0)  # retorno sobre investimento (x)
    sov = Column(Float, default=0)  # share of voice (%)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    
    # Relacionamentos
    campaign = relationship("MLCampaign")
    
    # Índices
    __table_args__ = (
        Index('ix_campaign_metrics_date', 'campaign_id', 'metric_date'),
    )


