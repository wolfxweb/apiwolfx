"""
Serviço de sincronização diária com Asaas
Sincroniza status e datas de vencimento das assinaturas
Inativa empresas quando necessário
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.saas_models import Subscription, Company, CompanyStatus
from app.services.asaas_service import asaas_service

logger = logging.getLogger(__name__)


class AsaasSyncService:
    """Serviço para sincronização diária com Asaas"""
    
    def __init__(self, db: Session):
        self.db = db
        self.asaas_service = asaas_service
    
    def sync_all_subscriptions(self) -> Dict[str, Any]:
        """
        Sincroniza todas as assinaturas ativas/pendentes com o Asaas
        
        Returns:
            Dict com estatísticas da sincronização
        """
        try:
            logger.info("🔄 Iniciando sincronização diária com Asaas...")
            
            # Buscar todas as assinaturas que precisam ser sincronizadas
            subscriptions = self.db.query(Subscription).filter(
                or_(
                    Subscription.status == "active",
                    Subscription.status == "pending",
                    Subscription.is_trial == True
                ),
                Subscription.asaas_subscription_id.isnot(None)
            ).all()
            
            logger.info(f"📊 Encontradas {len(subscriptions)} assinaturas para sincronizar")
            
            stats = {
                "total": len(subscriptions),
                "updated": 0,
                "inactivated": 0,
                "errors": 0,
                "details": []
            }
            
            for subscription in subscriptions:
                try:
                    result = self._sync_single_subscription(subscription)
                    stats["updated"] += result.get("updated", 0)
                    stats["inactivated"] += result.get("inactivated", 0)
                    stats["errors"] += result.get("errors", 0)
                    stats["details"].append(result)
                except Exception as e:
                    logger.error(f"❌ Erro ao sincronizar assinatura {subscription.id}: {e}")
                    stats["errors"] += 1
                    stats["details"].append({
                        "subscription_id": subscription.id,
                        "company_id": subscription.company_id,
                        "error": str(e)
                    })
            
            self.db.commit()
            
            logger.info(f"✅ Sincronização concluída: {stats['updated']} atualizadas, {stats['inactivated']} inativadas, {stats['errors']} erros")
            
            return {
                "success": True,
                "stats": stats
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro na sincronização diária com Asaas: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }
    
    def _sync_single_subscription(self, subscription: Subscription) -> Dict[str, Any]:
        """
        Sincroniza uma única assinatura com o Asaas
        
        Args:
            subscription: Objeto Subscription
            
        Returns:
            Dict com resultado da sincronização
        """
        result = {
            "subscription_id": subscription.id,
            "company_id": subscription.company_id,
            "updated": 0,
            "inactivated": 0,
            "errors": 0
        }
        
        try:
            asaas_subscription_id = subscription.asaas_subscription_id
            
            if not asaas_subscription_id:
                logger.warning(f"⚠️ Assinatura {subscription.id} não tem asaas_subscription_id")
                return result
            
            # Buscar dados da assinatura no Asaas
            asaas_subscription = self.asaas_service.get_subscription(asaas_subscription_id)
            
            if not asaas_subscription:
                logger.warning(f"⚠️ Assinatura {asaas_subscription_id} não encontrada no Asaas")
                return result
            
            # Atualizar status da assinatura
            asaas_status = asaas_subscription.get("status", "").upper()
            
            # Mapear status do Asaas para nosso sistema
            status_mapping = {
                "ACTIVE": "active",
                "INACTIVE": "inactive",
                "EXPIRED": "inactive",
                "CANCELLED": "inactive"
            }
            
            new_status = status_mapping.get(asaas_status, subscription.status)
            
            # Buscar pagamentos da assinatura para verificar parcelas
            subscription_payments = self.asaas_service.get_subscription_payments(asaas_subscription_id)
            
            # Encontrar próxima parcela pendente
            now = datetime.now()
            next_pending_payment = None
            overdue_payments = []
            
            for payment in subscription_payments:
                payment_status = payment.get("status", "").upper()
                due_date_str = payment.get("dueDate")
                
                if due_date_str:
                    try:
                        due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                        
                        if payment_status in ["PENDING", "OVERDUE"]:
                            if due_date >= now:
                                # Parcela futura pendente
                                if not next_pending_payment or due_date < next_pending_payment["dueDate"]:
                                    next_pending_payment = {
                                        "dueDate": due_date,
                                        "payment": payment
                                    }
                            elif due_date < now:
                                # Parcela vencida
                                overdue_payments.append({
                                    "dueDate": due_date,
                                    "payment": payment
                                })
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao processar data de vencimento {due_date_str}: {e}")
            
            # Atualizar assinatura
            subscription.status = new_status
            subscription.updated_at = datetime.now()
            
            # Atualizar datas de vencimento
            if next_pending_payment:
                subscription.next_charge_date = next_pending_payment["dueDate"]
                subscription.ends_at = next_pending_payment["dueDate"]
            else:
                # Não há parcelas futuras, usar data de término da assinatura do Asaas
                end_date_str = asaas_subscription.get("endDate")
                if end_date_str:
                    try:
                        subscription.ends_at = datetime.strptime(end_date_str, "%Y-%m-%d")
                    except:
                        pass
            
            # Verificar se deve inativar a empresa
            should_inactivate = False
            
            # Condição 1: Não há parcelas futuras pendentes
            if not next_pending_payment:
                logger.info(f"⚠️ Assinatura {subscription.id} não tem parcelas futuras pendentes")
                should_inactivate = True
            
            # Condição 2: Há parcelas vencidas
            if overdue_payments:
                logger.info(f"⚠️ Assinatura {subscription.id} tem {len(overdue_payments)} parcela(s) vencida(s)")
                should_inactivate = True
            
            # Condição 3: Status da assinatura no Asaas é inativo/expirado/cancelado
            if asaas_status in ["INACTIVE", "EXPIRED", "CANCELLED"]:
                logger.info(f"⚠️ Assinatura {subscription.id} está {asaas_status} no Asaas")
                should_inactivate = True
            
            # Inativar empresa se necessário
            if should_inactivate:
                company = self.db.query(Company).filter(Company.id == subscription.company_id).first()
                if company and company.status != CompanyStatus.INACTIVE:
                    company.status = CompanyStatus.INACTIVE
                    company.updated_at = datetime.now()
                    logger.info(f"🔴 Empresa {company.id} ({company.name}) inativada devido a assinatura vencida/cancelada")
                    result["inactivated"] = 1
                    
                    # Atualizar assinatura também
                    subscription.status = "inactive"
                    subscription.is_trial = False
            
            result["updated"] = 1
            
            next_due_str = next_pending_payment['dueDate'].strftime('%d/%m/%Y') if next_pending_payment else 'N/A'
            logger.info(f"✅ Assinatura {subscription.id} sincronizada: status={new_status}, próxima_parcela={next_due_str}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao sincronizar assinatura {subscription.id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            result["errors"] = 1
        
        return result

