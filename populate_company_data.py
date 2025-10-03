#!/usr/bin/env python3
"""
Script para popular dados de empresa e atualizar registros existentes
"""
import psycopg2
import sys
import os

def connect_db():
    """Conecta ao banco de dados"""
    return psycopg2.connect(
        host='pgadmin.wolfx.com.br',
        port=5432,
        database='comercial',
        user='postgres',
        password='97452c28f62db6d77be083917b698660'
    )

def create_default_company():
    """Cria empresa padrão"""
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # Verificar se já existe uma empresa padrão
        cursor.execute("SELECT id FROM companies WHERE slug = 'default-company'")
        result = cursor.fetchone()
        
        if result:
            company_id = result[0]
            print(f"✅ Empresa padrão já existe (ID: {company_id})")
            return company_id
        
        # Criar empresa padrão
        cursor.execute("""
            INSERT INTO companies (
                name, slug, description, domain, status, 
                max_ml_accounts, max_users, features,
                created_at, updated_at
            ) VALUES (
                'Empresa Padrão', 'default-company', 
                'Empresa padrão para desenvolvimento e testes',
                'localhost', 'ACTIVE', 10, 50, 
                '{"api_access": true, "analytics": true, "reports": true}',
                NOW(), NOW()
            ) RETURNING id;
        """)
        
        company_id = cursor.fetchone()[0]
        conn.commit()
        print(f"✅ Empresa padrão criada (ID: {company_id})")
        return company_id
        
    except Exception as e:
        print(f"❌ Erro ao criar empresa padrão: {e}")
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()

def update_existing_records(company_id):
    """Atualiza registros existentes com company_id"""
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # Atualizar tokens
        cursor.execute("""
            UPDATE tokens 
            SET company_id = %s 
            WHERE company_id IS NULL;
        """, (company_id,))
        tokens_updated = cursor.rowcount
        print(f"✅ {tokens_updated} tokens atualizados")
        
        # Atualizar user_sessions
        cursor.execute("""
            UPDATE user_sessions 
            SET company_id = %s 
            WHERE company_id IS NULL;
        """, (company_id,))
        sessions_updated = cursor.rowcount
        print(f"✅ {sessions_updated} sessões atualizadas")
        
        # Atualizar user_ml_accounts
        cursor.execute("""
            UPDATE user_ml_accounts 
            SET company_id = %s 
            WHERE company_id IS NULL;
        """, (company_id,))
        user_ml_updated = cursor.rowcount
        print(f"✅ {user_ml_updated} associações usuário-ML atualizadas")
        
        conn.commit()
        print("✅ Todos os registros foram atualizados com company_id")
        
    except Exception as e:
        print(f"❌ Erro ao atualizar registros: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def show_company_summary(company_id):
    """Mostra resumo da empresa"""
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # Informações da empresa
        cursor.execute("""
            SELECT name, slug, status, max_users, max_ml_accounts
            FROM companies WHERE id = %s;
        """, (company_id,))
        company = cursor.fetchone()
        
        if company:
            print(f"\\n🏢 EMPRESA: {company[0]}")
            print(f"   Slug: {company[1]}")
            print(f"   Status: {company[2]}")
            print(f"   Max Usuários: {company[3]}")
            print(f"   Max Contas ML: {company[4]}")
        
        # Contar registros por tabela
        tables = ['users', 'ml_accounts', 'tokens', 'products', 'user_sessions', 'user_ml_accounts', 'api_logs']
        
        print(f"\\n📊 REGISTROS POR TABELA:")
        for table in tables:
            cursor.execute(f"""
                SELECT COUNT(*) FROM {table} 
                WHERE company_id = %s;
            """, (company_id,))
            count = cursor.fetchone()[0]
            print(f"   {table}: {count} registros")
            
    except Exception as e:
        print(f"❌ Erro ao obter resumo: {e}")
    finally:
        cursor.close()
        conn.close()

def main():
    """Função principal"""
    print("🏢 POPULANDO DADOS DE EMPRESA PARA SAAS")
    print("=" * 50)
    
    # Criar empresa padrão
    company_id = create_default_company()
    
    if not company_id:
        print("❌ Não foi possível criar empresa padrão")
        return
    
    # Atualizar registros existentes
    update_existing_records(company_id)
    
    # Mostrar resumo
    show_company_summary(company_id)
    
    print("\\n✅ Processo concluído com sucesso!")
    print("\\n💡 Próximos passos:")
    print("   1. Criar usuários para a empresa")
    print("   2. Configurar contas do Mercado Livre")
    print("   3. Testar o sistema multi-tenant")

if __name__ == "__main__":
    main()
