"""
Rotas para receber notificações (webhooks) do Mercado Livre
"""
from fastapi import APIRouter, Request, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import logging
import copy
import json
from starlette.requests import ClientDisconnect

from app.config.database import get_db, SessionLocal
from app.controllers.ml_notifications_controller import MLNotificationsController

logger = logging.getLogger(__name__)

# Router para notificações
ml_notifications_router = APIRouter()

# Instância do controller
notifications_controller = MLNotificationsController()

@ml_notifications_router.post("/notifications")
async def receive_ml_notification(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Endpoint para receber notificações (webhooks) do Mercado Livre
    
    Tipos de notificações suportadas:
    - orders_v2: Pedidos criados ou atualizados
    - items: Produtos criados ou atualizados
    - messages: Mensagens recebidas
    - questions: Perguntas recebidas
    - payments: Pagamentos criados ou atualizados
    - shipments: Envios criados ou atualizados
    - claims: Reclamações
    """
    try:
        # Obter dados da notificação
        try:
            notification_data = await request.json()
        except ClientDisconnect:
            logger.warning("⚠️ ClientDisconnect: corpo da notificação ausente. Retornando 200 para evitar reenvio.")
            return JSONResponse(
                status_code=200,
                content={"status": "received", "message": "Notificação recebida sem corpo"}
            )
        
        topic = notification_data.get('topic')
        resource = notification_data.get('resource')
        notification_id = notification_data.get('_id')
        
        # Segundo a documentação do ML, o campo principal é 'user_id' que identifica o vendedor
        # Documentação: https://developers.mercadolivre.com.br/pt_br/recebendo-notificacoes
        ml_user_id = notification_data.get('user_id')
        
        logger.info(f"📬 ========== NOTIFICAÇÃO RECEBIDA DO ML ==========")
        logger.info(f"📬 Topic: {topic}")
        logger.info(f"📬 Resource: {resource}")
        logger.info(f"📬 User ID (ml_user_id): {ml_user_id} (tipo: {type(ml_user_id)})")
        logger.info(f"📬 Application ID: {notification_data.get('application_id')}")
        logger.info(f"📬 Notification ID: {notification_id}")
        logger.info(f"📬 Todos os campos da notificação: {list(notification_data.keys())}")
        logger.info(f"📬 Dados completos: {json.dumps(notification_data, indent=2, default=str)}")
        
        # Segundo a documentação, se user_id não vier, devemos buscar do pedido via API
        # GET /orders/{ORDER_ID} para obter o seller_id
        if ml_user_id is None and topic == "orders_v2" and resource:
            logger.warning(f"⚠️ user_id não encontrado na notificação (campo padrão do ML)")
            logger.warning(f"⚠️ Segundo a documentação, vamos buscar do pedido via resource: {resource}")
            logger.warning(f"⚠️ A notificação será processada, mas o user_id será extraído do pedido")
        elif ml_user_id is None:
            error_msg = "user_id não encontrado na notificação e não é possível extrair do resource (topic não é orders_v2)"
            logger.error(f"❌ ERRO CRÍTICO: {error_msg}")
            logger.error(f"❌ Dados recebidos: {json.dumps(notification_data, indent=2, default=str)}")
            # Mesmo com erro, retornar 200 para evitar reenvios
            return JSONResponse(
                status_code=200,
                content={"status": "error", "message": error_msg}
            )
        
        # IMPORTANTE: Criar cópia dos dados e nova sessão no background
        # para evitar problemas com sessão fechada antes do processamento terminar
        notification_data_copy = copy.deepcopy(notification_data)
        
        def process_in_background(notification_data_copy):
            """Processa notificação em background com nova sessão"""
            import asyncio
            db_background = SessionLocal()
            topic_bg = notification_data_copy.get('topic')
            resource_bg = notification_data_copy.get('resource')
            ml_user_id_bg = notification_data_copy.get('user_id')
            
            try:
                logger.info(f"🔄 ========== INICIANDO PROCESSAMENTO EM BACKGROUND ==========")
                logger.info(f"🔄 Topic: {topic_bg}")
                logger.info(f"🔄 Resource: {resource_bg}")
                logger.info(f"🔄 ML User ID: {ml_user_id_bg} (tipo: {type(ml_user_id_bg)})")
                
                # Criar novo event loop se necessário
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Executar função assíncrona
                logger.info(f"🔄 Chamando process_notification...")
                loop.run_until_complete(
                    notifications_controller.process_notification(notification_data_copy, db_background)
                )
                logger.info(f"✅ ========== NOTIFICAÇÃO PROCESSADA COM SUCESSO ==========")
                logger.info(f"✅ Topic: {topic_bg}, Resource: {resource_bg}")
            except Exception as e:
                logger.error(f"❌ ========== ERRO NO PROCESSAMENTO EM BACKGROUND ==========")
                logger.error(f"❌ Topic: {topic_bg}")
                logger.error(f"❌ Resource: {resource_bg}")
                logger.error(f"❌ ML User ID: {ml_user_id_bg}")
                logger.error(f"❌ Erro: {str(e)}")
                logger.error(f"❌ Tipo da exceção: {type(e).__name__}")
                logger.error(f"❌ Traceback completo:", exc_info=True)
                logger.error(f"❌ Dados da notificação que falhou: {json.dumps(notification_data_copy, indent=2, default=str)}")
            finally:
                db_background.close()
                logger.info(f"🔒 Sessão do banco fechada para notificação: topic={topic_bg}")
        
        # Retornar 200 imediatamente (dentro de 500ms conforme documentação ML)
        # O processamento será feito em background
        background_tasks.add_task(
            process_in_background,
            notification_data_copy
        )
        
        return JSONResponse(
            status_code=200,
            content={"status": "received", "message": "Notificação recebida com sucesso"}
        )
        
    except Exception as e:
        logger.error(f"❌ Erro ao receber notificação: {e}", exc_info=True)
        # Mesmo com erro, retornar 200 para evitar reenvios
        return JSONResponse(
            status_code=200,
            content={"status": "error", "message": str(e)}
        )

@ml_notifications_router.post("/notification")
async def receive_ml_notification_singular(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Endpoint alternativo para /api/notification (sem 's')
    Redireciona para a função principal de notificações
    """
    return await receive_ml_notification(request, background_tasks, db)

@ml_notifications_router.get("/notifications/test")
async def test_notifications_endpoint():
    """Endpoint de teste para verificar se as notificações estão funcionando"""
    return {
        "status": "ok",
        "message": "Endpoint de notificações funcionando",
        "url": "/api/notifications",
        "url_alternativa": "/api/notification",
        "method": "POST"
    }

