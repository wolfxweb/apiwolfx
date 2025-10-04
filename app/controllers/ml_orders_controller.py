from sqlalchemy.orm import Session
from typing import Dict, Optional
import logging

from app.services.ml_orders_service import MLOrdersService
from app.models.saas_models import MLAccount, MLAccountStatus

logger = logging.getLogger(__name__)

class MLOrdersController:
    def __init__(self, db: Session):
        self.db = db
        self.orders_service = MLOrdersService(db)
    
    def get_orders_list(self, company_id: int, ml_account_id: Optional[int] = None,
                       limit: int = 50, offset: int = 0,
                       status_filter: Optional[str] = None,
                       date_from: Optional[str] = None,
                       date_to: Optional[str] = None) -> Dict:
        """Busca lista de orders para exibição"""
        try:
            logger.info(f"Buscando lista de orders para company_id: {company_id}")
            
            # Se ml_account_id não foi especificado, buscar todas as contas da empresa
            if ml_account_id:
                # Buscar orders de uma conta específica
                accounts = self.db.query(MLAccount).filter(
                    MLAccount.id == ml_account_id,
                    MLAccount.company_id == company_id,
                    MLAccount.status == MLAccountStatus.ACTIVE
                ).all()
            else:
                # Buscar orders de todas as contas da empresa
                accounts = self.db.query(MLAccount).filter(
                    MLAccount.company_id == company_id,
                    MLAccount.status == MLAccountStatus.ACTIVE
                ).all()
            
            if not accounts:
                return {
                    "success": False,
                    "error": "Nenhuma conta ML ativa encontrada",
                    "orders": [],
                    "total": 0,
                    "accounts": []
                }
            
            # Buscar orders diretamente do banco de dados
            from app.models.saas_models import MLOrder, OrderStatus
            from sqlalchemy import and_, or_
            
            # Construir query base
            query = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id
            )
            
            # Se ml_account_id foi especificado, filtrar por conta
            if ml_account_id:
                query = query.filter(MLOrder.ml_account_id == ml_account_id)
            else:
                # Filtrar apenas contas da empresa
                account_ids = [acc.id for acc in accounts]
                query = query.filter(MLOrder.ml_account_id.in_(account_ids))
            
            # Aplicar filtros
            if status_filter:
                try:
                    status_enum = OrderStatus(status_filter)
                    query = query.filter(MLOrder.status == status_enum)
                except ValueError:
                    logger.warning(f"Status inválido: {status_filter}")
            
            if date_from:
                try:
                    from datetime import datetime
                    date_from_obj = datetime.fromisoformat(date_from)
                    query = query.filter(MLOrder.date_created >= date_from_obj)
                except ValueError:
                    logger.warning(f"Data inválida: {date_from}")
            
            if date_to:
                try:
                    from datetime import datetime
                    date_to_obj = datetime.fromisoformat(date_to)
                    query = query.filter(MLOrder.date_created <= date_to_obj)
                except ValueError:
                    logger.warning(f"Data inválida: {date_to}")
            
            # Ordenar por data de criação (mais recentes primeiro)
            query = query.order_by(MLOrder.date_created.desc())
            
            # Contar total
            total_orders = query.count()
            
            # Aplicar paginação
            orders = query.offset(offset).limit(limit).all()
            
            # Converter para formato de resposta
            all_orders = []
            for order in orders:
                # Buscar informações da conta ML
                account = next((acc for acc in accounts if acc.id == order.ml_account_id), None)
                
                order_data = {
                    "id": order.id,
                    "ml_order_id": order.ml_order_id,
                    "order_id": order.order_id,
                    "buyer_nickname": order.buyer_nickname,
                    "buyer_email": order.buyer_email,
                    "status": order.status.value if order.status else None,
                    "status_detail": order.status_detail,
                    "total_amount": order.total_amount,
                    "currency_id": order.currency_id,
                    "payment_status": order.payment_status,
                    "shipping_cost": order.shipping_cost,
                    "shipping_method": order.shipping_method,
                    "date_created": order.date_created.isoformat() if order.date_created else None,
                    "last_updated": order.last_updated.isoformat() if order.last_updated else None,
                    "order_items": order.order_items,
                    "shipping_address": order.shipping_address,
                    "account_nickname": account.nickname if account else "N/A",
                    "account_email": account.email if account else "N/A",
                    "account_country": account.country_id if account else "N/A"
                }
                all_orders.append(order_data)
            
            # Criar lista de contas com contagem de orders
            accounts_data = []
            for account in accounts:
                account_orders_count = self.db.query(MLOrder).filter(
                    MLOrder.ml_account_id == account.id,
                    MLOrder.company_id == company_id
                ).count()
                
                accounts_data.append({
                    "id": account.id,
                    "nickname": account.nickname,
                    "email": account.email,
                    "country_id": account.country_id,
                    "orders_count": account_orders_count
                })
            
            return {
                "success": True,
                "orders": all_orders,
                "total": total_orders,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_orders,
                "accounts": accounts_data
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar lista de orders: {e}")
            return {
                "success": False,
                "error": str(e),
                "orders": [],
                "total": 0,
                "accounts": []
            }
    
    def sync_orders(self, company_id: int, ml_account_id: Optional[int] = None, is_full_import: bool = False) -> Dict:
        """Sincroniza orders da API do Mercado Libre"""
        try:
            logger.info(f"Sincronizando orders para company_id: {company_id}")
            
            # Se ml_account_id não foi especificado, sincronizar todas as contas
            if ml_account_id:
                accounts = self.db.query(MLAccount).filter(
                    MLAccount.id == ml_account_id,
                    MLAccount.company_id == company_id,
                    MLAccount.status == MLAccountStatus.ACTIVE
                ).all()
            else:
                accounts = self.db.query(MLAccount).filter(
                    MLAccount.company_id == company_id,
                    MLAccount.status == MLAccountStatus.ACTIVE
                ).all()
            
            if not accounts:
                return {
                    "success": False,
                    "error": "Nenhuma conta ML ativa encontrada"
                }
            
            # Sincronizar orders de cada conta
            sync_results = []
            total_saved = 0
            total_updated = 0
            
            for account in accounts:
                try:
                    result = self.orders_service.sync_orders_from_api(account.id, company_id, is_full_import=is_full_import)
                    
                    if result.get("success"):
                        sync_results.append({
                            "account_id": account.id,
                            "account_nickname": account.nickname,
                            "success": True,
                            "saved_count": result.get("saved_count", 0),
                            "updated_count": result.get("updated_count", 0),
                            "message": result.get("message")
                        })
                        
                        total_saved += result.get("saved_count", 0)
                        total_updated += result.get("updated_count", 0)
                    else:
                        sync_results.append({
                            "account_id": account.id,
                            "account_nickname": account.nickname,
                            "success": False,
                            "error": result.get("error")
                        })
                        
                except Exception as e:
                    logger.error(f"Erro ao sincronizar orders da conta {account.id}: {e}")
                    sync_results.append({
                        "account_id": account.id,
                        "account_nickname": account.nickname,
                        "success": False,
                        "error": str(e)
                    })
            
            return {
                "success": True,
                "message": f"Sincronização concluída: {total_saved} orders criadas, {total_updated} orders atualizadas",
                "total_saved": total_saved,
                "total_updated": total_updated,
                "accounts_results": sync_results
            }
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar orders: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_order_details(self, company_id: int, order_id: int) -> Dict:
        """Busca detalhes de uma order específica"""
        try:
            from app.models.saas_models import MLOrder
            
            # Buscar order
            order = self.db.query(MLOrder).filter(
                MLOrder.id == order_id,
                MLOrder.company_id == company_id
            ).first()
            
            if not order:
                return {
                    "success": False,
                    "error": "Order não encontrada"
                }
            
            # Converter para formato de resposta
            order_data = {
                "id": order.id,
                "ml_order_id": order.ml_order_id,
                "order_id": order.order_id,
                "buyer_nickname": order.buyer_nickname,
                "buyer_email": order.buyer_email,
                "buyer_first_name": order.buyer_first_name,
                "buyer_last_name": order.buyer_last_name,
                "status": order.status.value if order.status else None,
                "status_detail": order.status_detail,
                "total_amount": order.total_amount,
                "currency_id": order.currency_id,
                "payment_method_id": order.payment_method_id,
                "payment_type_id": order.payment_type_id,
                "payment_status": order.payment_status,
                "shipping_cost": order.shipping_cost,
                "shipping_method": order.shipping_method,
                "shipping_status": order.shipping_status,
                "shipping_address": order.shipping_address,
                "feedback": order.feedback,
                "tags": order.tags,
                "order_items": order.order_items,
                "date_created": order.date_created.isoformat() if order.date_created else None,
                "last_updated": order.last_updated.isoformat() if order.last_updated else None,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "updated_at": order.updated_at.isoformat() if order.updated_at else None
            }
            
            return {
                "success": True,
                "order": order_data
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes da order: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_orders_summary(self, company_id: int) -> Dict:
        """Busca resumo de orders para dashboard"""
        try:
            from app.models.saas_models import MLOrder, OrderStatus
            from sqlalchemy import func
            
            # Buscar contas ativas da empresa
            accounts = self.db.query(MLAccount).filter(
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).all()
            
            if not accounts:
                return {
                    "success": False,
                    "error": "Nenhuma conta ML ativa encontrada",
                    "summary": {}
                }
            
            account_ids = [acc.id for acc in accounts]
            
            # Buscar estatísticas de orders
            total_orders = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id,
                MLOrder.ml_account_id.in_(account_ids)
            ).count()
            
            # Orders por status
            orders_by_status = {}
            for status in OrderStatus:
                count = self.db.query(MLOrder).filter(
                    MLOrder.company_id == company_id,
                    MLOrder.ml_account_id.in_(account_ids),
                    MLOrder.status == status
                ).count()
                orders_by_status[status.value] = count
            
            # Total de vendas
            total_sales = self.db.query(func.sum(MLOrder.total_amount)).filter(
                MLOrder.company_id == company_id,
                MLOrder.ml_account_id.in_(account_ids),
                MLOrder.status.in_([OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DELIVERED])
            ).scalar() or 0
            
            # Orders dos últimos 30 dias
            from datetime import datetime, timedelta
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            recent_orders = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id,
                MLOrder.ml_account_id.in_(account_ids),
                MLOrder.date_created >= thirty_days_ago
            ).count()
            
            return {
                "success": True,
                "summary": {
                    "total_orders": total_orders,
                    "orders_by_status": orders_by_status,
                    "total_sales": total_sales,
                    "recent_orders": recent_orders,
                    "active_accounts": len(accounts)
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar resumo de orders: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": {}
            }
