"""
Controller para processar notificações do Mercado Livre
"""
import logging
import httpx
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path

from app.utils.notification_logger import global_logger

logger = logging.getLogger(__name__)

# Configurar logger para também escrever no arquivo system.log
def _setup_file_logging():
    """Configura o logger para escrever no arquivo system.log"""
    # Evitar duplicação de handlers
    if any(isinstance(h, logging.FileHandler) and 'system.log' in h.baseFilename for h in logger.handlers):
        return
    
    # Usar o mesmo diretório do global_logger
    log_dir = Path(global_logger.log_dir)
    log_file = log_dir / "system.log"
    
    # Criar handler para arquivo
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Formatter com timestamp
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)

# Configurar logging ao importar o módulo
_setup_file_logging()

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
        
        # Segundo a documentação oficial do Mercado Livre:
        # https://developers.mercadolivre.com.br/pt_br/recebendo-notificacoes
        # O campo 'user_id' identifica o vendedor (seller) na notificação
        # Se não vier, devemos buscar do pedido via GET /orders/{ORDER_ID} para obter seller_id
        ml_user_id = notification_data.get("user_id")
        
        try:
            logger.info(f"🔄 ========== NOVA NOTIFICAÇÃO RECEBIDA ==========")
            logger.info(f"🔄 Topic: {topic}")
            logger.info(f"🔄 Resource: {resource}")
            logger.info(f"🔄 ML User ID (user_id da notificação): {ml_user_id} (tipo: {type(ml_user_id)})")
            logger.info(f"🔄 Application ID: {notification_data.get('application_id')}")
            logger.info(f"🔄 Todos os campos: {list(notification_data.keys())}")
            logger.info(f"🔄 Notification Data Completo: {notification_data}")
            
            # Segundo a documentação: se user_id não vier, buscar do pedido via API
            # GET /orders/{ORDER_ID} retorna seller_id que é equivalente ao ml_user_id
            if not ml_user_id and topic == "orders_v2" and resource:
                logger.info(f"🔍 user_id não veio na notificação, buscando seller_id do pedido via API...")
                logger.info(f"🔍 Segundo documentação ML: GET /orders/{resource.split('/')[-1]}")
                order_id = resource.split("/")[-1]
                ml_user_id = await self._extract_ml_user_id_from_order(order_id, db)
                if ml_user_id:
                    logger.info(f"✅ seller_id extraído do pedido {order_id}: {ml_user_id}")
                else:
                    logger.error(f"❌ Não foi possível extrair seller_id do pedido {order_id}")
                    logger.error(f"❌ Isso pode indicar que nenhum token ativo está disponível")
            
            # 1. Determinar company_id a partir do ml_user_id
            if ml_user_id:
                logger.info(f"🔍 Iniciando busca de company_id para ml_user_id: {ml_user_id}")
                company_id = self._get_company_id_from_ml_user(ml_user_id, db)
            else:
                company_id = None
                
            if not company_id:
                error_msg = f"Company não encontrada para ml_user_id: {ml_user_id}"
                logger.error(f"❌ ========== ERRO: COMPANY NÃO ENCONTRADA ==========")
                logger.error(f"❌ ML User ID: {ml_user_id}")
                logger.error(f"❌ Topic: {topic}")
                logger.error(f"❌ Resource: {resource}")
                logger.error(f"❌ Esta notificação NÃO será processada!")
                global_logger.log_notification_processed(
                    notification_data, 
                    None, 
                    False, 
                    error_msg
                )
                global_logger.log_event(
                    event_type="notification_rejected_no_company",
                    data={
                        "topic": topic,
                        "resource": resource,
                        "ml_user_id": ml_user_id,
                        "ml_user_id_type": type(ml_user_id).__name__,
                        "description": f"Notificação rejeitada: company não encontrada para ml_user_id {ml_user_id}"
                    },
                    company_id=None,
                    success=False,
                    error_message=error_msg
                )
                return
            
            logger.info(f"✅ Company ID encontrado: {company_id}")
            
            # Log da notificação recebida
            global_logger.log_notification_received(notification_data, company_id)
            
            logger.info(f"🏢 Processando notificação para company_id: {company_id}")
            
            # Roteamento por tipo de notificação
            success = True
            error_message = None
            
            # Lista de notificações ignoradas intencionalmente (não são erros)
            ignored_topics = [
                "price_suggestion",      # Sugestão de preço (não implementado)
                "items_prices",          # Mudança de preço (não implementado)
                "stock-locations",       # Localização de estoque (não implementado)
                "fbm_stock_operations",  # Operações FBM (não implementado)
                "catalog_item_competition_status",  # Status de competição (não implementado)
                "public_candidates"      # Candidatos públicos (não implementado)
            ]
            
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
                elif topic == "invoices":
                    await self._process_invoice_notification(resource, ml_user_id, company_id, db)
                elif topic == "claims" or topic == "post_purchase":
                    await self._process_claim_notification(resource, ml_user_id, company_id, db)
                elif topic in ignored_topics:
                    # Notificações ignoradas intencionalmente - não são erros
                    logger.info(f"ℹ️ Notificação '{topic}' recebida e ignorada (não implementada)")
                    success = True  # Marcar como sucesso para não gerar alarmes
                    error_message = None
                else:
                    # Tipo realmente desconhecido
                    logger.warning(f"⚠️ Tipo de notificação desconhecido: {topic}")
                    success = False
                    error_message = f"Tipo de notificação desconhecido: {topic}"
                
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
            logger.info(f"📦 ========== INICIANDO PROCESSAMENTO DE PEDIDO ==========")
            logger.info(f"📦 Order ID: {order_id}")
            logger.info(f"📦 Resource: {resource}")
            logger.info(f"📦 ML User ID: {ml_user_id}")
            logger.info(f"📦 Company ID: {company_id}")
            
            global_logger.log_event(
                event_type="order_notification_start",
                data={
                    "order_id": order_id,
                    "resource": resource,
                    "ml_user_id": ml_user_id,
                    "company_id": company_id,
                    "description": f"Iniciando processamento do pedido {order_id}"
                },
                company_id=company_id,
                success=True
            )
            
            # Buscar token do usuário ML
            logger.info(f"🔑 Buscando token para ml_user_id: {ml_user_id}")
            access_token = self._get_user_token(ml_user_id, db)
            if not access_token:
                error_msg = f"Token não encontrado para ml_user_id: {ml_user_id}"
                logger.error(f"❌ {error_msg}")
                logger.error(f"❌ Não foi possível processar pedido {order_id} sem token")
                global_logger.log_order_processed(order_id, company_id, False, "error", error_msg)
                global_logger.log_event(
                    event_type="order_notification_token_error",
                    data={
                        "order_id": order_id,
                        "ml_user_id": ml_user_id,
                        "error": error_msg,
                        "description": f"Falha ao obter token para processar pedido {order_id}"
                    },
                    company_id=company_id,
                    success=False,
                    error_message=error_msg
                )
                return
            
            logger.info(f"✅ Token obtido com sucesso para ml_user_id: {ml_user_id}")
            
            # Buscar detalhes do pedido na API do ML
            logger.info(f"🌐 [NOTIF] ========== BUSCANDO DADOS DO PEDIDO NA API ==========")
            logger.info(f"🌐 [NOTIF] Order ID: {order_id}")
            logger.info(f"🌐 [NOTIF] URL: {self.api_base_url}/orders/{order_id}")
            logger.info(f"🌐 [NOTIF] Token disponível: {'✅ SIM' if access_token else '❌ NÃO'}")
            
            order_data = await self._fetch_order_details(order_id, access_token)
            if not order_data:
                error_msg = f"Não foi possível buscar dados do pedido {order_id} na API"
                logger.error(f"❌ [NOTIF] {error_msg}")
                logger.error(f"❌ [NOTIF] Verifique se o token está válido e se o pedido existe no ML")
                global_logger.log_order_processed(order_id, company_id, False, "error", error_msg)
                global_logger.log_event(
                    event_type="order_notification_api_error",
                    data={
                        "order_id": order_id,
                        "ml_user_id": ml_user_id,
                        "error": error_msg,
                        "description": f"Falha ao buscar dados do pedido {order_id} na API"
                    },
                    company_id=company_id,
                    success=False,
                    error_message=error_msg
                )
                return
            
            logger.info(f"✅ [NOTIF] ========== DADOS DO PEDIDO OBTIDOS DA API ==========")
            logger.info(f"✅ [NOTIF] Order ID: {order_id}")
            logger.info(f"✅ [NOTIF] Status (API): {order_data.get('status')}")
            logger.info(f"✅ [NOTIF] Total: R$ {order_data.get('total_amount', 0)}")
            logger.info(f"✅ [NOTIF] Date Created: {order_data.get('date_created')}")
            logger.info(f"✅ [NOTIF] Date Closed: {order_data.get('date_closed')}")
            logger.info(f"✅ [NOTIF] Last Updated: {order_data.get('last_updated')}")
            logger.info(f"✅ [NOTIF] Buyer ID: {order_data.get('buyer', {}).get('id')}")
            logger.info(f"✅ [NOTIF] Shipping ID: {order_data.get('shipping', {}).get('id')}")
            logger.info(f"✅ [NOTIF] Shipping Status: {order_data.get('shipping', {}).get('status')}")
            logger.info(f"✅ [NOTIF] Payments: {len(order_data.get('payments', []))} pagamento(s)")
            logger.info(f"✅ [NOTIF] Order Items: {len(order_data.get('order_items', []))} item(ns)")
            
            # Atualizar ou criar pedido no banco com company_id
            logger.info(f"💾 [NOTIF] ========== INICIANDO SALVAMENTO/ATUALIZAÇÃO NO BANCO ==========")
            logger.info(f"💾 [NOTIF] Order ID: {order_id}")
            logger.info(f"💾 [NOTIF] Company ID: {company_id}")
            await self._upsert_order(order_data, company_id, db, access_token)
            logger.info(f"💾 [NOTIF] ✅ Função _upsert_order concluída para pedido {order_id}")
            
            logger.info(f"✅ ========== PEDIDO PROCESSADO COM SUCESSO ==========")
            logger.info(f"✅ Pedido {order_id} atualizado com sucesso para company_id: {company_id}")
            global_logger.log_order_processed(order_id, company_id, True, "updated")
            global_logger.log_event(
                event_type="order_notification_success",
                data={
                    "order_id": order_id,
                    "ml_user_id": ml_user_id,
                    "company_id": company_id,
                    "status": order_data.get('status'),
                    "total_amount": order_data.get('total_amount', 0),
                    "description": f"Pedido {order_id} processado com sucesso"
                },
                company_id=company_id,
                success=True
            )
            
        except Exception as e:
            error_msg = f"Erro ao processar pedido {order_id}: {str(e)}"
            logger.error(f"❌ ========== ERRO AO PROCESSAR PEDIDO ==========")
            logger.error(f"❌ Order ID: {order_id}")
            logger.error(f"❌ ML User ID: {ml_user_id}")
            logger.error(f"❌ Company ID: {company_id}")
            logger.error(f"❌ Erro: {error_msg}")
            logger.error(f"❌ Tipo da exceção: {type(e).__name__}")
            logger.error(f"❌ Traceback completo:", exc_info=True)
            global_logger.log_order_processed(order_id, company_id, False, "error", error_msg)
            global_logger.log_event(
                event_type="order_notification_exception",
                data={
                    "order_id": order_id,
                    "ml_user_id": ml_user_id,
                    "company_id": company_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "description": f"Exceção ao processar pedido {order_id}"
                },
                company_id=company_id,
                success=False,
                error_message=str(e)
            )
    
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
            from sqlalchemy import or_
            
            # Normalizar ml_user_id: converter para string e remover espaços
            ml_user_id_str = str(ml_user_id).strip() if ml_user_id is not None else None
            
            logger.info(f"🔍 Buscando company_id para ml_user_id: {ml_user_id} (original), '{ml_user_id_str}' (normalizado), tipo: {type(ml_user_id)}")
            
            if not ml_user_id_str:
                logger.error(f"❌ ml_user_id é None ou vazio após normalização")
                return None
            
            # Buscar conta ATIVA primeiro - tentar com diferentes formatos
            ml_account = db.query(MLAccount).filter(
                MLAccount.ml_user_id == ml_user_id_str,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).first()
            
            # Se não encontrou, tentar buscar sem considerar espaços extras (usando func.trim)
            if not ml_account:
                from sqlalchemy import func
                ml_account = db.query(MLAccount).filter(
                    func.trim(MLAccount.ml_user_id) == ml_user_id_str,
                    MLAccount.status == MLAccountStatus.ACTIVE
                ).first()
            
            if ml_account:
                logger.info(f"✅ Conta ML ATIVA encontrada: ml_user_id={ml_user_id}, company_id={ml_account.company_id}, nickname={ml_account.nickname}")
                global_logger.log_event(
                    event_type="ml_account_found",
                    data={
                        "ml_user_id": ml_user_id,
                        "company_id": ml_account.company_id,
                        "status": "ACTIVE",
                        "nickname": ml_account.nickname,
                        "description": f"Conta ML encontrada para ml_user_id {ml_user_id}"
                    },
                    company_id=ml_account.company_id,
                    success=True
                )
                return ml_account.company_id
            
            # Se não encontrou ATIVA, buscar qualquer conta (ativa ou inativa)
            logger.warning(f"⚠️ Conta ATIVA não encontrada, buscando qualquer conta para ml_user_id: {ml_user_id_str}")
            ml_account_any = db.query(MLAccount).filter(
                MLAccount.ml_user_id == ml_user_id_str
            ).first()
            
            # Se ainda não encontrou, tentar sem considerar espaços
            if not ml_account_any:
                from sqlalchemy import func
                ml_account_any = db.query(MLAccount).filter(
                    func.trim(MLAccount.ml_user_id) == ml_user_id_str
                ).first()
            
            if ml_account_any:
                logger.warning(f"⚠️ Conta ML existe mas está INATIVA: ml_user_id={ml_user_id}, status={ml_account_any.status}, company_id={ml_account_any.company_id}, nickname={ml_account_any.nickname}")
                logger.warning(f"⚠️ Processando notificação mesmo com conta INATIVA para ml_user_id: {ml_user_id}")
                global_logger.log_event(
                    event_type="ml_account_inactive_found",
                    data={
                        "ml_user_id": ml_user_id,
                        "company_id": ml_account_any.company_id,
                        "status": str(ml_account_any.status),
                        "nickname": ml_account_any.nickname,
                        "description": f"Conta ML INATIVA encontrada para ml_user_id {ml_user_id}, mas processando notificação"
                    },
                    company_id=ml_account_any.company_id,
                    success=True
                )
                # Retornar mesmo se inativa, pois a notificação deve ser processada
                return ml_account_any.company_id
            else:
                logger.error(f"❌ Conta ML NÃO encontrada: ml_user_id={ml_user_id}")
                # Debug: listar algumas contas para verificar formato
                all_accounts = db.query(
                    MLAccount.ml_user_id, 
                    MLAccount.company_id, 
                    MLAccount.status,
                    MLAccount.nickname
                ).limit(10).all()
                if all_accounts:
                    logger.info(f"📋 Exemplo de contas cadastradas (primeiras 10): {[(str(acc.ml_user_id), acc.company_id, str(acc.status), acc.nickname) for acc in all_accounts]}")
                    logger.info(f"📋 Buscando exatamente: ml_user_id='{ml_user_id}' (tipo: {type(ml_user_id).__name__})")
                else:
                    logger.warning(f"⚠️ Nenhuma conta ML cadastrada no sistema")
                
                global_logger.log_event(
                    event_type="ml_account_not_found",
                    data={
                        "ml_user_id": ml_user_id,
                        "ml_user_id_type": type(ml_user_id).__name__,
                        "example_accounts": [(str(acc.ml_user_id), acc.company_id, str(acc.status)) for acc in all_accounts[:5]],
                        "description": f"Conta ML não encontrada para ml_user_id {ml_user_id}"
                    },
                    company_id=None,
                    success=False,
                    error_message=f"Conta ML não encontrada para ml_user_id {ml_user_id}"
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar company_id: {e}", exc_info=True)
            global_logger.log_event(
                event_type="ml_account_search_error",
                data={
                    "ml_user_id": ml_user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "description": f"Erro ao buscar conta ML para ml_user_id {ml_user_id}"
                },
                company_id=None,
                success=False,
                error_message=str(e)
            )
            return None

    def _get_user_token(self, ml_user_id: int, db: Session) -> Optional[str]:
        """Busca token ativo para o seller usando TokenManager (com renovação automática)."""
        try:
            from app.services.token_manager import TokenManager
            from sqlalchemy import text

            account_query = text(
                "SELECT id, company_id FROM ml_accounts WHERE ml_user_id = CAST(:ml_user_id AS VARCHAR) LIMIT 1"
            )
            account_row = db.execute(account_query, {"ml_user_id": str(ml_user_id)}).fetchone()

            if not account_row:
                logger.error(f"❌ Conta ML não encontrada para ml_user_id={ml_user_id}")
                return None

            ml_account_id, company_id = account_row

            token_manager = TokenManager(db)
            token_record = token_manager.get_token_record_for_account(
                ml_account_id,
                company_id,
                expected_ml_user_id=str(ml_user_id),
            )

            if not token_record or not token_record.access_token:
                logger.warning(
                    "⚠️ Nenhum token ativo encontrado para ml_account_id=%s (ml_user_id=%s)",
                    ml_account_id,
                    ml_user_id,
                )
                return None

            token_ml_user = None
            try:
                if token_record.ml_account and token_record.ml_account.ml_user_id:
                    token_ml_user = str(token_record.ml_account.ml_user_id)
            except Exception:
                token_ml_user = None

            if token_ml_user and token_ml_user != str(ml_user_id):
                logger.warning(
                    "⚠️ Token retornado pertence a ml_user_id=%s, mas esperado %s",
                    token_ml_user,
                    ml_user_id,
                )

                fallback_query = text(
                    "SELECT id FROM ml_accounts WHERE company_id = :company_id AND ml_user_id = CAST(:ml_user_id AS VARCHAR)"
                )
                fallback_account = db.execute(
                    fallback_query, {"company_id": company_id, "ml_user_id": str(ml_user_id)}
                ).fetchone()

                if fallback_account:
                    token_record = token_manager.get_token_record_for_account(
                        fallback_account[0],
                        company_id,
                        expected_ml_user_id=str(ml_user_id),
                    )
                    if not token_record or not token_record.access_token:
                        logger.error(
                            "❌ Token não encontrado para ml_user_id=%s após fallback",
                            ml_user_id,
                        )
                        return None
                else:
                    logger.error(
                        "❌ Nenhuma conta correspondente encontrada para ml_user_id=%s no company_id=%s",
                        ml_user_id,
                        company_id,
                    )
                    return None

            logger.info(
                "✅ Token válido recuperado via TokenManager (ml_account_id=%s, ml_user_id=%s)",
                ml_account_id,
                ml_user_id,
            )
            return token_record.access_token

        except Exception as e:
            logger.error(f"❌ Erro ao buscar token via TokenManager: {e}", exc_info=True)
            return None
    
    def _refresh_token_for_ml_user(self, refresh_token: str, ml_account_id: int, user_id: Optional[int], db: Session) -> Optional[str]:
        """Renova token usando refresh token para uma conta ML"""
        try:
            from app.models.saas_models import Token
            from datetime import timedelta
            from sqlalchemy import text
            from app.config.settings import Settings
            
            settings = Settings()
            
            # Dados para renovar token (usa credenciais do ambiente)
            data = {
                "grant_type": "refresh_token",
                "client_id": settings.ml_app_id,
                "client_secret": settings.ml_client_secret,
                "refresh_token": refresh_token
            }
            
            headers = {
                "accept": "application/json",
                "content-type": "application/x-www-form-urlencoded"
            }
            
            # Chamar API do ML para renovar token
            response = httpx.post(
                "https://api.mercadolibre.com/oauth/token",
                data=data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Desativar tokens antigos desta conta
                db.execute(text("""
                    UPDATE tokens 
                    SET is_active = false 
                    WHERE ml_account_id = :ml_account_id
                """), {"ml_account_id": ml_account_id})
                
                # Buscar user_id se não foi fornecido
                if not user_id:
                    user_query = text("""
                        SELECT id FROM users 
                        WHERE company_id = (SELECT company_id FROM ml_accounts WHERE id = :ml_account_id) 
                        LIMIT 1
                    """)
                    user_result = db.execute(user_query, {"ml_account_id": ml_account_id}).fetchone()
                    user_id = user_result[0] if user_result else None
                
                if not user_id:
                    logger.error(f"❌ user_id não encontrado para ml_account_id: {ml_account_id}")
                    return None
                
                # Criar novo token
                new_token = Token(
                    user_id=user_id,
                    ml_account_id=ml_account_id,
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token"),
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_in=token_data.get("expires_in", 21600),
                    scope=token_data.get("scope", ""),
                    expires_at=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 21600)),
                    is_active=True
                )
                
                db.add(new_token)
                db.commit()
                
                logger.info(f"✅ Novo token salvo para ml_account_id: {ml_account_id}")
                return token_data["access_token"]
            else:
                logger.error(f"❌ Erro ao renovar token: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao renovar token: {e}", exc_info=True)
            db.rollback()
            return None
    
    async def _extract_ml_user_id_from_order(self, order_id: str, db: Session) -> Optional[int]:
        """Extrai seller_id de um pedido (fallback quando user_id não vem na notificação)."""
        try:
            from app.services.token_manager import TokenManager

            token_manager = TokenManager(db)
            token_record = token_manager.get_any_active_token()

            if not token_record or not token_record.access_token:
                logger.error("❌ Nenhum token ativo disponível para buscar pedido %s", order_id)
                return None

            order_data = await self._fetch_order_details(order_id, token_record.access_token)
            if not order_data:
                logger.error(
                    "❌ Não foi possível buscar pedido %s para extrair seller_id",
                    order_id,
                )
                return None

            seller_id = order_data.get("seller_id") or order_data.get("sellerId")
            if seller_id:
                logger.info("✅ seller_id extraído do pedido %s: %s", order_id, seller_id)
                return int(seller_id)

            logger.error("❌ seller_id não encontrado nos dados do pedido %s", order_id)
            logger.error("📋 Campos disponíveis: %s", list(order_data.keys()))
            return None

        except Exception as e:
            logger.error(
                "❌ Erro ao extrair ml_user_id do pedido %s: %s",
                order_id,
                e,
                exc_info=True,
            )
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
                    logger.error(f"❌ Response: {response.text if hasattr(response, 'text') else 'N/A'}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Erro ao buscar detalhes do pedido: {e}")
            return None
    
    async def _get_order_from_invoice_api(self, invoice_id: str, ml_user_id: int, access_token: str) -> Optional[str]:
        """Busca order_id através do invoice_id na API do ML"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                # Endpoint para buscar invoice: GET /users/{user_id}/invoices/{invoice_id}
                response = await client.get(
                    f"{self.api_base_url}/users/{ml_user_id}/invoices/{invoice_id}",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    invoice_data = response.json()
                    # A resposta da API de invoice contém order_id ou pack_id
                    order_id = invoice_data.get("order_id") or invoice_data.get("pack_id")
                    if not order_id:
                        items = invoice_data.get("items") or invoice_data.get("documents") or []
                        if isinstance(items, dict):
                            items = items.get("results") or items.get("items") or []
                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            external_order_id = item.get("external_order_id")
                            if external_order_id:
                                order_id = external_order_id
                                logger.info(f"✅ Order ID {order_id} encontrado nos itens do invoice {invoice_id}")
                                break
                            original_item = item.get("original_item")
                            if isinstance(original_item, dict):
                                external_order_id = original_item.get("external_order_id")
                                if external_order_id:
                                    order_id = external_order_id
                                    logger.info(f"✅ Order ID {order_id} encontrado no original_item do invoice {invoice_id}")
                                    break
                    if order_id:
                        logger.info(f"✅ Order ID {order_id} encontrado no invoice {invoice_id}")
                        return str(order_id)
                    else:
                        logger.warning(f"⚠️ Invoice {invoice_id} não contém order_id ou pack_id")
                        logger.warning(f"⚠️ Dados do invoice: {invoice_data}")
                        return None
                elif response.status_code == 404:
                    logger.warning(f"⚠️ Invoice {invoice_id} não encontrado na API (404)")
                    return None
                elif response.status_code == 401:
                    logger.error(f"❌ Token inválido ao buscar invoice {invoice_id} (401 Unauthorized)")
                    return None
                elif response.status_code == 403:
                    logger.error(f"❌ Acesso negado ao buscar invoice {invoice_id} (403 Forbidden)")
                    logger.error(f"❌ Possível problema: ml_user_id {ml_user_id} não é dono deste invoice")
                    return None
                else:
                    logger.error(f"❌ Erro ao buscar invoice via API: {response.status_code}")
                    logger.error(f"❌ Response: {response.text if hasattr(response, 'text') else 'N/A'}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Exceção ao buscar invoice via API: {e}")
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
                logger.info(f"🔧 [NOTIF] ========== ATUALIZANDO PEDIDO EXISTENTE ==========")
                logger.info(f"🔧 [NOTIF] Order ID: {order_id}")
                logger.info(f"🔧 [NOTIF] Company ID: {company_id}")
                logger.info(f"🔧 [NOTIF] ID do registro no BD: {existing[0]}")
                
                # Buscar dados atuais do pedido para comparação
                current_data_query = text("""
                    SELECT status, shipping_status, shipping_type, total_amount, paid_amount, 
                           date_closed, last_updated, shipping_id, shipping_method
                    FROM ml_orders 
                    WHERE ml_order_id = :order_id AND company_id = :company_id
                """)
                current_data = db.execute(current_data_query, {"order_id": str(order_id), "company_id": company_id}).fetchone()
                
                if current_data:
                    current_status = current_data[0]
                    current_shipping_status = current_data[1]
                    current_shipping_type = current_data[2]
                    current_total = current_data[3]
                    current_paid = current_data[4]
                    current_date_closed = current_data[5]
                    current_last_updated = current_data[6]
                    current_shipping_id = current_data[7]
                    current_shipping_method = current_data[8]
                    
                    logger.info(f"📊 [NOTIF] ========== DADOS ATUAIS DO PEDIDO ==========")
                    logger.info(f"📊 [NOTIF] Status atual: {current_status}")
                    logger.info(f"📊 [NOTIF] Shipping Status atual: {current_shipping_status}")
                    logger.info(f"📊 [NOTIF] Shipping Type atual: {current_shipping_type}")
                    logger.info(f"📊 [NOTIF] Total atual: R$ {current_total}")
                    logger.info(f"📊 [NOTIF] Pago atual: R$ {current_paid}")
                    logger.info(f"📊 [NOTIF] Data fechamento atual: {current_date_closed}")
                    logger.info(f"📊 [NOTIF] Last Updated atual: {current_last_updated}")
                    logger.info(f"📊 [NOTIF] Shipping ID atual: {current_shipping_id}")
                    logger.info(f"📊 [NOTIF] Shipping Method atual: {current_shipping_method}")
                else:
                    logger.warning(f"⚠️ [NOTIF] Não foi possível buscar dados atuais do pedido")
                
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
                
                # Calcular valores novos para comparação
                new_paid_amount = payments[0].get("total_paid_amount") if payments else 0
                new_shipping_cost = shipping.get("cost", 0) if shipping else 0
                new_date_closed = order_data.get("date_closed")
                new_last_updated = order_data.get("last_updated")
                
                # Log detalhado para debug - DADOS DA API
                logger.info(f"🌐 [NOTIF] ========== DADOS RECEBIDOS DA API DO ML ==========")
                logger.info(f"🌐 [NOTIF] Order Status (API): '{api_status}'")
                if shipment_substatus:
                    logger.info(f"🌐 [NOTIF] Substatus (fulfillment): '{shipment_substatus}'")
                logger.info(f"🌐 [NOTIF] Shipping Status (API): '{shipping_status}'")
                logger.info(f"🌐 [NOTIF] Shipping ID: {shipping_id}")
                if logistic_type:
                    logger.info(f"🌐 [NOTIF] Logistics Type: '{logistic_type}'")
                logger.info(f"🌐 [NOTIF] Shipping Method: {shipping_method}")
                logger.info(f"🌐 [NOTIF] Date Created (shipment): {shipping_date}")
                logger.info(f"🌐 [NOTIF] Estimated Delivery: {estimated_delivery_date}")
                logger.info(f"🌐 [NOTIF] Date Closed: {new_date_closed}")
                logger.info(f"🌐 [NOTIF] Last Updated: {new_last_updated}")
                logger.info(f"🌐 [NOTIF] Total Amount: R$ {total_amount}")
                logger.info(f"🌐 [NOTIF] Paid Amount: R$ {new_paid_amount}")
                logger.info(f"🌐 [NOTIF] Shipping Cost: R$ {new_shipping_cost}")
                
                # Log de mapeamento de status
                logger.info(f"🔄 [NOTIF] ========== MAPEAMENTO DE STATUS ==========")
                if shipment_substatus:
                    logger.info(f"🔄 [NOTIF] Substatus '{shipment_substatus}' -> DB Status: '{substatus_db_status}'")
                logger.info(f"🔄 [NOTIF] Shipping Status '{shipping_status}' -> DB Status: '{shipping_db_status}'")
                logger.info(f"🔄 [NOTIF] Order Status '{api_status}' -> DB Status: '{order_db_status}'")
                logger.info(f"🔄 [NOTIF] 🎯 Status Final Calculado: '{db_status}'")
                
                # Comparação com dados atuais
                if current_data:
                    logger.info(f"📊 [NOTIF] ========== COMPARAÇÃO: ANTES vs DEPOIS ==========")
                    status_changed = current_status != db_status
                    shipping_status_changed = current_shipping_status != shipping_status
                    shipping_type_changed = current_shipping_type != logistic_type
                    total_changed = current_total != total_amount
                    paid_changed = current_paid != new_paid_amount
                    date_closed_changed = current_date_closed != new_date_closed
                    shipping_id_changed = current_shipping_id != str(shipping_id) if shipping_id else False
                    shipping_method_changed = current_shipping_method != shipping_method
                    
                    logger.info(f"📊 [NOTIF] Status: '{current_status}' -> '{db_status}' {'✅ MUDOU' if status_changed else '➡️ IGUAL'}")
                    logger.info(f"📊 [NOTIF] Shipping Status: '{current_shipping_status}' -> '{shipping_status}' {'✅ MUDOU' if shipping_status_changed else '➡️ IGUAL'}")
                    logger.info(f"📊 [NOTIF] Shipping Type: '{current_shipping_type}' -> '{logistic_type}' {'✅ MUDOU' if shipping_type_changed else '➡️ IGUAL'}")
                    logger.info(f"📊 [NOTIF] Total: R$ {current_total} -> R$ {total_amount} {'✅ MUDOU' if total_changed else '➡️ IGUAL'}")
                    logger.info(f"📊 [NOTIF] Pago: R$ {current_paid} -> R$ {new_paid_amount} {'✅ MUDOU' if paid_changed else '➡️ IGUAL'}")
                    logger.info(f"📊 [NOTIF] Date Closed: {current_date_closed} -> {new_date_closed} {'✅ MUDOU' if date_closed_changed else '➡️ IGUAL'}")
                    logger.info(f"📊 [NOTIF] Shipping ID: {current_shipping_id} -> {shipping_id} {'✅ MUDOU' if shipping_id_changed else '➡️ IGUAL'}")
                    logger.info(f"📊 [NOTIF] Shipping Method: {current_shipping_method} -> {shipping_method} {'✅ MUDOU' if shipping_method_changed else '➡️ IGUAL'}")
                    
                    if status_changed:
                        logger.info(f"🔄 [NOTIF] ⚠️ ATENÇÃO: Status do pedido mudou de '{current_status}' para '{db_status}'")
                    else:
                        logger.info(f"ℹ️ [NOTIF] Status do pedido permaneceu '{db_status}' (sem mudanças)")
                
                import json
                
                logger.info(f"💾 [NOTIF] ========== EXECUTANDO UPDATE NO BANCO ==========")
                logger.info(f"💾 [NOTIF] Query preparada com os seguintes valores:")
                logger.info(f"💾 [NOTIF]   - status: '{db_status}'")
                logger.info(f"💾 [NOTIF]   - shipping_status: '{shipping_status}'")
                logger.info(f"💾 [NOTIF]   - shipping_type: '{logistic_type}'")
                logger.info(f"💾 [NOTIF]   - total_amount: R$ {total_amount}")
                logger.info(f"💾 [NOTIF]   - paid_amount: R$ {new_paid_amount}")
                logger.info(f"💾 [NOTIF]   - shipping_id: {shipping_id}")
                
                result = db.execute(update_query, {
                    "order_id": str(order_id),
                    "company_id": company_id,
                    "status": db_status,
                    "status_detail": order_data.get("status_detail", {}).get("code") if order_data.get("status_detail") else None,
                    "date_closed": order_data.get("date_closed"),
                    "last_updated": order_data.get("last_updated"),
                    "total_amount": total_amount,
                    "paid_amount": new_paid_amount,
                    "shipping_cost": new_shipping_cost,
                    "shipping_type": logistic_type,
                    "shipping_status": shipping_status,
                    "shipping_id": str(shipping_id) if shipping_id else None,
                    "shipping_method": shipping_method,
                    "shipping_date": shipping_date,
                    "estimated_delivery_date": estimated_delivery_date,
                    "shipping_details": json.dumps(shipment_data_json) if shipment_data_json else None,
                    "payments": json.dumps(payments) if payments else None
                })
                
                rows_affected = result.rowcount
                logger.info(f"💾 [NOTIF] UPDATE executado. Linhas afetadas: {rows_affected}")
                
                if rows_affected == 0:
                    logger.warning(f"⚠️ [NOTIF] ATENÇÃO: Nenhuma linha foi atualizada! Verifique se o pedido existe no banco.")
                elif rows_affected > 1:
                    logger.warning(f"⚠️ [NOTIF] ATENÇÃO: Múltiplas linhas foram atualizadas ({rows_affected})! Isso não deveria acontecer.")
                else:
                    logger.info(f"✅ [NOTIF] UPDATE executado com sucesso! 1 linha atualizada.")
                
                # IMPORTANTE: Fazer commit da atualização
                logger.info(f"💾 [NOTIF] ========== REALIZANDO COMMIT ==========")
                try:
                    db.commit()
                    logger.info(f"✅ [NOTIF] ✅ COMMIT REALIZADO COM SUCESSO para pedido {order_id}")
                    logger.info(f"✅ [NOTIF] Status atualizado para: '{db_status}'")
                    
                    # Verificar se o commit realmente persistiu os dados
                    verify_query = text("""
                        SELECT status, shipping_status, shipping_type, total_amount, paid_amount, updated_at
                        FROM ml_orders 
                        WHERE ml_order_id = :order_id AND company_id = :company_id
                    """)
                    verify_data = db.execute(verify_query, {"order_id": str(order_id), "company_id": company_id}).fetchone()
                    
                    if verify_data:
                        verified_status = verify_data[0]
                        verified_shipping_status = verify_data[1]
                        verified_shipping_type = verify_data[2]
                        verified_total = verify_data[3]
                        verified_paid = verify_data[4]
                        verified_updated_at = verify_data[5]
                        
                        logger.info(f"✅ [NOTIF] ========== VERIFICAÇÃO PÓS-COMMIT ==========")
                        logger.info(f"✅ [NOTIF] Status no BD: '{verified_status}' {'✅ CORRETO' if verified_status == db_status else '❌ DIFERENTE'}")
                        logger.info(f"✅ [NOTIF] Shipping Status no BD: '{verified_shipping_status}' {'✅ CORRETO' if verified_shipping_status == shipping_status else '❌ DIFERENTE'}")
                        logger.info(f"✅ [NOTIF] Shipping Type no BD: '{verified_shipping_type}' {'✅ CORRETO' if verified_shipping_type == logistic_type else '❌ DIFERENTE'}")
                        logger.info(f"✅ [NOTIF] Total no BD: R$ {verified_total} {'✅ CORRETO' if verified_total == total_amount else '❌ DIFERENTE'}")
                        logger.info(f"✅ [NOTIF] Pago no BD: R$ {verified_paid} {'✅ CORRETO' if verified_paid == new_paid_amount else '❌ DIFERENTE'}")
                        logger.info(f"✅ [NOTIF] Updated At: {verified_updated_at}")
                        
                        if verified_status == db_status:
                            logger.info(f"✅ [NOTIF] ✅✅✅ CONFIRMADO: Status foi atualizado corretamente no banco de dados!")
                        else:
                            logger.error(f"❌ [NOTIF] ❌❌❌ ERRO: Status no BD ('{verified_status}') não corresponde ao esperado ('{db_status}')!")
                    else:
                        logger.error(f"❌ [NOTIF] ❌ ERRO: Não foi possível verificar os dados após o commit!")
                        
                except Exception as commit_error:
                    logger.error(f"❌ [NOTIF] ❌❌❌ ERRO AO FAZER COMMIT: {commit_error}")
                    logger.error(f"❌ [NOTIF] Tipo do erro: {type(commit_error).__name__}")
                    logger.error(f"❌ [NOTIF] Traceback:", exc_info=True)
                    db.rollback()
                    logger.error(f"❌ [NOTIF] Rollback realizado devido ao erro no commit")
                    raise
                
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
                        
                        # ✅ NOVO: Verificar nota fiscal após criar pedido (se status for PAID/CONFIRMED)
                        order_status = order_data.get("status", "").lower()
                        if order_status in ["paid", "confirmed"]:
                            logger.info(f"🧾 Verificando nota fiscal para pedido recém-criado {order_id}")
                            await self._check_invoice_for_order(order_id, company_id, db)
                    else:
                        error_msg = f"MLAccount não encontrada para company_id {company_id}"
                        logger.warning(f"⚠️ {error_msg}")
                        raise Exception(error_msg)
                
                except Exception as e:
                    from sqlalchemy.exc import IntegrityError
                    
                    # Se for erro de chave duplicada, tentar atualizar o pedido existente
                    if isinstance(e, IntegrityError) and "duplicate key" in str(e).lower():
                        logger.warning(f"⚠️ Pedido {order_id} já existe (erro de chave duplicada), tentando atualizar...")
                        db.rollback()
                        
                        try:
                            # Buscar o pedido existente e atualizar
                            from app.models.saas_models import MLOrder as MLOrderModel
                            from sqlalchemy import text
                            
                            existing = db.query(MLOrderModel).filter(
                                MLOrderModel.ml_order_id == str(order_id),
                                MLOrderModel.company_id == company_id
                            ).first()
                            
                            if existing:
                                logger.info(f"🔄 Pedido {order_id} encontrado, atualizando via webhook")
                                
                                # Usar a mesma lógica de atualização do bloco "if existing_order"
                                orders_service = MLOrdersService(db)
                                result = orders_service._save_order_to_database(order_data, ml_account.id, company_id)
                                
                                db.commit()
                                logger.info(f"✅ Pedido {order_id} atualizado com sucesso após erro de chave duplicada")
                                
                                # Verificar nota fiscal
                                order_status = order_data.get("status", "").lower()
                                if order_status in ["paid", "confirmed"]:
                                    await self._check_invoice_for_order(order_id, company_id, db)
                            else:
                                logger.error(f"❌ Pedido {order_id} não encontrado após erro de chave duplicada")
                                raise
                        except Exception as retry_error:
                            logger.error(f"❌ Erro ao tentar atualizar pedido {order_id} após chave duplicada: {retry_error}")
                            db.rollback()
                            raise
                    else:
                        logger.error(f"❌ Erro ao criar pedido {order_id} via webhook: {e}", exc_info=True)
                        db.rollback()
                        raise
            
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
                SELECT id, ml_order_id, pack_id, shipping_id, invoice_emitted, ml_account_id, seller_id
                FROM ml_orders 
                WHERE ml_order_id = :order_id AND company_id = :company_id
            """)
            
            order_result = db.execute(order_query, {"order_id": str(order_id), "company_id": company_id}).fetchone()
            
            if not order_result:
                logger.warning(f"⚠️ Pedido {order_id} não encontrado para verificação de NF")
                return
            
            order_db_id, ml_order_id, pack_id, shipping_id, current_invoice_status, ml_account_id, seller_id = order_result
            
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
            
            # Prioridade: order_id -> pack_id -> shipment_id (mesma estratégia do serviço)
            invoice_data = None
            
            logger.info(f"🔍 [AUTO-NF] Buscando NF por order_id {order_id}")
            invoice_data = shipment_service._check_order_invoice(
                order_id=str(order_id),
                company_id=company_id,
                access_token=access_token,
                seller_id=seller_id,
                ml_account_id=ml_account_id
            )
            
            if (not invoice_data or not invoice_data.get('has_invoice')) and pack_id:
                logger.info(f"🔍 [AUTO-NF] Buscando NF pelo pack_id {pack_id} para pedido {order_id}")
                invoice_data = shipment_service._check_pack_invoice(pack_id, access_token)
            
            if (not invoice_data or not invoice_data.get('has_invoice')) and shipping_id:
                logger.info(f"🔍 [AUTO-NF] Buscando NF pelo shipping_id {shipping_id} para pedido {order_id} (fulfillment)")
                invoice_data = shipment_service._check_shipment_invoice(
                    shipment_id=shipping_id,
                    company_id=company_id,
                    access_token=access_token,
                    seller_id=seller_id,
                    ml_account_id=ml_account_id
                )
            
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
    
    async def _process_invoice_notification(self, resource: str, ml_user_id: int, company_id: int, db: Session):
        """
        Processa notificação de nota fiscal (invoices)
        Quando o ML notifica que uma NF foi emitida ou atualizada
        """
        try:
            logger.info(f"🧾 ========== PROCESSANDO NOTIFICAÇÃO DE NOTA FISCAL ==========")
            logger.info(f"🧾 Resource: {resource}")
            logger.info(f"🧾 ML User ID: {ml_user_id}")
            logger.info(f"🧾 Company ID: {company_id}")
            
            # O resource geralmente vem no formato:
            # /orders/{order_id}/invoice ou /packs/{pack_id}/invoice
            # Também pode vir como: /users/{user_id}/invoices/{invoice_id}
            
            # Extrair order_id ou pack_id do resource
            parts = resource.split("/")
            
            order_id = None
            pack_id = None
            invoice_id = None
            
            if "orders" in parts:
                # Formato: /orders/123456/invoice
                order_index = parts.index("orders")
                if len(parts) > order_index + 1:
                    order_id = parts[order_index + 1]
            
            elif "packs" in parts:
                # Formato: /packs/123456/invoice
                pack_index = parts.index("packs")
                if len(parts) > pack_index + 1:
                    pack_id = parts[pack_index + 1]
                    
                    # Buscar order_id pelo pack_id
                    from sqlalchemy import text
                    pack_query = text("""
                        SELECT ml_order_id 
                        FROM ml_orders 
                        WHERE pack_id = :pack_id AND company_id = :company_id
                        LIMIT 1
                    """)
                    
                    result = db.execute(pack_query, {
                        "pack_id": str(pack_id),
                        "company_id": company_id
                    }).fetchone()
                    
                    if result:
                        order_id = result[0]
                        logger.info(f"🧾 Pack ID {pack_id} corresponde ao Order ID {order_id}")
            
            elif "invoices" in parts:
                # Formato: /users/{user_id}/invoices/{invoice_id}
                invoice_index = parts.index("invoices")
                if len(parts) > invoice_index + 1:
                    invoice_id = parts[invoice_index + 1]
                    logger.info(f"🧾 Invoice ID detectado: {invoice_id}")
                    
                    # Buscar order_id pelo invoice_id no banco
                    from sqlalchemy import text
                    invoice_query = text("""
                        SELECT ml_order_id 
                        FROM ml_orders 
                        WHERE invoice_number = :invoice_id 
                        AND company_id = :company_id
                        LIMIT 1
                    """)
                    
                    result = db.execute(invoice_query, {
                        "invoice_id": str(invoice_id),
                        "company_id": company_id
                    }).fetchone()
                    
                    if result:
                        order_id = result[0]
                        logger.info(f"🧾 Invoice ID {invoice_id} corresponde ao Order ID {order_id}")
                    else:
                        # Se não encontrou pelo invoice_number, buscar pela API do ML
                        logger.info(f"🔍 Buscando order_id do invoice {invoice_id} via API do ML...")
                        token = self._get_user_token_by_company(company_id, db)
                        if token:
                            order_id = await self._get_order_from_invoice_api(invoice_id, ml_user_id, token)
                            if order_id:
                                logger.info(f"✅ Order ID {order_id} obtido via API do ML para invoice {invoice_id}")
                        
                        if not order_id:
                            logger.warning(f"⚠️ Não foi possível encontrar pedido para invoice {invoice_id}. Notificação será ignorada.")
                            return
            
            if not order_id:
                logger.warning(f"⚠️ Não foi possível extrair order_id do resource: {resource}")
                return
            
            logger.info(f"🧾 Verificando nota fiscal para pedido: {order_id}")
            
            # Chamar a função existente para verificar e atualizar a NF
            await self._check_invoice_for_order(order_id, company_id, db)
            
            logger.info(f"✅ Notificação de nota fiscal processada para pedido {order_id}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar notificação de nota fiscal: {e}", exc_info=True)
            raise
    
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
            
            # ⚡ Mapear status da API ML (minúsculas) para enum do banco (MAIÚSCULAS)
            status_mapping = {
                "active": "ACTIVE",
                "paused": "PAUSED",
                "closed": "CLOSED",
                "under_review": "UNDER_REVIEW",
                "inactive": "INACTIVE"
            }
            
            api_status = item_data.get("status", "active")
            db_status = status_mapping.get(api_status, "ACTIVE")
            
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
                    "status": db_status
                })
                
                db.commit()
                logger.info(f"✅ Produto {item_id} atualizado")
            else:
                logger.info(f"ℹ️ Produto {item_id} não existe no banco, será sincronizado na próxima sync completa")
                
        except Exception as e:
            logger.error(f"❌ Erro ao salvar produto: {e}")
            db.rollback()

