"""
Script para testar a API de mensagens do Mercado Livre
"""
import requests
import sys
from app.config.database import SessionLocal
from app.services.token_manager import TokenManager

def test_messages_api():
    db = SessionLocal()
    try:
        # Buscar token válido (assumindo company_id 15, user_id do primeiro usuário)
        from app.models.saas_models import Company, User, MLAccount
        
        company = db.query(Company).filter(Company.id == 15).first()
        if not company:
            print("❌ Company 15 não encontrada")
            return
        
        user = db.query(User).filter(User.company_id == 15).first()
        if not user:
            print("❌ Nenhum usuário encontrado para company 15")
            return
        
        print(f"✅ Usuário encontrado: {user.email} (ID: {user.id})")
        
        token_manager = TokenManager(db)
        access_token = token_manager.get_valid_token(user.id)
        
        if not access_token:
            print("❌ Token não encontrado ou expirado")
            return
        
        print(f"✅ Token obtido: {access_token[:20]}...")
        
        # Buscar ML Account
        ml_account = db.query(MLAccount).filter(
            MLAccount.company_id == 15,
            MLAccount.status == 'ACTIVE'
        ).first()
        
        if not ml_account:
            print("❌ Nenhuma conta ML ativa encontrada")
            return
        
        ml_user_id = str(ml_account.ml_user_id)
        print(f"✅ ML Account encontrada: {ml_account.nickname} (ML User ID: {ml_user_id})")
        
        # Testar API
        base_url = "https://api.mercadolibre.com"
        url = f"{base_url}/messages/packages/search"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        params = {
            "seller_id": ml_user_id,
            "limit": 50,
            "offset": 0
        }
        
        print(f"\n📡 Testando endpoint: {url}")
        print(f"📡 Parâmetros: {params}")
        print(f"📡 Headers Authorization: Bearer {access_token[:30]}...\n")
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📊 Headers: {dict(response.headers)}\n")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Resposta recebida:")
            print(f"   - Chaves principais: {list(data.keys())}")
            
            packages = data.get("results", [])
            print(f"   - Total de pacotes: {len(packages)}")
            
            if "paging" in data:
                print(f"   - Paging: {data['paging']}")
            
            if packages:
                print(f"\n📦 Primeiro pacote:")
                print(f"   - Chaves: {list(packages[0].keys())}")
                print(f"   - Dados: {packages[0]}")
            else:
                print("\n⚠️ Nenhum pacote encontrado na resposta")
        else:
            print(f"❌ Erro na resposta:")
            print(f"   - Status: {response.status_code}")
            print(f"   - Texto: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Erro: {e}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    test_messages_api()
