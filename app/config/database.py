"""
Configuração do banco de dados
"""
import os
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func

# URL do banco de dados
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:97452c28f62db6d77be083917b698660@pgadmin.wolfx.com.br:5432/comercial"
)

# Criar engine do SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,  # Mude para True para ver queries SQL
    pool_size=10,
    max_overflow=20
)

# Criar sessão
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)

# Base para modelos
Base = declarative_base()

def get_db():
    """Dependency para obter sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

