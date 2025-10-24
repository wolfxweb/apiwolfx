"""
Controller para processar notificações do Mercado Livre
"""
import logging
import httpx
from typing import Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.utils.notification_logger import global_logger

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
        topic = notification_data.get("topic")
        resource = notification_data.get("resource")
        ml_user_id = notification_data.get("user_id")
        
        try:
            logger.info(f"🔄 Processando notificação: topic={topic}, resource={resource}, ml_user_id={ml_user_id}")
            
            # 1. Determinar company_id a partir do ml_user_id
            company_id = self._get_company_id_from_ml_user(ml_user_id, db)
            if not company_id:
                logger.warning(f"⚠️ Company não encontrada para ml_user_id: {ml_user_id}")
                global_logger.log_notification_processed(
                    notification_data, 
                    None, 
                    False, 
                    f"Company não encontrada para ml_user_id: {ml_user_id}"
                )
                return
            
            # Log da notificação recebida
            global_logger.log_notification_received(notification_data, company_id)
            
            logger.info(f"🏢 Processando notificação para company_id: {company_id}")
            
            # Roteamento por tipo de notificação
            success = True
            error_message = None
            
            try:
                if topic == "orders_v2":
                    await self._process_order_notification(resource, ml_user_id, company_id, db)
                elif topic == "items":
                    await self._process_item_notification(resource, ml_user_id, company_id, db)
                elif topic == "messages":
                    await self._process_message_notification(resource, ml_user_id, company_id, db)
                elif topic == "questions":
                    await self._process_question_notification(resource, ml_user_id, company_id, db)
                elif topic == "payments":
                    await self._process_payment_notification(resource, ml_user_id, company_id, db)
                elif topic == "shipments":
                    await self._process_shipment_notification(resource, ml_user_id, company_id, db)
                elif topic == "claims" or topic == "post_purchase":
                    await self._process_claim_notification(resource, ml_user_id, company_id, db)
                else:
                    logger.warning(f"⚠️ Tipo de notificação não suportado: {topic}")
                    success = False
                    error_message = f"Tipo de notificação não suportado: {topic}"
                
            except Exception as e:
                success = False
                error_message = str(e)
                logger.error(f"❌ Erro ao processar {topic}: {e}")
            
            # Log do resultado do processamento
            global_logger.log_notification_processed(
                notification_data, 
                company_id, 
                success, 
                error_message
            )
            
            if success:
                logger.info(f"✅ Notificação processada: {topic} para company_id: {company_id}")
            else:
                logger.error(f"❌ Falha ao processar notificação: {topic} para company_id: {company_id}")
            
        except Exception as e:
            logger.error(f"❌ Erro geral ao processar notificação: {e}")
            global_logger.log_notification_processed(
                notification_data, 
                None, 
                False, 
                f"Erro geral: {str(e)}"
            )
    
    async def _process_order_notification(self, resource: str, ml_user_id: int, company_id: int, db: Session):
        """Processa notificação de pedido (orders_v2)"""
        order_id = resource.split("/")[-1]
        
        try:
            logger.info(f"📦 Processando pedido: {order_id} para company_id: {company_id}")
            
            # Buscar token do usuário ML
            access_token = self._get_user_token(ml_user_id, db)
            if not access_token:
                error_msg = f"Token não encontrado para ml_user_id: {ml_user_id}"
                logger.warning(f"⚠️ {error_msg}")
                global_logger.log_order_processed(order_id, company_id, False, "error", error_msg)
                return
            
            # Buscar detalhes do pedido na API do ML
            order_data = await self._fetch_order_details(order_id, access_token)
            if not order_data:
                error_msg = f"Não foi possível buscar dados do pedido {order_id} na API"
                logger.warning(f"⚠️ {error_msg}")
                global_logger.log_order_processed(order_id, company_id, False, "error", error_msg)
                return
            
            # Atualizar ou criar pedido no banco com company_id
            await self._upsert_order(order_data, company_id, db)
            
            logger.info(f"✅ Pedido {order_id} atualizado com sucesso para company_id: {company_id}")
            global_logger.log_order_processed(order_id, company_id, True, "updated")
            
        except Exception as e:
            error_msg = f"Erro ao processar pedido {order_id}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            global_logger.log_order_processed(order_id, company_id, False, "error", error_msg)
    
    async def _process_item_notification(self, resource: str, ml_user_id: int, company_id: int, db: Session):
        """Processa notificação de produto (items)"""
        item_id = resource.split("/")[-1]
        
        try:
            logger.info(f"🏷️ Processando produto: {item_id} para company_id: {company_id}")
            
            # Buscar token
            access_token = self._get_user_token(ml_user_id, db)
            if not access_token:
                error_msg = f"Token não encontrado para ml_user_id: {ml_user_id}"
                logger.warning(f"⚠️ {error_msg}")
                global_logger.log_product_processed(item_id, company_id, False, "error", error_msg)
                return
            
            # Buscar detalhes do produto
            item_data = await self._fetch_item_details(item_id, access_token)
            if not item_data:
                error_msg = f"Não foi possível buscar dados do produto {item_id} na API"
                logger.warning(f"⚠️ {error_msg}")
                global_logger.log_product_processed(item_id, company_id, False, "error", error_msg)
                return
            
            # Atualizar produto no banco
            await self._upsert_item(item_data, company_id, db)
            
            logger.info(f"✅ Produto {item_id} atualizado com sucesso para company_id: {company_id}")
            global_logger.log_product_processed(item_id, company_id, True, "updated")
            
        except Exception as e:
            error_msg = f"Erro ao processar produto {item_id}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            global_logger.log_product_processed(item_id, company_id, False, "error", error_msg)
    
    async def _process_message_notification(self, resource: str, ml_user_id: int, company_id: int, db: Session):
        """Processa notificação de mensagem"""
        logger.info(f"💬 Notificação de mensagem recebida: {resource} para company_id: {company_id}")
        # TODO: Implementar processamento de mensagens
    
    async def _process_question_notification(self, resource: str, ml_user_id: int, company_id: int, db: Session):
        """Processa notificação de pergunta"""
        logger.info(f"❓ Notificação de pergunta recebida: {resource} para company_id: {company_id}")
        # TODO: Implementar processamento de perguntas
    
    async def _process_payment_notification(self, resource: str, ml_user_id: int, company_id: int, db: Session):
        """Processa notificação de pagamento"""
        logger.info(f"💰 Notificação de pagamento recebida: {resource} para company_id: {company_id}")
        # TODO: Implementar processamento de pagamentos
    
    async def _process_shipment_notification(self, resource: str, ml_user_id: int, company_id: int, db: Session):
        """Processa notificação de envio"""
        logger.info(f"🚚 Notificação de envio recebida: {resource} para company_id: {company_id}")
        # TODO: Implementar processamento de envios
    
    async def _process_claim_notification(self, resource: str, ml_user_id: int, company_id: int, db: Session):
        """Processa notificação de reclamação"""
        logger.info(f"⚠️ Notificação de reclamação recebida: {resource} para company_id: {company_id}")
        # TODO: Implementar processamento de reclamações
    
    def _get_company_id_from_ml_user(self, ml_user_id: int, db: Session) -> int:
        """Busca company_id a partir do ml_user_id do Mercado Livre"""
        try:
            from sqlalchemy import text
            
            query = text("""
                SELECT ma.company_id 
                FROM ml_accounts ma 
                WHERE ma.ml_user_id = :ml_user_id
                AND ma.status = 'ACTIVE'
            """)
            
            result = db.execute(query, {"ml_user_id": str(ml_user_id)}).fetchone()
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar company_id: {e}")
            return None

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
    
    async def _upsert_order(self, order_data: Dict[str, Any], company_id: int, db: Session):
        """Atualiza ou cria pedido no banco de dados"""
        try:
            from sqlalchemy import text
            from datetime import datetime
            
            order_id = order_data.get("id")
            
            # Verificar se o pedido já existe para esta empresa
            check_query = text("SELECT id FROM ml_orders WHERE ml_order_id = :order_id AND company_id = :company_id")
            existing = db.execute(check_query, {"order_id": str(order_id), "company_id": company_id}).fetchone()
            
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
                    WHERE ml_order_id = :order_id AND company_id = :company_id
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
                    "company_id": company_id,
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
    
    async def _upsert_item(self, item_data: Dict[str, Any], company_id: int, db: Session):
        """Atualiza produto no banco de dados"""
        try:
            from sqlalchemy import text
            
            item_id = item_data.get("id")
            
            # Verificar se o produto existe para esta empresa
            check_query = text("SELECT id FROM ml_products WHERE ml_item_id = :item_id AND company_id = :company_id")
            existing = db.execute(check_query, {"item_id": item_id, "company_id": company_id}).fetchone()
            
            if existing:
                # Atualizar produto
                update_query = text("""
                    UPDATE ml_products SET
                        title = :title,
                        price = :price,
                        available_quantity = :available_quantity,
                        sold_quantity = :sold_quantity,
                        status = :status,
                        updated_at = NOW()
                    WHERE ml_item_id = :item_id AND company_id = :company_id
                """)
                
                db.execute(update_query, {
                    "item_id": item_id,
                    "company_id": company_id,
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

