"""
Serviço para integração com a API do Mercado Pago
Implementa checkout transparente e gerenciamento de pagamentos
"""
import requests
import logging
import hashlib
import hmac
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.config.settings import settings
from app.models.payment_models import (
    PaymentRequest, PaymentResponse, PreferenceRequest, PreferenceResponse,
    WebhookNotification, PaymentError
)

logger = logging.getLogger(__name__)


class MercadoPagoService:
    """Serviço principal para integração com Mercado Pago"""
    
    def __init__(self):
        self.access_token = settings.mp_access_token
        self.public_key = settings.mp_public_key
        self.base_url = settings.mp_base_url
        self.sandbox = settings.mp_sandbox
        
        # Headers padrão para requisições
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": ""  # Será definido por método
        }
    
    def _generate_idempotency_key(self, data: Dict[str, Any]) -> str:
        """Gera chave de idempotência baseada nos dados"""
        import json
        import uuid
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Faz requisição para a API do Mercado Pago"""
        url = f"{self.base_url}{endpoint}"
        
        # Configurar headers
        headers = self.headers.copy()
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        
        try:
            logger.info(f"🔗 {method} {url}")
            
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"Método HTTP não suportado: {method}")
            
            logger.info(f"📊 Status: {response.status_code}")
            
            # Log da resposta (sem dados sensíveis)
            if response.status_code >= 400:
                logger.error(f"❌ Erro na API MP: {response.text[:500]}")
                logger.error(f"❌ Status Code: {response.status_code}")
                logger.error(f"❌ URL: {url}")
                logger.error(f"❌ Request Data: {data}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro na requisição para MP: {e}")
            raise e
        except Exception as e:
            logger.error(f"❌ Erro inesperado: {e}")
            raise e
    
    def create_payment(self, payment_data: PaymentRequest) -> PaymentResponse:
        """Cria um pagamento via checkout transparente"""
        try:
            # Preparar dados do pagamento
            mp_payment_data = {
                "transaction_amount": payment_data.transaction_amount,
                "description": payment_data.description,
                "payment_method_id": payment_data.payment_method_id,
                "payer": payment_data.payer,
                "installments": payment_data.installments,
                "token": payment_data.token
            }
            
            # Adicionar issuer_id se fornecido
            if payment_data.issuer_id:
                mp_payment_data["issuer_id"] = payment_data.issuer_id
            
            # Gerar chave de idempotência
            idempotency_key = self._generate_idempotency_key(mp_payment_data)
            
            # Fazer requisição
            response_data = self._make_request(
                "POST", 
                "/v1/payments", 
                mp_payment_data, 
                idempotency_key
            )
            
            logger.info(f"✅ Pagamento criado: ID {response_data.get('id')}")
            return PaymentResponse(**response_data)
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar pagamento: {e}")
            raise e
    
    def create_preference(self, preference_data: PreferenceRequest) -> PreferenceResponse:
        """Cria uma preferência de pagamento"""
        try:
            # Gerar chave de idempotência
            idempotency_key = self._generate_idempotency_key(preference_data.dict())
            
            # Fazer requisição
            response_data = self._make_request(
                "POST", 
                "/checkout/preferences", 
                preference_data.dict(), 
                idempotency_key
            )
            
            logger.info(f"✅ Preferência criada: ID {response_data.get('id')}")
            return PreferenceResponse(**response_data)
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar preferência: {e}")
            raise e
    
    def get_payment(self, payment_id: int) -> PaymentResponse:
        """Busca informações de um pagamento"""
        try:
            response_data = self._make_request("GET", f"/v1/payments/{payment_id}")
            return PaymentResponse(**response_data)
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar pagamento {payment_id}: {e}")
            raise e
    
    def get_payment_by_external_reference(self, external_reference: str) -> List[PaymentResponse]:
        """Busca pagamentos por referência externa"""
        try:
            response_data = self._make_request(
                "GET", 
                f"/v1/payments/search?external_reference={external_reference}"
            )
            
            payments = []
            for payment_data in response_data.get("results", []):
                payments.append(PaymentResponse(**payment_data))
            
            return payments
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar pagamentos por referência {external_reference}: {e}")
            raise e
    
    def cancel_payment(self, payment_id: int) -> PaymentResponse:
        """Cancela um pagamento"""
        try:
            cancel_data = {"status": "cancelled"}
            
            response_data = self._make_request(
                "PUT", 
                f"/v1/payments/{payment_id}", 
                cancel_data
            )
            
            logger.info(f"✅ Pagamento {payment_id} cancelado")
            return PaymentResponse(**response_data)
            
        except Exception as e:
            logger.error(f"❌ Erro ao cancelar pagamento {payment_id}: {e}")
            raise e
    
    def refund_payment(self, payment_id: int, amount: Optional[float] = None) -> PaymentResponse:
        """Estorna um pagamento"""
        try:
            refund_data = {}
            if amount:
                refund_data["amount"] = amount
            
            response_data = self._make_request(
                "POST", 
                f"/v1/payments/{payment_id}/refunds", 
                refund_data
            )
            
            logger.info(f"✅ Pagamento {payment_id} estornado")
            return PaymentResponse(**response_data)
            
        except Exception as e:
            logger.error(f"❌ Erro ao estornar pagamento {payment_id}: {e}")
            raise e
    
    def get_payment_methods(self) -> Dict[str, Any]:
        """Busca métodos de pagamento disponíveis"""
        try:
            response_data = self._make_request("GET", "/v1/payment_methods")
            return response_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar métodos de pagamento: {e}")
            raise e
    
    def get_installments(self, amount: float, payment_method_id: str, 
                        issuer_id: Optional[str] = None) -> Dict[str, Any]:
        """Busca opções de parcelamento"""
        try:
            params = f"amount={amount}&payment_method_id={payment_method_id}"
            if issuer_id:
                params += f"&issuer_id={issuer_id}"
            
            # Endpoint correto para parcelamentos
            response_data = self._make_request("GET", f"/v1/payment_methods/installments?{params}")
            return response_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar parcelamentos: {e}")
            # Retornar parcelamentos padrão se API falhar
            return {
                "payment_method_id": payment_method_id,
                "payment_type_id": "credit_card",
                "payer_costs": [
                    {
                        "installments": 1,
                        "installment_rate": 0,
                        "discount_rate": 0,
                        "labels": [],
                        "min_allowed_amount": 0,
                        "max_allowed_amount": 100000,
                        "recommended_message": "Pagamento à vista",
                        "installment_amount": amount,
                        "total_amount": amount
                    },
                    {
                        "installments": 2,
                        "installment_rate": 0,
                        "discount_rate": 0,
                        "labels": [],
                        "min_allowed_amount": 0,
                        "max_allowed_amount": 100000,
                        "recommended_message": "2x sem juros",
                        "installment_amount": amount / 2,
                        "total_amount": amount
                    }
                ]
            }
    
    def get_card_token_info(self, token: str) -> Dict[str, Any]:
        """Busca informações do token do cartão"""
        try:
            # Nota: Este endpoint pode não estar disponível em todas as versões
            response_data = self._make_request("GET", f"/v1/card_tokens/{token}")
            return response_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar token do cartão: {e}")
            raise e
    
    def validate_webhook_signature(self, payload: str, signature: str) -> bool:
        """Valida a assinatura do webhook"""
        try:
            if not settings.mp_webhook_secret:
                logger.warning("⚠️ Webhook secret não configurado")
                return True  # Permitir em modo de desenvolvimento
            
            # Em modo sandbox, ser mais flexível com a validação
            if self.sandbox and not signature:
                logger.info("✅ Modo sandbox - aceitando webhook sem assinatura")
                return True
            
            if not signature:
                logger.warning("⚠️ Webhook sem assinatura")
                return False
            
            # Gerar assinatura esperada
            expected_signature = hmac.new(
                settings.mp_webhook_secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Mercado Pago usa HMAC SHA256 com prefixo sha256=
            is_valid = hmac.compare_digest(f"sha256={expected_signature}", signature)
            
            if is_valid:
                logger.info("✅ Assinatura do webhook válida")
            else:
                logger.warning(f"⚠️ Assinatura inválida - Esperado: sha256={expected_signature[:20]}..., Recebido: {signature}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"❌ Erro ao validar assinatura do webhook: {e}")
            # Em modo sandbox, aceitar mesmo com erro
            return self.sandbox
    
    def process_webhook_notification(self, notification_data: Dict[str, Any]) -> WebhookNotification:
        """Processa notificação de webhook"""
        try:
            notification = WebhookNotification(**notification_data)
            logger.info(f"📨 Webhook processado: {notification.type} - {notification.action}")
            return notification
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar webhook: {e}")
            raise e
    
    def create_test_payment(self, amount: float = 100.0) -> PaymentResponse:
        """Cria um pagamento de teste (apenas para desenvolvimento)"""
        if not self.sandbox:
            raise ValueError("Pagamentos de teste só são permitidos em modo sandbox")
        
        # Para teste, usar dados de cartão de teste do Mercado Pago
        test_payment_data = {
            "transaction_amount": amount,
            "description": "Pagamento de teste",
            "payment_method_id": "visa",
            "payer": {
                "email": "test@example.com",
                "identification": {
                    "type": "CPF",
                    "number": "12345678901"
                }
            },
            "token": "TEST-1234567890abcdef1234567890abcdef-12345678901234567890123456789012"
        }
        
        # Fazer requisição direta para teste
        response_data = self._make_request("POST", "/v1/payments", test_payment_data)
        return PaymentResponse(**response_data)
    
    def get_merchant_account_info(self) -> Dict[str, Any]:
        """Busca informações da conta do merchant"""
        try:
            response_data = self._make_request("GET", "/v1/account")
            return response_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar informações da conta: {e}")
            raise e


# Instância global do serviço
mercado_pago_service = MercadoPagoService()
