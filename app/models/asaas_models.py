"""
Modelos Pydantic para integração com Asaas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AsaasBillingType(str, Enum):
    """Tipos de cobrança do Asaas"""
    BOLETO = "BOLETO"
    CREDIT_CARD = "CREDIT_CARD"
    PIX = "PIX"
    DEBIT_CARD = "DEBIT_CARD"
    UNDEFINED = "UNDEFINED"


class AsaasCycle(str, Enum):
    """Ciclos de cobrança recorrente"""
    WEEKLY = "WEEKLY"  # Semanal
    BIWEEKLY = "BIWEEKLY"  # Quinzenal
    MONTHLY = "MONTHLY"  # Mensal
    QUARTERLY = "QUARTERLY"  # Trimestral
    SEMIANNUALLY = "SEMIANNUALLY"  # Semestral
    YEARLY = "YEARLY"  # Anual


class AsaasPaymentStatus(str, Enum):
    """Status de pagamento do Asaas"""
    PENDING = "PENDING"  # Aguardando
    CONFIRMED = "CONFIRMED"  # Confirmado
    RECEIVED = "RECEIVED"  # Recebido
    OVERDUE = "OVERDUE"  # Vencido
    REFUNDED = "REFUNDED"  # Estornado
    RECEIVED_IN_CASH_UNDONE = "RECEIVED_IN_CASH_UNDONE"  # Recebido em dinheiro desfeito
    CHARGEBACK_REQUESTED = "CHARGEBACK_REQUESTED"  # Chargeback solicitado
    CHARGEBACK_DISPUTE = "CHARGEBACK_DISPUTE"  # Chargeback em disputa
    AWAITING_CHARGEBACK_REVERSAL = "AWAITING_CHARGEBACK_REVERSAL"  # Aguardando reversão
    DUNNING_REQUESTED = "DUNNING_REQUESTED"  # Negativação solicitada
    DUNNING_RECEIVED = "DUNNING_RECEIVED"  # Negativação recebida
    AWAITING_RISK_ANALYSIS = "AWAITING_RISK_ANALYSIS"  # Aguardando análise de risco


class AsaasCreateCustomerRequest(BaseModel):
    """Request para criar cliente no Asaas"""
    name: str = Field(..., description="Nome completo ou razão social")
    email: str = Field(..., description="Email do cliente")
    phone: Optional[str] = Field(None, description="Telefone (formato: (00) 00000-0000)")
    mobilePhone: Optional[str] = Field(None, description="Celular (formato: (00) 00000-0000)")
    cpfCnpj: Optional[str] = Field(None, description="CPF ou CNPJ (apenas números)")
    postalCode: Optional[str] = Field(None, description="CEP (apenas números)")
    address: Optional[str] = Field(None, description="Endereço")
    addressNumber: Optional[str] = Field(None, description="Número do endereço")
    complement: Optional[str] = Field(None, description="Complemento")
    province: Optional[str] = Field(None, description="Bairro")
    city: Optional[str] = Field(None, description="Cidade")
    state: Optional[str] = Field(None, description="Estado (UF)")
    country: Optional[str] = Field("Brasil", description="País")
    externalReference: Optional[str] = Field(None, description="Referência externa (ID do usuário/empresa)")
    notificationDisabled: Optional[bool] = Field(False, description="Desabilitar notificações")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "João Silva",
                "email": "joao@exemplo.com",
                "phone": "(11) 98765-4321",
                "cpfCnpj": "12345678901",
                "postalCode": "01310100",
                "address": "Av. Paulista",
                "addressNumber": "1000",
                "complement": "Apto 101",
                "province": "Bela Vista",
                "city": "São Paulo",
                "state": "SP",
                "externalReference": "user_123"
            }
        }


class AsaasCreateSubscriptionRequest(BaseModel):
    """Request para criar assinatura recorrente no Asaas"""
    customer: str = Field(..., description="ID do cliente no Asaas")
    billingType: AsaasBillingType = Field(..., description="Tipo de cobrança")
    value: float = Field(..., description="Valor da assinatura")
    nextDueDate: str = Field(..., description="Data do próximo vencimento (YYYY-MM-DD)")
    cycle: AsaasCycle = Field(..., description="Ciclo de cobrança")
    description: str = Field(..., description="Descrição da assinatura")
    endDate: Optional[str] = Field(None, description="Data de término (YYYY-MM-DD)")
    externalReference: Optional[str] = Field(None, description="Referência externa")
    creditCard: Optional[Dict[str, Any]] = Field(None, description="Dados do cartão de crédito")
    creditCardHolderInfo: Optional[Dict[str, Any]] = Field(None, description="Dados do portador do cartão")
    creditCardToken: Optional[str] = Field(None, description="Token do cartão (se já tokenizado)")
    remoteIp: Optional[str] = Field(None, description="IP do cliente")
    
    class Config:
        json_schema_extra = {
            "example": {
                "customer": "cus_000000000000",
                "billingType": "CREDIT_CARD",
                "value": 99.90,
                "nextDueDate": "2024-02-01",
                "cycle": "MONTHLY",
                "description": "Assinatura Plano Pro - Mensal",
                "externalReference": "subscription_123"
            }
        }


class AsaasCustomerResponse(BaseModel):
    """Response do cliente criado no Asaas"""
    id: str = Field(..., description="ID do cliente")
    dateCreated: str = Field(..., description="Data de criação")
    name: str = Field(..., description="Nome")
    email: str = Field(..., description="Email")
    phone: Optional[str] = None
    mobilePhone: Optional[str] = None
    cpfCnpj: Optional[str] = None
    postalCode: Optional[str] = None
    address: Optional[str] = None
    addressNumber: Optional[str] = None
    complement: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    externalReference: Optional[str] = None


class AsaasSubscriptionResponse(BaseModel):
    """Response da assinatura criada no Asaas"""
    id: str = Field(..., description="ID da assinatura")
    dateCreated: str = Field(..., description="Data de criação")
    customer: str = Field(..., description="ID do cliente")
    billingType: str = Field(..., description="Tipo de cobrança")
    value: float = Field(..., description="Valor")
    nextDueDate: str = Field(..., description="Próximo vencimento")
    cycle: str = Field(..., description="Ciclo")
    description: str = Field(..., description="Descrição")
    endDate: Optional[str] = None
    externalReference: Optional[str] = None
    status: Optional[str] = None  # ACTIVE, EXPIRED, etc.


class AsaasWebhookNotification(BaseModel):
    """Notificação de webhook do Asaas"""
    event: str = Field(..., description="Tipo de evento")
    payment: Optional[Dict[str, Any]] = Field(None, description="Dados do pagamento")
    subscription: Optional[Dict[str, Any]] = Field(None, description="Dados da assinatura")
    
    class Config:
        json_schema_extra = {
            "example": {
                "event": "PAYMENT_CONFIRMED",
                "payment": {
                    "id": "pay_123456789",
                    "subscription": "sub_123456789",
                    "status": "CONFIRMED",
                    "value": 99.90,
                    "dueDate": "2024-02-01",
                    "paymentDate": "2024-02-01"
                }
            }
        }


class AsaasError(BaseModel):
    """Erro da API Asaas"""
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="Lista de erros")
    message: Optional[str] = Field(None, description="Mensagem de erro")

