from sqlalchemy.orm import Session
from typing import Dict, List, Optional
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
                
                # Extrair dados de pagamento para usar os valores corretos
                payments_data = order.payments
                payment_transaction_amount = 0
                payment_coupon_amount = 0
                payment_total_paid_amount = 0
                
                if payments_data:
                    import json
                    if isinstance(payments_data, str):
                        payments = json.loads(payments_data)
                    else:
                        payments = payments_data
                    
                    if payments and len(payments) > 0:
                        payment = payments[0]
                        payment_transaction_amount = payment.get("transaction_amount", 0)
                        payment_coupon_amount = payment.get("coupon_amount", 0)
                        payment_total_paid_amount = payment.get("total_paid_amount", 0)
                
                order_data = {
                    "id": order.id,
                    "ml_order_id": order.ml_order_id,
                    "order_id": order.order_id,
                    "buyer_nickname": order.buyer_nickname,
                    "buyer_email": order.buyer_email,
                    "status": order.status.value if order.status else None,
                    "status_detail": order.status_detail,
                    "total_amount": payment_transaction_amount,  # Valor do produto
                    "paid_amount": payment_total_paid_amount,    # Total final
                    "currency_id": order.currency_id,
                    "payment_status": order.payment_status,
                    "shipping_cost": order.shipping_cost,
                    "shipping_method": order.shipping_method,
                    "sale_fees": order.sale_fees,
                    "coupon_amount": payment_coupon_amount,      # Desconto do cupom
                    "date_created": order.date_created.isoformat() if order.date_created else None,
                    "last_updated": order.last_updated.isoformat() if order.last_updated else None,
                    "order_items": order.order_items,
                    "shipping_address": order.shipping_address,
                    "account_nickname": account.nickname if account else "N/A",
                    "account_email": account.email if account else "N/A",
                    "account_country": account.country_id if account else "N/A",
                    "is_advertising_sale": order.is_advertising_sale,  # Origem da venda
                    "advertising_cost": order.advertising_cost or 0,  # Custo de publicidade
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
                
                # Dados do comprador
                "buyer_id": order.buyer_id,
                "buyer_nickname": order.buyer_nickname,
                "buyer_email": order.buyer_email,
                "buyer_first_name": order.buyer_first_name,
                "buyer_last_name": order.buyer_last_name,
                "buyer_phone": order.buyer_phone,
                
                # Dados do vendedor
                "seller_id": order.seller_id,
                "seller_nickname": order.seller_nickname,
                "seller_phone": order.seller_phone,
                
                # Status e valores
                "status": order.status.value if order.status else None,
                "status_detail": order.status_detail,
                "total_amount": order.total_amount,
                "paid_amount": order.paid_amount,
                "currency_id": order.currency_id,
                
                # Pagamento
                "payment_method_id": order.payment_method_id,
                "payment_type_id": order.payment_type_id,
                "payment_status": order.payment_status,
                "payments": order.payments,
                
                # Envio
                "shipping_cost": order.shipping_cost,
                "shipping_method": order.shipping_method,
                "shipping_status": order.shipping_status,
                "shipping_address": order.shipping_address,
                "shipping_details": order.shipping_details,
                
                # Taxas
                "total_fees": order.total_fees,
                "sale_fees": order.sale_fees,
                "shipping_fees": order.shipping_fees,
                
                # Descontos
                "coupon_amount": order.coupon_amount,
                "discounts_applied": order.discounts_applied,
                
                # Publicidade e anúncios
                "is_advertising_sale": order.is_advertising_sale,
                "advertising_campaign_id": order.advertising_campaign_id,
                "advertising_cost": order.advertising_cost,
                "advertising_metrics": order.advertising_metrics,
                
                # Produtos de catálogo (temporariamente desabilitado)
                "has_catalog_products": False,
                "catalog_products_count": 0,
                "catalog_products": [],
                
                # Itens e outros dados
                "order_items": order.order_items,
                "feedback": order.feedback,
                "tags": order.tags,
                "context": order.context,
                
                # Datas
                "date_created": order.date_created.isoformat() if order.date_created else None,
                "date_closed": order.date_closed.isoformat() if order.date_closed else None,
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
    
    def delete_orders(self, company_id: int, order_ids: List[int]) -> Dict:
        """Remove pedidos selecionados"""
        try:
            logger.info(f"Removendo pedidos: {order_ids} para company_id: {company_id}")
            
            if not order_ids:
                return {
                    "success": False,
                    "error": "Nenhum pedido selecionado para remoção"
                }
            
            result = self.orders_service.delete_orders(order_ids, company_id)
            
            if result.get("success"):
                logger.info(f"Pedidos removidos com sucesso: {result.get('deleted_count', 0)}")
            else:
                logger.error(f"Erro ao remover pedidos: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro no controller ao remover pedidos: {e}")
            return {
                "success": False,
                "error": f"Erro interno: {str(e)}"
            }
    
    def delete_all_orders(self, company_id: int) -> Dict:
        """Remove todos os pedidos da empresa"""
        try:
            logger.info(f"Removendo todos os pedidos para company_id: {company_id}")
            
            result = self.orders_service.delete_all_orders(company_id)
            
            if result.get("success"):
                logger.info(f"Todos os pedidos removidos com sucesso: {result.get('deleted_count', 0)}")
            else:
                logger.error(f"Erro ao remover todos os pedidos: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro no controller ao remover todos os pedidos: {e}")
            return {
                "success": False,
                "error": f"Erro interno: {str(e)}"
            }
    
    def count_available_orders(self, company_id: int) -> Dict:
        """Verifica total de pedidos disponíveis no ML vs importados"""
        try:
            import requests
            from app.models.saas_models import MLOrder
            
            logger.info(f"Verificando total de pedidos disponíveis para company_id: {company_id}")
            
            # Buscar conta ML ativa
            accounts = self.db.query(MLAccount).filter(
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).all()
            
            if not accounts:
                return {
                    "success": False,
                    "error": "Nenhuma conta ML ativa encontrada"
                }
            
            # Contar pedidos já importados
            account_ids = [acc.id for acc in accounts]
            total_imported = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id,
                MLOrder.ml_account_id.in_(account_ids)
            ).count()
            
            # Buscar total disponível no ML (primeira conta ativa)
            account = accounts[0]
            access_token = self.orders_service._get_active_token(account.id)
            
            if not access_token:
                return {
                    "success": False,
                    "error": "Token não encontrado ou expirado"
                }
            
            # Consultar API do ML
            headers = {"Authorization": f"Bearer {access_token}"}
            url = "https://api.mercadolibre.com/orders/search"
            params = {
                "seller": account.ml_user_id,
                "limit": 1  # Só queremos o total
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                total_available = data.get("paging", {}).get("total", 0)
                
                return {
                    "success": True,
                    "total_available": total_available,
                    "total_imported": total_imported,
                    "remaining": total_available - total_imported
                }
            else:
                logger.error(f"Erro ao consultar ML API: {response.status_code}")
                return {
                    "success": False,
                    "error": "Erro ao consultar Mercado Livre"
                }
                
        except Exception as e:
            logger.error(f"Erro ao contar pedidos disponíveis: {e}")
            return {
                "success": False,
                "error": f"Erro interno: {str(e)}"
            }
    
    def import_orders_batch(self, company_id: int, offset: int = 0, limit: int = 50) -> Dict:
        """Importa um lote específico de pedidos"""
        try:
            logger.info(f"Importando lote - company_id: {company_id}, offset: {offset}, limit: {limit}")
            
            # Buscar conta ML ativa
            accounts = self.db.query(MLAccount).filter(
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).all()
            
            if not accounts:
                return {
                    "success": False,
                    "error": "Nenhuma conta ML ativa encontrada"
                }
            
            # Importar pedidos da primeira conta ativa
            account = accounts[0]
            
            # Obter token ativo
            access_token = self.orders_service._get_active_token(account.id)
            if not access_token:
                return {
                    "success": False,
                    "error": "Token não encontrado ou expirado"
                }
            
            # Buscar pedidos da API com offset e limit específicos
            import requests
            headers = {"Authorization": f"Bearer {access_token}"}
            url = "https://api.mercadolibre.com/orders/search"
            params = {
                "seller": account.ml_user_id,
                "limit": limit,
                "offset": offset,
                "sort": "date_desc"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=60)
            
            if response.status_code != 200:
                logger.error(f"Erro ao buscar pedidos do ML: {response.status_code}")
                return {
                    "success": False,
                    "error": f"Erro ao buscar pedidos: {response.status_code}"
                }
            
            data = response.json()
            orders_data = data.get("results", [])
            
            if not orders_data:
                return {
                    "success": True,
                    "message": "Nenhum pedido encontrado neste lote",
                    "saved_count": 0,
                    "updated_count": 0
                }
            
            # Salvar pedidos no banco com pausas entre cada pedido
            saved_count = 0
            updated_count = 0
            
            import time
            
            for idx, order_data in enumerate(orders_data):
                try:
                    # Pausa de 5 segundos entre cada pedido (exceto o primeiro)
                    if idx > 0:
                        logger.info(f"Aguardando 5 segundos antes de processar pedido {idx + 1}/{len(orders_data)}")
                        time.sleep(5)
                    
                    # Buscar informações completas
                    complete_data = self.orders_service._fetch_complete_order_data(order_data, access_token)
                    
                    # Salvar no banco
                    result = self.orders_service._save_order_to_database(complete_data, account.id, company_id)
                    
                    if result["action"] == "created":
                        saved_count += 1
                    elif result["action"] == "updated":
                        updated_count += 1
                    
                    logger.info(f"Pedido {idx + 1}/{len(orders_data)} processado: {order_data.get('id')}")
                        
                except Exception as e:
                    logger.error(f"Erro ao processar pedido {order_data.get('id')}: {e}")
                    continue
            
            self.db.commit()
            
            return {
                "success": True,
                "message": f"Lote importado: {saved_count} criados, {updated_count} atualizados",
                "saved_count": saved_count,
                "updated_count": updated_count,
                "processed": len(orders_data)
            }
            
        except Exception as e:
            logger.error(f"Erro ao importar lote: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": f"Erro interno: {str(e)}"
            }
