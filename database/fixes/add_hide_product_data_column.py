"""
Script para adicionar coluna hide_product_data na tabela companies
"""
from app.config.database import engine
from sqlalchemy import text

def add_hide_product_data_column():
    """Adiciona coluna hide_product_data na tabela companies"""
    try:
        with engine.begin() as conn:
            # Verificar se a coluna já existe
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'companies' 
                AND column_name = 'hide_product_data'
            """)
            result = conn.execute(check_query).fetchone()
            
            if not result:
                # Adicionar coluna
                alter_query = text("""
                    ALTER TABLE companies 
                    ADD COLUMN hide_product_data BOOLEAN DEFAULT FALSE
                """)
                conn.execute(alter_query)
                print("✅ Coluna 'hide_product_data' adicionada com sucesso")
            else:
                print("ℹ️ Coluna 'hide_product_data' já existe")
    except Exception as e:
        print(f"❌ Erro ao adicionar coluna: {e}")
        raise

if __name__ == "__main__":
    add_hide_product_data_column()

