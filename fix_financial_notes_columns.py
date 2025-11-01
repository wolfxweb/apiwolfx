#!/usr/bin/env python3
"""
Script para adicionar a coluna 'notes' nas tabelas financeiras se não existir
"""
import sys
from sqlalchemy import create_engine, text, inspect
from app.config.database import DATABASE_URL

def add_notes_column_if_not_exists(table_name):
    """Adiciona a coluna notes em uma tabela se ela não existir"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            # Verificar se a tabela existe
            inspector = inspect(engine)
            
            # Verificar se a tabela existe
            if table_name not in inspector.get_table_names():
                print(f"⚠️  Tabela '{table_name}' não existe. Pulando...")
                return False
            
            # Verificar se a coluna já existe
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            
            if 'notes' in columns:
                print(f"✅ A coluna 'notes' já existe na tabela {table_name}")
                return True
            
            # Adicionar a coluna
            print(f"🔄 Adicionando coluna 'notes' na tabela {table_name}...")
            conn.execute(text(f"""
                ALTER TABLE {table_name} 
                ADD COLUMN IF NOT EXISTS notes TEXT;
            """))
            conn.commit()
            
            print(f"✅ Coluna 'notes' adicionada com sucesso em {table_name}!")
            return True
            
        except Exception as e:
            print(f"⚠️  Erro ao processar tabela {table_name}: {e}")
            return False

def fix_all_financial_tables():
    """Adiciona a coluna notes em todas as tabelas financeiras"""
    tables = [
        'financial_customers',
        'financial_suppliers'
    ]
    
    print("🔧 Verificando e corrigindo colunas 'notes' nas tabelas financeiras...\n")
    
    for table in tables:
        add_notes_column_if_not_exists(table)
    
    print("\n✅ Verificação concluída!")

if __name__ == '__main__':
    try:
        fix_all_financial_tables()
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

