#!/usr/bin/env python3
"""
Script para adicionar o servidor MCP da API SELVEZ ao arquivo de configuração do Cursor
Suporta desenvolvimento (local) e produção (https://www.selvez.com.br)
"""
import json
import os
import sys
from pathlib import Path

def get_project_root():
    """Retorna o diretório raiz do projeto"""
    return Path(__file__).parent.absolute()

def get_python_path():
    """Retorna o caminho do Python"""
    return sys.executable

def add_mcp_server(environment="development"):
    """
    Adiciona o servidor MCP ao arquivo de configuração do Cursor
    
    Args:
        environment: "development" (local) ou "production" (produção)
    """
    mcp_config_path = Path.home() / ".cursor" / "mcp.json"
    project_root = get_project_root()
    python_path = get_python_path()
    
    # Configurações por ambiente
    env_configs = {
        "development": {
            "API_BASE_URL": "http://localhost:8000",
            "DATABASE_URL": os.getenv("DATABASE_URL", "postgresql://postgres:97452c28f62db6d77be083917b698660@pgadmin.wolfx.com.br:5432/comercial"),
            "ENVIRONMENT": "development"
        },
        "production": {
            "API_BASE_URL": "https://www.selvez.com.br",
            "DATABASE_URL": os.getenv("DATABASE_URL", "postgresql://api_user:%40Wolfx20202025@207.231.108.38:5432/selvez"),
            "ENVIRONMENT": "production"
        }
    }
    
    if environment not in env_configs:
        print(f"❌ Ambiente inválido: {environment}")
        print(f"   Ambientes disponíveis: development, production")
        return False
    
    config = env_configs[environment]
    server_name = f"selvez-api-{environment}"
    
    print(f"📁 Caminho do projeto: {project_root}")
    print(f"🐍 Python: {python_path}")
    print(f"📄 Arquivo de configuração: {mcp_config_path}")
    print(f"🌍 Ambiente: {environment}")
    print(f"🔗 API URL: {config['API_BASE_URL']}")
    print()
    
    # Ler configuração existente ou criar nova
    if mcp_config_path.exists():
        print(f"✅ Arquivo mcp.json encontrado, lendo configuração existente...")
        with open(mcp_config_path, 'r') as f:
            mcp_config = json.load(f)
    else:
        print(f"⚠️  Arquivo mcp.json não encontrado, criando novo...")
        mcp_config = {"mcpServers": {}}
    
    # Configuração do servidor SELVEZ
    server_config = {
        "command": python_path,
        "args": [
            "-m",
            "app.mcp"
        ],
        "cwd": str(project_root),
        "env": {
            "DATABASE_URL": config["DATABASE_URL"],
            "API_BASE_URL": config["API_BASE_URL"],
            "PYTHONPATH": str(project_root),
            "ENVIRONMENT": config["ENVIRONMENT"]
        }
    }
    
    # Adicionar ou atualizar servidor
    if "mcpServers" not in mcp_config:
        mcp_config["mcpServers"] = {}
    
    mcp_config["mcpServers"][server_name] = server_config
    
    # Salvar configuração
    try:
        with open(mcp_config_path, 'w') as f:
            json.dump(mcp_config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Servidor MCP '{server_name}' adicionado com sucesso!")
        print()
        print("📋 Configuração adicionada:")
        print(f"   Nome: {server_name}")
        print(f"   Command: {python_path}")
        print(f"   CWD: {project_root}")
        print(f"   API URL: {config['API_BASE_URL']}")
        print(f"   Ambiente: {environment}")
        print()
        print("🔄 Próximos passos:")
        print("   1. Feche completamente o Cursor (Cmd+Q)")
        print("   2. Reabra o Cursor")
        print("   3. O servidor MCP será carregado automaticamente")
        print()
        
        if environment == "production":
            print("⚠️  ATENÇÃO - Produção:")
            print("   - Certifique-se de que a API está rodando em https://www.selvez.com.br")
            print("   - Você precisará fazer login na API de produção para obter o session_token")
            print("   - Use: https://www.selvez.com.br/auth/login")
        else:
            print("⚠️  ATENÇÃO - Desenvolvimento:")
            print("   - Certifique-se de que a API está rodando localmente na porta 8000")
            print("   - Use: http://localhost:8000/auth/login para fazer login")
        
        print()
        print("📖 Para ver todas as ferramentas disponíveis, consulte:")
        print("   app/mcp/README.md")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao salvar configuração: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ADICIONANDO SERVIDOR MCP AO CURSOR")
    print("=" * 60)
    print()
    
    # Permitir escolher ambiente via argumento
    if len(sys.argv) > 1:
        env = sys.argv[1].lower()
    else:
        # Perguntar ao usuário
        print("Escolha o ambiente:")
        print("  1. Development (local - http://localhost:8000)")
        print("  2. Production (produção - https://www.selvez.com.br)")
        choice = input("\nDigite 1 ou 2 (padrão: 1): ").strip()
        
        if choice == "2":
            env = "production"
        else:
            env = "development"
    
    success = add_mcp_server(env)
    
    if success:
        print()
        print("=" * 60)
        print("✅ CONCLUÍDO!")
        print("=" * 60)
    else:
        print()
        print("=" * 60)
        print("❌ FALHA!")
        print("=" * 60)
        exit(1)
