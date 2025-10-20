#!/usr/bin/env python3
"""
Script para corrigir os valores do enum no banco
"""
import os
import sys
sys.path.append('/Users/wolfx/Documents/wolfx/apiwolfx')

from sqlalchemy import create_engine, text

# Configuração do banco
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:97452c28f62db6d77be083917b698660@pgadmin.wolfx.com.br:5432/comercial"
)

def fix_enum_values():
    """Corrige os valores do enum no banco"""
    print("🔧 Corrigindo valores do enum...")
    
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Recriar o enum com os valores corretos
            print("1. Recriando enum SuperAdminRole...")
            conn.execute(text("""
                -- Renomear enum antigo
                ALTER TYPE superadminrole RENAME TO old_superadminrole;
                
                -- Criar novo enum com valores corretos
                CREATE TYPE superadminrole AS ENUM ('super_admin', 'plan_manager', 'company_manager');
                
                -- Atualizar coluna para usar novo enum
                ALTER TABLE super_admins ALTER COLUMN role TYPE superadminrole USING role::text::superadminrole;
                
                -- Remover enum antigo
                DROP TYPE old_superadminrole;
            """))
            
            conn.commit()
            print("   ✅ Enum recriado com valores corretos")
            
            # Verificar se funcionou
            print("2. Verificando valores...")
            result = conn.execute(text("""
                SELECT unnest(enum_range(NULL::superadminrole)) as enum_value
            """)).fetchall()
            
            print("   Valores do enum:")
            for row in result:
                print(f"   - {row[0]}")
            
            # Verificar dados da tabela
            print("3. Verificando dados da tabela...")
            result = conn.execute(text("SELECT username, role FROM super_admins")).fetchall()
            
            print("   Dados na tabela:")
            for row in result:
                print(f"   - Username: {row[0]}, Role: {row[1]}")
            
        print("\n🎉 Enum corrigido com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao corrigir enum: {e}")
        return False

if __name__ == "__main__":
    fix_enum_values()
