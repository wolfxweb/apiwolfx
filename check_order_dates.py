#!/usr/bin/env python3
"""
Verificar campos de data disponíveis nos pedidos
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from sqlalchemy import text
import json

def check_order_dates():
    """Verificar campos de data disponíveis nos pedidos"""
    print("🔍 Verificando Campos de Data dos Pedidos")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Buscar alguns pedidos para analisar as datas
        result = db.execute(text("""
            SELECT 
                ml_order_id,
                order_id,
                status,
                date_created,
                date_closed,
                last_updated,
                payments,
                total_amount,
                paid_amount
            FROM ml_orders 
            WHERE company_id = :company_id
            ORDER BY date_created DESC
            LIMIT 5
        """), {"company_id": company_id})
        
        orders = result.fetchall()
        
        print(f"📊 Encontrados {len(orders)} pedidos para análise")
        print()
        
        for i, order in enumerate(orders, 1):
            print(f"📦 Pedido {i}: {order.ml_order_id}")
            print(f"   🆔 Order ID: {order.order_id}")
            print(f"   📊 Status: {order.status}")
            print(f"   📅 Date Created: {order.date_created}")
            print(f"   📅 Date Closed: {order.date_closed}")
            print(f"   📅 Last Updated: {order.last_updated}")
            print(f"   💰 Total Amount: R$ {order.total_amount}")
            print(f"   💰 Paid Amount: R$ {order.paid_amount}")
            
            # Analisar payments JSON
            if order.payments:
                try:
                    payments_data = json.loads(order.payments) if isinstance(order.payments, str) else order.payments
                    if isinstance(payments_data, list) and len(payments_data) > 0:
                        payment = payments_data[0]  # Primeiro pagamento
                        print(f"   💳 Payment Data:")
                        print(f"      Status: {payment.get('status', 'N/A')}")
                        print(f"      Date Created: {payment.get('date_created', 'N/A')}")
                        print(f"      Date Approved: {payment.get('date_approved', 'N/A')}")
                        print(f"      Date Last Modified: {payment.get('date_last_modified', 'N/A')}")
                        print(f"      Transaction Amount: {payment.get('transaction_amount', 'N/A')}")
                    else:
                        print(f"   💳 Payment Data: {payments_data}")
                except Exception as e:
                    print(f"   💳 Payment Data: Erro ao parsear - {e}")
            else:
                print(f"   💳 Payment Data: N/A")
            
            print()
        
        # Verificar se há diferenças significativas entre as datas
        print("📊 Análise de Diferenças de Data:")
        print("-" * 40)
        
        result = db.execute(text("""
            SELECT 
                COUNT(*) as total_orders,
                COUNT(CASE WHEN date_created IS NOT NULL THEN 1 END) as with_date_created,
                COUNT(CASE WHEN date_closed IS NOT NULL THEN 1 END) as with_date_closed,
                COUNT(CASE WHEN last_updated IS NOT NULL THEN 1 END) as with_last_updated,
                AVG(EXTRACT(EPOCH FROM (date_closed - date_created))/3600) as avg_hours_created_to_closed,
                AVG(EXTRACT(EPOCH FROM (last_updated - date_created))/3600) as avg_hours_created_to_updated
            FROM ml_orders 
            WHERE company_id = :company_id
        """), {"company_id": company_id})
        
        stats = result.fetchone()
        
        print(f"   📦 Total Pedidos: {stats.total_orders}")
        print(f"   📅 Com Date Created: {stats.with_date_created}")
        print(f"   📅 Com Date Closed: {stats.with_date_closed}")
        print(f"   📅 Com Last Updated: {stats.with_last_updated}")
        print(f"   ⏱️  Média Created → Closed: {stats.avg_hours_created_to_closed:.1f} horas")
        print(f"   ⏱️  Média Created → Updated: {stats.avg_hours_created_to_updated:.1f} horas")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def main():
    """Função principal"""
    print("🔍 Verificando Campos de Data dos Pedidos")
    print("=" * 60)
    print()
    
    success = check_order_dates()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ANÁLISE DE DATAS CONCLUÍDA!")
    else:
        print("❌ Erro na análise!")

if __name__ == "__main__":
    main()
