"""
Script de teste para verificar integração com Mercado Pago
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.mercado_pago_service import mercado_pago_service
from app.models.payment_models import PaymentRequest, PreferenceRequest

def test_mercado_pago_connection():
    """Testa conexão com Mercado Pago"""
    print("🧪 Testando conexão com Mercado Pago...")
    
    try:
        # Testar métodos de pagamento
        print("\n1️⃣ Testando métodos de pagamento...")
        methods = mercado_pago_service.get_payment_methods()
        print(f"✅ {len(methods)} métodos de pagamento encontrados")
        
        # Testar parcelamentos
        print("\n2️⃣ Testando parcelamentos...")
        installments = mercado_pago_service.get_installments(100.0, "credit_card")
        print(f"✅ Opções de parcelamento carregadas")
        
        # Testar criação de preferência
        print("\n3️⃣ Testando criação de preferência...")
        preference_data = PreferenceRequest(
            items=[
                {
                    "title": "Teste WolfX Pro",
                    "quantity": 1,
                    "unit_price": 59.90
                }
            ],
            payer={
                "email": "teste@wolfx.com.br"
            },
            back_urls={
                "success": "https://wolfx.com.br/success",
                "failure": "https://wolfx.com.br/failure",
                "pending": "https://wolfx.com.br/pending"
            },
            external_reference="test_preference_001"
        )
        
        preference = mercado_pago_service.create_preference(preference_data)
        print(f"✅ Preferência criada: {preference.id}")
        print(f"🔗 URL de pagamento: {preference.init_point}")
        
        # Testar pagamento de teste (apenas em sandbox)
        if mercado_pago_service.sandbox:
            print("\n4️⃣ Testando pagamento de teste...")
            test_payment = mercado_pago_service.create_test_payment(10.0)
            print(f"✅ Pagamento de teste criado: {test_payment.id}")
            print(f"📊 Status: {test_payment.status}")
        
        print("\n🎉 Todos os testes passaram com sucesso!")
        return True
        
    except Exception as e:
        print(f"\n❌ Erro nos testes: {e}")
        return False

def test_payment_flow():
    """Testa fluxo completo de pagamento"""
    print("\n🔄 Testando fluxo de pagamento...")
    
    try:
        # 1. Criar preferência
        preference_data = PreferenceRequest(
            items=[
                {
                    "title": "Plano Pro WolfX",
                    "quantity": 1,
                    "unit_price": 59.90
                }
            ],
            payer={
                "email": "cliente@exemplo.com",
                "name": "Cliente Teste"
            },
            external_reference="subscription_test_001"
        )
        
        preference = mercado_pago_service.create_preference(preference_data)
        print(f"✅ Preferência criada: {preference.id}")
        
        # 2. Simular webhook de pagamento aprovado
        webhook_data = {
            "id": 1234567890,
            "live_mode": False,
            "type": "payment",
            "date_created": "2024-01-15T10:30:00.000Z",
            "application_id": 1234567890,
            "user_id": 987654321,
            "version": 1,
            "api_version": "v1",
            "action": "payment.created",
            "data": {
                "id": str(preference.id)
            }
        }
        
        notification = mercado_pago_service.process_webhook_notification(webhook_data)
        print(f"✅ Webhook processado: {notification.type}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no fluxo de pagamento: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando testes de integração Mercado Pago\n")
    
    # Teste de conexão
    connection_ok = test_mercado_pago_connection()
    
    if connection_ok:
        # Teste de fluxo
        flow_ok = test_payment_flow()
        
        if flow_ok:
            print("\n🎉 Integração Mercado Pago funcionando perfeitamente!")
            print("\n📋 Próximos passos:")
            print("1. Acesse http://localhost:8000/checkout-example.html para testar o frontend")
            print("2. Configure webhooks no painel do Mercado Pago")
            print("3. Teste pagamentos reais em modo sandbox")
        else:
            print("\n⚠️ Fluxo de pagamento com problemas")
    else:
        print("\n❌ Conexão com Mercado Pago falhou")
        print("Verifique as credenciais e conexão com a internet")

