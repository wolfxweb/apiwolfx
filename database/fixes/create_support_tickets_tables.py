#!/usr/bin/env python3
"""
Script para criar as tabelas de chamados de suporte
Execute este script para criar as tabelas support_tickets e support_ticket_messages
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config.database import engine, SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_support_tickets_tables():
    """Cria as tabelas support_tickets e support_ticket_messages"""
    
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
        
        -- Status/Situação
        status supportticketstatus DEFAULT 'open'::supportticketstatus NOT NULL,
        
        -- Timestamps
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        closed_at TIMESTAMP WITH TIME ZONE,
        
        CONSTRAINT fk_support_tickets_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
        CONSTRAINT fk_support_tickets_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    );

    -- Criar tabela support_ticket_messages
    CREATE TABLE IF NOT EXISTS support_ticket_messages (
        id SERIAL PRIMARY KEY,
        ticket_id INTEGER NOT NULL,
        user_id INTEGER,
        
        -- Tipo de mensagem
        is_from_support BOOLEAN DEFAULT FALSE NOT NULL,
        
        -- Conteúdo
        message TEXT NOT NULL,
        
        -- Timestamps
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        
        CONSTRAINT fk_support_ticket_messages_ticket FOREIGN KEY (ticket_id) REFERENCES support_tickets(id) ON DELETE CASCADE,
        CONSTRAINT fk_support_ticket_messages_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    );

    -- Criar tabela support_ticket_attachments
    CREATE TABLE IF NOT EXISTS support_ticket_attachments (
        id SERIAL PRIMARY KEY,
        ticket_id INTEGER NOT NULL,
        message_id INTEGER,
        
        -- Dados do arquivo
        filename VARCHAR(500) NOT NULL,
        file_path VARCHAR(1000) NOT NULL,
        file_size BIGINT,
        content_type VARCHAR(100),
        
        -- Usuário que fez upload
        uploaded_by INTEGER,
        
        -- Timestamps
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        
        CONSTRAINT fk_support_ticket_attachments_ticket FOREIGN KEY (ticket_id) REFERENCES support_tickets(id) ON DELETE CASCADE,
        CONSTRAINT fk_support_ticket_attachments_message FOREIGN KEY (message_id) REFERENCES support_ticket_messages(id) ON DELETE CASCADE,
        CONSTRAINT fk_support_ticket_attachments_user FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL
    );

    -- Criar índices para support_tickets
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

    -- Criar índices para support_ticket_messages
    DO $$ 
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_support_ticket_messages_ticket') THEN
            CREATE INDEX ix_support_ticket_messages_ticket ON support_ticket_messages(ticket_id);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_support_ticket_messages_user') THEN
            CREATE INDEX ix_support_ticket_messages_user ON support_ticket_messages(user_id);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_support_ticket_messages_created') THEN
            CREATE INDEX ix_support_ticket_messages_created ON support_ticket_messages(created_at);
        END IF;
    END $$;

    -- Criar índices para support_ticket_attachments
    DO $$ 
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_support_ticket_attachments_ticket') THEN
            CREATE INDEX ix_support_ticket_attachments_ticket ON support_ticket_attachments(ticket_id);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_support_ticket_attachments_message') THEN
            CREATE INDEX ix_support_ticket_attachments_message ON support_ticket_attachments(message_id);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_support_ticket_attachments_user') THEN
            CREATE INDEX ix_support_ticket_attachments_user ON support_ticket_attachments(uploaded_by);
        END IF;
    END $$;

    -- Adicionar coluna closed_at se não existir (para migração)
    DO $$ 
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'support_tickets' AND column_name = 'closed_at'
        ) THEN
            ALTER TABLE support_tickets ADD COLUMN closed_at TIMESTAMP WITH TIME ZONE;
        END IF;
    END $$;

    -- Remover colunas antigas se existirem (migração)
    DO $$ 
    BEGIN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'support_tickets' AND column_name = 'response'
        ) THEN
            ALTER TABLE support_tickets DROP COLUMN response;
        END IF;
        
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'support_tickets' AND column_name = 'responded_by'
        ) THEN
            ALTER TABLE support_tickets DROP COLUMN responded_by;
        END IF;
        
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'support_tickets' AND column_name = 'responded_at'
        ) THEN
            ALTER TABLE support_tickets DROP COLUMN responded_at;
        END IF;
    END $$;
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        logger.info("✅ Tabelas de suporte criadas/atualizadas com sucesso!")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas de suporte: {e}")
        return False

if __name__ == "__main__":
    create_support_tickets_tables()

