#!/usr/bin/env python3
"""
Script para verificar tokens no banco
"""
import sys
import os
sys.path.append('/app')

from app.config.database import get_db
from app.models.saas_models import Token, MLAccount

def check_tokens():
    """Verifica tokens disponíveis"""
    print("🔍 Verificando tokens no banco...")
    
    # Obter sessão do banco
    db = next(get_db())
    
    try:
        # Buscar contas ML da company_id 15
        accounts = db.query(MLAccount).filter(MLAccount.company_id == 15).all()
        print(f"📋 Encontradas {len(accounts)} contas ML para company_id 15:")
        
        for account in accounts:
            print(f"  - Account ID: {account.id}, Nickname: {account.nickname}, Status: {account.status}")
            
            # Buscar tokens para esta conta
            tokens = db.query(Token).filter(Token.ml_account_id == account.id).order_by(Token.created_at.desc()).limit(3).all()
            print(f"    Tokens encontrados: {len(tokens)}")
            
            for token in tokens:
                print(f"      - Token ID: {token.id}, Created: {token.created_at}")
                print(f"        Access Token: {token.access_token[:20] if token.access_token else 'None'}...")
                print(f"        Refresh Token: {token.refresh_token[:20] if token.refresh_token else 'None'}...")
                print(f"        Expires: {token.expires_at}")
                print()
        
        # Buscar todos os tokens da company_id 15
        print("🔍 Buscando todos os tokens da company_id 15...")
        tokens = db.query(Token).join(MLAccount).filter(MLAccount.company_id == 15).order_by(Token.created_at.desc()).limit(5).all()
        
        for token in tokens:
            print(f"  - Token ID: {token.id}, ML Account ID: {token.ml_account_id}")
            print(f"    Access: {token.access_token[:30] if token.access_token else 'None'}...")
            print(f"    Refresh: {token.refresh_token[:30] if token.refresh_token else 'None'}...")
            print(f"    Expires: {token.expires_at}")
            print()
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
    
    finally:
        db.close()

if __name__ == "__main__":
    check_tokens()
