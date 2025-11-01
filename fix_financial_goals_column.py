#!/usr/bin/env python3
"""
Script para adicionar a coluna 'name' na tabela financial_goals se não existir
"""
import sys
from sqlalchemy import create_engine, text, inspect
from app.config.database import DATABASE_URL

def add_name_column_if_not_exists():
    """Adiciona a coluna name se ela não existir"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            # Verificar se a tabela existe
            inspector = inspect(engine)
            
            if 'financial_goals' not in inspector.get_table_names():
                print("⚠️  Tabela 'financial_goals' não existe. Pulando...")
                return False
            
            # Verificar se a coluna já existe
            columns = [col['name'] for col in inspector.get_columns('financial_goals')]
            
            if 'name' in columns:
                print("✅ A coluna 'name' já existe na tabela financial_goals")
                return True
            
            # Verificar estrutura atual da tabela
            print(f"📋 Colunas atuais: {', '.join(columns)}")
            
            # Adicionar a coluna (como nullable primeiro, depois podemos tornar required)
            print("🔄 Adicionando coluna 'name' na tabela financial_goals...")
            conn.execute(text("""
                ALTER TABLE financial_goals 
                ADD COLUMN IF NOT EXISTS name VARCHAR(255);
            """))
            conn.commit()
            
            # Se houver registros, preencher com um valor padrão baseado em campos existentes
            conn.execute(text("""
                UPDATE financial_goals 
                SET name = COALESCE(
                    notes,
                    CASE 
                        WHEN goal_type IS NOT NULL THEN goal_type || ' - ' || goal_period
                        ELSE 'Meta Financeira'
                    END,
                    'Meta ' || id::text
                )
                WHERE name IS NULL;
            """))
            
            # Agora tornar NOT NULL (após preencher valores)
            try:
                conn.execute(text("""
                    ALTER TABLE financial_goals 
                    ALTER COLUMN name SET NOT NULL;
                """))
                conn.commit()
            except Exception as e:
                print(f"⚠️  Não foi possível tornar coluna NOT NULL: {e}")
                print("   Mantendo como nullable")
            
            print("✅ Coluna 'name' adicionada com sucesso!")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao processar tabela financial_goals: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    try:
        add_name_column_if_not_exists()
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

