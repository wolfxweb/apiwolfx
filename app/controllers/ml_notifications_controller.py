"""
Controller para processar notificações do Mercado Livre
"""
import logging
import httpx
from typing import Dict, Any, Optional
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
            await self._upsert_order(order_data, company_id, db, access_token)
            
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
        """Processa notificação de mensagem pós-venda"""
        logger.info(f"💬 ========== PROCESSANDO NOTIFICAÇÃO DE MENSAGEM ==========")
        logger.info(f"💬 Resource (package_id): {resource}")
        logger.info(f"💬 ML User ID: {ml_user_id}")
        logger.info(f"💬 Company ID: {company_id}")
        logger.info(f"💬 Tipo: mensagem pós-venda (messages)")
        
        try:
            # O resource é o package_id (ID do pacote/conversa)
            package_id = resource.strip() if resource else None
            
            if not package_id:
                logger.error(f"❌ Package ID vazio ou inválido: {resource}")
                raise ValueError(f"Package ID vazio: {resource}")
            
            logger.info(f"📦 Package ID extraído: {package_id}")
            
            from app.controllers.ml_messages_controller import MLMessagesController
            
            logger.info(f"🔧 Criando instância do MLMessagesController...")
            controller = MLMessagesController(db)
            
            logger.info(f"🔄 Iniciando processamento da mensagem pós-venda {package_id} via MLMessagesController...")
            logger.info(f"📊 Parâmetros: package_id={package_id}, ml_user_id={ml_user_id}, company_id={company_id}")
            
            result = controller.process_notification(package_id, ml_user_id, company_id)
            
            logger.info(f"📥 Resultado do processamento: {result}")
            
            if result.get("success"):
                thread_id = result.get("thread_id")
                logger.info(f"✅ Mensagem pós-venda {package_id} processada com sucesso!")
                logger.info(f"✅ Thread ID criado/atualizado: {thread_id}")
                logger.info(f"✅ Company ID: {company_id}")
                
                global_logger.log_event(
                    event_type="message_notification_success",
                    data={
                        "package_id": package_id,
                        "resource": resource,
                        "ml_user_id": ml_user_id,
                        "thread_id": thread_id,
                        "description": f"Mensagem pós-venda {package_id} processada com sucesso"
                    },
                    company_id=company_id,
                    success=True
                )
                logger.info(f"💬 ========== NOTIFICAÇÃO DE MENSAGEM PROCESSADA COM SUCESSO ==========")
            else:
                error_msg = result.get("error", "Erro desconhecido")
                logger.error(f"❌ Erro ao processar mensagem pós-venda {package_id}")
                logger.error(f"❌ Mensagem de erro: {error_msg}")
                logger.error(f"❌ Resultado completo: {result}")
                
                global_logger.log_event(
                    event_type="message_notification_error",
                    data={
                        "package_id": package_id,
                        "resource": resource,
                        "ml_user_id": ml_user_id,
                        "error": error_msg,
                        "result": result
                    },
                    company_id=company_id,
                    success=False,
                    error_message=error_msg
                )
                logger.error(f"💬 ========== ERRO AO PROCESSAR NOTIFICAÇÃO DE MENSAGEM ==========")
            
        except Exception as e:
            logger.error(f"❌ ========== EXCEÇÃO AO PROCESSAR NOTIFICAÇÃO DE MENSAGEM ==========")
            logger.error(f"❌ Resource: {resource}")
            logger.error(f"❌ ML User ID: {ml_user_id}")
            logger.error(f"❌ Company ID: {company_id}")
            logger.error(f"❌ Erro: {str(e)}")
            logger.error(f"❌ Tipo da exceção: {type(e).__name__}")
            logger.error(f"❌ Traceback completo:", exc_info=True)
            
            global_logger.log_event(
                event_type="message_notification_exception",
                data={
                    "resource": resource,
                    "ml_user_id": ml_user_id,
                    "company_id": company_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                company_id=company_id,
                success=False,
                error_message=str(e)
            )
            logger.error(f"💬 ========== FIM DO ERRO NA NOTIFICAÇÃO DE MENSAGEM ==========")
    
    async def _process_question_notification(self, resource: str, ml_user_id: int, company_id: int, db: Session):
        """Processa notificação de pergunta"""
        logger.info(f"❓ Notificação de pergunta recebida - Resource: {resource}, ML User ID: {ml_user_id}, Company ID: {company_id}")
        
        try:
            # Extrair question_id para logs detalhados
            question_id = None
            try:
                question_id = int(resource.split("/")[-1])
                logger.info(f"📋 Question ID extraído: {question_id}")
            except (ValueError, IndexError) as e:
                logger.warning(f"⚠️ Não foi possível extrair question_id do resource '{resource}': {e}")
            
            from app.controllers.ml_questions_controller import MLQuestionsController
            
            controller = MLQuestionsController(db)
            
            logger.info(f"🔄 Iniciando processamento da pergunta {question_id} via MLQuestionsController...")
            success = controller.process_notification(resource, ml_user_id, company_id)
            
            if success:
                logger.info(f"✅ Pergunta {question_id} processada com sucesso para company_id: {company_id}")
                global_logger.log_event(
                    event_type="question_notification_success",
                    data={
                        "question_id": question_id,
                        "resource": resource,
                        "ml_user_id": ml_user_id,
                        "description": f"Pergunta {question_id} processada com sucesso"
                    },
                    company_id=company_id,
                    success=True
                )
            else:
                logger.warning(f"⚠️ Falha ao processar pergunta {question_id} para company_id: {company_id}")
                global_logger.log_event(
                    event_type="question_notification_error",
                    data={
                        "question_id": question_id,
                        "resource": resource,
                        "ml_user_id": ml_user_id,
                        "description": f"Falha ao processar pergunta {question_id}"
                    },
                    company_id=company_id,
                    success=False,
                    error_message="Processamento falhou (ver logs detalhados em question_processed)"
                )
                
        except Exception as e:
            error_msg = f"Erro ao processar notificação de pergunta: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            global_logger.log_event(
                event_type="question_notification_exception",
                data={
                    "question_id": question_id if question_id else None,
                    "resource": resource,
                    "ml_user_id": ml_user_id,
                    "description": f"Exceção ao processar notificação de pergunta"
                },
                company_id=company_id,
                success=False,
                error_message=error_msg
            )
    
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
            from app.models.saas_models import MLAccount, MLAccountStatus
            # Usar ORM ao invés de SQL direto para garantir compatibilidade com Enum
            ml_account = db.query(MLAccount).filter(
                MLAccount.ml_user_id == str(ml_user_id),
                MLAccount.status == MLAccountStatus.ACTIVE
            ).first()
            
            return ml_account.company_id if ml_account else None
            
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
    
    async def _upsert_order(self, order_data: Dict[str, Any], company_id: int, db: Session, access_token: str = None):
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
                        shipping_type = :shipping_type,
                        shipping_status = :shipping_status,
                        shipping_id = :shipping_id,
                        shipping_method = :shipping_method,
                        shipping_date = :shipping_date,
                        estimated_delivery_date = :estimated_delivery_date,
                        shipping_details = :shipping_details,
                        payments = :payments,
                        updated_at = NOW()
                    WHERE ml_order_id = :order_id AND company_id = :company_id
                """)
                
                # Buscar detalhes completos do shipment para obter substatus (fulfillment)
                shipping = order_data.get("shipping", {})
                shipping_status = shipping.get("status")
                shipping_id = shipping.get("id")
                
                # Tentar buscar detalhes completos do shipment se tiver ID
                shipment_substatus = None
                logistic_type = None
                shipping_method = None
                shipment_data_json = None
                shipping_date = None
                estimated_delivery_date = None
                
                if shipping_id and access_token:
                    try:
                        # Buscar detalhes completos do shipment com header x-format-new
                        import httpx
                        shipment_url = f"{self.api_base_url}/shipments/{shipping_id}"
                        shipment_headers = {
                            "Authorization": f"Bearer {access_token}",
                            "x-format-new": "true"
                        }
                        
                        async with httpx.AsyncClient() as client:
                            shipment_response = await client.get(shipment_url, headers=shipment_headers, timeout=30)
                            
                            if shipment_response.status_code == 200:
                                shipment_data = shipment_response.json()
                                shipment_data_json = shipment_data  # Salvar JSON completo para salvar no banco
                                shipment_substatus = shipment_data.get("substatus")
                                logistic_type = shipment_data.get("logistic_type")  # Campo direto
                                shipping_date = shipment_data.get("date_created")
                                
                                # Buscar método de envio
                                shipping_option = shipment_data.get("shipping_option", {})
                                shipping_method_name = shipping_option.get("shipping_method", {}).get("name") if shipping_option.get("shipping_method") else None
                                shipping_method = shipping_method_name
                                
                                # Buscar data estimada de entrega
                                estimated_delivery = shipping_option.get("estimated_delivery_final", {})
                                estimated_delivery_date = estimated_delivery.get("date")
                                
                                logger.info(f"📦 Shipment {shipping_id}: substatus={shipment_substatus}, type={logistic_type}, method={shipping_method}, date={shipping_date}, estimated={estimated_delivery_date}")
                    except Exception as e:
                        logger.warning(f"Erro ao buscar detalhes do shipment {shipping_id}: {e}")
                
                # Mapear status de envio conforme documentação ML (shipment_statuses API)
                # Priorizar status de shipment quando disponível (mais confiável)
                shipping_status_mapping = {
                    # Status de Shipment (MAIS PRECISOS)
                    "pending": "PENDING",
                    "handling": "CONFIRMED", 
                    "ready_to_ship": "PAID",
                    "shipped": "SHIPPED",
                    "delivered": "DELIVERED",
                    "not_delivered": "CANCELLED",
                    "cancelled": "CANCELLED",
                    "closed": "DELIVERED",  # Feito/entregue
                    # Status adicionais de fulfillment
                    "to_be_agreed": "PENDING",
                    "active": "CONFIRMED",
                    "error": "CANCELLED"
                }
                
                # Mapeamento de substatus (fulfillment)
                substatus_mapping = {
                    "in_warehouse": "PAID",  # Processando no centro de distribuição
                    "ready_to_print": "PAID",
                    "printed": "PAID",
                    "ready_to_pack": "PAID",
                    "ready_to_ship": "PAID",
                    "shipped": "SHIPPED",
                    "in_transit": "SHIPPED",
                    "delivered": "DELIVERED",
                    "lost": "CANCELLED",
                    "damaged": "CANCELLED"
                }
                
                # Status geral do pedido (fallback)
                order_status_mapping = {
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
                
                # Prioridade: substatus > shipping_status > order_status
                substatus_db_status = substatus_mapping.get(shipment_substatus) if shipment_substatus else None
                shipping_db_status = shipping_status_mapping.get(shipping_status)
                order_db_status = order_status_mapping.get(api_status, "PENDING")
                
                # Usar substatus como prioridade máxima (fulfillment)
                db_status = substatus_db_status or shipping_db_status or order_db_status
                
                # Log detalhado para debug
                logger.info(f"🔄 [WEBHOOK] Atualizando pedido {order_id}:")
                if shipment_substatus:
                    logger.info(f"   🏭 Substatus (fulfillment): '{shipment_substatus}' -> '{substatus_db_status}'")
                logger.info(f"   📦 Shipping Status: '{shipping_status}' -> '{shipping_db_status}'")
                logger.info(f"   📋 Order Status: '{api_status}' -> '{order_db_status}'")
                logger.info(f"   🎯 Final Status: '{db_status}'")
                if logistic_type:
                    logger.info(f"   📦 Logistics Type: '{logistic_type}'")
                logger.info(f"   📅 Data fechamento: {order_data.get('date_closed')}")
                logger.info(f"   💰 Total: {total_amount}")
                
                import json
                
                db.execute(update_query, {
                    "order_id": str(order_id),
                    "company_id": company_id,
                    "status": db_status,
                    "status_detail": order_data.get("status_detail", {}).get("code") if order_data.get("status_detail") else None,
                    "date_closed": order_data.get("date_closed"),
                    "last_updated": order_data.get("last_updated"),
                    "total_amount": total_amount,
                    "paid_amount": payments[0].get("total_paid_amount") if payments else 0,
                    "shipping_cost": shipping.get("cost", 0) if shipping else 0,
                    "shipping_type": logistic_type,
                    "shipping_status": shipping_status,
                    "shipping_id": str(shipping_id) if shipping_id else None,
                    "shipping_method": shipping_method,
                    "shipping_date": shipping_date,
                    "estimated_delivery_date": estimated_delivery_date,
                    "shipping_details": json.dumps(shipment_data_json) if shipment_data_json else None,
                    "payments": json.dumps(payments) if payments else None
                })
                
                logger.info(f"✅ [WEBHOOK] Pedido {order_id} atualizado com status: {db_status}")
                
                # IMPORTANTE: Fazer commit da atualização
                db.commit()
                logger.info(f"✅ Commit realizado para atualização do pedido {order_id}")
                
                # Verificar nota fiscal automaticamente para pedidos pagos
                if db_status in ["PAID", "CONFIRMED"]:
                    await self._check_invoice_for_order(order_id, company_id, db)
                    
            else:
                logger.info(f"🆕 Pedido {order_id} não existe no banco, criando novo pedido via webhook")
                
                # Criar novo pedido usando MLOrdersService
                try:
                    from app.services.ml_orders_service import MLOrdersService
                    from app.models.saas_models import MLAccount, MLAccountStatus
                    
                    # Buscar MLAccount ativa da empresa
                    ml_account = db.query(MLAccount).filter(
                        MLAccount.company_id == company_id,
                        MLAccount.status == MLAccountStatus.ACTIVE
                    ).first()
                    
                    if ml_account:
                        orders_service = MLOrdersService(db)
                        result = orders_service._save_order_to_database(order_data, ml_account.id, company_id)
                        
                        if result.get("action") == "created":
                            logger.info(f"✅ Novo pedido {order_id} criado com sucesso via webhook")
                        elif result.get("action") == "updated":
                            logger.info(f"✅ Pedido {order_id} atualizado via webhook")
                        
                        # IMPORTANTE: Garantir commit após criar/atualizar pedido
                        db.commit()
                        logger.info(f"✅ Commit realizado para pedido {order_id}")
                    else:
                        error_msg = f"MLAccount não encontrada para company_id {company_id}"
                        logger.warning(f"⚠️ {error_msg}")
                        raise Exception(error_msg)
                
                except Exception as e:
                    logger.error(f"❌ Erro ao criar pedido {order_id} via webhook: {e}", exc_info=True)
                    db.rollback()
                    raise  # Re-raise para ser capturado no except externo
            
            # Não precisa fazer commit aqui pois:
            # - Pedidos existentes: commit já foi feito acima (linha ~467)
            # - Pedidos novos: commit já foi feito no bloco acima (linha ~497)
            logger.info(f"✅ Pedido {order_id} processado com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar pedido {order_id}: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception as rollback_error:
                logger.error(f"❌ Erro ao fazer rollback: {rollback_error}", exc_info=True)
            raise  # Re-raise para que o erro seja logado no nível superior
    
    async def _check_invoice_for_order(self, order_id: str, company_id: int, db: Session):
        """
        Verifica automaticamente se um pedido tem nota fiscal emitida
        Chamado quando um pedido é atualizado via webhook
        """
        try:
            from sqlalchemy import text
            
            # Buscar dados do pedido incluindo pack_id e shipping_id
            order_query = text("""
                SELECT id, ml_order_id, pack_id, shipping_id, invoice_emitted 
                FROM ml_orders 
                WHERE ml_order_id = :order_id AND company_id = :company_id
            """)
            
            order_result = db.execute(order_query, {"order_id": str(order_id), "company_id": company_id}).fetchone()
            
            if not order_result:
                logger.warning(f"⚠️ Pedido {order_id} não encontrado para verificação de NF")
                return
            
            order_db_id, ml_order_id, pack_id, shipping_id, current_invoice_status = order_result
            
            if current_invoice_status:
                logger.info(f"ℹ️ Pedido {order_id} já tem NF marcada - pulando verificação")
                return
            
            # Buscar token de acesso para esta empresa
            access_token = self._get_user_token_by_company(company_id, db)
            if not access_token:
                logger.warning(f"⚠️ Token não encontrado para company_id: {company_id}")
                return
            
            # Verificar NF no ML usando ShipmentService
            from app.services.shipment_service import ShipmentService
            shipment_service = ShipmentService(db)
            
            # Tentar buscar NF por pack_id primeiro
            invoice_data = None
            if pack_id:
                logger.info(f"🔍 Buscando NF pelo pack_id {pack_id} para pedido {order_id}")
                invoice_data = shipment_service._check_pack_invoice(pack_id, access_token)
            
            # Se não encontrou pelo pack_id e tem shipping_id, tentar pelo shipping_id (fulfillment)
            if not invoice_data and shipping_id:
                logger.info(f"🔍 Buscando NF pelo shipping_id {shipping_id} para pedido {order_id} (fulfillment)")
                invoice_data = shipment_service._check_shipment_invoice(shipping_id, company_id, access_token)
            
            if invoice_data and invoice_data.get('has_invoice'):
                # Atualizar pedido com dados da NF
                update_invoice_query = text("""
                    UPDATE ml_orders SET
                        invoice_emitted = true,
                        invoice_emitted_at = NOW(),
                        invoice_number = :invoice_number,
                        invoice_series = :invoice_series,
                        invoice_key = :invoice_key,
                        invoice_xml_url = :invoice_xml_url,
                        invoice_pdf_url = :invoice_pdf_url,
                        updated_at = NOW()
                    WHERE id = :order_db_id
                """)
                
                db.execute(update_invoice_query, {
                    "order_db_id": order_db_id,
                    "invoice_number": invoice_data.get('number'),
                    "invoice_series": invoice_data.get('series'),
                    "invoice_key": invoice_data.get('key'),
                    "invoice_xml_url": invoice_data.get('xml_url'),
                    "invoice_pdf_url": invoice_data.get('pdf_url')
                })
                
                logger.info(f"✅ [AUTO-NF] Nota fiscal detectada e atualizada para pedido {order_id}")
                
            else:
                logger.info(f"ℹ️ [AUTO-NF] Pedido {order_id} ainda não tem nota fiscal emitida")
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar NF do pedido {order_id}: {e}")
    
    def _get_user_token_by_company(self, company_id: int, db: Session) -> Optional[str]:
        """Busca token de acesso para uma empresa específica"""
        try:
            from app.services.token_manager import TokenManager
            from app.models.saas_models import User
            
            # Buscar um usuário ativo da empresa
            user = db.query(User).filter(
                User.company_id == company_id,
                User.is_active == True
            ).first()
            
            if not user:
                return None
            
            token_manager = TokenManager(db)
            return token_manager.get_valid_token(user.id)
            
        except Exception as e:
            logger.error(f"Erro ao buscar token para company_id {company_id}: {e}")
            return None
    
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

