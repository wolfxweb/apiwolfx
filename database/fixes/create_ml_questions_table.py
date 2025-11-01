#!/usr/bin/env python3
"""
Script para criar a tabela ml_questions no banco de dados
Execute este script em produção para criar a tabela de perguntas do Mercado Livre

Uso:
    python database/fixes/create_ml_questions_table.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config.database import engine, SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_ml_questions_table():
    """Cria a tabela ml_questions e todos os índices"""
    
    sql = """
    -- Criar enum MLQuestionStatus se não existir
    DO $$ 
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'mlquestionstatus') THEN
            CREATE TYPE mlquestionstatus AS ENUM ('UNANSWERED', 'ANSWERED', 'CLOSED_UNANSWERED');
        END IF;
    END $$;

    -- Criar tabela ml_questions
    CREATE TABLE IF NOT EXISTS ml_questions (
        id SERIAL PRIMARY KEY,
        company_id INTEGER NOT NULL,
        ml_account_id INTEGER NOT NULL,
        ml_question_id BIGINT UNIQUE NOT NULL,
        ml_item_id VARCHAR(50) NOT NULL,
        ml_seller_id VARCHAR(50) NOT NULL,
        ml_buyer_id VARCHAR(50),
        question_text TEXT NOT NULL,
        status mlquestionstatus NOT NULL DEFAULT 'UNANSWERED',
        item_title VARCHAR(500),
        item_thumbnail VARCHAR(500),
        answer_text TEXT,
        answer_status VARCHAR(50),
        answered_at TIMESTAMP,
        deleted_from_list BOOLEAN DEFAULT FALSE,
        hold BOOLEAN DEFAULT FALSE,
        buyer_nickname VARCHAR(255),
        buyer_answered_questions INTEGER,
        question_date TIMESTAMP NOT NULL,
        answer_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_sync TIMESTAMP,
        question_data JSONB,
        CONSTRAINT fk_ml_questions_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
        CONSTRAINT fk_ml_questions_ml_account FOREIGN KEY (ml_account_id) REFERENCES ml_accounts(id) ON DELETE CASCADE
    );

    -- Criar índices
    CREATE INDEX IF NOT EXISTS ix_ml_questions_company_id ON ml_questions(company_id);
    CREATE INDEX IF NOT EXISTS ix_ml_questions_ml_account_id ON ml_questions(ml_account_id);
    CREATE INDEX IF NOT EXISTS ix_ml_questions_ml_question_id ON ml_questions(ml_question_id);
    CREATE INDEX IF NOT EXISTS ix_ml_questions_ml_item_id ON ml_questions(ml_item_id);
    CREATE INDEX IF NOT EXISTS ix_ml_questions_ml_seller_id ON ml_questions(ml_seller_id);
    CREATE INDEX IF NOT EXISTS ix_ml_questions_status ON ml_questions(status);
    CREATE INDEX IF NOT EXISTS ix_ml_questions_question_date ON ml_questions(question_date);
    CREATE INDEX IF NOT EXISTS ix_ml_questions_company_status ON ml_questions(company_id, status);
    CREATE INDEX IF NOT EXISTS ix_ml_questions_item ON ml_questions(ml_item_id);
    CREATE INDEX IF NOT EXISTS ix_ml_questions_date ON ml_questions(question_date);
    """
    
    db = SessionLocal()
    try:
        logger.info("🚀 Criando tabela ml_questions...")
        
        # Executar SQL
        with db.begin():
            db.execute(text(sql))
        
        logger.info("✅ Tabela ml_questions criada com sucesso!")
        logger.info("✅ Índices criados com sucesso!")
        
        # Verificar se a tabela foi criada
        check_sql = text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ml_questions')")
        result = db.execute(check_sql).scalar()
        
        if result:
            logger.info("✅ Verificação: Tabela ml_questions existe no banco de dados")
            
            # Contar colunas
            count_sql = text("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'ml_questions'
            """)
            column_count = db.execute(count_sql).scalar()
            logger.info(f"📊 Colunas criadas: {column_count}")
        else:
            logger.error("❌ Erro: Tabela ml_questions não foi criada")
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabela ml_questions: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_ml_questions_table()

