"""
Rotas para integração com Asaas
"""
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
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


@router.post("/payments/{payment_id}/update-subscription", response_model=Dict[str, Any])
async def update_subscription_from_payment(
    payment_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Atualiza o cadastro (status e vencimento) baseado em um pagamento confirmado relacionado ao plano
    """
    try:
        user = get_current_user(request, db)
        
        # Buscar o pagamento no Asaas
        from app.services.asaas_service import asaas_service
        payment = asaas_service._make_request("GET", f"/payments/{payment_id}")
        
        if not payment or payment.get("status") not in ["CONFIRMED", "RECEIVED"]:
            return {
                "success": False,
                "message": "Pagamento não está confirmado"
            }
        
        # Buscar assinatura da empresa
        from sqlalchemy import text
        from app.models.saas_models import Subscription, Company, CompanyStatus
        from datetime import datetime, timedelta
        
        subscription_query = text("""
            SELECT * FROM subscriptions 
            WHERE company_id = :company_id 
            AND (status = 'active' OR status = 'pending' OR is_trial = true)
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        subscription_result = db.execute(subscription_query, {"company_id": user["company_id"]}).fetchone()
        
        if not subscription_result:
            return {
                "success": False,
                "message": "Nenhuma assinatura encontrada"
            }
        
        subscription = dict(subscription_result._mapping)
        asaas_subscription_id = subscription.get("asaas_subscription_id")
        plan_name = subscription.get("plan_name", "").strip()
        
        # Função para remover qualquer tipo de emoji
        import re
        def remove_all_emojis(text: str) -> str:
            """
            Remove qualquer tipo de emoji do texto usando padrão Unicode completo
            Cobre todos os ranges de emojis definidos pelo Unicode Standard
            """
            if not text:
                return ""
            
            # Padrão completo para remover todos os tipos de emojis Unicode
            # Baseado no Unicode Emoji Standard - cobre todos os emojis conhecidos
            emoji_pattern = re.compile(
                "["
                # Emoticons
                "\U0001F600-\U0001F64F"
                # Symbols & Pictographs
                "\U0001F300-\U0001F5FF"
                # Transport & Map Symbols
                "\U0001F680-\U0001F6FF"
                # Flags
                "\U0001F1E0-\U0001F1FF"
                # Dingbats
                "\U00002702-\U000027B0"
                # Enclosed characters
                "\U000024C2-\U0001F251"
                # Supplemental Symbols and Pictographs
                "\U0001F900-\U0001F9FF"
                # Chess Symbols
                "\U0001FA00-\U0001FA6F"
                # Symbols and Pictographs Extended-A
                "\U0001FA70-\U0001FAFF"
                # Miscellaneous Symbols
                "\U00002600-\U000026FF"
                # Dingbats
                "\U00002700-\U000027BF"
                # Various asian characters
                "\U0001F018-\U0001F270"
                # Alchemical symbols
                "\U0001F700-\U0001F77F"
                # Geometric Shapes Extended
                "\U0001F780-\U0001F7FF"
                # Supplemental Arrows-C
                "\U0001F800-\U0001F8FF"
                # Emoji modifiers
                "\U0001F3FB-\U0001F3FF"
                # Variation selectors
                "\U0000FE00-\U0000FE0F"
                # Combining diacritical marks for symbols
                "\U0000200D"
                # Zero width joiner
                "\U000020E3"
                # Combining enclosing keycap
                "]+",
                flags=re.UNICODE
            )
            
            # Remover emojis
            text = emoji_pattern.sub('', text)
            
            # Limpar espaços múltiplos
            text = re.sub(r'\s+', ' ', text)
            
            return text.strip()
        
        # Verificar se o pagamento está relacionado ao plano
        payment_subscription_id = payment.get("subscription")
        payment_description = payment.get("description", "").strip()
        
        # PRIMEIRA VALIDAÇÃO: Verificar subscription_id
        is_related_by_subscription = False
        if payment_subscription_id and asaas_subscription_id and payment_subscription_id == asaas_subscription_id:
            is_related_by_subscription = True
            logger.info(f"✅ Pagamento relacionado ao plano via subscription_id: {payment_subscription_id}")
        
        # SEGUNDA VALIDAÇÃO: Verificar se a descrição contém o nome do plano (sem emojis)
        is_related_by_description = False
        if plan_name and payment_description:
            # Remover emojis do nome do plano e da descrição antes de comparar
            plan_name_clean = remove_all_emojis(plan_name)
            payment_description_clean = remove_all_emojis(payment_description)
            
            plan_name_lower = plan_name_clean.lower()
            payment_description_lower = payment_description_clean.lower()
            
            # Verificar se o nome do plano (sem emoji) está na descrição
            if plan_name_lower and plan_name_lower in payment_description_lower:
                is_related_by_description = True
                logger.info(f"✅ Pagamento relacionado ao plano via descrição: '{plan_name_clean}' encontrado em '{payment_description_clean}'")
        
        # TERCEIRA VALIDAÇÃO: Se o pagamento não tem subscription_id, mas temos asaas_subscription_id,
        # buscar pagamentos da assinatura para verificar se este pagamento pertence a ela
        is_related_by_subscription_payments = False
        if not is_related_by_subscription and not is_related_by_description and asaas_subscription_id:
            try:
                subscription_payments = asaas_service.get_subscription_payments(asaas_subscription_id)
                payment_id_from_asaas = payment.get("id")
                
                for sub_payment in subscription_payments:
                    if sub_payment.get("id") == payment_id_from_asaas:
                        is_related_by_subscription_payments = True
                        logger.info(f"✅ Pagamento relacionado ao plano via lista de pagamentos da assinatura: {payment_id_from_asaas}")
                        break
            except Exception as e:
                logger.warning(f"⚠️ Erro ao buscar pagamentos da assinatura para validação: {e}")
        
        # Considerar relacionado se passar em qualquer uma das validações
        is_related_to_plan = is_related_by_subscription or is_related_by_description or is_related_by_subscription_payments
        
        if not is_related_to_plan:
            logger.warning(f"⚠️ Pagamento não relacionado ao plano:")
            logger.warning(f"   - Payment subscription_id: {payment_subscription_id}")
            logger.warning(f"   - Plan subscription_id: {asaas_subscription_id}")
            logger.warning(f"   - Payment description: '{payment_description}'")
            logger.warning(f"   - Plan name: '{plan_name}'")
            return {
                "success": False,
                "message": "Este pagamento não está relacionado ao plano. Apenas pagamentos do plano podem atualizar o cadastro."
            }
        
        # Buscar a próxima parcela pendente da assinatura no Asaas
        next_due = None
        if asaas_subscription_id:
            try:
                # Buscar pagamentos da assinatura
                subscription_payments = asaas_service.get_subscription_payments(asaas_subscription_id)
                
                # Encontrar a próxima parcela pendente (mais próxima no futuro)
                now = datetime.now()
                pending_payments = []
                
                for sub_payment in subscription_payments:
                    if sub_payment.get("status") in ["PENDING", "OVERDUE"]:
                        due_date_str = sub_payment.get("dueDate")
                        if due_date_str:
                            try:
                                due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                                if due_date >= now:
                                    pending_payments.append({
                                        "dueDate": due_date,
                                        "payment": sub_payment
                                    })
                            except:
                                pass
                
                # Ordenar por data e pegar a mais próxima
                if pending_payments:
                    pending_payments.sort(key=lambda x: x["dueDate"])
                    next_due = pending_payments[0]["dueDate"]
                    logger.info(f"✅ Próxima parcela pendente encontrada: {next_due.strftime('%d/%m/%Y')}")
            
            except Exception as e:
                logger.warning(f"⚠️ Erro ao buscar próxima parcela: {e}")
        
        # Se não encontrou próxima parcela, calcular baseado no billing_cycle
        if not next_due:
            billing_cycle = subscription.get("billing_cycle", "monthly")
            now = datetime.now()
            
            if billing_cycle == "monthly":
                next_due = now + timedelta(days=30)
            elif billing_cycle == "quarterly":
                next_due = now + timedelta(days=90)
            elif billing_cycle == "semiannually":
                next_due = now + timedelta(days=180)
            elif billing_cycle == "yearly":
                next_due = now + timedelta(days=365)
            else:
                next_due = now + timedelta(days=30)
            
            logger.info(f"📅 Próxima data calculada baseada no billing_cycle: {next_due.strftime('%d/%m/%Y')}")
        
        # Atualizar assinatura usando ORM para evitar problemas com enum
        subscription_obj = db.query(Subscription).filter(Subscription.id == subscription["id"]).first()
        if subscription_obj:
            subscription_obj.status = "active"
            subscription_obj.is_trial = False
            subscription_obj.ends_at = next_due
            subscription_obj.next_charge_date = next_due
            subscription_obj.trial_ends_at = None
            subscription_obj.updated_at = datetime.now()
        
        # Atualizar empresa usando ORM
        company_obj = db.query(Company).filter(Company.id == user["company_id"]).first()
        if company_obj:
            company_obj.status = CompanyStatus.ACTIVE
            company_obj.plan_expires_at = next_due
            company_obj.trial_ends_at = None
            company_obj.updated_at = datetime.now()
            
            # Adicionar tokens mensais do plano
            from app.models.saas_models import Plan
            plan = db.query(Plan).filter(Plan.plan_name == subscription.get("plan_name")).first()
            
            if plan and hasattr(plan, 'ai_analysis_monthly') and plan.ai_analysis_monthly:
                tokens_to_add = plan.ai_analysis_monthly
                # Adicionar tokens mensais (não substituir, somar)
                if not company_obj.ai_tokens_monthly:
                    company_obj.ai_tokens_monthly = 0
                company_obj.ai_tokens_monthly += tokens_to_add
                logger.info(f"✅ Tokens mensais adicionados: +{tokens_to_add} tokens (total: {company_obj.ai_tokens_monthly})")
            else:
                logger.warning(f"⚠️ Plano '{subscription.get('plan_name')}' não encontrado ou sem ai_analysis_monthly definido")
        
        db.commit()
        
        logger.info(f"✅ Cadastro atualizado para empresa {user['company_id']} baseado no pagamento {payment_id}")
        logger.info(f"   - Próximo vencimento: {next_due.strftime('%d/%m/%Y')}")
        
        return {
            "success": True,
            "message": "Cadastro atualizado com sucesso",
            "next_due_date": next_due.strftime("%d/%m/%Y")
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro ao atualizar cadastro: {e}")
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


@router.post("/subscriptions/cancel", response_model=Dict[str, Any])
async def cancel_subscription(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Cancela a assinatura definindo endDate no Asaas como a data de vencimento atual
    """
    try:
        user = get_current_user(request, db)
        from app.models.saas_models import Subscription
        from app.services.asaas_service import asaas_service
        
        # Buscar assinatura ativa da empresa
        subscription = db.query(Subscription).filter(
            Subscription.company_id == user["company_id"],
            Subscription.status == "active",
            Subscription.asaas_subscription_id.isnot(None)
        ).order_by(Subscription.created_at.desc()).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Assinatura não encontrada")
        
        # Obter data de vencimento atual (ends_at ou next_charge_date)
        cancel_date = subscription.ends_at or subscription.next_charge_date
        if not cancel_date:
            # Se não tiver data, usar data atual + 30 dias como fallback
            cancel_date = datetime.now() + timedelta(days=30)
        
        # Atualizar assinatura no Asaas com endDate
        asaas_subscription_data = {
            "endDate": cancel_date.strftime("%Y-%m-%d")
        }
        
        result = asaas_service.update_subscription(
            subscription.asaas_subscription_id,
            asaas_subscription_data
        )
        
        logger.info(f"✅ Assinatura {subscription.id} cancelada no Asaas. Cancelará em {cancel_date.strftime('%d/%m/%Y')}")
        
        return {
            "success": True,
            "message": f"Assinatura cancelada. Acesso será suspenso em {cancel_date.strftime('%d/%m/%Y')}",
            "cancel_date": cancel_date.strftime("%Y-%m-%d")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao cancelar assinatura: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/subscriptions/reactivate", response_model=Dict[str, Any])
async def reactivate_subscription(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Reativa a assinatura removendo endDate no Asaas (renovação automática)
    """
    try:
        user = get_current_user(request, db)
        from app.models.saas_models import Subscription
        from app.services.asaas_service import asaas_service
        
        # Buscar assinatura da empresa
        subscription = db.query(Subscription).filter(
            Subscription.company_id == user["company_id"],
            Subscription.asaas_subscription_id.isnot(None)
        ).order_by(Subscription.created_at.desc()).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Assinatura não encontrada")
        
        # Buscar assinatura atual no Asaas para manter outros campos
        asaas_subscription = asaas_service.get_subscription(subscription.asaas_subscription_id)
        
        # Preparar dados de atualização - remover endDate (None = renovação automática)
        # No Asaas, para remover endDate, precisamos passar None ou não incluir o campo
        # Vamos passar explicitamente None
        asaas_subscription_data = {}
        # Não incluir endDate = renovação automática
        
        # Tentar atualizar sem endDate primeiro
        try:
            result = asaas_service.update_subscription(
                subscription.asaas_subscription_id,
                asaas_subscription_data
            )
        except Exception as e:
            # Se não funcionar, tentar passar endDate como None explicitamente
            logger.warning(f"⚠️ Tentativa sem endDate falhou, tentando com endDate=None: {e}")
            asaas_subscription_data = {
                "endDate": None
            }
            result = asaas_service.update_subscription(
                subscription.asaas_subscription_id,
                asaas_subscription_data
            )
        
        logger.info(f"✅ Assinatura {subscription.id} reativada no Asaas (renovação automática)")
        
        return {
            "success": True,
            "message": "Assinatura reativada com sucesso. Renovação automática ativada.",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao reativar assinatura: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))

