#!/usr/bin/env python3
"""
Script manual para sincronizar notas fiscais em lotes
Uso: python scripts/sync_invoices_manual.py
"""
import sys
sys.path.insert(0, '.')

from app.config.database import SessionLocal
from app.models.saas_models import Token, MLAccount, MLOrder
from app.services.shipment_service import ShipmentService
from datetime import datetime, timedelta
import time

def sync_invoices_batch(batch_size=50, max_batches=40):
    """Sincroniza notas fiscais em lotes pequenos"""
    
    db = SessionLocal()
    
    try:
        # Buscar token
        account = db.query(MLAccount).filter(MLAccount.company_id == 15).first()
        token = db.query(Token).filter(
            Token.ml_account_id == account.id, 
            Token.is_active == True
        ).first()
        
        if not token:
            print("❌ Token não encontrado")
            return
        
        access_token = token.access_token
        service = ShipmentService(db)
        
        # Buscar pedidos antigos sem NF
        cutoff_date = datetime.now() - timedelta(days=15)
        total_to_sync = db.query(MLOrder).filter(
            MLOrder.company_id == 15,
            MLOrder.date_created < cutoff_date,
            MLOrder.invoice_emitted == False
        ).count()
        
        print(f"📊 Total de pedidos para sincronizar: {total_to_sync}")
        print(f"🔄 Processando em lotes de {batch_size}...")
        
        total_updated = 0
        total_errors = 0
        
        for batch_num in range(max_batches):
            # Buscar lote de pedidos
            orders = db.query(MLOrder).filter(
                MLOrder.company_id == 15,
                MLOrder.date_created < cutoff_date,
                MLOrder.invoice_emitted == False
            ).limit(batch_size).all()
            
            if not orders:
                print(f"✅ Todos os pedidos foram processados!")
                break
            
            print(f"\n--- Lote {batch_num + 1} ({len(orders)} pedidos) ---")
            
            batch_updated = 0
            batch_errors = 0
            
            for order in orders:
                try:
                    result = service.sync_single_order_invoice(
                        order.ml_order_id, 15, access_token
                    )
                    if result.get('success') and result.get('invoice_updated'):
                        batch_updated += 1
                except Exception as e:
                    batch_errors += 1
                    print(f"❌ Erro no pedido {order.ml_order_id}: {e}")
            
            total_updated += batch_updated
            total_errors += batch_errors
            
            print(f"✅ Lote concluído: {batch_updated} atualizados, {batch_errors} erros")
            
            # Commit após cada lote
            try:
                db.commit()
            except Exception as e:
                print(f"⚠️ Erro no commit: {e}")
                db.rollback()
            
            # Pausa entre lotes
            time.sleep(2)
        
        print(f"\n{'='*60}")
        print(f"📈 RESUMO FINAL")
        print(f"{'='*60}")
        print(f"Total atualizados: {total_updated}")
        print(f"Total erros: {total_errors}")
        print(f"Pedidos restantes: {total_to_sync - total_updated - total_errors}")
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == '__main__':
    sync_invoices_batch()
