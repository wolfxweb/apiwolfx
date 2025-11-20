"""
Script de teste para integração Asaas
Testa: criação de cliente, cobrança e webhook
"""
import os
import sys
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Carregar variáveis de ambiente do .env
from dotenv import load_dotenv
load_dotenv()

from app.config.settings import Settings

# Configurações
settings = Settings()
ASAAS_API_KEY = settings.asaas_api_key or os.getenv("ASAAS_API_KEY")
BASE_URL = "https://sandbox.asaas.com/api/v3" if not settings.is_production else "https://api.asaas.com/v3"

HEADERS = {
    "access_token": ASAAS_API_KEY,
    "Content-Type": "application/json"
}

# Dados do teste
TEST_CUSTOMER = {
    "name": "Carlos Eduardo",
    "email": "carlos.eduardo@teste.com",
    "cpfCnpj": "00401584976",  # CPF apenas números
    "phone": "(11) 98765-4321",
    "mobilePhone": "(11) 98765-4321",
    "postalCode": "01310-100",
    "address": "Avenida Paulista",
    "addressNumber": "1000",
    "complement": "Sala 100",
    "province": "Bela Vista",
    "city": "São Paulo",
    "state": "SP",
    "country": "Brasil",
    "externalReference": "test_carlos_eduardo"
}

TEST_PAYMENT = {
    "value": 99.90,
    "billingType": "PIX",  # PIX para pagamento imediato
    "dueDate": datetime.now().strftime("%Y-%m-%d"),  # Hoje
    "description": "Teste de integração Asaas - Carlos Eduardo",
    "externalReference": f"test_payment_{datetime.now().strftime('%Y%m%d%H%M%S')}"
}


