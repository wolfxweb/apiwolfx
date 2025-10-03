#!/usr/bin/env python3
"""
Script para gerenciar migrações do banco de dados
"""
import subprocess
import sys
import os

def run_command(command):
    """Executa comando no container"""
    try:
        result = subprocess.run(
            f"docker-compose exec api {command}",
            shell=True,
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def show_help():
    """Mostra ajuda do script"""
    print("🔧 Script de Migração do Banco de Dados")
    print("=" * 50)
    print("Comandos disponíveis:")
    print("  python migrate.py create 'mensagem'  - Criar nova migração")
    print("  python migrate.py upgrade           - Aplicar migrações")
    print("  python migrate.py downgrade         - Reverter migração")
    print("  python migrate.py current           - Ver migração atual")
    print("  python migrate.py history           - Ver histórico")
    print("  python migrate.py tables            - Listar tabelas")
    print("  python migrate.py help              - Mostrar esta ajuda")

def create_migration(message):
    """Cria nova migração"""
    print(f"📝 Criando migração: {message}")
    success, stdout, stderr = run_command(f"alembic revision --autogenerate -m '{message}'")
    
    if success:
        print("✅ Migração criada com sucesso!")
        print(stdout)
    else:
        print("❌ Erro ao criar migração:")
        print(stderr)

def upgrade_migration():
    """Aplica migrações"""
    print("🚀 Aplicando migrações...")
    success, stdout, stderr = run_command("alembic upgrade head")
    
    if success:
        print("✅ Migrações aplicadas com sucesso!")
        print(stdout)
    else:
        print("❌ Erro ao aplicar migrações:")
        print(stderr)

def downgrade_migration():
    """Reverte migração"""
    print("⬇️ Revertendo migração...")
    success, stdout, stderr = run_command("alembic downgrade -1")
    
    if success:
        print("✅ Migração revertida com sucesso!")
        print(stdout)
    else:
        print("❌ Erro ao reverter migração:")
        print(stderr)

def show_current():
    """Mostra migração atual"""
    print("📊 Migração atual:")
    success, stdout, stderr = run_command("alembic current")
    
    if success:
        print(stdout)
    else:
        print("❌ Erro ao obter migração atual:")
        print(stderr)

def show_history():
    """Mostra histórico de migrações"""
    print("📚 Histórico de migrações:")
    success, stdout, stderr = run_command("alembic history")
    
    if success:
        print(stdout)
    else:
        print("❌ Erro ao obter histórico:")
        print(stderr)

def show_tables():
    """Lista tabelas do banco"""
    print("📋 Tabelas do banco de dados:")
    success, stdout, stderr = run_command("""
python -c "
import psycopg2
conn = psycopg2.connect(
    host='pgadmin.wolfx.com.br',
    port=5432,
    database='comercial',
    user='postgres',
    password='97452c28f62db6d77be083917b698660'
)
cursor = conn.cursor()
cursor.execute('''
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name;
''')
tables = cursor.fetchall()
for table in tables:
    print(f'   ✅ {table[0]}')
cursor.close()
conn.close()
"
    """)
    
    if success:
        print(stdout)
    else:
        print("❌ Erro ao listar tabelas:")
        print(stderr)

def main():
    """Função principal"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "create":
        if len(sys.argv) < 3:
            print("❌ Erro: Forneça uma mensagem para a migração")
            print("Exemplo: python migrate.py create 'Adicionar campo email'")
            return
        message = sys.argv[2]
        create_migration(message)
    
    elif command == "upgrade":
        upgrade_migration()
    
    elif command == "downgrade":
        downgrade_migration()
    
    elif command == "current":
        show_current()
    
    elif command == "history":
        show_history()
    
    elif command == "tables":
        show_tables()
    
    elif command == "help":
        show_help()
    
    else:
        print(f"❌ Comando desconhecido: {command}")
        show_help()

if __name__ == "__main__":
    main()
