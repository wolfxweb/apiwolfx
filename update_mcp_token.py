#!/usr/bin/env python3
"""
Script para atualizar token no mcp.json
Busca token válido do banco e atualiza o arquivo
"""
import json
import os
import sys
import requests
from pathlib import Path

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent))

from app.config.database import SessionLocal
from app.models.saas_models import Token, MLAccount, MLAccountStatus, Company
from sqlalchemy import desc

def get_valid_token_for_company(company_id: int) -> str:
    """Busca token válido para uma empresa"""
    db = SessionLocal()
    try:
        # Verificar se company existe
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            print(f"❌ Company ID {company_id} não encontrada")
            return None
        
        print(f"✅ Company encontrada: {company.name} (ID: {company.id})")
        
        # Buscar contas ML ativas
        accounts = db.query(MLAccount).filter(
            MLAccount.company_id == company_id,
            MLAccount.status == MLAccountStatus.ACTIVE
        ).all()
        
        if not accounts:
            print(f"❌ Nenhuma conta ML ativa encontrada para company_id {company_id}")
            return None
        
        # Tentar encontrar token válido
        for account in accounts:
            print(f"\n🔍 Buscando token para conta: {account.nickname}")
            
            # Buscar qualquer token
            token = db.query(Token).filter(
                Token.ml_account_id == account.id,
                Token.access_token.isnot(None),
                Token.access_token != ''
            ).order_by(desc(Token.created_at)).first()
            
            if token:
                # Testar token
                print(f"   Testando token...")
                response = requests.get(
                    'https://api.mercadolibre.com/users/me',
                    headers={'Authorization': f'Bearer {token.access_token}'},
                    timeout=5
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    print(f"   ✅ Token VÁLIDO!")
                    print(f"   Usuário ML: {user_data.get('nickname', 'N/A')}")
                    return token.access_token
                else:
                    print(f"   ❌ Token expirado (status: {response.status_code})")
                    
                    # Tentar renovar se houver refresh_token
                    if token.refresh_token:
                        print(f"   🔄 Tentando renovar com refresh_token...")
                        new_token = refresh_token(token.refresh_token)
                        if new_token:
                            print(f"   ✅ Token renovado!")
                            return new_token
        
        print(f"\n⚠️  Nenhum token válido encontrado")
        print(f"   É necessário fazer login via OAuth para obter um novo token")
        return None
        
    finally:
        db.close()

def refresh_token(refresh_token_value: str) -> str:
    """Renova token usando refresh_token"""
    try:
        url = 'https://api.mercadolibre.com/oauth/token'
        data = {
            'grant_type': 'refresh_token',
            'client_id': '6987936494418444',
            'client_secret': 'puvG9Z7XBgICZg5yK3t0PAXAmnco18Tl',
            'refresh_token': refresh_token_value
        }
        
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            return response.json().get('access_token')
        return None
    except Exception as e:
        print(f"   ❌ Erro ao renovar: {e}")
        return None

def update_mcp_json(token: str, company_id: int):
    """Atualiza o arquivo mcp.json com novo token"""
    mcp_path = Path.home() / ".cursor" / "mcp.json"
    
    if not mcp_path.exists():
        print(f"❌ Arquivo mcp.json não encontrado em {mcp_path}")
        return False
    
    try:
        # Ler arquivo atual
        with open(mcp_path, 'r') as f:
            mcp_config = json.load(f)
        
        # Atualizar tokens
        if 'mercadolibre-mcp-server' in mcp_config.get('mcpServers', {}):
            mcp_config['mcpServers']['mercadolibre-mcp-server']['headers']['Authorization'] = f"Bearer {token}"
            mcp_config['mcpServers']['mercadolibre-mcp-server']['headers']['X-Company-ID'] = str(company_id)
        
        if 'mercadopago-mcp-server' in mcp_config.get('mcpServers', {}):
            mcp_config['mcpServers']['mercadopago-mcp-server']['headers']['Authorization'] = f"Bearer {token}"
            mcp_config['mcpServers']['mercadopago-mcp-server']['headers']['X-Company-ID'] = str(company_id)
        
        # Salvar arquivo
        with open(mcp_path, 'w') as f:
            json.dump(mcp_config, f, indent=2)
        
        print(f"\n✅ Arquivo mcp.json atualizado com sucesso!")
        print(f"   Token atualizado")
        print(f"   Company ID: {company_id}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao atualizar mcp.json: {e}")
        return False

if __name__ == "__main__":
    company_id = 15
    
    print("=" * 60)
    print("🔄 ATUALIZANDO TOKEN NO MCP.JSON")
    print("=" * 60)
    print()
    
    # Buscar token válido
    token = get_valid_token_for_company(company_id)
    
    if token:
        # Atualizar arquivo
        success = update_mcp_json(token, company_id)
        if success:
            print(f"\n✅ Processo concluído com sucesso!")
        else:
            print(f"\n❌ Erro ao atualizar arquivo")
    else:
        print(f"\n⚠️  Não foi possível obter token válido")
        print(f"\n📋 Para obter um novo token:")
        print(f"   1. Acesse:")
        print(f"      https://auth.mercadolivre.com.br/authorization?response_type=code&client_id=6987936494418444&redirect_uri=https://9d175879a07f.ngrok-free.app/api/callback")
        print(f"   2. Faça login e autorize a aplicação")
        print(f"   3. Execute este script novamente após o token ser salvo")

