#!/usr/bin/env python3
"""
Script para criar as tabelas de campanhas de publicidade
"""
from sqlalchemy import create_engine, text
from app.config.database import DATABASE_URL

def create_tables():
    """Cria as tabelas de campanhas"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Tabela de campanhas
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ml_campaigns (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL REFERENCES companies(id),
                ml_account_id INTEGER NOT NULL REFERENCES ml_accounts(id),
                campaign_id VARCHAR(100) UNIQUE NOT NULL,
                advertiser_id VARCHAR(100) NOT NULL,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(50) NOT NULL,
                daily_budget FLOAT DEFAULT 0,
                total_budget FLOAT DEFAULT 0,
                total_spent FLOAT DEFAULT 0,
                total_impressions INTEGER DEFAULT 0,
                total_clicks INTEGER DEFAULT 0,
                total_conversions INTEGER DEFAULT 0,
                total_revenue FLOAT DEFAULT 0,
                ctr FLOAT DEFAULT 0,
                cpc FLOAT DEFAULT 0,
                roas FLOAT DEFAULT 0,
                bidding_strategy VARCHAR(50),
                optimization_goal VARCHAR(50),
                campaign_data JSONB,
                campaign_created_at TIMESTAMP,
                campaign_updated_at TIMESTAMP,
                last_sync_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # Índices para ml_campaigns
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ml_campaigns_company_id ON ml_campaigns(company_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ml_campaigns_ml_account_id ON ml_campaigns(ml_account_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ml_campaigns_campaign_id ON ml_campaigns(campaign_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ml_campaigns_advertiser_id ON ml_campaigns(advertiser_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ml_campaigns_status ON ml_campaigns(status);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ml_campaigns_company_status ON ml_campaigns(company_id, status);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ml_campaigns_account_status ON ml_campaigns(ml_account_id, status);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ml_campaigns_last_sync ON ml_campaigns(last_sync_at);"))
        
        # Tabela de produtos em campanhas
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ml_campaign_products (
                id SERIAL PRIMARY KEY,
                campaign_id INTEGER NOT NULL REFERENCES ml_campaigns(id),
                ml_product_id INTEGER NOT NULL REFERENCES ml_products(id),
                status VARCHAR(50) NOT NULL,
                impressions INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                conversions INTEGER DEFAULT 0,
                spent FLOAT DEFAULT 0,
                revenue FLOAT DEFAULT 0,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_sync_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # Índices para ml_campaign_products
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_campaign_products_campaign ON ml_campaign_products(campaign_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_campaign_products_product ON ml_campaign_products(ml_product_id);"))
        
        # Tabela de métricas diárias
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ml_campaign_metrics (
                id SERIAL PRIMARY KEY,
                campaign_id INTEGER NOT NULL REFERENCES ml_campaigns(id),
                metric_date TIMESTAMP NOT NULL,
                impressions INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                conversions INTEGER DEFAULT 0,
                spent FLOAT DEFAULT 0,
                revenue FLOAT DEFAULT 0,
                ctr FLOAT DEFAULT 0,
                cpc FLOAT DEFAULT 0,
                roas FLOAT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # Índices para ml_campaign_metrics
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_campaign_metrics_campaign ON ml_campaign_metrics(campaign_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_campaign_metrics_date ON ml_campaign_metrics(metric_date);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_campaign_metrics_campaign_date ON ml_campaign_metrics(campaign_id, metric_date);"))
        
        conn.commit()
        
    print("✅ Tabelas de campanhas criadas com sucesso!")

if __name__ == "__main__":
    create_tables()

