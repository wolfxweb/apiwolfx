"""
Rotas para integração com Mercado Pago
"""
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers.payment_controller import PaymentController
from app.services.test_account_service import test_account_service
from app.models.payment_models import (
    PaymentRequest, PaymentResponse, PreferenceRequest, PreferenceResponse
)
from app.controllers.auth_controller import AuthController

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["payments"])


def get_current_user(request: Request) -> Dict[str, Any]:
    """Obtém usuário atual da sessão"""
    from app.controllers.auth_controller import AuthController
    from app.config.database import get_db
    
    # Tentar obter session_token dos cookies
    session_token = request.cookies.get("session_token")
    logger.info(f"🔍 Session token: {session_token}")
    
    if not session_token:
        # Usar usuário padrão para testes
        logger.info("🔄 Usando usuário padrão para testes (ID: 2)")
        return {
            "id": 2,  # Usuário da company ID 15 (wolfx)
            "email": "wolfxweb@gmail.com",
            "company_id": 15
        }
    
    try:
        # Buscar usuário real da sessão
        auth_controller = AuthController()
        db = next(get_db())
        result = auth_controller.get_user_by_session(session_token, db)
        
        if result.get("error"):
            # Usar usuário padrão se houver erro
            return {
                "id": 2,
                "email": "wolfxweb@gmail.com",
                "company_id": 15
            }
        
        user_data = result["user"]
        return {
            "id": user_data["id"],
            "email": user_data["email"],
            "company_id": user_data.get("company_id", 15)
        }
        
    except Exception as e:
        print(f"Erro ao obter usuário: {e}")
        # Usar usuário padrão em caso de erro
        return {
            "id": 2,
            "email": "wolfxweb@gmail.com",
            "company_id": 15
        }


