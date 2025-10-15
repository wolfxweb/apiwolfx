"""
Teste simples da integração Mercado Pago
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.mercado_pago_service import mercado_pago_service
from app.models.payment_models import PreferenceRequest

def test_basic_functionality():
    """Testa funcionalidades básicas"""
    print("🚀 Testando integração Mercado Pago - Funcionalidades Básicas\n")
    
    try:
        # 1. Testar métodos de pagamento
        print("1️⃣ Testando métodos de pagamento...")
        methods = mercado_pago_service.get_payment_methods()
        print(f"✅ {len(methods)} métodos de pagamento encontrados")
        
        # Listar alguns métodos
        for method in methods[:5]:
            print(f"   - {method.get('name', 'N/A')} ({method.get('id', 'N/A')})")
        
        # 2. Testar criação de preferência
        print("\n2️⃣ Testando criação de preferência...")
        preference_data = PreferenceRequest(
            items=[
                {
                    "title": "Plano Pro WolfX",
                    "quantity": 1,
                    "unit_price": 59.90
                }
            ],
            payer={
                "email": "cliente@wolfx.com.br",
                "name": "Cliente Teste"
            },
            back_urls={
                "success": "https://wolfx.com.br/payment/success",
                "failure": "https://wolfx.com.br/payment/failure",
                "pending": "https://wolfx.com.br/payment/pending"
            },
            external_reference="test_wolfx_001"
        )
        
        preference = mercado_pago_service.create_preference(preference_data)
        print(f"✅ Preferência criada com sucesso!")
        print(f"   ID: {preference.id}")
        print(f"   URL: {preference.init_point}")
        
        print("\n🎉 Testes básicos passaram com sucesso!")
        print("\n📋 Status da Integração:")
        print("✅ Conexão com API: OK")
        print("✅ Métodos de pagamento: OK")
        print("✅ Criação de preferências: OK")
        
        print("\n🔗 Próximos passos:")
        print("1. Acesse a URL da preferência para testar o checkout")
        print("2. Configure webhooks no painel do Mercado Pago")
        print("3. Teste o frontend em /checkout-example.html")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro nos testes: {e}")
        return False

if __name__ == "__main__":
    success = test_basic_functionality()
    
    if success:
        print("\n🚀 Integração Mercado Pago pronta para uso!")
    else:
        print("\n❌ Verifique as configurações e tente novamente")
