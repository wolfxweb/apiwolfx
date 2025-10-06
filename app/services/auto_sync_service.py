"""
Serviço de sincronização automática
Sincroniza pedidos do Mercado Livre automaticamente
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.saas_models import MLAccount, MLAccountStatus
from app.services.ml_orders_service import MLOrdersService
from app.services.token_manager import TokenManager

logger = logging.getLogger(__name__)

class AutoSyncService:
    """Serviço de sincronização automática"""
    
    def __init__(self):
        self.sync_interval_minutes = 15  # Sincronizar a cada 15 minutos
    
    def sync_today_orders(self) -> dict:
        """
        Sincroniza pedidos do dia atual para todas as contas ativas
        """
        try:
            logger.info("🔄 Iniciando sincronização automática - pedidos do dia")
            
            # Obter sessão do banco
            db = next(get_db())
            
            # Buscar todas as contas ML ativas
            active_accounts = db.query(MLAccount).filter(
                MLAccount.status == MLAccountStatus.ACTIVE
            ).all()
            
            if not active_accounts:
                logger.info("ℹ️ Nenhuma conta ML ativa encontrada")
                return {
                    "success": True,
                    "message": "Nenhuma conta ativa para sincronizar",
                    "accounts_processed": 0,
                    "total_orders": 0
                }
            
            logger.info(f"📋 Encontradas {len(active_accounts)} contas ativas")
            
            # Processar cada conta
            total_orders = 0
            accounts_processed = 0
            
            for account in active_accounts:
                try:
                    logger.info(f"🔄 Sincronizando conta: {account.nickname} (ID: {account.id})")
                    
                    # Obter user_id da conta (primeiro usuário da empresa)
                    user_id = self._get_user_id_for_account(account, db)
                    if not user_id:
                        logger.warning(f"⚠️ Nenhum usuário encontrado para a conta {account.nickname}")
                        continue
                    
                    # Verificar/renovar token usando TokenManager
                    token_manager = TokenManager(db)
                    valid_token = token_manager.get_valid_token(user_id)
                    
                    if not valid_token:
                        logger.warning(f"⚠️ Não foi possível obter token válido para {account.nickname}")
                        continue
                    
                    # Criar serviço de orders
                    orders_service = MLOrdersService(db)
                    
                    # Sincronizar apenas pedidos do dia atual
                    result = orders_service.sync_today_orders(
                        ml_account_id=account.id,
                        company_id=account.company_id,
                        limit=50  # Limite razoável para pedidos do dia
                    )
                    
                    if result.get("success"):
                        orders_count = result.get("saved_count", 0) + result.get("updated_count", 0)
                        total_orders += orders_count
                        accounts_processed += 1
                        
                        logger.info(f"✅ Conta {account.nickname}: {orders_count} pedidos processados")
                    else:
                        logger.warning(f"⚠️ Erro na conta {account.nickname}: {result.get('error', 'Erro desconhecido')}")
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao sincronizar conta {account.nickname}: {e}")
                    continue
            
            # Fechar sessão
            db.close()
            
            logger.info(f"🎉 Sincronização automática concluída: {total_orders} pedidos em {accounts_processed} contas")
            
            return {
                "success": True,
                "message": f"Sincronização automática concluída: {total_orders} pedidos processados",
                "accounts_processed": accounts_processed,
                "total_orders": total_orders,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na sincronização automática: {e}")
            return {
                "success": False,
                "error": f"Erro na sincronização automática: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def _get_user_id_for_account(self, account, db: Session) -> int:
        """Obtém o user_id para uma conta ML"""
        try:
            # Buscar primeiro usuário da empresa
            from app.models.saas_models import User
            user = db.query(User).filter(User.company_id == account.company_id).first()
            return user.id if user else None
        except Exception as e:
            logger.error(f"Erro ao buscar user_id para conta {account.id}: {e}")
            return None

    def get_sync_status(self) -> dict:
        """Retorna status da última sincronização"""
        return {
            "service_active": True,
            "sync_interval_minutes": self.sync_interval_minutes,
            "last_sync": datetime.now().isoformat(),
            "next_sync_in_minutes": self.sync_interval_minutes
        }
