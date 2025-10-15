"""
Script para criar tabela de transações de pagamento
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.config.database import DATABASE_URL

def create_payment_transactions_table():
    """Cria tabela de transações de pagamento"""
    
    # Conectar ao banco
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Criar tabela de transações de pagamento
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS payment_transactions (
                id SERIAL PRIMARY KEY,
                mp_payment_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                subscription_id INTEGER,
                amount DECIMAL(10,2) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                description TEXT,
                payment_method VARCHAR(50),
                external_reference VARCHAR(255),
                mp_response JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # Criar índices para payment_transactions
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mp_payment_id ON payment_transactions (mp_payment_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_id ON payment_transactions (user_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_subscription_id ON payment_transactions (subscription_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_status ON payment_transactions (status);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_external_reference ON payment_transactions (external_reference);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_created_at ON payment_transactions (created_at);"))
        
        # Criar tabela de planos do Mercado Pago
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mp_plans (
                id SERIAL PRIMARY KEY,
                plan_name VARCHAR(100) NOT NULL,
                description TEXT,
                price DECIMAL(10,2) NOT NULL,
                currency VARCHAR(10) DEFAULT 'BRL',
                billing_cycle VARCHAR(20) DEFAULT 'monthly',
                mp_plan_id VARCHAR(255),
                mp_preference_id VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # Criar índices para mp_plans
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_plan_name ON mp_plans (plan_name);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mp_plan_id ON mp_plans (mp_plan_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_is_active ON mp_plans (is_active);"))
        
        # Criar tabela de preapprovals
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mp_preapprovals (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                subscription_id INTEGER,
                mp_preapproval_id VARCHAR(255) NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                amount DECIMAL(10,2),
                currency VARCHAR(10) DEFAULT 'BRL',
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                auto_recurring BOOLEAN DEFAULT TRUE,
                payment_method_id VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # Criar índices para mp_preapprovals
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mp_preapprovals_user_id ON mp_preapprovals (user_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mp_preapprovals_subscription_id ON mp_preapprovals (subscription_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mp_preapproval_id ON mp_preapprovals (mp_preapproval_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mp_preapprovals_status ON mp_preapprovals (status);"))
        
        conn.commit()
        
        print("✅ Tabelas de pagamento criadas com sucesso!")
        print("📊 Tabelas criadas:")
        print("   - payment_transactions")
        print("   - mp_plans") 
        print("   - mp_preapprovals")

if __name__ == "__main__":
    create_payment_transactions_table()