def print_section(title: str):
    """Imprime um separador visual"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def make_request(method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Faz requisição para API Asaas"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        print(f"🔗 {method} {url}")
        if data:
            print(f"📤 Dados: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        if method.upper() == "GET":
            response = requests.get(url, headers=HEADERS, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=HEADERS, json=data, timeout=30)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=HEADERS, json=data, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=HEADERS, timeout=30)
        else:
            raise ValueError(f"Método HTTP não suportado: {method}")
        
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code >= 400:
            print(f"❌ Erro: {response.text[:500]}")
            response.raise_for_status()
        
        if response.content:
            result = response.json()
            print(f"✅ Resposta: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return result
        return {}
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro na requisição: {e}")
        raise e
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        raise e


def test_find_existing_customer() -> Optional[str]:
    """Testa busca de cliente existente por CPF/CNPJ"""
    print_section("1.1. BUSCANDO CLIENTE EXISTENTE POR CPF/CNPJ")
    
    cpf_cnpj = TEST_CUSTOMER["cpfCnpj"]
    print(f"🔍 Buscando cliente com CPF/CNPJ: {cpf_cnpj}")
    
    try:
        # Buscar por CPF/CNPJ
        result = make_request("GET", f"/customers?cpfCnpj={cpf_cnpj}")
        
        # Asaas retorna {"data": [...]} ou lista direta
        customers = []
        if isinstance(result, dict) and "data" in result:
            customers = result["data"]
        elif isinstance(result, list):
            customers = result
        
        if customers and len(customers) > 0:
            customer = customers[0]
            customer_id = customer.get("id")
            print(f"✅ Cliente existente encontrado!")
            print(f"   ID: {customer_id}")
            print(f"   Nome: {customer.get('name')}")
            print(f"   CPF: {customer.get('cpfCnpj')}")
            print(f"   Email: {customer.get('email')}")
            return customer_id
        else:
            print(f"ℹ️ Nenhum cliente encontrado com CPF/CNPJ: {cpf_cnpj}")
            return None
    except Exception as e:
        print(f"⚠️ Erro ao buscar cliente existente: {e}")
        return None


def test_create_customer() -> str:
    """Testa criação de cliente no Asaas"""
    print_section("1.2. CRIANDO CLIENTE NO ASAAS")
    
    # PRIMEIRO: Verificar se cliente já existe
    print("🔍 Verificando se cliente já existe...")
    existing_customer_id = test_find_existing_customer()
    
    if existing_customer_id:
        print(f"✅ Usando cliente existente: {existing_customer_id}")
        return existing_customer_id
    
    # Se não existe, criar novo
    print("📝 Cliente não encontrado, criando novo cliente...")
    customer_result = make_request("POST", "/customers", TEST_CUSTOMER)
    
    customer_id = customer_result.get("id")
    if not customer_id:
        raise ValueError("Cliente criado mas sem ID retornado")
    
    print(f"✅ Cliente criado com sucesso!")
    print(f"   ID: {customer_id}")
    print(f"   Nome: {customer_result.get('name')}")
    print(f"   CPF: {customer_result.get('cpfCnpj')}")
    print(f"   Email: {customer_result.get('email')}")
    
    return customer_id


def test_create_payment(customer_id: str) -> Dict[str, Any]:
    """Testa criação de cobrança no Asaas"""
    print_section("2. CRIANDO COBRANÇA NO ASAAS")
    
    # Adicionar customer_id ao payment
    payment_data = TEST_PAYMENT.copy()
    payment_data["customer"] = customer_id
    
    print("💳 Criando cobrança...")
    payment_result = make_request("POST", "/payments", payment_data)
    
    payment_id = payment_result.get("id")
    invoice_url = payment_result.get("invoiceUrl") or payment_result.get("invoice_url")
    
    if not payment_id:
        raise ValueError("Cobrança criada mas sem ID retornado")
    
    print(f"✅ Cobrança criada com sucesso!")
    print(f"   ID: {payment_id}")
    print(f"   Valor: R$ {payment_result.get('value', 0):.2f}")
    print(f"   Tipo: {payment_result.get('billingType')}")
    print(f"   Vencimento: {payment_result.get('dueDate')}")
    print(f"   Status: {payment_result.get('status')}")
    
    if invoice_url:
        print(f"   ✅ Invoice URL: {invoice_url}")
        print(f"   🌐 Abra este link no navegador para pagar: {invoice_url}")
    else:
        print(f"   ⚠️ Invoice URL não disponível")
        print(f"   📋 Dados completos: {json.dumps(payment_result, indent=2, ensure_ascii=False)}")
    
    return payment_result


def test_get_payment(payment_id: str):
    """Testa busca de cobrança no Asaas"""
    print_section("3. BUSCANDO COBRANÇA CRIADA")
    
    print(f"🔍 Buscando pagamento {payment_id}...")
    payment = make_request("GET", f"/payments/{payment_id}")
    
    print(f"✅ Pagamento encontrado!")
    print(f"   Status: {payment.get('status')}")
    print(f"   Valor: R$ {payment.get('value', 0):.2f}")
    print(f"   Invoice URL: {payment.get('invoiceUrl') or payment.get('invoice_url', 'N/A')}")


def test_webhook_simulation(payment_data: Dict[str, Any]):
    """Simula webhook do Asaas"""
    print_section("4. SIMULANDO WEBHOOK DO ASAAS")
    
    # Dados que o Asaas enviaria no webhook
    webhook_data = {
        "event": "PAYMENT_CONFIRMED",
        "payment": {
            "id": payment_data.get("id"),
            "customer": payment_data.get("customer"),
            "value": payment_data.get("value"),
            "netValue": payment_data.get("value"),
            "originalValue": payment_data.get("value"),
            "status": "CONFIRMED",
            "billingType": payment_data.get("billingType"),
            "dueDate": payment_data.get("dueDate"),
            "paymentDate": datetime.now().strftime("%Y-%m-%d"),
            "invoiceUrl": payment_data.get("invoiceUrl") or payment_data.get("invoice_url"),
            "externalReference": payment_data.get("externalReference")
        }
    }
    
    print("📨 Dados do webhook que seriam enviados:")
    print(json.dumps(webhook_data, indent=2, ensure_ascii=False))
    
    # Testar processamento do webhook (se tiver endpoint local)
    webhook_url = settings.asaas_webhook_url
    if webhook_url:
        print(f"\n🔗 URL do webhook configurada: {webhook_url}")
        print("💡 Para testar o webhook real, você pode:")
        print("   1. Configurar o webhook no painel do Asaas")
        print("   2. Fazer o pagamento usando o invoiceUrl")
        print("   3. O Asaas enviará o webhook automaticamente")
    else:
        print("⚠️ URL do webhook não configurada em settings")


def main():
    """Executa todos os testes"""
    print("\n" + "🚀" * 40)
    print("  TESTE DE INTEGRAÇÃO ASAAS")
    print("  Cliente: Carlos Eduardo - CPF: 00401584976")
    print("🚀" * 40)
    
    try:
        # Verificar configuração
        if not ASAAS_API_KEY:
            print("❌ ERRO: ASAAS_API_KEY não configurada!")
            print("   Configure no arquivo .env ou settings.py")
            return
        
        print(f"✅ API Key configurada: {ASAAS_API_KEY[:20]}...")
        print(f"✅ Ambiente: {'PRODUÇÃO' if settings.is_production else 'SANDBOX'}")
        print(f"✅ Base URL: {BASE_URL}")
        
        # 1. Buscar ou criar cliente (testa se já existe)
        customer_id = test_create_customer()
        
        # 1.3. Testar busca novamente (deve encontrar o cliente criado)
        print_section("1.3. TESTANDO BUSCA APÓS CRIAÇÃO (deve encontrar o mesmo cliente)")
        found_customer_id = test_find_existing_customer()
        if found_customer_id == customer_id:
            print(f"✅ Teste passou! Cliente encontrado é o mesmo criado: {customer_id}")
        else:
            print(f"⚠️ Atenção: IDs diferentes (criado: {customer_id}, encontrado: {found_customer_id})")
        
        # 2. Criar cobrança
        payment_result = test_create_payment(customer_id)
        payment_id = payment_result.get("id")
        invoice_url = payment_result.get("invoiceUrl") or payment_result.get("invoice_url")
        
        # 3. Buscar cobrança
        if payment_id:
            test_get_payment(payment_id)
        
        # 4. Simular webhook
        test_webhook_simulation(payment_result)
        
        # Resumo final
        print_section("✅ TESTE CONCLUÍDO COM SUCESSO")
        print(f"📋 Resumo:")
        print(f"   Cliente ID: {customer_id}")
        print(f"   Pagamento ID: {payment_id}")
        if invoice_url:
            print(f"   🌐 Link de Pagamento: {invoice_url}")
            print(f"\n💡 PRÓXIMOS PASSOS:")
            print(f"   1. Abra o link acima no navegador")
            print(f"   2. Faça o pagamento (use dados de teste do sandbox)")
            print(f"   3. Verifique se o webhook foi recebido no servidor")
        else:
            print(f"   ⚠️ Invoice URL não disponível - verifique os logs acima")
        
    except Exception as e:
        print_section("❌ ERRO NO TESTE")
        print(f"Erro: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

