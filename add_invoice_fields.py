"""
Script para adicionar campos de nota fiscal à tabela ml_orders
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# URL do banco de dados
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:97452c28f62db6d77be083917b698660@pgadmin.wolfx.com.br:5432/comercial"
)

# Criar engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def add_invoice_fields():
    """Adiciona campos de nota fiscal à tabela ml_orders"""
    
    db = SessionLocal()
    
    try:
        # Verificar se os campos já existem
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'ml_orders' 
            AND column_name = 'invoice_emitted'
        """)
        
        result = db.execute(check_query).fetchone()
        
        if result:
            print("✅ Campos de nota fiscal já existem na tabela ml_orders")
            return
        
        print("📝 Adicionando campos de nota fiscal à tabela ml_orders...")
        
        # Adicionar campos
        alter_query = text("""
            ALTER TABLE ml_orders
            ADD COLUMN IF NOT EXISTS invoice_emitted BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS invoice_emitted_at TIMESTAMP,
            ADD COLUMN IF NOT EXISTS invoice_number VARCHAR(50),
            ADD COLUMN IF NOT EXISTS invoice_series VARCHAR(10),
            ADD COLUMN IF NOT EXISTS invoice_key VARCHAR(44),
            ADD COLUMN IF NOT EXISTS invoice_xml_url VARCHAR(500),
            ADD COLUMN IF NOT EXISTS invoice_pdf_url VARCHAR(500);
        """)
        
        db.execute(alter_query)
        db.commit()
        
        print("✅ Campos de nota fiscal adicionados com sucesso!")
        
        # Criar índices
        print("📝 Criando índices...")
        
        try:
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_ml_orders_invoice_emitted ON ml_orders(invoice_emitted);"))
            db.commit()
            print("✅ Índices criados com sucesso!")
        except Exception as e:
            print(f"⚠️  Aviso ao criar índices: {e}")
        
    except Exception as e:
        print(f"❌ Erro ao adicionar campos: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    add_invoice_fields()
    print("✅ Script executado com sucesso!")
