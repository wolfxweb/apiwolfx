"""
Rotas para integração com Asaas
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers.asaas_controller import AsaasController
from app.models.asaas_models import (
    AsaasCreateSubscriptionRequest,
    AsaasWebhookNotification
)
from app.controllers.auth_controller import AuthController

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/asaas", tags=["asaas"])


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Obtém usuário atual da sessão"""
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    
    auth_controller = AuthController()
    result = auth_controller.get_user_by_session(session_token, db)
    
    if result.get("error"):
        raise HTTPException(status_code=401, detail=result.get("error", "Sessão inválida"))
    
    return result["user"]


@router.post("/subscriptions", response_model=Dict[str, Any])
async def create_subscription(
    subscription_data: Dict[str, Any],
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Cria uma assinatura recorrente no Asaas
    """
    try:
        user = get_current_user(request, db)
        controller = AsaasController(db)
        
        result = controller.create_subscription(
            plan_id=subscription_data.get("plan_id"),
            company_id=user["company_id"],
            user_id=user["id"],
            subscriber_data=subscription_data.get("subscriber_data", {})
        )
        
        logger.info(f"✅ Assinatura criada para usuário {user['id']}: {result.get('subscription_id')}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar assinatura: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/subscriptions/{subscription_id}", response_model=Dict[str, Any])
async def get_subscription(
    subscription_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Busca dados de uma assinatura
    """
    try:
        user = get_current_user(request, db)
        controller = AsaasController(db)
        
        result = controller.get_subscription(subscription_id)
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar assinatura: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/subscriptions/{subscription_id}", response_model=Dict[str, Any])
async def cancel_subscription(
    subscription_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Cancela uma assinatura
    """
    try:
        user = get_current_user(request, db)
        controller = AsaasController(db)
        
        result = controller.cancel_subscription(subscription_id)
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro ao cancelar assinatura: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/payments/my-payments", response_model=Dict[str, Any])
async def get_my_payments(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Busca pagamentos do cliente atual no Asaas usando CPF/CNPJ
    """
    try:
        user = get_current_user(request, db)
        
        # Buscar CPF/CNPJ da empresa do usuário
        from sqlalchemy import text
        from app.models.saas_models import Company
        
        company_query = text("""
            SELECT cnpj FROM companies 
            WHERE id = :company_id
        """)
        
        company_result = db.execute(company_query, {"company_id": user["company_id"]}).fetchone()
        
        if not company_result or not company_result[0]:
            logger.warning(f"⚠️ CPF/CNPJ não cadastrado para empresa {user['company_id']}")
            return {
                "success": True,
                "payments": [],
                "message": "CPF/CNPJ não cadastrado"
            }
        
        cpf_cnpj = company_result[0]
        logger.info(f"🔍 Buscando pagamentos para CPF/CNPJ: {cpf_cnpj} (usuário: {user['id']}, empresa: {user['company_id']})")
        
        # Buscar cliente no Asaas pelo CPF/CNPJ
        from app.services.asaas_service import asaas_service
        customer = asaas_service.find_customer_by_cpf_cnpj(cpf_cnpj)
        
        if not customer or not customer.get("id"):
            logger.warning(f"⚠️ Cliente não encontrado no Asaas para CPF/CNPJ: {cpf_cnpj}")
            return {
                "success": True,
                "payments": [],
                "message": "Cliente não encontrado no Asaas"
            }
        
        customer_id = customer["id"]
        logger.info(f"✅ Cliente encontrado no Asaas: {customer_id} (CPF/CNPJ: {cpf_cnpj})")
        
        # Buscar TODOS os pagamentos do cliente no Asaas (todos os status)
        payments = asaas_service.get_customer_payments(customer_id, limit=500)
        
        logger.info(f"📊 Total de {len(payments)} pagamentos encontrados para cliente {customer_id} (CPF/CNPJ: {cpf_cnpj})")
        
        # Formatar pagamentos para o frontend
        formatted_payments = []
        for payment in payments:
            status = payment.get("status", "PENDING")
            formatted_payments.append({
                "id": payment.get("id"),
                "value": payment.get("value", 0),
                "status": status.lower(),
                "billingType": payment.get("billingType", ""),
                "dueDate": payment.get("dueDate"),
                "paymentDate": payment.get("paymentDate"),
                "description": payment.get("description", ""),
                "invoiceUrl": payment.get("invoiceUrl"),
                "created_at": payment.get("dateCreated") or payment.get("dueDate"),
                "originalStatus": status  # Manter status original para referência
            })
        
        # Ordenar por data mais recente primeiro (usando paymentDate se disponível, senão dueDate)
        formatted_payments.sort(key=lambda x: (
            x.get("paymentDate") or x.get("dueDate") or x.get("created_at") or ""
        ), reverse=True)
        
        # Log de estatísticas
        status_counts = {}
        for payment in formatted_payments:
            status = payment.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        logger.info(f"📈 Estatísticas de pagamentos: {status_counts}")
        
        return {
            "success": True,
            "payments": formatted_payments,
            "total": len(formatted_payments)
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar pagamentos: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhooks")
async def receive_asaas_webhook(
    notification: Dict[str, Any],
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Recebe notificações de webhook do Asaas
    
    Eventos suportados:
    - PAYMENT_CONFIRMED: Pagamento confirmado
    - PAYMENT_RECEIVED: Pagamento recebido
    - PAYMENT_OVERDUE: Pagamento vencido
    - PAYMENT_REFUNDED: Pagamento estornado
    """
    try:
        from app.services.asaas_service import asaas_service
        
        # Validar webhook (se necessário)
        # signature = request.headers.get("asaas-signature")
        # if not asaas_service.validate_webhook(str(notification), signature):
        #     raise HTTPException(status_code=401, detail="Webhook inválido")
        
        controller = AsaasController(db)
        result = controller.process_webhook_notification(notification)
        
        logger.info(f"✅ Webhook Asaas processado: {notification.get('event')}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro ao processar webhook do Asaas: {e}")
        raise HTTPException(status_code=400, detail=str(e))

