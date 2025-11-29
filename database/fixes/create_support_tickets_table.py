#!/usr/bin/env python3
"""
Script para criar a tabela de chamados de suporte
Execute este script para criar a tabela support_tickets
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config.database import engine, SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_support_tickets_table():
    """Cria a tabela support_tickets e enum SupportTicketStatus"""
    
    sql = """
    -- Criar enum SupportTicketStatus se não existir
    DO $$ 
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'supportticketstatus') THEN
            CREATE TYPE supportticketstatus AS ENUM ('open', 'in_progress', 'waiting_user', 'resolved', 'closed');
        END IF;
    END $$;

    -- Criar tabela support_tickets
    CREATE TABLE IF NOT EXISTS support_tickets (
        id SERIAL PRIMARY KEY,
        company_id INTEGER NOT NULL,
        user_id INTEGER,
        
        -- Dados do chamado
        subject VARCHAR(500) NOT NULL,
        description TEXT NOT NULL,
        category VARCHAR(100),
        priority VARCHAR(20) DEFAULT 'medium',
        
        -- Status
        status supportticketstatus DEFAULT 'open'::supportticketstatus NOT NULL,
        
        -- Resposta do suporte
        response TEXT,
        responded_by INTEGER,
        responded_at TIMESTAMP WITH TIME ZONE,
        
        -- Timestamps
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        
        CONSTRAINT fk_support_tickets_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
        CONSTRAINT fk_support_tickets_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
        CONSTRAINT fk_support_tickets_responder FOREIGN KEY (responded_by) REFERENCES users(id) ON DELETE SET NULL
    );

    -- Criar índices
    DO $$ 
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_support_tickets_company_id') THEN
            CREATE INDEX ix_support_tickets_company_id ON support_tickets(company_id);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_support_tickets_user_id') THEN
            CREATE INDEX ix_support_tickets_user_id ON support_tickets(user_id);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_support_tickets_status') THEN
            CREATE INDEX ix_support_tickets_status ON support_tickets(status);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_support_tickets_company_status') THEN
            CREATE INDEX ix_support_tickets_company_status ON support_tickets(company_id, status);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_support_tickets_created_at') THEN
            CREATE INDEX ix_support_tickets_created_at ON support_tickets(created_at);
        END IF;
    END $$;
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        logger.info("✅ Tabela support_tickets criada com sucesso!")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabela support_tickets: {e}")
        return False

if __name__ == "__main__":
    create_support_tickets_table()

