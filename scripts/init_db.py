#!/usr/bin/env python3
"""
Script para inicializar o banco de dados
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.database import engine, Base
from app.models.database_models import User, Token, Product, Category, ApiLog
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Inicializa o banco de dados criando todas as tabelas"""
    try:
        logger.info("Criando tabelas do banco de dados...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Banco de dados inicializado com sucesso!")
        
        # Verificar tabelas criadas
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"📊 Tabelas criadas: {', '.join(tables)}")
        
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar banco de dados: {e}")
        raise

if __name__ == "__main__":
    init_database()
