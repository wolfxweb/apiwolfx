#!/usr/bin/env python3
"""
Script para adicionar a coluna ml_orders_as_receivables na tabela companies
"""
import sys
import os
import time

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def add_column_to_database():
    """Adiciona a coluna ml_orders_as_receivables na tabela companies"""
    try:
        print("🔌 Conectando ao banco de dados...")
        from app.config.database import engine
        from sqlalchemy import text
        
        print("✅ Conexão estabelecida!")
        
        with engine.connect() as conn:
            print("🔍 Verificando se a coluna já existe...")
            
            # Verificar se a coluna já existe
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'companies' 
                AND column_name = 'ml_orders_as_receivables'
            """)
            
            result = conn.execute(check_query).fetchone()
            
            if result:
                print("✅ A coluna ml_orders_as_receivables já existe na tabela companies")
                return True
            
            print("➕ Adicionando coluna ml_orders_as_receivables...")
            
            # Adicionar a coluna
            alter_query = text("""
                ALTER TABLE companies 
                ADD COLUMN ml_orders_as_receivables BOOLEAN NOT NULL DEFAULT true
            """)
            
            conn.execute(alter_query)
            conn.commit()
            
            print("✅ Coluna ml_orders_as_receivables adicionada com sucesso na tabela companies!")
            
            # Verificar se foi criada corretamente
            verify_query = text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'companies' 
                AND column_name = 'ml_orders_as_receivables'
            """)
            
            verify_result = conn.execute(verify_query).fetchone()
            if verify_result:
                print(f"📋 Detalhes da coluna criada:")
                print(f"   - Nome: {verify_result[0]}")
                print(f"   - Tipo: {verify_result[1]}")
                print(f"   - Nullable: {verify_result[2]}")
                print(f"   - Default: {verify_result[3]}")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro ao adicionar coluna: {e}")
        print(f"🔧 Tipo do erro: {type(e).__name__}")
        return False

def main():
    """Função principal"""
    print("=" * 60)
    print("🚀 SCRIPT PARA ADICIONAR COLUNA ML_ORDERS_AS_RECEIVABLES")
    print("=" * 60)
    print()
    
    start_time = time.time()
    
    try:
        success = add_column_to_database()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print()
        print("=" * 60)
        if success:
            print("🎉 OPERAÇÃO CONCLUÍDA COM SUCESSO!")
            print(f"⏱️  Tempo de execução: {duration:.2f} segundos")
            sys.exit(0)
        else:
            print("💥 FALHA NA OPERAÇÃO!")
            print(f"⏱️  Tempo de execução: {duration:.2f} segundos")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Operação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

