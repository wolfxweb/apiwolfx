"""
Modelos Pydantic para integração com Mercado Pago
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PaymentStatus(str, Enum):
    """Status de pagamento do Mercado Pago"""
    PENDING = "pending"
    APPROVED = "approved"
    AUTHORIZED = "authorized"
    IN_PROCESS = "in_process"
    IN_MEDIATION = "in_mediation"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    CHARGED_BACK = "charged_back"


class PaymentMethod(str, Enum):
    """Métodos de pagamento aceitos"""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PIX = "pix"
    BOLETO = "bolbradesco"
    ACCOUNT_MONEY = "account_money"


class PaymentMethodType(str, Enum):
    """Tipos de métodos de pagamento"""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    DIGITAL_WALLET = "digital_wallet"
    BANK_TRANSFER = "bank_transfer"


class PaymentRequest(BaseModel):
    """Request para criar pagamento"""
    transaction_amount: float = Field(..., description="Valor da transação")
    description: str = Field(..., description="Descrição do pagamento")
    payment_method_id: PaymentMethod = Field(..., description="Método de pagamento")
    payer: Dict[str, Any] = Field(..., description="Dados do pagador")
    installments: int = Field(default=1, description="Número de parcelas")
    token: str = Field(..., description="Token do cartão (frontend)")
    issuer_id: Optional[str] = Field(None, description="ID do emissor do cartão")
    
    class Config:
        json_schema_extra = {
            "example": {
                "transaction_amount": 59.90,
                "description": "Assinatura Plano Pro - 1 mês",
                "payment_method_id": "credit_card",
                "payer": {
                    "email": "cliente@exemplo.com",
                    "identification": {
                        "type": "CPF",
                        "number": "12345678901"
                    }
                },
                "installments": 1,
                "token": "card_token_from_frontend",
                "issuer_id": "25"
            }
        }


class PreferenceRequest(BaseModel):
    """Request para criar preferência de pagamento"""
    items: List[Dict[str, Any]] = Field(..., description="Itens do pagamento")
    payer: Optional[Dict[str, Any]] = Field(None, description="Dados do pagador")
    back_urls: Optional[Dict[str, str]] = Field(None, description="URLs de retorno")
    auto_return: Optional[str] = None
    payment_methods: Optional[Dict[str, Any]] = Field(None, description="Configuração de métodos")
    notification_url: Optional[str] = Field(None, description="URL de notificação")
    external_reference: Optional[str] = Field(None, description="Referência externa")
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "title": "Plano Pro",
                        "quantity": 1,
                        "unit_price": 59.90
                    }
                ],
                "payer": {
                    "email": "cliente@exemplo.com"
                },
                "back_urls": {
                    "success": "https://wolfx.com.br/payment/success",
                    "failure": "https://wolfx.com.br/payment/failure",
                    "pending": "https://wolfx.com.br/payment/pending"
                },
                "auto_return": "approved",
                "notification_url": "https://wolfx.com.br/api/webhooks/mercadopago"
            }
        }


class PaymentResponse(BaseModel):
    """Response do pagamento"""
    id: int = Field(..., description="ID do pagamento")
    status: PaymentStatus = Field(..., description="Status do pagamento")
    status_detail: Optional[str] = Field(None, description="Detalhes do status")
    transaction_amount: float = Field(..., description="Valor da transação")
    description: str = Field(..., description="Descrição")
    payment_method_id: str = Field(..., description="Método de pagamento")
    payment_type_id: str = Field(..., description="Tipo de pagamento")
    date_created: datetime = Field(..., description="Data de criação")
    date_approved: Optional[datetime] = Field(None, description="Data de aprovação")
    payer: Dict[str, Any] = Field(..., description="Dados do pagador")
    external_reference: Optional[str] = Field(None, description="Referência externa")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadados")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1234567890,
                "status": "approved",
                "status_detail": "accredited",
                "transaction_amount": 59.90,
                "description": "Assinatura Plano Pro - 1 mês",
                "payment_method_id": "credit_card",
                "payment_type_id": "credit_card",
                "date_created": "2024-01-15T10:30:00.000Z",
                "date_approved": "2024-01-15T10:30:05.000Z",
                "payer": {
                    "email": "cliente@exemplo.com",
                    "identification": {
                        "type": "CPF",
                        "number": "12345678901"
                    }
                },
                "external_reference": "subscription_123",
                "metadata": {
                    "plan_id": "pro_monthly",
                    "company_id": "15"
                }
            }
        }


class PreferenceResponse(BaseModel):
    """Response da preferência"""
    id: str = Field(..., description="ID da preferência")
    init_point: str = Field(..., description="URL de pagamento")
    sandbox_init_point: Optional[str] = Field(None, description="URL de pagamento sandbox")
    date_created: datetime = Field(..., description="Data de criação")
    items: List[Dict[str, Any]] = Field(..., description="Itens")
    payer: Optional[Dict[str, Any]] = Field(None, description="Pagador")
    back_urls: Optional[Dict[str, str]] = Field(None, description="URLs de retorno")
    notification_url: Optional[str] = Field(None, description="URL de notificação")
    external_reference: Optional[str] = Field(None, description="Referência externa")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "1234567890-abc123",
                "init_point": "https://www.mercadopago.com.br/checkout/v1/redirect?pref_id=1234567890-abc123",
                "sandbox_init_point": "https://sandbox.mercadopago.com.br/checkout/v1/redirect?pref_id=1234567890-abc123",
                "date_created": "2024-01-15T10:30:00.000Z",
                "items": [
                    {
                        "title": "Plano Pro",
                        "quantity": 1,
                        "unit_price": 59.90
                    }
                ],
                "payer": {
                    "email": "cliente@exemplo.com"
                },
                "back_urls": {
                    "success": "https://wolfx.com.br/payment/success",
                    "failure": "https://wolfx.com.br/payment/failure",
                    "pending": "https://wolfx.com.br/payment/pending"
                },
                "external_reference": "subscription_123"
            }
        }


class WebhookNotification(BaseModel):
    """Notificação de webhook"""
    id: int = Field(..., description="ID da notificação")
    live_mode: bool = Field(..., description="Modo produção")
    type: str = Field(..., description="Tipo de evento")
    date_created: datetime = Field(..., description="Data de criação")
    application_id: int = Field(..., description="ID da aplicação")
    user_id: int = Field(..., description="ID do usuário")
    version: int = Field(..., description="Versão")
    api_version: str = Field(..., description="Versão da API")
    action: str = Field(..., description="Ação")
    data: Dict[str, Any] = Field(..., description="Dados do evento")
    
    class Config:
        json_schema_extra = {
            "example": {
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
                    "id": "1234567890"
                }
            }
        }


class PaymentError(BaseModel):
    """Erro de pagamento"""
    message: str = Field(..., description="Mensagem de erro")
    error: str = Field(..., description="Tipo de erro")
    status: int = Field(..., description="Código de status")
    cause: Optional[List[Dict[str, Any]]] = Field(None, description="Causas do erro")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Invalid card number",
                "error": "bad_request",
                "status": 400,
                "cause": [
                    {
                        "code": "324",
                        "description": "The card number is invalid"
                    }
                ]
            }
        }

