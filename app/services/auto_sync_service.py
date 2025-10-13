"""
Serviço de sincronização automática em background
- Job 1: A cada 15 minutos - sincroniza pedidos novos (últimas horas)
- Job 2: À meia-noite - sincroniza pedidos dos últimos 7 dias completos
"""
import logging
from datetime import datetime, timedelta
from app.config.database import SessionLocal
from app.services.ml_orders_service import MLOrdersService
from app.models.saas_models import MLAccount, MLAccountStatus, Company

logger = logging.getLogger(__name__)

class AutoSyncService:
    """Serviço para sincronização automática de pedidos"""
    
    def __init__(self):
        self.sync_interval_minutes = 15
    
    def sync_today_orders(self) -> dict:
        """
        JOB 1: Sincroniza pedidos RECENTES (do dia atual) - Roda a cada 15 minutos
        Alias para sync_recent_orders (compatibilidade com código existente)
        """
        return self.sync_recent_orders()
    
    def sync_recent_orders(self) -> dict:
        """
        JOB 1: Sincroniza pedidos RECENTES (últimas horas) a cada 15 minutos
        Processa apenas pedidos novos do dia para todas as empresas ativas
        Roda SEM precisar de usuário logado
        """
        db = SessionLocal()
        try:
            logger.info("🔄 [AUTO-SYNC 15min] Iniciando sincronização de pedidos recentes...")
            
            # Buscar todas as empresas ativas
            from app.models.saas_models import CompanyStatus
            companies = db.query(Company).filter(Company.status == CompanyStatus.ACTIVE).all()
            
            if not companies:
                logger.info("Nenhuma empresa ativa para sincronizar")
                return {"success": True, "message": "Nenhuma empresa ativa"}
            
            total_companies = len(companies)
            total_accounts = 0
            total_processed = 0
            
            # Para cada empresa
            for company in companies:
                try:
                    # Buscar contas ML ativas da empresa
                    accounts = db.query(MLAccount).filter(
                        MLAccount.company_id == company.id,
                        MLAccount.status == MLAccountStatus.ACTIVE
                    ).all()
                    
                    if not accounts:
                        continue
                    
                    total_accounts += len(accounts)
                    
                    # Sincronizar pedidos de cada conta (apenas do dia)
                    for account in accounts:
                        try:
                            # Buscar token diretamente da conta ML (sem depender de usuário logado)
                            orders_service = MLOrdersService(db)
                            valid_token = orders_service._get_active_token(account.id)
                            
                            if not valid_token:
                                logger.warning(f"⚠️ Token inválido para {account.nickname}")
                                continue
                            
                            # Sincronizar pedidos do dia
                            orders_service = MLOrdersService(db)
                            result = orders_service.sync_today_orders(
                                ml_account_id=account.id,
                                company_id=company.id,
                                limit=50
                            )
                            
                            if result.get("success"):
                                new_orders = result.get("new_orders", 0)
                                total_processed += new_orders
                                existing_orders = result.get("existing_orders", 0)
                                if new_orders > 0:
                                    logger.info(f"   ✅ {company.name}/{account.nickname}: {new_orders} novos pedidos, {existing_orders} já existiam")
                                elif existing_orders > 0:
                                    logger.info(f"   ℹ️ {company.name}/{account.nickname}: {existing_orders} pedidos já existiam (nenhum novo)")
                            
                        except Exception as e:
                            logger.error(f"   ❌ Erro conta {account.nickname}: {e}")
                            continue
                    
                except Exception as e:
                    logger.error(f"❌ Erro empresa {company.name}: {e}")
                    continue
            
            logger.info(f"✅ [AUTO-SYNC 15min] Concluído: {total_processed} novos pedidos em {total_accounts} contas")
            
            return {
                "success": True,
                "message": f"{total_processed} novos pedidos sincronizados",
                "total_processed": total_processed,
                "companies": total_companies,
                "accounts": total_accounts
            }
            
        except Exception as e:
            logger.error(f"❌ [AUTO-SYNC 15min] Erro: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            db.close()
    
    def sync_last_7_days_orders(self) -> dict:
        """
        JOB 2: Sincroniza TODOS os pedidos dos últimos 7 dias - Roda à meia-noite
        Garante dados completos e atualizados
        Roda SEM precisar de usuário logado
        """
        db = SessionLocal()
        try:
            logger.info("🌙 [AUTO-SYNC MEIA-NOITE] Iniciando sincronização dos últimos 7 dias...")
            
            # Buscar todas as empresas ativas
            from app.models.saas_models import CompanyStatus
            companies = db.query(Company).filter(Company.status == CompanyStatus.ACTIVE).all()
            
            if not companies:
                logger.info("Nenhuma empresa ativa para sincronizar")
                return {"success": True, "message": "Nenhuma empresa ativa"}
            
            total_companies = len(companies)
            total_accounts = 0
            total_new = 0
            total_updated = 0
            
            # Para cada empresa
            for company in companies:
                try:
                    # Buscar contas ML ativas da empresa
                    accounts = db.query(MLAccount).filter(
                        MLAccount.company_id == company.id,
                        MLAccount.status == MLAccountStatus.ACTIVE
                    ).all()
                    
                    if not accounts:
                        continue
                    
                    total_accounts += len(accounts)
                    
                    # Sincronizar pedidos dos últimos 7 dias de cada conta
                    for account in accounts:
                        try:
                            # Buscar token diretamente da conta ML (sem depender de usuário logado)
                            orders_service = MLOrdersService(db)
                            valid_token = orders_service._get_active_token(account.id)
                            
                            if not valid_token:
                                logger.warning(f"⚠️ Token inválido para {account.nickname}")
                                continue
                            
                            # Sincronizar pedidos dos últimos 7 dias (paginação completa)
                            orders_service = MLOrdersService(db)
                            result = orders_service.sync_orders_from_api(
                                ml_account_id=account.id,
                                company_id=company.id,
                                limit=50,
                                is_full_import=False  # False = últimos 7 dias
                            )
                            
                            if result.get("success"):
                                new_count = result.get("saved_count", 0)
                                updated_count = result.get("updated_count", 0)
                                total_new += new_count
                                total_updated += updated_count
                                
                                if new_count > 0 or updated_count > 0:
                                    logger.info(f"   ✅ {company.name}/{account.nickname}: {new_count} novos, {updated_count} atualizados")
                            
                        except Exception as e:
                            logger.error(f"   ❌ Erro conta {account.nickname}: {e}")
                            continue
                    
                except Exception as e:
                    logger.error(f"❌ Erro empresa {company.name}: {e}")
                    continue
            
            logger.info(f"✅ [AUTO-SYNC MEIA-NOITE] Concluído: {total_new} novos, {total_updated} atualizados em {total_accounts} contas")
            
            return {
                "success": True,
                "message": f"Sincronização 7 dias: {total_new} novos, {total_updated} atualizados",
                "total_new": total_new,
                "total_updated": total_updated,
                "companies": total_companies,
                "accounts": total_accounts
            }
            
        except Exception as e:
            logger.error(f"❌ [AUTO-SYNC MEIA-NOITE] Erro: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            db.close()
    
    def get_sync_status(self) -> dict:
        """Retorna status do serviço de sincronização"""
        return {
            "service_active": True,
            "sync_interval_minutes": self.sync_interval_minutes,
            "last_sync": datetime.now().isoformat(),
            "next_sync_in_minutes": self.sync_interval_minutes
        }
