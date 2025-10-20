#!/usr/bin/env python3
"""
Script para corrigir o role do superadmin
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

def fix_superadmin_role():
    """Corrige o role do superadmin"""
    print("🔧 Corrigindo role do superadmin...")
    
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Atualizar o role do superadmin
            print("1. Atualizando role do superadmin...")
            result = conn.execute(text("""
                UPDATE super_admins 
                SET role = 'SUPER_ADMIN' 
                WHERE username = 'admin'
            """))
            
            conn.commit()
            print(f"   ✅ {result.rowcount} registro(s) atualizado(s)")
            
            # Verificar o resultado
            print("2. Verificando atualização...")
            result = conn.execute(text("SELECT username, role FROM super_admins WHERE username = 'admin'")).fetchone()
            if result:
                print(f"   ✅ Username: {result[0]}, Role: {result[1]}")
            else:
                print("   ❌ Superadmin não encontrado")
            
        print("\n🎉 Role do superadmin corrigido com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao corrigir role: {e}")
        return False

if __name__ == "__main__":
    fix_superadmin_role()
