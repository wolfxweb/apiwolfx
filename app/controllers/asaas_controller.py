"""
Controller para operações de assinatura Asaas
"""
import logging
import json
import re
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.services.asaas_service import asaas_service
from app.models.asaas_models import (
    AsaasCreateCustomerRequest,
    AsaasCreateSubscriptionRequest
)
from app.models.saas_models import Subscription, Company, User, CompanyStatus

logger = logging.getLogger(__name__)


def _remove_emojis(text: str) -> str:
    """
    Remove emojis e caracteres especiais não permitidos pelo Asaas
    
    Args:
        text: Texto que pode conter emojis
        
    Returns:
        Texto sem emojis
    """
    if not text:
        return ""
    
    # Remover emojis usando regex
    # Padrão para remover emojis Unicode
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed characters
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "]+", 
        flags=re.UNICODE
    )
    
    # Remover emojis
    text = emoji_pattern.sub('', text)
    
    # Remover outros caracteres especiais problemáticos
    # Manter apenas letras, números, espaços e alguns caracteres básicos
    text = re.sub(r'[^\w\s\-\.\,\:\;\(\)\/]', '', text)
    
    # Limpar espaços múltiplos
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


class AsaasController:
    """Controller para operações de assinatura Asaas"""
    
    def __init__(self, db: Session):
        self.db = db
        self.asaas_service = asaas_service
    
    def create_subscription(
        self,
        plan_id: str,
        company_id: int,
        user_id: int,
        subscriber_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Cria uma assinatura recorrente no Asaas
        
        Args:
            plan_id: ID do plano (subscription template ID)
            company_id: ID da empresa
            user_id: ID do usuário
            subscriber_data: Dados do assinante (email, nome, CPF, etc.)
        
        Returns:
            Dict com dados da assinatura criada
        """
        try:
            # Buscar empresa e usuário
            company = self.db.query(Company).filter(Company.id == company_id).first()
            if not company:
                raise ValueError("Empresa não encontrada")
            
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("Usuário não encontrado")
            
            # Buscar plano template
            plan = self.db.query(Subscription).filter(
                Subscription.id == int(plan_id),
                Subscription.company_id.is_(None),
                Subscription.status == "template"
            ).first()
            
            if not plan:
                raise ValueError("Plano não encontrado")
            
            # 1. Criar ou buscar cliente no Asaas
            asaas_customer_id = self._get_or_create_customer(
                company_id=company_id,
                user_id=user_id,
                subscriber_data=subscriber_data
            )
            
            # 2. Preparar dados da assinatura
            billing_type = subscriber_data.get("billing_type", "CREDIT_CARD")
            if billing_type not in ["BOLETO", "CREDIT_CARD", "PIX", "DEBIT_CARD"]:
                billing_type = "CREDIT_CARD"
            
            # Converter billing_cycle para ciclo do Asaas
            cycle_map = {
                "monthly": "MONTHLY",
                "quarterly": "QUARTERLY",
                "yearly": "YEARLY",
                "semiannually": "SEMIANNUALLY",
                "weekly": "WEEKLY",
                "biweekly": "BIWEEKLY"
            }
            asaas_cycle = cycle_map.get(plan.billing_cycle, "MONTHLY")
            
            # Calcular próxima data de vencimento
            next_due_date = datetime.now() + timedelta(days=30)  # Default: mensal
            if plan.billing_cycle == "quarterly":
                next_due_date = datetime.now() + timedelta(days=90)  # 3 meses
            elif plan.billing_cycle == "semiannually":
                next_due_date = datetime.now() + timedelta(days=180)  # 6 meses
            elif plan.billing_cycle == "yearly":
                next_due_date = datetime.now() + timedelta(days=365)  # 12 meses
            
            # Calcular data de término da assinatura (ends_at)
            ends_at = None
            if plan.billing_cycle == "monthly":
                ends_at = datetime.now() + timedelta(days=30)
            elif plan.billing_cycle == "quarterly":
                ends_at = datetime.now() + timedelta(days=90)
            elif plan.billing_cycle == "semiannually":
                ends_at = datetime.now() + timedelta(days=180)
            elif plan.billing_cycle == "yearly":
                ends_at = datetime.now() + timedelta(days=365)
            
            # Valor do plano
            plan_value = float(plan.price.replace("R$", "").replace(",", ".").strip())
            
            # Remover emojis da descrição (Asaas não permite emojis)
            subscription_description = _remove_emojis(f"{plan.plan_name} - {plan.billing_cycle}")
            
            # IMPORTANTE: Não incluir callback na assinatura
            # O callback requer domínio configurado no Asaas
            # Como já obtemos o invoiceUrl do pagamento, não precisamos do callback
            subscription_data = {
                "customer": asaas_customer_id,
                "billingType": billing_type,
                "value": plan_value,
                "nextDueDate": next_due_date.strftime("%Y-%m-%d"),
                "cycle": asaas_cycle,
                "description": subscription_description,
                "externalReference": f"company_{company_id}_user_{user_id}"
            }
            
            # Adicionar dados do cartão se for cartão de crédito
            if billing_type == "CREDIT_CARD" and "credit_card_token" in subscriber_data:
                subscription_data["creditCardToken"] = subscriber_data["credit_card_token"]
            
            # IMPORTANTE: Criar o pagamento PRIMEIRO (sem assinatura) para obter invoiceUrl
            # Igual ao teste que funcionou - criar pagamento direto, depois criar assinatura
            invoice_url = None
            payment_result = None
            payment_id = None
            
            try:
                logger.info(f"💳 Criando cobrança inicial (SEM assinatura) para obter invoiceUrl...")
                logger.info(f"   Cliente: {asaas_customer_id}")
                logger.info(f"   Valor: R$ {plan_value:.2f}")
                logger.info(f"   Tipo: {billing_type}")
                
                # Criar pagamento SEM o campo "subscription" (igual ao teste que funcionou)
                # A data de vencimento deve ser hoje para pagamento imediato
                due_date = datetime.now()  # Vencimento para hoje (pagamento imediato)
                
                # Remover emojis da descrição (Asaas não permite emojis)
                payment_description = _remove_emojis(f"{plan.plan_name} - Primeiro pagamento")
                
                payment_data = {
                    "customer": asaas_customer_id,
                    "billingType": billing_type,
                    "value": plan_value,
                    "dueDate": due_date.strftime("%Y-%m-%d"),
                    "description": payment_description,
                    "externalReference": f"company_{company_id}_user_{user_id}_initial"
                    # NÃO incluir "subscription" aqui - igual ao teste que funcionou
                }
                
                # Adicionar parcelamento se for cartão de crédito parcelado
                if billing_type == "CREDIT_CARD":
                    installments = subscriber_data.get("installments", 1)
                    if installments and installments > 1:
                        payment_data["installmentCount"] = installments
                        payment_data["installmentValue"] = round(plan_value / installments, 2)
                        logger.info(f"💳 Pagamento parcelado: {installments}x de R$ {payment_data['installmentValue']:.2f}")
                
                logger.info(f"📤 Dados do pagamento (sem assinatura, igual ao teste): {payment_data}")
                payment_result = self.asaas_service.create_payment(payment_data)
                logger.info(f"📥 Resposta completa do pagamento: {json.dumps(payment_result, indent=2, default=str)}")
                
                payment_id = payment_result.get("id")
                
                # Tentar múltiplas chaves possíveis para invoiceUrl (igual ao teste)
                invoice_url = (
                    payment_result.get("invoiceUrl") or 
                    payment_result.get("invoice_url")
                )
                
                logger.info(f"🔍 Invoice URL extraída: {invoice_url}")
                
                if not invoice_url:
                    logger.error(f"❌ Invoice URL não encontrada na resposta do pagamento!")
                    logger.error(f"❌ Chaves disponíveis: {list(payment_result.keys()) if isinstance(payment_result, dict) else 'N/A'}")
                else:
                    logger.info(f"✅ Invoice URL obtida com sucesso: {invoice_url}")
            except Exception as e:
                logger.error(f"❌ Erro ao criar cobrança inicial: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Continuar mesmo sem invoiceUrl - tentar criar assinatura
            
            # 3. Criar assinatura no Asaas (após criar o pagamento)
            logger.info(f"📤 Criando assinatura no Asaas com dados: {subscription_data}")
            asaas_result = self.asaas_service.create_subscription(subscription_data)
            logger.info(f"📥 Resposta completa do Asaas: {asaas_result}")
            asaas_subscription_id = asaas_result.get("id")
            
            if not asaas_subscription_id:
                logger.error(f"❌ Resposta do Asaas não contém ID: {asaas_result}")
                raise ValueError("Assinatura criada no Asaas mas sem ID retornado")
            
            logger.info(f"✅ Assinatura criada no Asaas: {asaas_subscription_id}")
            
            # 4. Buscar ou criar assinatura local
            # Buscar por company_id (pode estar pending, active, etc)
            subscription = self.db.query(Subscription).filter(
                Subscription.company_id == company_id
            ).first()
            
            if not subscription:
                # IMPORTANTE: Criar assinatura com status PENDING e mantendo TRIAL
                # O status só será alterado para ACTIVE e o trial removido após confirmação de pagamento via webhook
                trial_days = plan.trial_days if plan.trial_days else 0
                is_trial = trial_days > 0
                trial_ends_at = datetime.now() + timedelta(days=trial_days) if is_trial else None
                
                subscription = Subscription(
                    company_id=company_id,
                    plan_name=plan.plan_name,
                    description=plan.description,
                    plan_features=plan.plan_features,
                    price=plan.price,
                    promotional_price=plan.promotional_price,
                    currency=plan.currency,
                    billing_cycle=plan.billing_cycle,
                    max_users=plan.max_users,
                    max_ml_accounts=plan.max_ml_accounts,
                    storage_gb=plan.storage_gb,
                    ai_analysis_monthly=plan.ai_analysis_monthly,
                    catalog_monitoring_slots=plan.catalog_monitoring_slots,
                    product_mining_slots=plan.product_mining_slots,
                    product_monitoring_slots=plan.product_monitoring_slots,
                    trial_days=plan.trial_days,
                    status="pending",  # PENDING até pagamento ser confirmado
                    is_trial=is_trial,  # Manter trial até pagamento ser confirmado
                    starts_at=None,  # Será definido após confirmação de pagamento
                    ends_at=None,  # Será definido após confirmação de pagamento
                    next_charge_date=None,  # Será definido após confirmação de pagamento
                    trial_ends_at=trial_ends_at,  # Manter trial até pagamento
                    asaas_subscription_id=asaas_subscription_id,
                    asaas_customer_id=asaas_customer_id,
                    payment_provider="asaas"
                )
                self.db.add(subscription)
                logger.info(f"📝 Assinatura criada com status PENDING e trial={is_trial} (aguardando confirmação de pagamento)")
            else:
                # Atualizar assinatura existente (apenas IDs do Asaas, não alterar status/trial)
                subscription.asaas_subscription_id = asaas_subscription_id
                subscription.asaas_customer_id = asaas_customer_id
                subscription.payment_provider = "asaas"
                # NÃO alterar status, is_trial, starts_at, ends_at aqui - só após confirmação de pagamento
                subscription.updated_at = datetime.now()
                logger.info(f"📝 Assinatura existente atualizada (mantendo status atual até confirmação de pagamento)")
            
            self.db.commit()
            self.db.refresh(subscription)
            
            logger.info(f"✅ Assinatura Asaas criada: {asaas_subscription_id} para empresa {company_id}")
            
            # Se não tivermos invoiceUrl do pagamento inicial, tentar buscar nos pagamentos da assinatura
            if not invoice_url:
                logger.warning(f"⚠️ Invoice URL não obtida do pagamento inicial, buscando nos pagamentos da assinatura...")
                try:
                    payments = self.asaas_service.get_subscription_payments(asaas_subscription_id)
                    logger.info(f"📋 Pagamentos encontrados: {len(payments) if payments else 0}")
                    if payments and len(payments) > 0:
                        # Buscar o pagamento mais recente
                        first_payment = payments[0]
                        logger.info(f"📄 Primeiro pagamento: {json.dumps(first_payment, indent=2, default=str)}")
                        invoice_url = (
                            first_payment.get("invoiceUrl") or 
                            first_payment.get("invoice_url")
                        )
                        logger.info(f"✅ Invoice URL obtida do primeiro pagamento: {invoice_url}")
                except Exception as e2:
                    logger.error(f"❌ Erro ao buscar pagamentos da assinatura: {e2}")
            
            result = {
                "success": True,
                "subscription_id": subscription.id,
                "asaas_subscription_id": asaas_subscription_id,
                "asaas_customer_id": asaas_customer_id,
                "status": "active",
                "message": "Assinatura criada com sucesso"
            }
            
            # Adicionar invoiceUrl se disponível (CRÍTICO para redirecionamento)
            if invoice_url:
                result["invoice_url"] = invoice_url
                logger.info(f"✅ Invoice URL obtida e adicionada ao resultado: {invoice_url}")
                logger.info(f"✅ Resultado final que será retornado: {json.dumps(result, indent=2, default=str)}")
            else:
                logger.error(f"❌ ATENÇÃO: Invoice URL não foi obtida! Não será possível redirecionar para pagamento.")
                logger.error(f"❌ Resultado do pagamento: {json.dumps(payment_result, indent=2, default=str) if payment_result else 'N/A'}")
                # Tentar uma última vez buscar nos pagamentos
                try:
                    logger.info(f"🔍 Tentando buscar invoiceUrl nos pagamentos da assinatura {asaas_subscription_id}...")
                    payments = self.asaas_service.get_subscription_payments(asaas_subscription_id)
                    logger.info(f"📋 Total de pagamentos encontrados: {len(payments) if payments else 0}")
                    if payments:
                        for idx, payment in enumerate(payments):
                            logger.info(f"📄 Pagamento {idx + 1}: {json.dumps(payment, indent=2, default=str)}")
                            temp_url = (
                                payment.get("invoiceUrl") or 
                                payment.get("invoice_url") or
                                payment.get("invoiceURL")
                            )
                            if temp_url:
                                invoice_url = temp_url
                                result["invoice_url"] = invoice_url
                                logger.info(f"✅ Invoice URL encontrada em pagamento existente: {invoice_url}")
                                break
                    else:
                        logger.warning(f"⚠️ Nenhum pagamento encontrado para a assinatura {asaas_subscription_id}")
                except Exception as e:
                    logger.error(f"❌ Erro ao buscar invoiceUrl em pagamentos existentes: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # Log final do resultado
            logger.info(f"📤 RESULTADO FINAL DO create_subscription:")
            logger.info(f"   - success: {result.get('success')}")
            logger.info(f"   - invoice_url: {result.get('invoice_url', 'NÃO DISPONÍVEL')}")
            logger.info(f"   - asaas_subscription_id: {result.get('asaas_subscription_id')}")
            
            return result
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao criar assinatura Asaas: {e}")
            raise e
    
    def _get_or_create_customer(
        self,
        company_id: int,
        user_id: int,
        subscriber_data: Dict[str, Any]
    ) -> str:
        """
        Busca ou cria cliente no Asaas
        
        Returns:
            ID do cliente no Asaas
        """
        try:
            # Buscar empresa para obter CNPJ/CPF salvo no campo cnpj
            company = self.db.query(Company).filter(Company.id == company_id).first()
            # O campo cnpj pode conter tanto CNPJ (14 dígitos) quanto CPF (11 dígitos)
            company_document = company.cnpj if company and company.cnpj else None
            
            # Usar documento da empresa (CNPJ ou CPF) se disponível, senão usar do subscriber_data
            cpf_cnpj_for_asaas = company_document or subscriber_data.get("cpf") or subscriber_data.get("document")
            
            # PRIMEIRO: Tentar buscar cliente existente por CPF/CNPJ no Asaas
            if cpf_cnpj_for_asaas:
                logger.info(f"🔍 Buscando cliente existente por CPF/CNPJ: {cpf_cnpj_for_asaas}")
                existing_customer = self.asaas_service.find_customer_by_cpf_cnpj(cpf_cnpj_for_asaas)
                if existing_customer and existing_customer.get("id"):
                    customer_id = existing_customer["id"]
                    logger.info(f"✅ Cliente existente encontrado no Asaas: {customer_id}")
                    return customer_id
            
            # SEGUNDO: Verificar se já existe cliente para esta empresa no banco local
            existing_subscription = self.db.query(Subscription).filter(
                Subscription.company_id == company_id,
                Subscription.asaas_customer_id.isnot(None)
            ).first()
            
            if existing_subscription and existing_subscription.asaas_customer_id:
                # Verificar se o cliente ainda existe no Asaas
                try:
                    customer = self.asaas_service.get_customer(existing_subscription.asaas_customer_id)
                    if customer and customer.get("id"):
                        logger.info(f"✅ Cliente existente encontrado via subscription local: {customer['id']}")
                        return customer["id"]
                except:
                    # Cliente não existe mais, criar novo
                    logger.warning(f"⚠️ Cliente {existing_subscription.asaas_customer_id} não existe mais no Asaas, criando novo")
                    pass
            
            # Criar novo cliente
            customer_data = {
                "name": subscriber_data.get("name", subscriber_data.get("email", "Cliente")),
                "email": subscriber_data.get("email"),
                "phone": subscriber_data.get("phone"),
                "cpfCnpj": cpf_cnpj_for_asaas,
                "postalCode": subscriber_data.get("postal_code"),
                "address": subscriber_data.get("address"),
                "addressNumber": subscriber_data.get("address_number"),
                "complement": subscriber_data.get("complement"),
                "province": subscriber_data.get("province"),
                "city": subscriber_data.get("city"),
                "state": subscriber_data.get("state"),
                "externalReference": f"company_{company_id}_user_{user_id}"
            }
            
            # Remover campos None
            customer_data = {k: v for k, v in customer_data.items() if v is not None}
            
            customer = self.asaas_service.create_customer(customer_data)
            return customer["id"]
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar/buscar cliente no Asaas: {e}")
            raise e
    
    def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Busca dados de uma assinatura
        
        Args:
            subscription_id: ID da assinatura no banco local
        
        Returns:
            Dict com dados da assinatura
        """
        try:
            subscription = self.db.query(Subscription).filter(
                Subscription.id == int(subscription_id)
            ).first()
            
            if not subscription:
                raise ValueError("Assinatura não encontrada")
            
            if not subscription.asaas_subscription_id:
                raise ValueError("Assinatura não possui ID do Asaas")
            
            # Buscar dados atualizados do Asaas
            asaas_subscription = self.asaas_service.get_subscription(subscription.asaas_subscription_id)
            
            return {
                "id": subscription.id,
                "asaas_subscription_id": subscription.asaas_subscription_id,
                "asaas_customer_id": subscription.asaas_customer_id,
                "status": subscription.status,
                "plan_name": subscription.plan_name,
                "price": subscription.price,
                "billing_cycle": subscription.billing_cycle,
                "asaas_data": asaas_subscription
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar assinatura: {e}")
            raise e
    
    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Cancela uma assinatura
        
        Args:
            subscription_id: ID da assinatura no banco local
        
        Returns:
            Dict com resultado do cancelamento
        """
        try:
            subscription = self.db.query(Subscription).filter(
                Subscription.id == int(subscription_id)
            ).first()
            
            if not subscription:
                raise ValueError("Assinatura não encontrada")
            
            if not subscription.asaas_subscription_id:
                raise ValueError("Assinatura não possui ID do Asaas")
            
            # Cancelar no Asaas
            self.asaas_service.cancel_subscription(subscription.asaas_subscription_id)
            
            # Atualizar status local
            subscription.status = "cancelled"
            subscription.ends_at = datetime.now()
            subscription.updated_at = datetime.now()
            
            self.db.commit()
            
            logger.info(f"✅ Assinatura {subscription_id} cancelada")
            
            return {
                "success": True,
                "message": "Assinatura cancelada com sucesso"
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao cancelar assinatura: {e}")
            raise e
    
    def process_webhook_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa notificação de webhook do Asaas
        
        Args:
            notification_data: Dados da notificação
        
        Returns:
            Dict com resultado do processamento
        """
        try:
            logger.info(f"📨 Webhook Asaas recebido: {json.dumps(notification_data, indent=2, default=str)}")
            
            processed = self.asaas_service.process_webhook_notification(notification_data)
            logger.info(f"📋 Dados processados do webhook: {json.dumps(processed, indent=2, default=str)}")
            
            event = processed.get("event")
            payment_id = processed.get("payment_id")
            subscription_id = processed.get("subscription_id")
            status = processed.get("status")
            
            logger.info(f"🔍 Buscando assinatura - event: {event}, payment_id: {payment_id}, subscription_id: {subscription_id}")
            
            subscription = None
            
            # PRIMEIRO: Tentar buscar pelo subscription_id do Asaas
            if subscription_id:
                subscription = self.db.query(Subscription).filter(
                    Subscription.asaas_subscription_id == subscription_id
                ).first()
                if subscription:
                    logger.info(f"✅ Assinatura encontrada pelo subscription_id: {subscription.id}")
            
            # SEGUNDO: Se não encontrou, tentar buscar pelo payment_id (via externalReference)
            if not subscription and payment_id:
                # O externalReference do pagamento tem o formato: company_{company_id}_user_{user_id}_initial
                # Buscar pagamento no Asaas para obter externalReference
                try:
                    payment_info = self.asaas_service._make_request("GET", f"/payments/{payment_id}")
                    external_ref = payment_info.get("externalReference", "")
                    logger.info(f"🔍 ExternalReference do pagamento: {external_ref}")
                    
                    if external_ref and "company_" in external_ref:
                        # Extrair company_id do externalReference
                        parts = external_ref.split("_")
                        if len(parts) >= 2:
                            try:
                                company_id_from_ref = int(parts[1])
                                # Buscar assinatura pendente para esta empresa
                                subscription = self.db.query(Subscription).filter(
                                    Subscription.company_id == company_id_from_ref,
                                    Subscription.status == "pending"
                                ).order_by(Subscription.created_at.desc()).first()
                                if subscription:
                                    logger.info(f"✅ Assinatura encontrada pelo externalReference: {subscription.id}")
                            except ValueError:
                                logger.warning(f"⚠️ Não foi possível extrair company_id de {external_ref}")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao buscar pagamento no Asaas: {e}")
            
            # TERCEIRO: Se ainda não encontrou, buscar pela assinatura mais recente pendente
            if not subscription:
                # Buscar assinatura pendente mais recente (pode ser a que acabou de ser criada)
                subscription = self.db.query(Subscription).filter(
                    Subscription.status == "pending"
                ).order_by(Subscription.created_at.desc()).first()
                if subscription:
                    logger.info(f"✅ Assinatura pendente encontrada (mais recente): {subscription.id}")
            
            if subscription:
                # Atualizar status baseado no evento
                if event == "PAYMENT_CONFIRMED" or event == "PAYMENT_RECEIVED":
                    subscription.status = "active"
                    subscription.is_trial = False  # Remover trial
                    
                    # Atualizar data de início
                    if not subscription.starts_at:
                        subscription.starts_at = datetime.now()
                    
                    # Calcular data de término baseada no billing_cycle
                    if subscription.billing_cycle:
                        if subscription.billing_cycle == "monthly":
                            subscription.ends_at = datetime.now() + timedelta(days=30)
                            subscription.next_charge_date = datetime.now() + timedelta(days=30)
                        elif subscription.billing_cycle == "quarterly":
                            subscription.ends_at = datetime.now() + timedelta(days=90)
                            subscription.next_charge_date = datetime.now() + timedelta(days=90)
                        elif subscription.billing_cycle == "semiannually":
                            subscription.ends_at = datetime.now() + timedelta(days=180)
                            subscription.next_charge_date = datetime.now() + timedelta(days=180)
                        elif subscription.billing_cycle == "yearly":
                            subscription.ends_at = datetime.now() + timedelta(days=365)
                            subscription.next_charge_date = datetime.now() + timedelta(days=365)
                    
                    # Remover trial_ends_at se existir
                    subscription.trial_ends_at = None
                    
                    # Atualizar empresa: remover trial, atualizar plan_expires_at e adicionar tokens mensais
                    if subscription.company_id:
                        company = self.db.query(Company).filter(Company.id == subscription.company_id).first()
                        if company:
                            # Remover status de trial
                            if company.status == CompanyStatus.TRIAL:
                                company.status = CompanyStatus.ACTIVE
                                logger.info(f"✅ Empresa {company.id} removida do trial")
                            
                            # Atualizar data de expiração do plano
                            company.plan_expires_at = subscription.ends_at
                            
                            # Remover trial_ends_at
                            company.trial_ends_at = None
                            
                            # Adicionar tokens mensais do plano
                            # Buscar o plano para pegar ai_analysis_monthly
                            from app.models.saas_models import Plan
                            plan = self.db.query(Plan).filter(Plan.plan_name == subscription.plan_name).first()
                            
                            if plan and hasattr(plan, 'ai_analysis_monthly') and plan.ai_analysis_monthly:
                                tokens_to_add = plan.ai_analysis_monthly
                                # Adicionar tokens mensais (não substituir, somar)
                                if not company.ai_tokens_monthly:
                                    company.ai_tokens_monthly = 0
                                company.ai_tokens_monthly += tokens_to_add
                                logger.info(f"✅ Tokens mensais adicionados: +{tokens_to_add} tokens (total: {company.ai_tokens_monthly})")
                            else:
                                logger.warning(f"⚠️ Plano '{subscription.plan_name}' não encontrado ou sem ai_analysis_monthly definido")
                            
                            logger.info(f"✅ Empresa {company.id} atualizada: status={company.status}, plan_expires_at={company.plan_expires_at}, ai_tokens_monthly={company.ai_tokens_monthly}")
                    
                    logger.info(f"✅ Assinatura {subscription.id} ativada após pagamento confirmado")
                    logger.info(f"   - Status: {subscription.status}")
                    logger.info(f"   - is_trial: {subscription.is_trial}")
                    logger.info(f"   - ends_at: {subscription.ends_at}")
                    logger.info(f"   - next_charge_date: {subscription.next_charge_date}")
                elif event == "PAYMENT_OVERDUE":
                    subscription.status = "overdue"
                elif event == "PAYMENT_REFUNDED":
                    subscription.status = "refunded"
                
                subscription.updated_at = datetime.now()
                self.db.commit()
                self.db.refresh(subscription)
                logger.info(f"✅ Status da assinatura {subscription.id} atualizado para: {subscription.status}")
            else:
                logger.warning(f"⚠️ Nenhuma assinatura encontrada para processar webhook")
                logger.warning(f"⚠️ Event: {event}, Payment ID: {payment_id}, Subscription ID: {subscription_id}")
            
            return {
                "success": True,
                "event": event,
                "processed": subscription is not None,
                "subscription_found": subscription is not None
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar webhook do Asaas: {e}")
            raise e

