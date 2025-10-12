"""
Rotas para receber notificações (webhooks) do Mercado Livre
"""
from fastapi import APIRouter, Request, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import logging

from app.config.database import get_db
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
        
        # Retornar 200 imediatamente (dentro de 500ms conforme documentação ML)
        # O processamento será feito em background
        background_tasks.add_task(
            notifications_controller.process_notification,
            notification_data,
            db
        )
        
        return JSONResponse(
            status_code=200,
            content={"status": "received", "message": "Notificação recebida com sucesso"}
        )
        
    except Exception as e:
        logger.error(f"❌ Erro ao receber notificação: {e}")
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

