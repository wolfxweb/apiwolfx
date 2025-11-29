#!/usr/bin/env python3
"""
Script para criar as tabelas de tarefas
Execute este script para criar a tabela tasks
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config.database import engine, SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tasks_tables():
    """Cria a tabela tasks"""
    
    sql = """
    -- Criar tabela tasks
    CREATE TABLE IF NOT EXISTS tasks (
        id SERIAL PRIMARY KEY,
        company_id INTEGER NOT NULL,
        created_by INTEGER NOT NULL,
        assigned_to INTEGER,
        title VARCHAR(500) NOT NULL,
        description TEXT,
        status VARCHAR(20) DEFAULT 'pending' NOT NULL,
        priority VARCHAR(20) DEFAULT 'medium',
        category VARCHAR(50),
        due_date DATE NOT NULL,
        completed_at TIMESTAMP WITH TIME ZONE,
        product_id INTEGER,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        
        CONSTRAINT fk_tasks_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
        CONSTRAINT fk_tasks_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE,
        CONSTRAINT fk_tasks_assigned_to FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL,
        CONSTRAINT fk_tasks_product FOREIGN KEY (product_id) REFERENCES internal_products(id) ON DELETE SET NULL
    );

    -- Criar índices
    CREATE INDEX IF NOT EXISTS ix_tasks_company_status ON tasks(company_id, status);
    CREATE INDEX IF NOT EXISTS ix_tasks_assigned_to ON tasks(assigned_to);
    CREATE INDEX IF NOT EXISTS ix_tasks_due_date ON tasks(due_date);
    CREATE INDEX IF NOT EXISTS ix_tasks_category ON tasks(category);
    CREATE INDEX IF NOT EXISTS ix_tasks_company_id ON tasks(company_id);
    CREATE INDEX IF NOT EXISTS ix_tasks_created_by ON tasks(created_by);
    CREATE INDEX IF NOT EXISTS ix_tasks_product_id ON tasks(product_id);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
            logger.info("✅ Tabela 'tasks' verificada/criada com sucesso")
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabela 'tasks': {e}", exc_info=True)
        raise


if __name__ == "__main__":
    create_tasks_tables()