@router.post("/create-preference", response_model=PreferenceResponse)
async def create_payment_preference(
    preference_data: PreferenceRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Cria uma preferência de pagamento no Mercado Pago
    """
    try:
        user = get_current_user(request)
        controller = PaymentController(db)
        
        # Adicionar dados do usuário à preferência
        subscription_data = {
            "plan_name": preference_data.items[0]["title"] if preference_data.items else "Plano",
            "amount": preference_data.items[0]["unit_price"] if preference_data.items else 0,
            "base_url": request.base_url.scheme + "://" + request.base_url.netloc
        }
        
        preference = controller.create_preference_for_subscription(
            subscription_data, 
            user["id"]
        )
        
        logger.info(f"✅ Preferência criada para usuário {user['id']}: {preference.id}")
        return preference
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar preferência: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/process", response_model=PaymentResponse)
async def process_payment(
    payment_data: PaymentRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Processa um pagamento via checkout transparente
    """
    try:
        user = get_current_user(request)
        controller = PaymentController(db)
        
        # Preparar dados da assinatura
        subscription_data = {
            "amount": payment_data.transaction_amount,
            "description": payment_data.description,
            "payment_method_id": payment_data.payment_method_id,
            "installments": payment_data.installments,
            "token": payment_data.token,
            "issuer_id": payment_data.issuer_id
        }
        
        payment = controller.create_subscription_payment(
            subscription_data, 
            user["id"]
        )
        
        logger.info(f"✅ Pagamento processado para usuário {user['id']}: {payment.id}")
        return payment
        
    except Exception as e:
        logger.error(f"❌ Erro ao processar pagamento: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status/{payment_id}", response_model=PaymentResponse)
async def get_payment_status(
    payment_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Busca o status de um pagamento
    """
    try:
        user = get_current_user(request)
        controller = PaymentController(db)
        
        payment = controller.get_payment_status(payment_id)
        
        return payment
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar status do pagamento {payment_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my-payments")
async def get_user_payments(
    limit: int = 10,
    offset: int = 0,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Busca pagamentos do usuário atual
    """
    try:
        user = get_current_user(request)
        logger.info(f"👤 Usuário atual: {user}")
        controller = PaymentController(db)
        
        payments = controller.get_user_payments(user["id"], limit, offset)
        
        return {
            "payments": payments,
            "total": len(payments),
            "limit": limit,
            "offset": offset,
            "user_id": user["id"]  # Adicionar para debug
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar pagamentos do usuário: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/test-payments/{user_id}")
async def test_user_payments(
    user_id: int,
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Endpoint de teste para buscar pagamentos de um usuário específico
    """
    try:
        logger.info(f"🧪 Testando pagamentos para usuário ID: {user_id}")
        controller = PaymentController(db)
        
        payments = controller.get_user_payments(user_id, limit, offset)
        
        return {
            "payments": payments,
            "total": len(payments),
            "limit": limit,
            "offset": offset,
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar pagamentos do usuário {user_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/test-update-expiry/{user_id}")
async def test_update_subscription_expiry(
    user_id: int,
    plan_name: str = "Enterprise",
    db: Session = Depends(get_db)
):
    """
    Endpoint de teste para atualizar expiração da assinatura
    """
    try:
        logger.info(f"🧪 Testando atualização de expiração para usuário ID: {user_id}, plano: {plan_name}")
        controller = PaymentController(db)
        
        # Dados de pagamento simulados
        payment_data = {
            "id": 130072395932,
            "external_reference": f"subscription_{user_id}_{plan_name}",
            "status": "approved"
        }
        
        success = controller.update_subscription_expiry(payment_data)
        
        return {
            "success": success,
            "message": "Expiração atualizada com sucesso" if success else "Falha ao atualizar expiração",
            "user_id": user_id,
            "plan_name": plan_name,
            "payment_data": payment_data
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao testar atualização de expiração: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/company-expiry/{user_id}")
async def get_company_expiry(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Endpoint para verificar a data de expiração da empresa
    """
    try:
        from app.models.saas_models import User, Company, Subscription
        
        # Buscar usuário
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        # Buscar empresa
        company = db.query(Company).filter(Company.id == user.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        
        # Buscar assinatura ativa
        subscription = db.query(Subscription).filter(
            Subscription.company_id == user.company_id,
            Subscription.status == "active"
        ).first()
        
        return {
            "user_id": user_id,
            "company_id": company.id,
            "company_name": company.name,
            "plan_expires_at": company.plan_expires_at.isoformat() if company.plan_expires_at else None,
            "subscription": {
                "plan_name": subscription.plan_name if subscription else None,
                "billing_cycle": subscription.billing_cycle if subscription else None,
                "status": subscription.status if subscription else None,
                "is_trial": subscription.is_trial if subscription else None,
                "ends_at": subscription.ends_at.isoformat() if subscription and subscription.ends_at else None
            } if subscription else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao buscar expiração da empresa: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cancel/{payment_id}")
async def cancel_payment(
    payment_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Cancela um pagamento
    """
    try:
        user = get_current_user(request)
        controller = PaymentController(db)
        
        payment = controller.cancel_payment(payment_id, user["id"])
        
        return {
            "message": "Pagamento cancelado com sucesso",
            "payment": payment
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao cancelar pagamento {payment_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refund/{payment_id}")
async def refund_payment(
    payment_id: int,
    amount: float = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Estorna um pagamento
    """
    try:
        user = get_current_user(request)
        controller = PaymentController(db)
        
        payment = controller.refund_payment(payment_id, user["id"], amount)
        
        return {
            "message": "Pagamento estornado com sucesso",
            "payment": payment
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao estornar pagamento {payment_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/payment-methods")
async def get_payment_methods():
    """
    Busca métodos de pagamento disponíveis
    """
    try:
        from app.services.mercado_pago_service import mercado_pago_service
        
        methods = mercado_pago_service.get_payment_methods()
        
        return methods
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar métodos de pagamento: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/installments")
async def get_installments(
    amount: float,
    payment_method_id: str,
    issuer_id: str = None
):
    """
    Busca opções de parcelamento
    """
    try:
        from app.services.mercado_pago_service import mercado_pago_service
        
        installments = mercado_pago_service.get_installments(
            amount, payment_method_id, issuer_id
        )
        
        return installments
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar parcelamentos: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhooks/mercadopago")
async def receive_mercadopago_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Recebe notificações de webhook do Mercado Pago
    """
    try:
        # Obter dados do webhook
        notification_data = await request.json()
        
        # Validar assinatura (se configurada)
        signature = request.headers.get("x-signature")
        if signature:
            payload = await request.body()
            from app.services.mercado_pago_service import mercado_pago_service
            
            if not mercado_pago_service.validate_webhook_signature(payload.decode(), signature):
                logger.warning("⚠️ Webhook com assinatura inválida")
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Processar notificação em background
        background_tasks.add_task(process_webhook_notification, notification_data, db)
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"❌ Erro ao processar webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))


async def process_webhook_notification(notification_data: Dict[str, Any], db: Session):
    """
    Processa notificação de webhook em background
    """
    try:
        controller = PaymentController(db)
        success = controller.process_webhook_notification(notification_data)
        
        if success:
            logger.info("✅ Webhook processado com sucesso")
        else:
            logger.warning("⚠️ Webhook não processado")
            
    except Exception as e:
        logger.error(f"❌ Erro ao processar webhook em background: {e}")


@router.post("/test-payment")
async def create_test_payment(
    amount: float = 100.0,
    db: Session = Depends(get_db)
):
    """
    Cria um pagamento de teste (apenas para desenvolvimento)
    """
    try:
        from app.services.mercado_pago_service import mercado_pago_service
        
        # Verificar se está em modo sandbox
        if not mercado_pago_service.sandbox:
            raise HTTPException(status_code=400, detail="Test payments only allowed in sandbox mode")
        
        payment = mercado_pago_service.create_test_payment(amount)
        
        return {
            "message": "Pagamento de teste criado",
            "payment": payment
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar pagamento de teste: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/test-accounts/create")
async def create_test_account(account_type: str = "buyer", country: str = "BR", description: str = "Conta de Teste"):
    """Cria uma conta de teste específica do Mercado Pago"""
    try:
        logger.info(f"🔄 Criando conta de teste: {account_type}")
        
        account = test_account_service.create_test_account(account_type, country, description)
        
        if account.get("error"):
            raise HTTPException(status_code=400, detail=account["error"])
        
        return {
            "message": f"Conta de teste {account_type} criada com sucesso",
            "account": account
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao criar conta de teste: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-accounts/setup-environment")
async def setup_test_environment():
    """Configura ambiente completo de teste com vendedor e comprador"""
    try:
        logger.info("🚀 Configurando ambiente de teste...")
        
        environment = test_account_service.setup_test_environment()
        
        if environment.get("error"):
            raise HTTPException(status_code=400, detail=environment["error"])
        
        return environment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao configurar ambiente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-accounts/cards")
async def get_test_cards(country: str = "BR"):
    """Retorna cartões de teste para o país especificado"""
    try:
        cards = test_account_service.get_test_cards(country)
        
        return {
            "message": f"Cartões de teste para {country}",
            "test_cards": cards,
            "usage_instructions": {
                "approved": {
                    "description": "Use para simular pagamentos aprovados",
                    "number": cards["approved"]["number"],
                    "holder": cards["approved"]["cardholder"]["name"]
                },
                "rejected": {
                    "description": "Use para simular pagamentos rejeitados",
                    "number": cards["rejected"]["number"],
                    "holder": cards["rejected"]["cardholder"]["name"]
                },
                "pending": {
                    "description": "Use para simular pagamentos pendentes",
                    "number": cards["pending"]["number"],
                    "holder": cards["pending"]["cardholder"]["name"]
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter cartões de teste: {e}")
        raise HTTPException(status_code=500, detail=str(e))

