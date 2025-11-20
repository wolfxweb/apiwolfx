"""
Script de teste específico para pagamento PIX no Asaas
Testa criação de pagamento PIX e verifica se o QR Code é gerado
"""
import os
import sys
import requests
import json
import time
from datetime import datetime

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

def print_section(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")

def make_request(method: str, endpoint: str, data: dict = None) -> dict:
    """Faz requisição para API do Asaas"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=HEADERS, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=HEADERS, json=data, timeout=30)
        else:
            raise ValueError(f"Método não suportado: {method}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"❌ Erro HTTP: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Resposta: {e.response.text[:500]}")
        raise
    except Exception as e:
        print(f"❌ Erro: {e}")
        raise

def test_find_or_create_customer() -> str:
    """Busca ou cria cliente no Asaas"""
    print_section("1. BUSCANDO/CRIANDO CLIENTE")
    
    cpf_cnpj = "00401584976"
    
    # Tentar buscar cliente existente
    print(f"🔍 Buscando cliente com CPF/CNPJ: {cpf_cnpj}")
    try:
        result = make_request("GET", f"/customers?cpfCnpj={cpf_cnpj}")
        customers = result.get("data", [])
        
        if customers and len(customers) > 0:
            customer = customers[0]
            customer_id = customer.get("id")
            print(f"✅ Cliente existente encontrado: {customer_id}")
            print(f"   Nome: {customer.get('name')}")
            return customer_id
    except Exception as e:
        print(f"⚠️ Erro ao buscar cliente: {e}")
    
    # Criar novo cliente
    print("📝 Criando novo cliente...")
    customer_data = {
        "name": "Teste PIX",
        "email": "teste.pix@example.com",
        "cpfCnpj": cpf_cnpj,
        "phone": "(11) 98765-4321",
        "mobilePhone": "(11) 98765-4321",
        "postalCode": "01310100",
        "address": "Avenida Paulista",
        "addressNumber": "1000",
        "complement": "Sala 100",
        "province": "Bela Vista",
        "city": "São Paulo",
        "state": "SP",
        "country": "Brasil"
    }
    
    customer_result = make_request("POST", "/customers", customer_data)
    customer_id = customer_result.get("id")
    
    if not customer_id:
        raise ValueError("Cliente criado mas sem ID retornado")
    
    print(f"✅ Cliente criado: {customer_id}")
    return customer_id

def test_create_pix_payment(customer_id: str):
    """Testa criação de pagamento PIX"""
    print_section("2. CRIANDO PAGAMENTO PIX")
    
    # Criar pagamento PIX
    payment_data = {
        "customer": customer_id,
        "billingType": "PIX",
        "value": 99.90,
        "dueDate": datetime.now().strftime("%Y-%m-%d"),
        "description": "Teste PIX - QR Code",
        "externalReference": f"test_pix_{int(time.time())}"
    }
    
    print(f"📤 Dados do pagamento:")
    print(json.dumps(payment_data, indent=2, ensure_ascii=False))
    print()
    
    payment_result = make_request("POST", "/payments", payment_data)
    
    payment_id = payment_result.get("id")
    if not payment_id:
        raise ValueError("Pagamento criado mas sem ID retornado")
    
    print(f"✅ Pagamento PIX criado!")
    print(f"   ID: {payment_id}")
    print(f"   Status: {payment_result.get('status')}")
    print(f"   Valor: R$ {payment_result.get('value', 0):.2f}")
    print(f"   Vencimento: {payment_result.get('dueDate')}")
    print()
    
    # Verificar resposta completa
    print("📋 Resposta completa do pagamento:")
    print(json.dumps(payment_result, indent=2, ensure_ascii=False, default=str))
    print()
    
    # Verificar QR Code na resposta inicial
    pix_qr_code = (
        payment_result.get("pixQrCode") or 
        payment_result.get("pixQrCodeBase64") or
        payment_result.get("pixQrCodeImage") or
        payment_result.get("qrCode")
    )
    pix_copia_cola = (
        payment_result.get("pixCopiaECola") or 
        payment_result.get("pixCopyPaste") or
        payment_result.get("copiaECola")
    )
    
    if pix_qr_code:
        print(f"✅ QR Code encontrado na resposta inicial!")
        print(f"   QR Code: {pix_qr_code[:100]}...")
        if pix_copia_cola:
            print(f"   Copia e Cola: {pix_copia_cola[:100]}...")
    else:
        print(f"⚠️ QR Code NÃO encontrado na resposta inicial")
        print(f"   Chaves disponíveis: {list(payment_result.keys())}")
    
    # Verificar invoiceUrl
    invoice_url = (
        payment_result.get("invoiceUrl") or 
        payment_result.get("invoice_url") or
        payment_result.get("invoiceURL")
    )
    
    if invoice_url:
        print(f"✅ Invoice URL: {invoice_url}")
    else:
        print(f"⚠️ Invoice URL não encontrada")
    
    return payment_id, payment_result

def test_get_payment_details(payment_id: str, max_retries: int = 5):
    """Busca detalhes do pagamento com múltiplas tentativas"""
    print_section("3. BUSCANDO DETALHES DO PAGAMENTO")
    
    for attempt in range(1, max_retries + 1):
        print(f"\n🔄 Tentativa {attempt}/{max_retries}...")
        
        if attempt > 1:
            wait_time = attempt
            print(f"   Aguardando {wait_time} segundos...")
            time.sleep(wait_time)
        
        try:
            payment_details = make_request("GET", f"/payments/{payment_id}")
            
            print(f"📋 Detalhes do pagamento (tentativa {attempt}):")
            print(json.dumps(payment_details, indent=2, ensure_ascii=False, default=str))
            print()
            
            # Verificar QR Code
            pix_qr_code = (
                payment_details.get("pixQrCode") or 
                payment_details.get("pixQrCodeBase64") or
                payment_details.get("pixQrCodeImage") or
                payment_details.get("qrCode")
            )
            pix_copia_cola = (
                payment_details.get("pixCopiaECola") or 
                payment_details.get("pixCopyPaste") or
                payment_details.get("copiaECola")
            )
            
            if pix_qr_code:
                print(f"✅ QR Code encontrado na tentativa {attempt}!")
                print(f"   QR Code: {pix_qr_code[:100]}...")
                if pix_copia_cola:
                    print(f"   Copia e Cola: {pix_copia_cola[:100]}...")
                return payment_details
            else:
                print(f"⚠️ QR Code ainda não disponível (tentativa {attempt})")
                print(f"   Status: {payment_details.get('status')}")
                print(f"   Chaves disponíveis: {list(payment_details.keys())}")
                
                # Verificar erros
                errors = payment_details.get("errors") or payment_details.get("error")
                if errors:
                    print(f"   ❌ Erros: {json.dumps(errors, indent=2, ensure_ascii=False)}")
                
        except Exception as e:
            print(f"❌ Erro ao buscar detalhes: {e}")
            if attempt < max_retries:
                continue
            else:
                raise
    
    print(f"\n❌ QR Code não foi gerado após {max_retries} tentativas")
    return None

if __name__ == "__main__":
    try:
        print("\n" + "=" * 80)
        print("  TESTE DE PAGAMENTO PIX NO ASAAS")
        print("=" * 80)
        
        # 1. Buscar ou criar cliente
        customer_id = test_find_or_create_customer()
        
        # 2. Criar pagamento PIX
        payment_id, payment_result = test_create_pix_payment(customer_id)
        
        # 3. Buscar detalhes do pagamento (com retry)
        payment_details = test_get_payment_details(payment_id, max_retries=5)
        
        # Resumo final
        print_section("4. RESUMO FINAL")
        
        invoice_url = (
            payment_result.get("invoiceUrl") or 
            payment_result.get("invoice_url") or
            payment_result.get("invoiceURL")
        )
        
        if invoice_url:
            print(f"🌐 Invoice URL: {invoice_url}")
            print(f"   Abra este link no navegador para ver o QR Code")
        
        if payment_details:
            pix_qr_code = (
                payment_details.get("pixQrCode") or 
                payment_details.get("pixQrCodeBase64") or
                payment_details.get("pixQrCodeImage") or
                payment_details.get("qrCode")
            )
            
            if pix_qr_code:
                print(f"✅ QR Code PIX foi gerado com sucesso!")
            else:
                print(f"❌ QR Code PIX NÃO foi gerado")
                print(f"   Verifique se a chave PIX está cadastrada no sandbox do Asaas")
                print(f"   Verifique os logs acima para mais detalhes")
        
    except Exception as e:
        print(f"\n❌ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

