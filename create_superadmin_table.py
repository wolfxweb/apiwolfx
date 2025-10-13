#!/usr/bin/env python3
"""
Script para criar a tabela super_admins diretamente no banco
"""
import os
import sys
sys.path.append('/Users/wolfx/Documents/wolfx/apiwolfx')

from sqlalchemy import create_engine, text
from passlib.context import CryptContext
from datetime import datetime

# Configuração do banco
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:97452c28f62db6d77be083917b698660@pgadmin.wolfx.com.br:5432/comercial"
)

# Configuração para hash de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_superadmin_table():
    """Cria a tabela super_admins e o primeiro superadmin"""
    print("🔧 Criando tabela super_admins...")
    
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Criar enum SuperAdminRole se não existir
            print("1. Criando enum SuperAdminRole...")
            conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE superadminrole AS ENUM ('super_admin', 'plan_manager', 'company_manager');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            conn.commit()
            print("   ✅ Enum criado")
            
            # Criar tabela super_admins
            print("2. Criando tabela super_admins...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS super_admins (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    first_name VARCHAR(100) NOT NULL,
                    last_name VARCHAR(100) NOT NULL,
                    role superadminrole DEFAULT 'company_manager',
                    is_active BOOLEAN DEFAULT true,
                    can_manage_companies BOOLEAN DEFAULT true,
                    can_manage_plans BOOLEAN DEFAULT true,
                    can_manage_users BOOLEAN DEFAULT true,
                    can_view_analytics BOOLEAN DEFAULT true,
                    can_access_system_logs BOOLEAN DEFAULT false,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                );
            """))
            conn.commit()
            print("   ✅ Tabela criada")
            
            # Criar índices
            print("3. Criando índices...")
            indices = [
                "CREATE INDEX IF NOT EXISTS ix_super_admins_email ON super_admins (email);",
                "CREATE INDEX IF NOT EXISTS ix_super_admins_username ON super_admins (username);",
                "CREATE INDEX IF NOT EXISTS ix_super_admins_is_active ON super_admins (is_active);",
                "CREATE INDEX IF NOT EXISTS ix_super_admins_role ON super_admins (role);",
                "CREATE INDEX IF NOT EXISTS ix_super_admins_email_active ON super_admins (email, is_active);",
                "CREATE INDEX IF NOT EXISTS ix_super_admins_role_active ON super_admins (role, is_active);"
            ]
            
            for idx in indices:
                conn.execute(text(idx))
            conn.commit()
            print("   ✅ Índices criados")
            
            # Verificar se já existe um superadmin
            print("4. Verificando se já existe superadmin...")
            result = conn.execute(text("SELECT COUNT(*) FROM super_admins")).fetchone()
            existing_count = result[0]
            
            if existing_count == 0:
                print("5. Criando primeiro superadmin...")
                password_hash = pwd_context.hash("admin123")
                
                conn.execute(text("""
                    INSERT INTO super_admins (
                        email, username, password_hash, first_name, last_name, 
                        role, can_manage_companies, can_manage_plans, 
                        can_manage_users, can_view_analytics, can_access_system_logs
                    ) VALUES (
                        'admin@givm.com', 'admin', :password_hash, 'Super', 'Admin',
                        'super_admin', true, true, true, true, true
                    )
                """), {"password_hash": password_hash})
                
                conn.commit()
                print("   ✅ Superadmin criado")
                print("   📧 Email: admin@givm.com")
                print("   👤 Username: admin")
                print("   🔑 Senha: admin123")
            else:
                print(f"   ℹ️  Já existem {existing_count} superadmin(s) no banco")
            
        print("\n🎉 Tabela super_admins criada com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar tabela: {e}")
        return False

if __name__ == "__main__":
    create_superadmin_table()
