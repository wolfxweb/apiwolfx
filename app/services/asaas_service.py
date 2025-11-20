"""
Serviço para integração com a API do Asaas
Implementa assinaturas recorrentes e gerenciamento de pagamentos
"""
import requests
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from app.config.settings import settings

logger = logging.getLogger(__name__)


class AsaasService:
    """Serviço principal para integração com Asaas"""
    
    def __init__(self):
        self.api_key = settings.asaas_api_key
        
        # Asaas usa sandbox.asaas.com para testes
        if settings.is_production:
            self.base_url = "https://api.asaas.com/v3"
            expected_key_prefix = "aact_prod_"
        else:
            self.base_url = "https://sandbox.asaas.com/api/v3"
            expected_key_prefix = "aact_hmlg_"
        
        self.sandbox = not settings.is_production
        
        # Log para debug e validação
        if not self.api_key:
            logger.error("❌ ERRO CRÍTICO: ASAAS_API_KEY não está configurada!")
            if not settings.is_production:
                logger.error("   Para desenvolvimento, use ASAAS_API_KEY_SANDBOX (chave de sandbox)")
                logger.error("   Obtenha em: https://sandbox.asaas.com -> Minha Conta -> Integrações")
            else:
                logger.error("   Para produção, use ASAAS_API_KEY (chave de produção)")
        else:
            # Validar se a chave corresponde ao ambiente
            if not settings.is_production and not self.api_key.startswith("$aact_hmlg_"):
                logger.warning(f"⚠️ ATENÇÃO: Você está usando chave de PRODUÇÃO em ambiente de DESENVOLVIMENTO!")
                logger.warning(f"   Chave detectada: {self.api_key[:30]}...")
                logger.warning(f"   Ambiente: DESENVOLVIMENTO (sandbox)")
                logger.warning(f"   Esperado: chave de SANDBOX (começa com 'aact_hmlg_')")
                logger.warning(f"   Configure ASAAS_API_KEY_SANDBOX no .env para desenvolvimento")
            elif settings.is_production and not self.api_key.startswith("$aact_prod_"):
                logger.warning(f"⚠️ ATENÇÃO: Você está usando chave de SANDBOX em ambiente de PRODUÇÃO!")
                logger.warning(f"   Configure ASAAS_API_KEY no .env para produção")
            else:
                logger.info(f"✅ ASAAS_API_KEY configurada corretamente: {self.api_key[:30]}...")
        
        # Headers padrão para requisições
        # Asaas usa "access_token" no header, não "Authorization"
        self.headers = {
            "access_token": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Validar se o header está correto
        if not self.headers.get("access_token"):
            logger.error("❌ ERRO: access_token não está configurado no header!")
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Faz requisição para a API do Asaas
        
        Args:
            method: Método HTTP (GET, POST, PUT, DELETE)
            endpoint: Endpoint da API (ex: /customers, /subscriptions)
            data: Dados para POST/PUT
        
        Returns:
            Dict com resposta da API
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.info(f"🔗 {method} {url}")
            
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=self.headers, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=self.headers, timeout=30)
            else:
                raise ValueError(f"Método HTTP não suportado: {method}")
            
            logger.info(f"📊 Status: {response.status_code}")
            
            if response.status_code >= 400:
                logger.error(f"❌ Erro na API Asaas: {response.text[:500]}")
                response.raise_for_status()
            
            # Asaas retorna JSON mesmo em caso de sucesso
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro na requisição para Asaas: {e}")
            raise e
        except Exception as e:
            logger.error(f"❌ Erro inesperado: {e}")
            raise e
    
    def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria um cliente no Asaas
        
        Args:
            customer_data: Dados do cliente (nome, email, CPF/CNPJ, etc.)
        
        Returns:
            Dict com dados do cliente criado
        """
        try:
            endpoint = "/customers"
            result = self._make_request("POST", endpoint, customer_data)
            logger.info(f"✅ Cliente criado no Asaas: {result.get('id')}")
            return result
        except Exception as e:
            logger.error(f"❌ Erro ao criar cliente no Asaas: {e}")
            raise e
    
    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """
        Busca dados de um cliente
        
        Args:
            customer_id: ID do cliente no Asaas
        
        Returns:
            Dict com dados do cliente
        """
        try:
            endpoint = f"/customers/{customer_id}"
            return self._make_request("GET", endpoint)
        except Exception as e:
            logger.error(f"❌ Erro ao buscar cliente {customer_id}: {e}")
            raise e
    
    def find_customer_by_cpf_cnpj(self, cpf_cnpj: str) -> Optional[Dict[str, Any]]:
        """
        Busca cliente por CPF/CNPJ no Asaas
        
        Args:
            cpf_cnpj: CPF (11 dígitos) ou CNPJ (14 dígitos)
        
        Returns:
            Dict com dados do cliente se encontrado, None caso contrário
        """
        try:
            # Asaas permite buscar por CPF/CNPJ usando query parameter
            endpoint = f"/customers?cpfCnpj={cpf_cnpj}"
            result = self._make_request("GET", endpoint)
            
            # Asaas retorna {"data": [...]} ou lista direta
            if isinstance(result, dict) and "data" in result:
                customers = result["data"]
                if customers and len(customers) > 0:
                    # Retornar o primeiro cliente encontrado
                    logger.info(f"✅ Cliente encontrado por CPF/CNPJ: {cpf_cnpj}")
                    return customers[0]
            elif isinstance(result, list) and len(result) > 0:
                logger.info(f"✅ Cliente encontrado por CPF/CNPJ: {cpf_cnpj}")
                return result[0]
            
            logger.info(f"ℹ️ Nenhum cliente encontrado com CPF/CNPJ: {cpf_cnpj}")
            return None
        except Exception as e:
            logger.warning(f"⚠️ Erro ao buscar cliente por CPF/CNPJ {cpf_cnpj}: {e}")
            # Não falhar - retornar None para criar novo cliente
            return None
    
    def update_customer(self, customer_id: str, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza dados de um cliente
        
        Args:
            customer_id: ID do cliente no Asaas
            customer_data: Dados atualizados
        
        Returns:
            Dict com dados do cliente atualizado
        """
        try:
            endpoint = f"/customers/{customer_id}"
            return self._make_request("PUT", endpoint, customer_data)
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar cliente {customer_id}: {e}")
            raise e
    
    def create_subscription(self, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria uma assinatura recorrente
        
        Args:
            subscription_data: Dados da assinatura (customer, billingType, value, cycle, etc.)
        
        Returns:
            Dict com dados da assinatura criada
        """
        try:
            endpoint = "/subscriptions"
            result = self._make_request("POST", endpoint, subscription_data)
            logger.info(f"✅ Assinatura criada no Asaas: {result.get('id')}")
            return result
        except Exception as e:
            logger.error(f"❌ Erro ao criar assinatura no Asaas: {e}")
            raise e
    
    def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Busca dados de uma assinatura
        
        Args:
            subscription_id: ID da assinatura no Asaas
        
        Returns:
            Dict com dados da assinatura
        """
        try:
            endpoint = f"/subscriptions/{subscription_id}"
            return self._make_request("GET", endpoint)
        except Exception as e:
            logger.error(f"❌ Erro ao buscar assinatura {subscription_id}: {e}")
            raise e
    
    def update_subscription(self, subscription_id: str, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza uma assinatura
        
        Args:
            subscription_id: ID da assinatura no Asaas
            subscription_data: Dados atualizados
        
        Returns:
            Dict com dados da assinatura atualizada
        """
        try:
            endpoint = f"/subscriptions/{subscription_id}"
            return self._make_request("PUT", endpoint, subscription_data)
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar assinatura {subscription_id}: {e}")
            raise e
    
    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Cancela uma assinatura
        
        Args:
            subscription_id: ID da assinatura no Asaas
        
        Returns:
            Dict com resultado do cancelamento
        """
        try:
            endpoint = f"/subscriptions/{subscription_id}"
            result = self._make_request("DELETE", endpoint)
            logger.info(f"✅ Assinatura {subscription_id} cancelada no Asaas")
            return result
        except Exception as e:
            logger.error(f"❌ Erro ao cancelar assinatura {subscription_id}: {e}")
            raise e
    
    def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria um pagamento no Asaas
        
        Args:
            payment_data: Dados do pagamento (customer, billingType, value, dueDate, etc.)
        
        Returns:
            Dict com dados do pagamento criado (inclui invoiceUrl)
        """
        try:
            endpoint = "/payments"
            result = self._make_request("POST", endpoint, payment_data)
            payment_id = result.get('id')
            invoice_url = result.get('invoiceUrl') or result.get('invoice_url') or result.get('invoiceURL')
            
            logger.info(f"✅ Pagamento criado no Asaas: {payment_id}")
            if invoice_url:
                logger.info(f"✅ Invoice URL retornada pelo Asaas: {invoice_url}")
            else:
                logger.warning(f"⚠️ Invoice URL não encontrada na resposta do pagamento")
                logger.warning(f"⚠️ Chaves disponíveis: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
            
            # Se for PIX, logar resposta completa e tentar buscar QR Code
            if payment_data.get("billingType") == "PIX" and payment_id:
                logger.info(f"🔍 Pagamento PIX criado - Verificando QR Code...")
                logger.info(f"📋 Resposta completa do pagamento PIX: {json.dumps(result, indent=2, default=str)}")
                
                # Verificar se já tem QR Code na resposta inicial
                pix_qr_code_initial = result.get("pixQrCode") or result.get("pixQrCodeBase64")
                pix_copia_cola_initial = result.get("pixCopiaECola")
                
                if pix_qr_code_initial:
                    logger.info(f"✅ QR Code PIX encontrado na resposta inicial!")
                    result["pixQrCode"] = pix_qr_code_initial
                    result["pixCopiaECola"] = pix_copia_cola_initial
                else:
                    logger.warning(f"⚠️ QR Code PIX não encontrado na resposta inicial, tentando buscar detalhes...")
            
            # Se for PIX, buscar QR Code usando o endpoint específico da documentação
            # Documentação: https://docs.asaas.com/docs/pix
            # Endpoint: GET /v3/payments/{id}/pixQrCode
            if payment_data.get("billingType") == "PIX" and payment_id and not result.get("pixQrCode"):
                try:
                    import time
                    # Aguardar um pouco para o QR Code ser gerado (conforme documentação)
                    time.sleep(2)
                    
                    # Usar o endpoint específico para obter QR Code PIX
                    logger.info(f"🔍 Buscando QR Code PIX usando endpoint específico: /payments/{payment_id}/pixQrCode")
                    pix_qr_code_data = self.get_pix_qr_code(payment_id)
                    
                    if pix_qr_code_data:
                        # Segundo a documentação, o endpoint retorna:
                        # - payload: Código Pix Copia e Cola
                        # - qrCodeBase64: Imagem do QR Code em Base64
                        # - expirationDate: Data de expiração
                        payload = pix_qr_code_data.get("payload") or pix_qr_code_data.get("pixCopiaECola")
                        qr_code_base64 = pix_qr_code_data.get("qrCodeBase64") or pix_qr_code_data.get("pixQrCodeBase64")
                        expiration_date = pix_qr_code_data.get("expirationDate")
                        
                        if payload or qr_code_base64:
                            result["pixQrCode"] = qr_code_base64
                            result["pixCopiaECola"] = payload
                            result["pixExpirationDate"] = expiration_date
                            logger.info(f"✅ QR Code PIX obtido com sucesso!")
                            logger.info(f"   Payload (Copia e Cola): {payload[:50] if payload else 'N/A'}...")
                            logger.info(f"   Expiração: {expiration_date or 'N/A'}")
                        else:
                            logger.warning(f"⚠️ QR Code PIX não encontrado na resposta do endpoint")
                            logger.warning(f"📋 Resposta completa: {json.dumps(pix_qr_code_data, indent=2, default=str)}")
                    else:
                        logger.warning(f"⚠️ Resposta vazia ao buscar QR Code PIX")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao buscar QR Code PIX: {e}")
                    logger.warning(f"⚠️ O QR Code estará disponível na invoiceUrl: {invoice_url}")
                    import traceback
                    logger.warning(traceback.format_exc())
            
            return result
        except Exception as e:
            logger.error(f"❌ Erro ao criar pagamento no Asaas: {e}")
            raise e
    
    def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Busca detalhes de um pagamento no Asaas
        
        Args:
            payment_id: ID do pagamento no Asaas
        
        Returns:
            Dict com dados do pagamento
        """
        try:
            endpoint = f"/payments/{payment_id}"
            result = self._make_request("GET", endpoint)
            logger.info(f"✅ Detalhes do pagamento {payment_id} obtidos")
            return result
        except Exception as e:
            logger.error(f"❌ Erro ao buscar pagamento {payment_id}: {e}")
            raise e
    
    def get_pix_qr_code(self, payment_id: str) -> Dict[str, Any]:
        """
        Busca o QR Code PIX de um pagamento no Asaas
        Segundo a documentação: https://docs.asaas.com/docs/pix
        Endpoint: GET /v3/payments/{id}/pixQrCode
        
        Args:
            payment_id: ID do pagamento no Asaas
        
        Returns:
            Dict com dados do QR Code PIX:
            - payload: Código Pix Copia e Cola
            - qrCodeBase64: Imagem do QR Code em Base64
            - expirationDate: Data de expiração do QR Code
        """
        try:
            endpoint = f"/payments/{payment_id}/pixQrCode"
            result = self._make_request("GET", endpoint)
            logger.info(f"✅ QR Code PIX obtido para pagamento {payment_id}")
            return result
        except Exception as e:
            logger.error(f"❌ Erro ao buscar QR Code PIX do pagamento {payment_id}: {e}")
            raise e
    
    def get_subscription_payments(self, subscription_id: str) -> List[Dict[str, Any]]:
        """
        Lista pagamentos de uma assinatura
        
        Args:
            subscription_id: ID da assinatura no Asaas
        
        Returns:
            Lista de pagamentos
        """
        try:
            endpoint = f"/subscriptions/{subscription_id}/payments"
            result = self._make_request("GET", endpoint)
            # Asaas retorna {"data": [...]} ou lista direta
            if isinstance(result, dict) and "data" in result:
                return result["data"]
            elif isinstance(result, list):
                return result
            return []
        except Exception as e:
            logger.error(f"❌ Erro ao buscar pagamentos da assinatura {subscription_id}: {e}")
            raise e
    
    def get_customer_payments(self, customer_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Lista TODOS os pagamentos de um cliente (pendentes, pagos, vencidos, etc.)
        
        Args:
            customer_id: ID do cliente no Asaas
            limit: Número máximo de pagamentos a retornar (padrão: 100)
        
        Returns:
            Lista de pagamentos com todos os status
        """
        try:
            all_payments = []
            offset = 0
            page_size = 100  # Asaas permite até 100 por página
            
            while True:
                # Buscar pagamentos com paginação
                endpoint = f"/payments?customer={customer_id}&limit={page_size}&offset={offset}"
                result = self._make_request("GET", endpoint)
                
                # Asaas retorna {"data": [...], "hasMore": bool} ou lista direta
                payments = []
                has_more = False
                
                if isinstance(result, dict):
                    if "data" in result:
                        payments = result["data"]
                        has_more = result.get("hasMore", False)
                    else:
                        # Se não tem "data", pode ser que seja a lista direta
                        payments = result if isinstance(result, list) else []
                elif isinstance(result, list):
                    payments = result
                
                if payments:
                    all_payments.extend(payments)
                    logger.info(f"📄 Buscados {len(payments)} pagamentos (offset: {offset}, total: {len(all_payments)})")
                
                # Se não há mais páginas ou atingiu o limite, parar
                if not has_more or len(all_payments) >= limit:
                    break
                
                offset += page_size
                
                # Limite de segurança para evitar loop infinito
                if offset > 10000:
                    logger.warning(f"⚠️ Limite de paginação atingido para cliente {customer_id}")
                    break
            
            logger.info(f"✅ Total de {len(all_payments)} pagamentos encontrados para cliente {customer_id}")
            return all_payments[:limit]  # Retornar até o limite especificado
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar pagamentos do cliente {customer_id}: {e}")
            raise e
    
    def validate_webhook(self, payload: str, signature: Optional[str] = None) -> bool:
        """
        Valida webhook do Asaas
        
        Args:
            payload: Corpo da requisição
            signature: Assinatura do webhook (se aplicável)
        
        Returns:
            True se válido
        """
        # Asaas pode usar token de webhook para validação
        # Por enquanto, retorna True (implementar validação se necessário)
        if settings.asaas_webhook_token:
            # Implementar validação com token se necessário
            pass
        return True
    
    def process_webhook_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa notificação de webhook do Asaas
        
        Args:
            notification_data: Dados da notificação
        
        Returns:
            Dict com dados processados
        """
        try:
            # Validar que é um dicionário
            if not isinstance(notification_data, dict):
                logger.error(f"❌ notification_data não é um dicionário: {type(notification_data)}")
                raise ValueError(f"notification_data deve ser um dicionário, recebido: {type(notification_data)}")
            
            event = notification_data.get("event")
            payment_data = notification_data.get("payment", {}) or {}
            
            # Se payment_data não for um dicionário, tentar extrair de outra forma
            if not isinstance(payment_data, dict):
                logger.warning(f"⚠️ payment_data não é um dicionário: {type(payment_data)}, tentando extrair...")
                payment_data = {}
            
            logger.info(f"📨 Webhook Asaas recebido: {event}")
            
            # O Asaas pode enviar subscription diretamente no webhook
            subscription_data = notification_data.get("subscription", {}) or {}
            if not isinstance(subscription_data, dict):
                subscription_data = {}
            
            subscription_id = subscription_data.get("id") or payment_data.get("subscription")
            
            return {
                "event": event,
                "payment_id": payment_data.get("id"),
                "subscription_id": subscription_id,
                "status": payment_data.get("status"),
                "value": payment_data.get("value"),
                "dueDate": payment_data.get("dueDate"),
                "paymentDate": payment_data.get("paymentDate"),
                "data": notification_data
            }
        except Exception as e:
            logger.error(f"❌ Erro ao processar webhook do Asaas: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise e


# Instância global do serviço
asaas_service = AsaasService()

