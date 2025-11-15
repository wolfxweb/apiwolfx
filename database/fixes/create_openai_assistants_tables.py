#!/usr/bin/env python3
"""
Script para criar as tabelas OpenAI Assistants no banco de dados
Execute este script em produção para criar as tabelas de gerenciamento de assistentes OpenAI

Uso:
    python database/fixes/create_openai_assistants_tables.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config.database import engine, SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_openai_assistants_tables():
    """Cria as tabelas OpenAI Assistants e todos os índices"""
    
    sql = """
    -- Criar enum InteractionMode se não existir
    DO $$ 
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'interactionmode') THEN
            CREATE TYPE interactionmode AS ENUM ('chat', 'report');
        END IF;
    END $$;

    -- Criar enum UsageStatus se não existir
    DO $$ 
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'usagestatus') THEN
            CREATE TYPE usagestatus AS ENUM ('pending', 'completed', 'failed', 'cancelled');
        END IF;
    END $$;

    -- Criar tabela openai_assistants
    CREATE TABLE IF NOT EXISTS openai_assistants (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        
        -- IDs da OpenAI
        assistant_id VARCHAR(255) UNIQUE NOT NULL,
        model VARCHAR(100) NOT NULL DEFAULT 'gpt-4-turbo-preview',
        
        -- Configurações
        instructions TEXT NOT NULL,
        temperature FLOAT,
        max_tokens INTEGER DEFAULT 4000,
        
        -- Ferramentas (JSON)
        tools_config JSONB,
        
        -- Modo de uso
        interaction_mode interactionmode DEFAULT 'report'::interactionmode NOT NULL,
        use_case VARCHAR(100),
        
        -- Status
        is_active BOOLEAN DEFAULT TRUE NOT NULL,
        
        -- Métricas
        total_runs INTEGER DEFAULT 0,
        total_tokens_used BIGINT DEFAULT 0,
        
        -- Timestamps
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        last_used_at TIMESTAMP WITH TIME ZONE
    );

    -- Criar tabela openai_assistant_threads
    CREATE TABLE IF NOT EXISTS openai_assistant_threads (
        id SERIAL PRIMARY KEY,
        assistant_id INTEGER NOT NULL,
        company_id INTEGER NOT NULL,
        user_id INTEGER,
        
        -- ID da thread na OpenAI
        thread_id VARCHAR(255) UNIQUE NOT NULL,
        
        -- Contexto da conversa (JSON)
        context_data JSONB,
        
        -- Status
        is_active BOOLEAN DEFAULT TRUE NOT NULL,
        
        -- Timestamps
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        last_message_at TIMESTAMP WITH TIME ZONE,
        
        CONSTRAINT fk_openai_assistant_threads_assistant FOREIGN KEY (assistant_id) REFERENCES openai_assistants(id) ON DELETE CASCADE,
        CONSTRAINT fk_openai_assistant_threads_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
        CONSTRAINT fk_openai_assistant_threads_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    );

    -- Criar tabela openai_assistant_usage
    CREATE TABLE IF NOT EXISTS openai_assistant_usage (
        id SERIAL PRIMARY KEY,
        assistant_id INTEGER NOT NULL,
        company_id INTEGER NOT NULL,
        user_id INTEGER,
        
        -- Thread (para modo chat)
        thread_id VARCHAR(255),
        
        -- Modo de uso
        interaction_mode VARCHAR(50) NOT NULL,
        use_case VARCHAR(100),
        
        -- Tokens utilizados
        prompt_tokens INTEGER DEFAULT 0 NOT NULL,
        completion_tokens INTEGER DEFAULT 0 NOT NULL,
        total_tokens INTEGER DEFAULT 0 NOT NULL,
        
        -- Status da execução
        status usagestatus NOT NULL,
        error_message TEXT,
        
        -- Dados da requisição (opcional, para debug)
        request_data_size INTEGER,
        response_data_size INTEGER,
        
        -- Timestamps
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP WITH TIME ZONE,
        duration_seconds FLOAT,
        
        CONSTRAINT fk_openai_assistant_usage_assistant FOREIGN KEY (assistant_id) REFERENCES openai_assistants(id) ON DELETE CASCADE,
        CONSTRAINT fk_openai_assistant_usage_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
        CONSTRAINT fk_openai_assistant_usage_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    );

    -- Criar índices para openai_assistants (usando DO para compatibilidade)
    DO $$ 
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_openai_assistants_assistant_id') THEN
            CREATE INDEX ix_openai_assistants_assistant_id ON openai_assistants(assistant_id);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_openai_assistants_is_active') THEN
            CREATE INDEX ix_openai_assistants_is_active ON openai_assistants(is_active);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_openai_assistants_model') THEN
            CREATE INDEX ix_openai_assistants_model ON openai_assistants(model);
        END IF;
    END $$;

    -- Criar índices para openai_assistant_threads
    DO $$ 
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_openai_assistant_threads_assistant') THEN
            CREATE INDEX ix_openai_assistant_threads_assistant ON openai_assistant_threads(assistant_id);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_openai_assistant_threads_company') THEN
            CREATE INDEX ix_openai_assistant_threads_company ON openai_assistant_threads(company_id);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_openai_assistant_threads_user') THEN
            CREATE INDEX ix_openai_assistant_threads_user ON openai_assistant_threads(user_id);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_openai_assistant_threads_thread_id') THEN
            CREATE INDEX ix_openai_assistant_threads_thread_id ON openai_assistant_threads(thread_id);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_openai_assistant_threads_active') THEN
            CREATE INDEX ix_openai_assistant_threads_active ON openai_assistant_threads(is_active);
        END IF;
    END $$;

    -- Criar índices para openai_assistant_usage
    DO $$ 
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_openai_assistant_usage_assistant') THEN
            CREATE INDEX ix_openai_assistant_usage_assistant ON openai_assistant_usage(assistant_id);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_openai_assistant_usage_company') THEN
            CREATE INDEX ix_openai_assistant_usage_company ON openai_assistant_usage(company_id);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_openai_assistant_usage_user') THEN
            CREATE INDEX ix_openai_assistant_usage_user ON openai_assistant_usage(user_id);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_openai_assistant_usage_thread_id') THEN
            CREATE INDEX ix_openai_assistant_usage_thread_id ON openai_assistant_usage(thread_id);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_openai_assistant_usage_created') THEN
            CREATE INDEX ix_openai_assistant_usage_created ON openai_assistant_usage(created_at);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_openai_assistant_usage_status') THEN
            CREATE INDEX ix_openai_assistant_usage_status ON openai_assistant_usage(status);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_assistant_usage_company_date') THEN
            CREATE INDEX ix_assistant_usage_company_date ON openai_assistant_usage(company_id, created_at);
        END IF;
    END $$;
    """
    
    db = SessionLocal()
    try:
        logger.info("🚀 Criando tabelas OpenAI Assistants...")
        
        # Executar SQL
        with db.begin():
            db.execute(text(sql))
        
        logger.info("✅ Tabelas OpenAI Assistants criadas com sucesso!")
        logger.info("✅ Índices criados com sucesso!")
        
        # Verificar se as tabelas foram criadas
        tables_to_check = [
            'openai_assistants',
            'openai_assistant_threads',
            'openai_assistant_usage'
        ]
        
        for table_name in tables_to_check:
            check_sql = text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')")
            result = db.execute(check_sql).scalar()
            
            if result:
                logger.info(f"✅ Verificação: Tabela {table_name} existe no banco de dados")
                
                # Contar colunas
                count_sql = text(f"""
                    SELECT COUNT(*) 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}'
                """)
                column_count = db.execute(count_sql).scalar()
                logger.info(f"📊 Colunas criadas em {table_name}: {column_count}")
            else:
                logger.error(f"❌ Erro: Tabela {table_name} não foi criada")
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas OpenAI Assistants: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_openai_assistants_tables()

