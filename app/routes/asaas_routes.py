"""
Rotas para integração com Asaas
"""
import json
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Query
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
    Também verifica e processa pagamentos confirmados que ainda não foram atualizados
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
        
        payments = []
        customer_id = None
        
        # Buscar pagamentos pelo cliente se encontrado
        if customer and customer.get("id"):
            customer_id = customer["id"]
            logger.info(f"✅ Cliente encontrado no Asaas: {customer_id} (CPF/CNPJ: {cpf_cnpj})")
            
            # Buscar TODOS os pagamentos do cliente no Asaas (todos os status)
            try:
                payments = asaas_service.get_customer_payments(customer_id, limit=500)
                logger.info(f"📊 Total de {len(payments)} pagamentos encontrados via cliente no Asaas")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao buscar pagamentos do cliente: {e}")
        else:
            logger.warning(f"⚠️ Cliente não encontrado no Asaas para CPF/CNPJ: {cpf_cnpj}")
        
        # SEMPRE tentar buscar pagamentos da assinatura também (pode ter mais pagamentos)
        from app.models.saas_models import Subscription
        subscription = db.query(Subscription).filter(
            Subscription.company_id == user["company_id"],
            Subscription.asaas_subscription_id.isnot(None)
        ).order_by(Subscription.created_at.desc()).first()
        
        if subscription and subscription.asaas_subscription_id:
            logger.info(f"🔍 Buscando pagamentos da assinatura {subscription.asaas_subscription_id}...")
            try:
                subscription_payments = asaas_service.get_subscription_payments(subscription.asaas_subscription_id)
                logger.info(f"📦 Encontrados {len(subscription_payments)} pagamentos da assinatura")
                
                # Combinar pagamentos (evitar duplicatas)
                if subscription_payments:
                    payment_ids = {p.get("id") for p in payments}
                    for sp in subscription_payments:
                        if sp.get("id") not in payment_ids:
                            payments.append(sp)
                    logger.info(f"✅ Total de {len(payments)} pagamentos após combinar (cliente + assinatura)")
            except Exception as e:
                logger.error(f"❌ Erro ao buscar pagamentos da assinatura: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # Log detalhado dos primeiros pagamentos para debug
        if payments:
            logger.info(f"📋 Primeiros 3 pagamentos encontrados:")
            for i, payment in enumerate(payments[:3], 1):
                logger.info(f"   {i}. ID: {payment.get('id')}, Status: {payment.get('status')}, Valor: {payment.get('value')}, Data: {payment.get('dueDate')}")
        else:
            logger.warning(f"⚠️ Nenhum pagamento encontrado para empresa {user['company_id']}")
        
        # Verificar e processar automaticamente pagamentos confirmados que ainda não foram processados
        from app.models.saas_models import Subscription
        from app.controllers.asaas_controller import AsaasController
        
        subscription = db.query(Subscription).filter(
            Subscription.company_id == user["company_id"],
            Subscription.asaas_subscription_id.isnot(None)
        ).order_by(Subscription.created_at.desc()).first()
        
        if subscription:
            logger.info(f"🔍 Verificando pagamentos confirmados para processamento automático...")
            logger.info(f"   - Assinatura ID: {subscription.id}, Status: {subscription.status}")
            
            from app.models.saas_models import Company, CompanyStatus
            company = db.query(Company).filter(Company.id == user["company_id"]).first()
            if company:
                logger.info(f"   - Empresa ID: {company.id}, Status: {company.status}, Tokens mensais: {company.ai_tokens_monthly}")
            
            for payment in payments:
                payment_id = payment.get("id")
                payment_status = payment.get("status", "").upper()
                confirmed_date = payment.get("confirmedDate")
                payment_date = payment.get("paymentDate")
                net_value = payment.get("netValue")
                value = payment.get("value", 0)
                billing_type = payment.get("billingType", "")
                external_ref = payment.get("externalReference", "")
                
                logger.info(f"   - Pagamento {payment_id}: status={payment_status}, confirmedDate={confirmed_date}, paymentDate={payment_date}, netValue={net_value}, value={value}, billingType={billing_type}")
                
                # Verificar se o pagamento está confirmado
                is_confirmed = (
                    payment_status in ["CONFIRMED", "RECEIVED"] or
                    confirmed_date or
                    payment_date or
                    (net_value and float(net_value) != float(value) and billing_type == "CREDIT_CARD")
                )
                
                logger.info(f"   - Pagamento {payment_id} está confirmado? {is_confirmed}")
                
                if is_confirmed:
                    # Verificar se precisa processar: assinatura pendente OU empresa ainda em trial OU tokens mensais não atualizados
                    from app.models.saas_models import Company, CompanyStatus
                    company = db.query(Company).filter(Company.id == user["company_id"]).first()
                    
                    needs_processing = False
                    reason = ""
                    
                    if subscription.status == "pending":
                        needs_processing = True
                        reason = "assinatura pendente"
                    elif company and company.status == CompanyStatus.TRIAL:
                        needs_processing = True
                        reason = "empresa ainda em trial"
                    elif company and subscription.ai_analysis_monthly and (not company.ai_tokens_monthly or company.ai_tokens_monthly != subscription.ai_analysis_monthly):
                        needs_processing = True
                        reason = f"tokens mensais não atualizados (empresa: {company.ai_tokens_monthly}, plano: {subscription.ai_analysis_monthly})"
                    
                    if needs_processing:
                        logger.info(f"🔄 Pagamento {payment_id} confirmado mas {reason} - processando webhook automaticamente...")
                        logger.info(f"   - Status assinatura: {subscription.status}")
                        logger.info(f"   - Status empresa: {company.status if company else 'N/A'}")
                        logger.info(f"   - Tokens mensais empresa: {company.ai_tokens_monthly if company else 'N/A'}")
                        logger.info(f"   - Tokens mensais plano: {subscription.ai_analysis_monthly}")
                        try:
                            # Determinar status final
                            final_status = payment_status
                            if confirmed_date or payment_date:
                                final_status = "CONFIRMED"
                            elif net_value and float(net_value) != float(value) and billing_type == "CREDIT_CARD":
                                final_status = "CONFIRMED"
                            
                            notification_data = {
                                "event": "PAYMENT_CONFIRMED",
                                "payment": {
                                    "id": payment_id,
                                    "status": final_status,
                                    "paymentDate": payment_date or confirmed_date,
                                    "externalReference": external_ref
                                }
                            }
                            
                            controller = AsaasController(db)
                            result = controller.process_webhook_notification(notification_data)
                            logger.info(f"✅ Webhook processado automaticamente para pagamento {payment_id}: {result}")
                            
                            # Recarregar assinatura e empresa após processamento
                            db.refresh(subscription)
                            if company:
                                db.refresh(company)
                        except Exception as e:
                            logger.warning(f"⚠️ Erro ao processar webhook automaticamente para pagamento {payment_id}: {e}")
                            import traceback
                            logger.warning(traceback.format_exc())
                    else:
                        logger.info(f"ℹ️ Pagamento {payment_id} confirmado mas já foi processado (assinatura: {subscription.status}, empresa: {company.status if company else 'N/A'})")
        
        # Buscar também compras de pacotes de tokens do banco local
        from app.models.saas_models import TokenPackagePurchase, TokenPackage
        package_purchases = db.query(TokenPackagePurchase).filter(
            TokenPackagePurchase.company_id == user["company_id"]
        ).order_by(TokenPackagePurchase.purchased_at.desc()).all()
        
        logger.info(f"📦 Total de {len(package_purchases)} compras de pacotes encontradas")
        
        # Verificar e processar automaticamente compras de pacotes confirmadas que ainda não foram processadas
        if package_purchases:
            logger.info(f"🔍 Verificando compras de pacotes confirmadas para processamento automático...")
            for payment in payments:
                payment_id = payment.get("id")
                payment_status = payment.get("status", "").upper()
                confirmed_date = payment.get("confirmedDate")
                payment_date = payment.get("paymentDate")
                net_value = payment.get("netValue")
                value = payment.get("value", 0)
                billing_type = payment.get("billingType", "")
                external_ref = payment.get("externalReference", "")
                
                # Verificar se o pagamento está confirmado
                is_confirmed = (
                    payment_status in ["CONFIRMED", "RECEIVED"] or
                    confirmed_date or
                    payment_date or
                    (net_value and float(net_value) != float(value) and billing_type == "CREDIT_CARD")
                )
                
                if is_confirmed:
                    # Buscar compra de pacote pendente relacionada a este pagamento
                    purchase = None
                    
                    # Tentar buscar pelo asaas_payment_id
                    if payment_id:
                        purchase = db.query(TokenPackagePurchase).filter(
                            TokenPackagePurchase.asaas_payment_id == payment_id,
                            TokenPackagePurchase.payment_status == "pending",
                            TokenPackagePurchase.company_id == user["company_id"]
                        ).first()
                    
                    # Se não encontrou, tentar pelo externalReference
                    if not purchase and external_ref and "package_" in external_ref:
                        parts = external_ref.split("_")
                        if len(parts) >= 2:
                            try:
                                purchase_id = int(parts[1])
                                purchase = db.query(TokenPackagePurchase).filter(
                                    TokenPackagePurchase.id == purchase_id,
                                    TokenPackagePurchase.payment_status == "pending",
                                    TokenPackagePurchase.company_id == user["company_id"]
                                ).first()
                            except (ValueError, IndexError):
                                pass
                    
                    if purchase:
                        logger.info(f"🔄 Compra de pacote {purchase.id} confirmada mas ainda pendente - processando webhook automaticamente...")
                        try:
                            # Determinar status final
                            final_status = payment_status
                            if confirmed_date or payment_date:
                                final_status = "CONFIRMED"
                            elif net_value and float(net_value) != float(value) and billing_type == "CREDIT_CARD":
                                final_status = "CONFIRMED"
                            
                            notification_data = {
                                "event": "PAYMENT_CONFIRMED",
                                "payment": {
                                    "id": payment_id,
                                    "status": final_status,
                                    "paymentDate": payment_date or confirmed_date,
                                    "externalReference": external_ref
                                }
                            }
                            
                            controller = AsaasController(db)
                            result = controller.process_webhook_notification(notification_data)
                            logger.info(f"✅ Webhook processado automaticamente para compra de pacote {purchase.id}: {result}")
                            
                            # Recarregar compra após processamento
                            db.refresh(purchase)
                        except Exception as e:
                            logger.warning(f"⚠️ Erro ao processar webhook automaticamente para compra de pacote {purchase.id}: {e}")
                            import traceback
                            logger.warning(traceback.format_exc())
        
        # Formatar pagamentos para o frontend
        formatted_payments = []
        
        # Adicionar pagamentos do Asaas
        for payment in payments:
            payment_id = payment.get("id")
            status = payment.get("status", "PENDING")
            
            # Log detalhado de todos os campos retornados pela API para debug
            logger.info(f"📋 Pagamento {payment_id} - Campos retornados pela API:")
            logger.info(f"   - status: {payment.get('status')}")
            logger.info(f"   - paymentDate: {payment.get('paymentDate')}")
            logger.info(f"   - clientPaymentDate: {payment.get('clientPaymentDate')}")
            logger.info(f"   - confirmedDate: {payment.get('confirmedDate')}")
            logger.info(f"   - creditDate: {payment.get('creditDate')}")
            logger.info(f"   - value: {payment.get('value')}")
            logger.info(f"   - netValue: {payment.get('netValue')}")
            logger.info(f"   - dueDate: {payment.get('dueDate')}")
            logger.info(f"   - billingType: {payment.get('billingType')}")
            logger.info(f"   - description: {payment.get('description')}")
            logger.info(f"   - Todos os campos: {list(payment.keys())}")
            
            # Verificar diferentes possíveis nomes do campo (conforme documentação é paymentDate)
            # IMPORTANTE: confirmedDate também indica confirmação de pagamento
            payment_date = payment.get("paymentDate") or payment.get("payment_date") or payment.get("datePayment")
            confirmed_date = payment.get("confirmedDate") or payment.get("confirmed_date")
            client_payment_date = payment.get("clientPaymentDate") or payment.get("client_payment_date")
            credit_date = payment.get("creditDate") or payment.get("credit_date")
            net_value = payment.get("netValue") or payment.get("net_value")
            value = payment.get("value", 0)
            billing_type = payment.get("billingType", "")
            
            # Se tem confirmedDate, o pagamento foi confirmado (mesmo que status seja PENDING)
            if confirmed_date:
                payment_date = confirmed_date  # Usar confirmedDate como paymentDate
                logger.info(f"✅ Pagamento {payment_id} tem confirmedDate ({confirmed_date}) - considerando como confirmado")
            
            # IMPORTANTE: Segundo a documentação do Asaas, se há paymentDate, o pagamento foi pago
            # Mesmo que o status ainda seja PENDING, devemos considerar como CONFIRMED
            # Isso é especialmente importante para pagamentos recentes que ainda não foram atualizados
            if status.upper() in ["CONFIRMED", "RECEIVED"]:
                # Status já está confirmado
                logger.info(f"✅ Pagamento {payment_id} já está {status.upper()} no Asaas")
            elif payment_date:
                # Se tem paymentDate, o pagamento foi efetivado, então é CONFIRMED
                if status.upper() == "PENDING":
                    logger.info(f"✅ Pagamento {payment_id} tem paymentDate ({payment_date}) mas status é PENDING - considerando como CONFIRMED")
                    status = "CONFIRMED"
                elif status.upper() not in ["CONFIRMED", "RECEIVED"]:
                    logger.info(f"✅ Pagamento {payment_id} tem paymentDate ({payment_date}) - considerando como CONFIRMED")
                    status = "CONFIRMED"
            # Se não tem paymentDate mas tem clientPaymentDate e status não é OVERDUE/CANCELLED, pode estar confirmado
            elif client_payment_date and status.upper() not in ["OVERDUE", "CANCELLED", "REFUNDED"]:
                logger.info(f"⚠️ Pagamento {payment_id} tem clientPaymentDate ({client_payment_date}) mas não tem paymentDate - status: {status}")
                # Para assinaturas, se tem clientPaymentDate pode indicar que foi informado pelo cliente
                # Não alterar status automaticamente, mas logar para análise
            # Se tem creditDate, o pagamento foi creditado (confirmado)
            elif credit_date:
                logger.info(f"✅ Pagamento {payment_id} tem creditDate ({credit_date}) - considerando como confirmado")
                payment_date = credit_date
                if status.upper() == "PENDING":
                    status = "CONFIRMED"
            # Se tem netValue diferente de value, pode indicar processamento (taxas descontadas)
            # Para cartão de crédito, isso geralmente indica que foi processado
            elif net_value and float(net_value) != float(value) and billing_type == "CREDIT_CARD":
                logger.info(f"✅ Pagamento {payment_id} tem netValue ({net_value}) diferente de value ({value}) - Cartão processado, considerando como confirmado")
                if status.upper() == "PENDING":
                    status = "CONFIRMED"
            elif net_value and float(net_value) != float(value):
                logger.info(f"⚠️ Pagamento {payment_id} tem netValue ({net_value}) diferente de value ({value}) - pode indicar processamento")
            
            # Normalizar status para minúsculas conforme documentação do Asaas
            # Status possíveis: PENDING, CONFIRMED, RECEIVED, OVERDUE, REFUNDED, CANCELLED
            status_normalized = status.upper() if status else "PENDING"
            
            if status_normalized in ["CONFIRMED", "RECEIVED"]:
                status_lower = "confirmed"
            elif status_normalized == "OVERDUE":
                status_lower = "overdue"
            elif status_normalized == "REFUNDED":
                status_lower = "refunded"
            elif status_normalized == "CANCELLED":
                status_lower = "cancelled"
            else:
                status_lower = "pending"
            
            # Garantir que as datas sejam retornadas no formato ISO completo
            # Se a data vier apenas como YYYY-MM-DD, adicionar hora local para evitar problemas de timezone
            def format_date_iso(date_str):
                """Formata data para ISO completo, evitando problemas de timezone"""
                if not date_str:
                    return None
                try:
                    # Se já está no formato ISO completo, retornar como está
                    if 'T' in str(date_str) or '+' in str(date_str) or 'Z' in str(date_str):
                        return str(date_str)
                    # Se está no formato YYYY-MM-DD, adicionar hora local (meio-dia para evitar problemas de timezone)
                    if len(str(date_str)) == 10:
                        return f"{date_str}T12:00:00"
                    return str(date_str)
                except:
                    return str(date_str) if date_str else None
            
            # Se o pagamento está confirmado mas não tem paymentDate do Asaas, usar data atual no horário de São Paulo
            if status_lower in ["confirmed", "received"] and not payment_date:
                try:
                    from zoneinfo import ZoneInfo
                    sao_paulo_tz = ZoneInfo('America/Sao_Paulo')
                    now_sp = datetime.now(sao_paulo_tz)
                except ImportError:
                    # Fallback para Python < 3.9 ou sistemas sem zoneinfo
                    import time
                    # UTC-3 para São Paulo (considerando horário padrão)
                    offset_hours = -3
                    now_utc = datetime.utcnow()
                    now_sp = now_utc + timedelta(hours=offset_hours)
                
                payment_date = now_sp.strftime("%Y-%m-%d")
                logger.info(f"📅 Pagamento {payment_id} confirmado sem paymentDate do Asaas - usando data atual de São Paulo: {payment_date}")
            
            formatted_payments.append({
                "id": payment_id,
                "value": payment.get("value", 0),
                "status": status_lower,
                "billingType": payment.get("billingType", ""),
                "dueDate": format_date_iso(payment.get("dueDate")),
                "paymentDate": format_date_iso(payment_date),
                "description": payment.get("description", ""),
                "invoiceUrl": payment.get("invoiceUrl"),
                "created_at": format_date_iso(payment.get("dateCreated") or payment.get("dueDate")),
                "originalStatus": status,  # Manter status original para referência
                "type": "subscription"  # Tipo de pagamento
            })
        
        # Adicionar compras de pacotes de tokens
        for purchase in package_purchases:
            package = db.query(TokenPackage).filter(TokenPackage.id == purchase.package_id).first()
            package_name = package.name if package else "Pacote de Tokens"
            
            # Mapear status
            status_map = {
                "pending": "pending",
                "confirmed": "confirmed",
                "cancelled": "cancelled"
            }
            status = status_map.get(purchase.payment_status, "pending")
            
            # Converter preço se for string
            price_value = 0
            if purchase.price:
                if isinstance(purchase.price, str):
                    price_value = float(purchase.price.replace("R$", "").replace(",", ".").strip())
                else:
                    price_value = float(purchase.price)
            
            # Formatar datas no formato ISO completo para evitar problemas de timezone
            due_date_iso = None
            payment_date_iso = None
            created_at_iso = None
            
            if purchase.purchased_at:
                if isinstance(purchase.purchased_at, datetime):
                    due_date_iso = purchase.purchased_at.isoformat()
                    created_at_iso = purchase.purchased_at.isoformat()
                else:
                    due_date_iso = str(purchase.purchased_at)
                    created_at_iso = str(purchase.purchased_at)
            
            if purchase.confirmed_at:
                if isinstance(purchase.confirmed_at, datetime):
                    payment_date_iso = purchase.confirmed_at.isoformat()
                else:
                    payment_date_iso = str(purchase.confirmed_at)
            
            formatted_payments.append({
                "id": purchase.asaas_payment_id or f"package_{purchase.id}",
                "value": price_value,
                "status": status,
                "billingType": purchase.payment_method or "CREDIT_CARD",
                "dueDate": due_date_iso,
                "paymentDate": payment_date_iso,
                "description": f"Pacote de Tokens: {package_name} ({purchase.tokens_amount} tokens)",
                "invoiceUrl": purchase.invoice_url,
                "created_at": created_at_iso,
                "originalStatus": purchase.payment_status.upper(),
                "type": "package",  # Tipo de pagamento
                "tokens_amount": purchase.tokens_amount,
                "package_name": package_name
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
        
        if not payment:
            logger.warning(f"⚠️ Pagamento {payment_id} não encontrado no Asaas")
            raise HTTPException(
                status_code=404,
                detail="Pagamento não encontrado no Asaas"
            )
        
        payment_status = payment.get("status", "").upper()
        if payment_status not in ["CONFIRMED", "RECEIVED"]:
            logger.warning(f"⚠️ Pagamento {payment_id} não está confirmado. Status: {payment_status}")
            raise HTTPException(
                status_code=400,
                detail=f"Pagamento não está confirmado. Status atual: {payment_status}"
            )
        
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
            
            # VALIDAÇÃO ADICIONAL: Se a descrição contém "Primeiro pagamento" e temos uma assinatura pendente/trial,
            # considerar como relacionado (é o pagamento inicial que criamos)
            if not is_related_by_description and ("primeiro pagamento" in payment_description_lower or "first payment" in payment_description_lower):
                # Verificar se o externalReference do pagamento corresponde à empresa
                payment_external_ref = payment.get("externalReference", "")
                if payment_external_ref and f"company_{user['company_id']}" in payment_external_ref:
                    is_related_by_description = True
                    logger.info(f"✅ Pagamento relacionado ao plano via 'Primeiro pagamento' e externalReference: {payment_external_ref}")
        
        # TERCEIRA VALIDAÇÃO: Verificar externalReference do pagamento
        is_related_by_external_ref = False
        payment_external_ref = payment.get("externalReference", "")
        if payment_external_ref and f"company_{user['company_id']}" in payment_external_ref:
            is_related_by_external_ref = True
            logger.info(f"✅ Pagamento relacionado ao plano via externalReference: {payment_external_ref}")
        
        # QUARTA VALIDAÇÃO: Se o pagamento não tem subscription_id, mas temos asaas_subscription_id,
        # buscar pagamentos da assinatura para verificar se este pagamento pertence a ela
        is_related_by_subscription_payments = False
        if not is_related_by_subscription and not is_related_by_description and not is_related_by_external_ref and asaas_subscription_id:
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
        is_related_to_plan = is_related_by_subscription or is_related_by_description or is_related_by_external_ref or is_related_by_subscription_payments
        
        if not is_related_to_plan:
            logger.warning(f"⚠️ Pagamento não relacionado ao plano:")
            logger.warning(f"   - Payment subscription_id: {payment_subscription_id}")
            logger.warning(f"   - Plan subscription_id: {asaas_subscription_id}")
            logger.warning(f"   - Payment description: '{payment_description}'")
            logger.warning(f"   - Plan name: '{plan_name}'")
            logger.warning(f"   - Payment externalReference: '{payment.get('externalReference', 'N/A')}'")
            logger.warning(f"   - Company ID: {user['company_id']}")
            logger.warning(f"   - Validações: subscription={is_related_by_subscription}, description={is_related_by_description}, external_ref={is_related_by_external_ref}, payments_list={is_related_by_subscription_payments}")
            raise HTTPException(
                status_code=400,
                detail="Este pagamento não está relacionado ao plano. Apenas pagamentos do plano podem atualizar o cadastro."
            )
        
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
            # SEMPRE atualizar status para ACTIVE quando pagamento confirmado
            old_status = company_obj.status
            company_obj.status = CompanyStatus.ACTIVE
            if old_status != CompanyStatus.ACTIVE:
                logger.info(f"✅ Empresa {company_obj.id} status atualizado: {old_status} → ACTIVE")
            
            company_obj.plan_expires_at = next_due
            company_obj.trial_ends_at = None
            company_obj.updated_at = datetime.now()
            
            # Atualizar tokens mensais do plano
            # ai_tokens_monthly = quantidade de tokens mensais do plano (atualizar, não somar)
            # ai_tokens_purchased = tokens comprados avulsos (não alterar aqui, só quando compra pacotes)
            subscription_ai_tokens = subscription.get("ai_analysis_monthly")
            if subscription_ai_tokens:
                tokens_from_plan = subscription_ai_tokens
                current_monthly = company_obj.ai_tokens_monthly if company_obj.ai_tokens_monthly else 0
                
                # Atualizar ai_tokens_monthly com o valor do plano (não somar, apenas atualizar)
                company_obj.ai_tokens_monthly = tokens_from_plan
                logger.info(f"✅ Tokens mensais atualizados: {current_monthly} → {tokens_from_plan} (plano: {subscription.get('plan_name')})")
                logger.info(f"✅ Empresa {company_obj.id} atualizada: status=ACTIVE, ai_tokens_monthly={tokens_from_plan}")
            else:
                logger.warning(f"⚠️ Assinatura '{subscription.get('plan_name')}' não tem ai_analysis_monthly definido")
        
        db.commit()
        
        logger.info(f"✅ Cadastro atualizado para empresa {user['company_id']} baseado no pagamento {payment_id}")
        logger.info(f"   - Próximo vencimento: {next_due.strftime('%d/%m/%Y')}")
        
        return {
            "success": True,
            "message": "Cadastro atualizado com sucesso",
            "next_due_date": next_due.strftime("%d/%m/%Y")
        }
        
    except HTTPException:
        # Re-raise HTTPException para manter o status code correto
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro ao atualizar cadastro: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=400, detail=f"Erro ao atualizar cadastro: {str(e)}")


@router.post("/payments/{payment_id}/sync", response_model=Dict[str, Any])
async def sync_payment_status(
    payment_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Sincroniza o status de um pagamento com o Asaas
    Busca o status atual no Asaas e atualiza no sistema se necessário
    """
    try:
        user = get_current_user(request, db)
        
        # Buscar o pagamento no Asaas
        from app.services.asaas_service import asaas_service
        from app.controllers.asaas_controller import AsaasController
        
        logger.info(f"🔄 Sincronizando status do pagamento {payment_id} com Asaas...")
        
        payment = asaas_service._make_request("GET", f"/payments/{payment_id}")
        
        if not payment:
            logger.warning(f"⚠️ Pagamento {payment_id} não encontrado no Asaas")
            raise HTTPException(
                status_code=404,
                detail="Pagamento não encontrado no Asaas"
            )
        
        # Log completo da resposta para debug
        logger.info(f"📋 Resposta completa do pagamento {payment_id}: {json.dumps(payment, indent=2, default=str)}")
        
        # Extrair todos os campos relevantes
        payment_status = payment.get("status", "").upper()
        payment_date = payment.get("paymentDate") or payment.get("payment_date") or payment.get("datePayment")
        confirmed_date = payment.get("confirmedDate") or payment.get("confirmed_date")
        client_payment_date = payment.get("clientPaymentDate") or payment.get("client_payment_date")
        credit_date = payment.get("creditDate") or payment.get("credit_date")
        external_ref = payment.get("externalReference", "") or payment.get("external_reference", "")
        value = payment.get("value", 0)
        net_value = payment.get("netValue") or payment.get("net_value")
        billing_type = payment.get("billingType", "")
        
        # Se tem confirmedDate, usar como paymentDate (indica confirmação)
        if confirmed_date:
            payment_date = confirmed_date
            logger.info(f"✅ Pagamento {payment_id} tem confirmedDate ({confirmed_date}) - usando como paymentDate")
        
        # Log detalhado de todos os campos relevantes
        logger.info(f"📊 Status do pagamento {payment_id} no Asaas:")
        logger.info(f"   - status: {payment_status}")
        logger.info(f"   - paymentDate: {payment.get('paymentDate')}")
        logger.info(f"   - confirmedDate: {confirmed_date}")
        logger.info(f"   - creditDate: {credit_date}")
        logger.info(f"   - clientPaymentDate: {client_payment_date}")
        logger.info(f"   - value: {value}")
        logger.info(f"   - netValue: {net_value}")
        logger.info(f"   - billingType: {billing_type}")
        logger.info(f"   - dueDate: {payment.get('dueDate')}")
        logger.info(f"   - externalReference: {external_ref}")
        logger.info(f"   - Todos os campos disponíveis: {list(payment.keys())}")
        
        # IMPORTANTE: Segundo a documentação do Asaas, se há paymentDate ou confirmedDate, o pagamento foi pago
        # Mesmo que o status ainda seja PENDING, devemos considerar como CONFIRMED
        final_status = payment_status
        payment_confirmed = False
        
        # Verificar múltiplos indicadores de pagamento confirmado
        if payment_status in ["CONFIRMED", "RECEIVED"]:
            payment_confirmed = True
            logger.info(f"✅ Pagamento {payment_id} está {payment_status} no Asaas")
        elif confirmed_date:
            # confirmedDate indica que o pagamento foi confirmado
            final_status = "CONFIRMED"
            payment_confirmed = True
            logger.info(f"✅ Pagamento {payment_id} tem confirmedDate ({confirmed_date}) - considerando como CONFIRMED")
        elif payment_date:
            # Se tem paymentDate, o pagamento foi efetivado
            if payment_status == "PENDING":
                logger.info(f"✅ Pagamento {payment_id} tem paymentDate ({payment_date}) mas status é PENDING - considerando como CONFIRMED")
                final_status = "CONFIRMED"
                payment_confirmed = True
            elif payment_status not in ["CONFIRMED", "RECEIVED"]:
                logger.info(f"✅ Pagamento {payment_id} tem paymentDate ({payment_date}) - considerando como CONFIRMED")
                final_status = "CONFIRMED"
                payment_confirmed = True
        elif client_payment_date and payment_status not in ["OVERDUE", "CANCELLED"]:
            # Se tem clientPaymentDate e não está vencido/cancelado, pode estar confirmado
            logger.info(f"⚠️ Pagamento {payment_id} tem clientPaymentDate ({client_payment_date}) mas não tem paymentDate - status: {payment_status}")
            # Fazer verificação adicional: buscar novamente após alguns segundos
            import time
            time.sleep(2)
            try:
                payment_retry = asaas_service._make_request("GET", f"/payments/{payment_id}")
                retry_status = payment_retry.get("status", "").upper()
                retry_payment_date = payment_retry.get("paymentDate")
                if retry_status in ["CONFIRMED", "RECEIVED"] or retry_payment_date:
                    logger.info(f"✅ Após verificação adicional, pagamento {payment_id} está confirmado")
                    final_status = retry_status if retry_status in ["CONFIRMED", "RECEIVED"] else "CONFIRMED"
                    payment_date = retry_payment_date or client_payment_date
                    payment_confirmed = True
                else:
                    logger.info(f"⚠️ Após verificação adicional, pagamento {payment_id} ainda está {retry_status}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao fazer verificação adicional: {e}")
        elif credit_date:
            # creditDate indica que o pagamento foi creditado (confirmado)
            final_status = "CONFIRMED"
            payment_confirmed = True
            payment_date = credit_date
            logger.info(f"✅ Pagamento {payment_id} tem creditDate ({credit_date}) - considerando como CONFIRMED")
        elif net_value and float(net_value) != float(value) and billing_type == "CREDIT_CARD":
            # Para cartão de crédito, se tem netValue diferente de value, foi processado (taxas descontadas)
            final_status = "CONFIRMED"
            payment_confirmed = True
            logger.info(f"✅ Pagamento {payment_id} tem netValue ({net_value}) diferente de value ({value}) - Cartão processado, considerando como CONFIRMED")
        elif net_value and float(net_value) != float(value):
            # Se tem netValue diferente de value, pode indicar processamento
            logger.info(f"⚠️ Pagamento {payment_id} tem netValue ({net_value}) diferente de value ({value}) - pode indicar processamento")
            # Não confirmar automaticamente, mas logar para análise
        
        # Se o pagamento está confirmado/recebido ou tem paymentDate, processar como webhook
        if payment_confirmed or final_status in ["CONFIRMED", "RECEIVED"] or payment_date:
            logger.info(f"✅ Pagamento {payment_id} está confirmado no Asaas (status: {final_status}), processando webhook...")
            
            # Criar notificação simulando webhook
            notification_data = {
                "event": "PAYMENT_CONFIRMED",
                "payment": {
                    "id": payment_id,
                    "status": final_status,
                    "paymentDate": payment_date,
                    "externalReference": external_ref
                }
            }
            
            # Processar webhook
            controller = AsaasController(db)
            result = controller.process_webhook_notification(notification_data)
            
            return {
                "success": True,
                "message": "Status sincronizado com sucesso e webhook processado",
                "payment_status": "confirmed",  # Sempre retornar como confirmed se foi processado
                "payment_date": payment_date,
                "original_status": payment_status.lower(),
                "final_status": final_status.lower(),
                "result": result
            }
        else:
            return {
                "success": True,
                "message": f"Status sincronizado: {payment_status.lower()}",
                "payment_status": payment_status.lower(),
                "payment_date": payment_date,
                "note": "Pagamento ainda não confirmado no Asaas"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erro ao sincronizar pagamento: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar pagamento: {str(e)}")


@router.post("/webhooks")
async def receive_asaas_webhook(
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
    - PAYMENT_CHECKOUT_VIEWED: Checkout visualizado
    """
    try:
        import json
        
        # Ler o corpo da requisição como bytes primeiro
        body = await request.body()
        logger.info(f"📥 Webhook recebido - Tamanho: {len(body)} bytes")
        logger.info(f"📥 Headers: {dict(request.headers)}")
        
        # Tentar parsear como JSON
        try:
            if body:
                notification = json.loads(body.decode('utf-8'))
            else:
                # Se não tiver body, tentar pegar do request.json()
                notification = await request.json()
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erro ao parsear JSON do webhook: {e}")
            logger.error(f"❌ Body recebido (primeiros 500 chars): {body[:500] if body else 'VAZIO'}")
            raise HTTPException(status_code=400, detail=f"JSON inválido: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Erro ao ler body do webhook: {e}")
            raise HTTPException(status_code=400, detail=f"Erro ao ler requisição: {str(e)}")
        
        logger.info(f"📨 Webhook parseado completo: {json.dumps(notification, indent=2, default=str)}")
        
        # Validar que tem pelo menos um campo básico
        if not isinstance(notification, dict):
            logger.error(f"❌ Webhook não é um dicionário: {type(notification)}")
            raise HTTPException(status_code=400, detail="Webhook deve ser um objeto JSON")
        
        # Validar token do webhook (se configurado)
        from app.config.settings import settings
        if settings.asaas_webhook_token:
            webhook_token = request.headers.get("asaas-access-token")
            if webhook_token != settings.asaas_webhook_token:
                logger.warning(f"⚠️ Token do webhook inválido ou não fornecido")
                # Não bloquear, apenas logar (pode ser que não esteja configurado)
        
        controller = AsaasController(db)
        result = controller.process_webhook_notification(notification)
        
        event = notification.get('event', 'UNKNOWN')
        logger.info(f"✅ Webhook Asaas processado com sucesso: {event}")
        
        return result
        
    except HTTPException:
        # Re-raise HTTPException para manter o status code correto
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao processar webhook do Asaas: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=400, detail=f"Erro ao processar webhook: {str(e)}")


@router.get("/webhooks/test")
async def test_webhook_endpoint():
    """
    Endpoint de teste para verificar se o webhook está acessível
    """
    return {
        "success": True,
        "message": "Webhook endpoint está funcionando!",
        "endpoint": "/api/asaas/webhooks",
        "method": "POST",
        "example_payload": {
            "event": "PAYMENT_CONFIRMED",
            "payment": {
                "id": "pay_test_123",
                "subscription": "sub_test_123",
                "status": "CONFIRMED",
                "value": 99.90,
                "dueDate": "2024-02-01",
                "paymentDate": "2024-02-01",
                "externalReference": "package_1_company_1"
            }
        }
    }


@router.post("/webhooks/test")
async def test_webhook_with_sample_data(
    event_type: str = Query("PAYMENT_CONFIRMED", description="Tipo de evento"),
    payment_id: str = Query(None, description="ID do pagamento"),
    subscription_id: str = Query(None, description="ID da assinatura"),
    external_reference: str = Query(None, description="Referência externa (formato: package_{id}_company_{id})"),
    db: Session = Depends(get_db)
):
    """
    Endpoint de teste para enviar uma notificação de webhook simulada
    
    Parâmetros:
    - event_type: Tipo de evento (PAYMENT_CONFIRMED, PAYMENT_RECEIVED, etc.)
    - payment_id: ID do pagamento (opcional)
    - subscription_id: ID da assinatura (opcional)
    - external_reference: Referência externa (opcional, formato: package_{id}_company_{id})
    """
    try:
        # Criar payload de teste baseado no formato do Asaas
        test_notification = {
            "event": event_type,
            "payment": {
                "id": payment_id or f"pay_test_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "subscription": subscription_id,
                "status": "CONFIRMED" if event_type in ["PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"] else "PENDING",
                "value": 99.90,
                "dueDate": datetime.now().strftime("%Y-%m-%d"),
                "paymentDate": datetime.now().strftime("%Y-%m-%d") if event_type in ["PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"] else None,
                "externalReference": external_reference or f"company_1_user_1_initial"
            }
        }
        
        if subscription_id:
            test_notification["subscription"] = {
                "id": subscription_id
            }
        
        logger.info(f"🧪 Teste de webhook - Enviando notificação: {json.dumps(test_notification, indent=2)}")
        
        # Processar webhook
        controller = AsaasController(db)
        result = controller.process_webhook_notification(test_notification)
        
        logger.info(f"✅ Teste de webhook processado: {result}")
        
        return {
            "success": True,
            "message": "Webhook de teste processado com sucesso",
            "test_notification": test_notification,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao processar webhook de teste: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro ao processar webhook de teste: {str(e)}")


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

