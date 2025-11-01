#!/usr/bin/env python3
"""
Script para criar as tabelas ml_message_threads e ml_messages no banco de dados
Execute este script em produção para criar as tabelas de mensageria pós-venda do Mercado Livre

Uso:
    python database/fixes/create_ml_messages_table.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config.database import engine, SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_ml_messages_tables():
    """Cria as tabelas ml_message_threads e ml_messages e todos os índices"""
    
    sql = """
    -- Criar enums se não existirem
    DO $$ 
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'mlmessagethreadstatus') THEN
            CREATE TYPE mlmessagethreadstatus AS ENUM ('open', 'closed');
        END IF;
    END $$;
    
    DO $$ 
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'mlmessagetype') THEN
            CREATE TYPE mlmessagetype AS ENUM ('text', 'image', 'system');
        END IF;
    END $$;
    
    -- Criar tabela ml_message_threads (conversas/pacotes)
    CREATE TABLE IF NOT EXISTS ml_message_threads (
        id SERIAL PRIMARY KEY,
        company_id INTEGER NOT NULL,
        ml_account_id INTEGER NOT NULL,
        ml_thread_id VARCHAR(100) UNIQUE NOT NULL,
        ml_package_id VARCHAR(100),  -- ID do pacote (pode ter um ou vários pedidos)
        ml_buyer_id VARCHAR(50) NOT NULL,
        buyer_nickname VARCHAR(255),
        reason VARCHAR(100),  -- Motivo escolhido pelo vendedor ao iniciar contato
        subject VARCHAR(500),  -- Assunto da conversa
        status mlmessagethreadstatus DEFAULT 'open'::mlmessagethreadstatus,
        last_message_date TIMESTAMP,
        last_message_text TEXT,
        order_ids JSONB,  -- Array de order_ids relacionados ao pacote
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_sync TIMESTAMP,
        thread_data JSONB,  -- Dados completos da API
        CONSTRAINT fk_ml_message_threads_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
        CONSTRAINT fk_ml_message_threads_ml_account FOREIGN KEY (ml_account_id) REFERENCES ml_accounts(id) ON DELETE CASCADE
    );

    -- Criar tabela ml_messages (mensagens individuais dentro de uma conversa)
    CREATE TABLE IF NOT EXISTS ml_messages (
        id SERIAL PRIMARY KEY,
        thread_id INTEGER NOT NULL,
        company_id INTEGER NOT NULL,
        ml_message_id VARCHAR(100) UNIQUE NOT NULL,
        from_user_id VARCHAR(50) NOT NULL,
        from_nickname VARCHAR(255),
        to_user_id VARCHAR(50) NOT NULL,
        to_nickname VARCHAR(255),
        message_text TEXT NOT NULL,
        message_type mlmessagetype DEFAULT 'text'::mlmessagetype,
        is_seller BOOLEAN DEFAULT FALSE,  -- Se a mensagem é do vendedor
        message_date TIMESTAMP NOT NULL,
        read BOOLEAN DEFAULT FALSE,
        message_data JSONB,  -- Dados completos da API
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_ml_messages_thread FOREIGN KEY (thread_id) REFERENCES ml_message_threads(id) ON DELETE CASCADE,
        CONSTRAINT fk_ml_messages_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
    );

    -- Criar índices para ml_message_threads
    CREATE INDEX IF NOT EXISTS ix_ml_message_threads_company_id ON ml_message_threads(company_id);
    CREATE INDEX IF NOT EXISTS ix_ml_message_threads_ml_account_id ON ml_message_threads(ml_account_id);
    CREATE INDEX IF NOT EXISTS ix_ml_message_threads_ml_thread_id ON ml_message_threads(ml_thread_id);
    CREATE INDEX IF NOT EXISTS ix_ml_message_threads_ml_package_id ON ml_message_threads(ml_package_id);
    CREATE INDEX IF NOT EXISTS ix_ml_message_threads_ml_buyer_id ON ml_message_threads(ml_buyer_id);
    CREATE INDEX IF NOT EXISTS ix_ml_message_threads_status ON ml_message_threads(status);
    CREATE INDEX IF NOT EXISTS ix_ml_message_threads_company_status ON ml_message_threads(company_id, status);
    CREATE INDEX IF NOT EXISTS ix_ml_message_threads_last_message_date ON ml_message_threads(last_message_date);

    -- Criar índices para ml_messages
    CREATE INDEX IF NOT EXISTS ix_ml_messages_thread_id ON ml_messages(thread_id);
    CREATE INDEX IF NOT EXISTS ix_ml_messages_company_id ON ml_messages(company_id);
    CREATE INDEX IF NOT EXISTS ix_ml_messages_ml_message_id ON ml_messages(ml_message_id);
    CREATE INDEX IF NOT EXISTS ix_ml_messages_from_user_id ON ml_messages(from_user_id);
    CREATE INDEX IF NOT EXISTS ix_ml_messages_message_date ON ml_messages(message_date);
    CREATE INDEX IF NOT EXISTS ix_ml_messages_thread_date ON ml_messages(thread_id, message_date);
    """
    
    db = SessionLocal()
    try:
        logger.info("🚀 Criando tabelas ml_message_threads e ml_messages...")
        
        # Executar SQL
        with db.begin():
            db.execute(text(sql))
        
        logger.info("✅ Tabelas criadas com sucesso!")
        logger.info("✅ Índices criados com sucesso!")
        
        # Verificar se as tabelas foram criadas
        check_sql = text("""
            SELECT 
                (SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ml_message_threads')) as threads_exists,
                (SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ml_messages')) as messages_exists
        """)
        result = db.execute(check_sql).fetchone()
        
        if result and result[0] and result[1]:
            logger.info("✅ Verificação: Tabelas ml_message_threads e ml_messages existem no banco de dados")
        else:
            logger.error("❌ Erro: Algumas tabelas não foram criadas")
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_ml_messages_tables()

