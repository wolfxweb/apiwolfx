"""
Configuração do banco de dados
"""
import os
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func

# Verificar se DATABASE_URL está definida diretamente (prioridade)
# Se não estiver, usar lógica baseada no ambiente
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Determinar ambiente: production usa selvez, homologation usa comercial, development usa comercial
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        # Banco de produção (selvez)
        # Nota: @ na senha precisa ser codificado como %40
        DATABASE_URL = "postgresql://api_user:%40Wolfx20202025@207.231.108.38:5432/selvez"
    elif environment == "homologation":
        # Banco de homologação (celx_prod)
        DATABASE_URL = "postgresql://postgres:97452c28f62db6d77be083917b698660@pgadmin.wolfx.com.br:5432/celx_prod"
    else:
        # Banco local/desenvolvimento (comercial)
        DATABASE_URL = "postgresql://postgres:97452c28f62db6d77be083917b698660@pgadmin.wolfx.com.br:5432/comercial"
# Criar engine do SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,  # Mude para True para ver queries SQL
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,  # Reciclar conexões a cada hora
    connect_args={
        "connect_timeout": 30,  # Aumentado de 10 para 30 segundos
        "application_name": "apiwolfx"
    }
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

