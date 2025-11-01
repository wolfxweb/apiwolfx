"""
Rotas para receber notificações (webhooks) do Mercado Livre
"""
from fastapi import APIRouter, Request, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import logging
import copy

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
        notification_data = await request.json()
        
        logger.info(f"📬 Notificação recebida do ML: {notification_data.get('topic')} - {notification_data.get('resource')}")
        
        # IMPORTANTE: Criar cópia dos dados e nova sessão no background
        # para evitar problemas com sessão fechada antes do processamento terminar
        notification_data_copy = copy.deepcopy(notification_data)
        
        def process_in_background(notification_data_copy):
            """Processa notificação em background com nova sessão"""
            import asyncio
            db_background = SessionLocal()
            try:
                # Criar novo event loop se necessário
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Executar função assíncrona
                loop.run_until_complete(
                    notifications_controller.process_notification(notification_data_copy, db_background)
                )
                logger.info(f"✅ Notificação processada com sucesso: {notification_data_copy.get('topic')}")
            except Exception as e:
                logger.error(f"❌ Erro no processamento em background: {e}", exc_info=True)
            finally:
                db_background.close()
        
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

@ml_notifications_router.get("/notifications/test")
async def test_notifications_endpoint():
    """Endpoint de teste para verificar se as notificações estão funcionando"""
    return {
        "status": "ok",
        "message": "Endpoint de notificações funcionando",
        "url": "/api/notifications",
        "method": "POST"
    }

