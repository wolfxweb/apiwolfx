"""
Controller para processar notificações do Mercado Livre
"""
import logging
import httpx
from typing import Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

logger = logging.getLogger(__name__)

class MLNotificationsController:
    """Controller para processar notificações do Mercado Livre"""
    
    def __init__(self):
        self.api_base_url = "https://api.mercadolibre.com"
    
    async def process_notification(self, notification_data: Dict[str, Any], db: Session):
        """
        Processa uma notificação recebida do Mercado Livre
        
        Estrutura da notificação:
        {
            "_id": "id_unico",
            "resource": "/orders/123456",
            "user_id": 123456789,
            "topic": "orders_v2",
            "application_id": 1234567890,
            "attempts": 1,
            "sent": "2024-01-01T12:00:00.000Z",
            "received": "2024-01-01T12:00:00.000Z"
        }
        """
        try:
            topic = notification_data.get("topic")
            resource = notification_data.get("resource")
            user_id = notification_data.get("user_id")
            
            logger.info(f"🔄 Processando notificação: topic={topic}, resource={resource}, user_id={user_id}")
            
            # Roteamento por tipo de notificação
            if topic == "orders_v2":
                await self._process_order_notification(resource, user_id, db)
            elif topic == "items":
                await self._process_item_notification(resource, user_id, db)
            elif topic == "messages":
                await self._process_message_notification(resource, user_id, db)
            elif topic == "questions":
                await self._process_question_notification(resource, user_id, db)
            elif topic == "payments":
                await self._process_payment_notification(resource, user_id, db)
            elif topic == "shipments":
                await self._process_shipment_notification(resource, user_id, db)
            elif topic == "claims" or topic == "post_purchase":
                await self._process_claim_notification(resource, user_id, db)
            else:
                logger.warning(f"⚠️ Tipo de notificação não suportado: {topic}")
            
            logger.info(f"✅ Notificação processada: {topic}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar notificação: {e}")
    
    async def _process_order_notification(self, resource: str, ml_user_id: int, db: Session):
        """Processa notificação de pedido (orders_v2)"""
        try:
            # Extrair order_id do resource
            order_id = resource.split("/")[-1]
            logger.info(f"📦 Processando pedido: {order_id}")
            
            # Buscar token do usuário ML
            access_token = self._get_user_token(ml_user_id, db)
            if not access_token:
                logger.warning(f"⚠️ Token não encontrado para user_id: {ml_user_id}")
                return
            
            # Buscar detalhes do pedido na API do ML
            order_data = await self._fetch_order_details(order_id, access_token)
            if not order_data:
                return
            
            # Atualizar ou criar pedido no banco
            await self._upsert_order(order_data, db)
            
            logger.info(f"✅ Pedido {order_id} atualizado com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar notificação de pedido: {e}")
    
    async def _process_item_notification(self, resource: str, ml_user_id: int, db: Session):
        """Processa notificação de produto (items)"""
        try:
            item_id = resource.split("/")[-1]
            logger.info(f"🏷️ Processando produto: {item_id}")
            
            # Buscar token
            access_token = self._get_user_token(ml_user_id, db)
            if not access_token:
                logger.warning(f"⚠️ Token não encontrado para user_id: {ml_user_id}")
                return
            
            # Buscar detalhes do produto
            item_data = await self._fetch_item_details(item_id, access_token)
            if not item_data:
                return
            
            # Atualizar produto no banco
            await self._upsert_item(item_data, ml_user_id, db)
            
            logger.info(f"✅ Produto {item_id} atualizado com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar notificação de produto: {e}")
    
    async def _process_message_notification(self, resource: str, ml_user_id: int, db: Session):
        """Processa notificação de mensagem"""
        logger.info(f"💬 Notificação de mensagem recebida: {resource}")
        # TODO: Implementar processamento de mensagens
    
    async def _process_question_notification(self, resource: str, ml_user_id: int, db: Session):
        """Processa notificação de pergunta"""
        logger.info(f"❓ Notificação de pergunta recebida: {resource}")
        # TODO: Implementar processamento de perguntas
    
    async def _process_payment_notification(self, resource: str, ml_user_id: int, db: Session):
        """Processa notificação de pagamento"""
        logger.info(f"💰 Notificação de pagamento recebida: {resource}")
        # TODO: Implementar processamento de pagamentos
    
    async def _process_shipment_notification(self, resource: str, ml_user_id: int, db: Session):
        """Processa notificação de envio"""
        logger.info(f"🚚 Notificação de envio recebida: {resource}")
        # TODO: Implementar processamento de envios
    
    async def _process_claim_notification(self, resource: str, ml_user_id: int, db: Session):
        """Processa notificação de reclamação"""
        logger.info(f"⚠️ Notificação de reclamação recebida: {resource}")
        # TODO: Implementar processamento de reclamações
    
    def _get_user_token(self, ml_user_id: int, db: Session) -> str:
        """Busca o token de acesso do usuário ML"""
        try:
            from sqlalchemy import text
            
            query = text("""
                SELECT t.access_token
                FROM tokens t
                JOIN ml_accounts ma ON ma.id = t.ml_account_id
                WHERE ma.ml_user_id = CAST(:ml_user_id AS VARCHAR)
                AND t.is_active = true
                ORDER BY t.expires_at DESC
                LIMIT 1
            """)
            
            result = db.execute(query, {"ml_user_id": str(ml_user_id)}).fetchone()
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar token: {e}")
            return None
    
    async def _fetch_order_details(self, order_id: str, access_token: str) -> Dict[str, Any]:
        """Busca detalhes do pedido na API do ML"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                response = await client.get(
                    f"{self.api_base_url}/orders/{order_id}",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"❌ Erro ao buscar pedido: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Erro ao buscar detalhes do pedido: {e}")
            return None
    
    async def _fetch_item_details(self, item_id: str, access_token: str) -> Dict[str, Any]:
        """Busca detalhes do produto na API do ML"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                response = await client.get(
                    f"{self.api_base_url}/items/{item_id}",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"❌ Erro ao buscar produto: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Erro ao buscar detalhes do produto: {e}")
            return None
    
    async def _upsert_order(self, order_data: Dict[str, Any], db: Session):
        """Atualiza ou cria pedido no banco de dados"""
        try:
            from sqlalchemy import text
            from datetime import datetime
            
            order_id = order_data.get("id")
            
            # Verificar se o pedido já existe
            check_query = text("SELECT id FROM ml_orders WHERE ml_order_id = :order_id")
            existing = db.execute(check_query, {"order_id": str(order_id)}).fetchone()
            
            # Extrair dados principais
            buyer = order_data.get("buyer", {})
            shipping = order_data.get("shipping", {})
            order_items = order_data.get("order_items", [])
            payments = order_data.get("payments", [])
            
            # Calcular total
            total_amount = sum(
                item.get("unit_price", 0) * item.get("quantity", 0) 
                for item in order_items
            )
            
            if existing:
                # Atualizar pedido existente
                logger.info(f"🔧 [NOTIF] Atualizando pedido existente: {order_id}")
                update_query = text("""
                    UPDATE ml_orders SET
                        status = :status,
                        status_detail = :status_detail,
                        date_closed = :date_closed,
                        last_updated = :last_updated,
                        total_amount = :total_amount,
                        paid_amount = :paid_amount,
                        shipping_cost = :shipping_cost,
                        updated_at = NOW()
                    WHERE ml_order_id = :order_id
                """)
                
                # Mapear status para o formato do enum
                status_mapping = {
                    "confirmed": "CONFIRMED",
                    "payment_required": "PENDING",
                    "payment_in_process": "PENDING",
                    "paid": "PAID",
                    "ready_to_ship": "PAID",
                    "shipped": "SHIPPED",
                    "delivered": "DELIVERED",
                    "cancelled": "CANCELLED",
                    "refunded": "REFUNDED"
                }
                api_status = order_data.get("status", "pending")
                db_status = status_mapping.get(api_status, "PENDING")
                logger.info(f"🔄 Atualizando pedido {order_id}: status API='{api_status}' -> DB='{db_status}'")
                
                db.execute(update_query, {
                    "order_id": str(order_id),
                    "status": db_status,
                    "status_detail": order_data.get("status_detail", {}).get("code") if order_data.get("status_detail") else None,
                    "date_closed": order_data.get("date_closed"),
                    "last_updated": order_data.get("last_updated"),
                    "total_amount": total_amount,
                    "paid_amount": payments[0].get("total_paid_amount") if payments else 0,
                    "shipping_cost": shipping.get("cost", 0) if shipping else 0
                })
                
                logger.info(f"✅ Pedido {order_id} atualizado")
            else:
                logger.info(f"ℹ️ Pedido {order_id} não existe no banco, será sincronizado na próxima sync completa")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar pedido: {e}")
            db.rollback()
    
    async def _upsert_item(self, item_data: Dict[str, Any], ml_user_id: int, db: Session):
        """Atualiza produto no banco de dados"""
        try:
            from sqlalchemy import text
            
            item_id = item_data.get("id")
            
            # Verificar se o produto existe
            check_query = text("SELECT id FROM products WHERE ml_item_id = :item_id")
            existing = db.execute(check_query, {"item_id": item_id}).fetchone()
            
            if existing:
                # Atualizar produto
                update_query = text("""
                    UPDATE products SET
                        title = :title,
                        price = :price,
                        available_quantity = :available_quantity,
                        sold_quantity = :sold_quantity,
                        status = :status,
                        updated_at = NOW()
                    WHERE ml_item_id = :item_id
                """)
                
                db.execute(update_query, {
                    "item_id": item_id,
                    "title": item_data.get("title"),
                    "price": item_data.get("price"),
                    "available_quantity": item_data.get("available_quantity"),
                    "sold_quantity": item_data.get("sold_quantity"),
                    "status": item_data.get("status")
                })
                
                db.commit()
                logger.info(f"✅ Produto {item_id} atualizado")
            else:
                logger.info(f"ℹ️ Produto {item_id} não existe no banco, será sincronizado na próxima sync completa")
                
        except Exception as e:
            logger.error(f"❌ Erro ao salvar produto: {e}")
            db.rollback()

