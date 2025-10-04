from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import logging
import requests
from datetime import datetime, timedelta

from app.models.saas_models import MLOrder, OrderStatus, MLAccount, MLAccountStatus

logger = logging.getLogger(__name__)

class MLOrdersService:
    def __init__(self, db: Session):
        self.db = db
        self.base_url = "https://api.mercadolibre.com"
    
    def get_orders_by_account(self, ml_account_id: int, company_id: int, 
                             limit: int = 50, offset: int = 0,
                             status_filter: Optional[str] = None,
                             date_from: Optional[str] = None,
                             date_to: Optional[str] = None) -> Dict:
        """Busca orders de uma conta ML específica"""
        try:
            logger.info(f"Buscando orders para ml_account_id: {ml_account_id}")
            
            # Verificar se a conta pertence à empresa
            account = self.db.query(MLAccount).filter(
                MLAccount.id == ml_account_id,
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).first()
            
            if not account:
                return {
                    "success": False,
                    "error": "Conta não encontrada ou inativa",
                    "orders": [],
                    "total": 0
                }
            
            # Buscar orders do banco de dados
            query = self.db.query(MLOrder).filter(
                MLOrder.ml_account_id == ml_account_id,
                MLOrder.company_id == company_id
            )
            
            # Aplicar filtros
            if status_filter:
                try:
                    status_enum = OrderStatus(status_filter)
                    query = query.filter(MLOrder.status == status_enum)
                except ValueError:
                    logger.warning(f"Status inválido: {status_filter}")
            
            if date_from:
                try:
                    date_from_obj = datetime.fromisoformat(date_from)
                    query = query.filter(MLOrder.date_created >= date_from_obj)
                except ValueError:
                    logger.warning(f"Data inválida: {date_from}")
            
            if date_to:
                try:
                    date_to_obj = datetime.fromisoformat(date_to)
                    query = query.filter(MLOrder.date_created <= date_to_obj)
                except ValueError:
                    logger.warning(f"Data inválida: {date_to}")
            
            # Ordenar por data de criação (mais recentes primeiro)
            query = query.order_by(MLOrder.date_created.desc())
            
            # Paginação
            total = query.count()
            orders = query.offset(offset).limit(limit).all()
            
            # Converter para formato de resposta
            orders_data = []
            for order in orders:
                orders_data.append({
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
                    "shipping_address": order.shipping_address
                })
            
            return {
                "success": True,
                "orders": orders_data,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar orders: {e}")
            return {
                "success": False,
                "error": str(e),
                "orders": [],
                "total": 0
            }
    
    def sync_orders_from_api(self, ml_account_id: int, company_id: int, 
                           limit: int = 100) -> Dict:
        """Sincroniza orders da API do Mercado Libre para o banco"""
        try:
            logger.info(f"Sincronizando orders para ml_account_id: {ml_account_id}")
            
            # Verificar se a conta pertence à empresa
            account = self.db.query(MLAccount).filter(
                MLAccount.id == ml_account_id,
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).first()
            
            if not account:
                return {
                    "success": False,
                    "error": "Conta não encontrada ou inativa"
                }
            
            # Obter token ativo
            access_token = self._get_active_token(ml_account_id)
            if not access_token:
                return {
                    "success": False,
                    "error": "Token não encontrado ou expirado"
                }
            
            # Buscar orders da API
            orders_data = self._fetch_orders_from_api(access_token, account.ml_user_id, limit)
            
            if not orders_data:
                return {
                    "success": False,
                    "error": "Nenhuma order encontrada na API"
                }
            
            # Salvar orders no banco
            saved_count = 0
            updated_count = 0
            
            for order_data in orders_data:
                try:
                    result = self._save_order_to_database(order_data, ml_account_id, company_id)
                    if result["action"] == "created":
                        saved_count += 1
                    elif result["action"] == "updated":
                        updated_count += 1
                except Exception as e:
                    logger.error(f"Erro ao salvar order {order_data.get('id')}: {e}")
                    continue
            
            self.db.commit()
            
            return {
                "success": True,
                "message": f"Sincronização concluída: {saved_count} orders criadas, {updated_count} orders atualizadas",
                "saved_count": saved_count,
                "updated_count": updated_count,
                "total_processed": len(orders_data)
            }
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar orders: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _fetch_orders_from_api(self, access_token: str, seller_id: str, limit: int = 100) -> List[Dict]:
        """Busca orders da API do Mercado Libre"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Buscar orders recentes do vendedor
            orders_url = f"{self.base_url}/orders/search"
            params = {
                "seller": seller_id,
                "limit": limit,
                "offset": 0,
                "sort": "date_desc"
            }
            
            response = requests.get(orders_url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            else:
                logger.warning(f"Erro ao buscar orders da API: {response.status_code} - {response.text[:200]}")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao buscar orders da API: {e}")
            return []
    
    def _save_order_to_database(self, order_data: Dict, ml_account_id: int, company_id: int) -> Dict:
        """Salva ou atualiza uma order no banco de dados"""
        try:
            ml_order_id = order_data.get("id")
            
            # Verificar se a order já existe
            existing_order = self.db.query(MLOrder).filter(
                MLOrder.ml_order_id == ml_order_id
            ).first()
            
            # Converter dados da API para o modelo
            order_dict = self._convert_api_order_to_model(order_data, ml_account_id, company_id)
            
            if existing_order:
                # Atualizar order existente
                for key, value in order_dict.items():
                    if key not in ["id", "ml_order_id", "created_at"]:
                        setattr(existing_order, key, value)
                
                existing_order.updated_at = datetime.utcnow()
                return {"action": "updated", "order": existing_order}
            else:
                # Criar nova order
                new_order = MLOrder(**order_dict)
                self.db.add(new_order)
                return {"action": "created", "order": new_order}
                
        except Exception as e:
            logger.error(f"Erro ao salvar order no banco: {e}")
            raise e
    
    def _convert_api_order_to_model(self, order_data: Dict, ml_account_id: int, company_id: int) -> Dict:
        """Converte dados da API para formato do modelo"""
        try:
            # Converter status
            status_mapping = {
                "confirmed": OrderStatus.CONFIRMED,
                "payment_required": OrderStatus.PENDING,
                "payment_in_process": OrderStatus.PENDING,
                "paid": OrderStatus.PAID,
                "ready_to_ship": OrderStatus.PAID,
                "shipped": OrderStatus.SHIPPED,
                "delivered": OrderStatus.DELIVERED,
                "cancelled": OrderStatus.CANCELLED,
                "refunded": OrderStatus.REFUNDED
            }
            
            status = order_data.get("status", "pending")
            order_status = status_mapping.get(status, OrderStatus.PENDING)
            
            # Converter datas
            date_created = None
            if order_data.get("date_created"):
                try:
                    date_created = datetime.fromisoformat(order_data["date_created"].replace('Z', '+00:00'))
                except:
                    pass
            
            last_updated = None
            if order_data.get("last_updated"):
                try:
                    last_updated = datetime.fromisoformat(order_data["last_updated"].replace('Z', '+00:00'))
                except:
                    pass
            
            # Extrair dados do comprador
            buyer = order_data.get("buyer", {})
            
            # Extrair dados de pagamento
            payments = order_data.get("payments", [])
            payment_status = None
            payment_method_id = None
            payment_type_id = None
            
            if payments:
                payment = payments[0]
                payment_status = payment.get("status")
                payment_method_id = payment.get("payment_method_id")
                payment_type_id = payment.get("payment_type_id")
            
            # Extrair dados de envio
            shipping = order_data.get("shipping", {})
            
            return {
                "company_id": company_id,
                "ml_account_id": ml_account_id,
                "ml_order_id": order_data.get("id"),  # Manter como número
                "order_id": str(order_data.get("id")),  # Converter para string apenas o order_id
                "buyer_id": buyer.get("id"),
                "buyer_nickname": buyer.get("nickname"),
                "buyer_email": buyer.get("email"),
                "buyer_first_name": buyer.get("first_name"),
                "buyer_last_name": buyer.get("last_name"),
                "status": order_status,
                "status_detail": order_data.get("status_detail"),
                "total_amount": order_data.get("total_amount"),
                "currency_id": order_data.get("currency_id"),
                "payment_method_id": payment_method_id,
                "payment_type_id": payment_type_id,
                "payment_status": payment_status,
                "shipping_cost": shipping.get("cost"),
                "shipping_method": shipping.get("method"),
                "shipping_status": shipping.get("status"),
                "shipping_address": shipping.get("receiver_address"),
                "feedback": order_data.get("feedback"),
                "tags": order_data.get("tags"),
                "order_items": order_data.get("order_items"),
                "date_created": date_created,
                "last_updated": last_updated
            }
            
        except Exception as e:
            logger.error(f"Erro ao converter dados da order: {e}")
            raise e
    
    def _get_active_token(self, ml_account_id: int) -> Optional[str]:
        """Obtém token ativo para uma conta ML específica"""
        try:
            from sqlalchemy import text
            
            query = text("""
                SELECT access_token
                FROM tokens 
                WHERE ml_account_id = :ml_account_id 
                AND is_active = true 
                AND expires_at > NOW()
                ORDER BY expires_at DESC
                LIMIT 1
            """)
            
            result = self.db.execute(query, {"ml_account_id": ml_account_id}).fetchone()
            
            if result:
                return result[0]
            else:
                logger.warning(f"Nenhum token ativo encontrado para ml_account_id: {ml_account_id}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao obter token ativo: {e}")
            return None
