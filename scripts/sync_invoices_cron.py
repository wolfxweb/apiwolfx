#!/usr/bin/env python3
"""
Script para rodar via cron (background)
Sincroniza pedidos antigos automaticamente
"""
import sys
sys.path.insert(0, '.')

from app.config.database import SessionLocal
from app.models.saas_models import Token, MLAccount, MLOrder
from app.services.shipment_service import ShipmentService
from datetime import datetime, timedelta
import time
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def sync_invoices_cron(batches_per_run=5, batch_size=50):
    """Sincroniza TODAS as notas fiscais pendentes periodicamente"""
    
    db = SessionLocal()
    
    try:
        account = db.query(MLAccount).filter(MLAccount.company_id == 15).first()
        token = db.query(Token).filter(
            Token.ml_account_id == account.id, 
            Token.is_active == True
        ).first()
        
        if not token:
            logger.error("Token não encontrado")
            return
        
        access_token = token.access_token
        service = ShipmentService(db)
        
        total_updated = 0
        
        for batch_num in range(batches_per_run):
            orders = db.query(MLOrder).filter(
                MLOrder.company_id == 15,
                MLOrder.invoice_emitted == False  # Todos os pedidos sem nota fiscal
            ).limit(batch_size).all()
            
            if not orders:
                logger.info("Todos os pedidos foram processados!")
                break
            
            for order in orders:
                try:
                    result = service.sync_single_order_invoice(
                        order.ml_order_id, 15, access_token
                    )
                    if result.get('success') and result.get('invoice_updated'):
                        total_updated += 1
                except Exception as e:
                    logger.error(f"Erro no pedido {order.ml_order_id}: {e}")
            
            db.commit()
            time.sleep(1)
        
        logger.info(f"✅ Sincronizados {total_updated} pedidos nesta execução")
        
    except Exception as e:
        logger.error(f"Erro geral: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    sync_invoices_cron()
