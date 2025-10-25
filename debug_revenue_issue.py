#!/usr/bin/env python3
"""
Debug do problema de receita zerada
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from sqlalchemy import text
from datetime import datetime
import json

def debug_revenue_issue():
    """Debug do problema de receita zerada"""
    print("🔍 Debug do Problema de Receita Zerada")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Teste 1: Verificar se a consulta SQL está funcionando
        print("📊 Teste 1: Verificar consulta SQL")
        print("-" * 40)
        
        result = db.execute(text("""
            SELECT 
                COUNT(*) as total_orders,
                SUM(total_amount) as total_revenue,
                AVG(total_amount) as avg_amount
            FROM ml_orders 
            WHERE company_id = :company_id
            AND status IN ('PAID', 'CONFIRMED', 'SHIPPED', 'DELIVERED')
            AND payments IS NOT NULL
            AND payments::text != '[]'
            AND payments::text != '{}'
            AND (
                (payments->0->>'date_approved')::timestamp AT TIME ZONE 'UTC-4' >= :start_date
                AND (payments->0->>'date_approved')::timestamp AT TIME ZONE 'UTC-4' <= :end_date
            )
        """), {
            "company_id": company_id,
            "start_date": datetime(2025, 10, 1),
            "end_date": datetime(2025, 10, 31, 23, 59, 59)
        })
        
        data = result.fetchone()
        print(f"   📦 Total Pedidos: {data.total_orders}")
        print(f"   💰 Receita Total: R$ {float(data.total_revenue or 0):.2f}")
        print(f"   💳 Valor Médio: R$ {float(data.avg_amount or 0):.2f}")
        
        # Teste 2: Verificar alguns pedidos específicos
        print(f"\n📊 Teste 2: Verificar pedidos específicos")
        print("-" * 40)
        
        result2 = db.execute(text("""
            SELECT 
                ml_order_id,
                status,
                total_amount,
                date_created,
                payments
            FROM ml_orders 
            WHERE company_id = :company_id
            AND status IN ('PAID', 'CONFIRMED', 'SHIPPED', 'DELIVERED')
            AND payments IS NOT NULL
            AND payments::text != '[]'
            AND (
                (payments->0->>'date_approved')::timestamp AT TIME ZONE 'UTC-4' >= :start_date
                AND (payments->0->>'date_approved')::timestamp AT TIME ZONE 'UTC-4' <= :end_date
            )
            ORDER BY date_created DESC
            LIMIT 5
        """), {
            "company_id": company_id,
            "start_date": datetime(2025, 10, 1),
            "end_date": datetime(2025, 10, 31, 23, 59, 59)
        })
        
        orders = result2.fetchall()
        
        print(f"   📦 Analisando {len(orders)} pedidos:")
        print()
        
        for order in orders:
            try:
                payments_data = json.loads(order.payments) if isinstance(order.payments, str) else order.payments
                if isinstance(payments_data, list) and len(payments_data) > 0:
                    payment = payments_data[0]
                    date_approved_str = payment.get('date_approved', '')
                    
                    if date_approved_str:
                        date_approved = datetime.fromisoformat(date_approved_str.replace('Z', '+00:00'))
                        
                        print(f"   🆔 {order.ml_order_id}:")
                        print(f"      📊 Status: {order.status}")
                        print(f"      💰 Total: R$ {order.total_amount}")
                        print(f"      📅 Created: {order.date_created}")
                        print(f"      💳 Approved: {date_approved}")
                        print()
            except Exception as e:
                print(f"   ❌ Erro ao processar {order.ml_order_id}: {e}")
        
        # Teste 3: Verificar se há problema com o fuso horário
        print(f"\n📊 Teste 3: Verificar fuso horário")
        print("-" * 40)
        
        result3 = db.execute(text("""
            SELECT 
                ml_order_id,
                total_amount,
                payments->0->>'date_approved' as date_approved_raw,
                (payments->0->>'date_approved')::timestamp as date_approved_utc,
                (payments->0->>'date_approved')::timestamp AT TIME ZONE 'UTC-4' as date_approved_utc4
            FROM ml_orders 
            WHERE company_id = :company_id
            AND status IN ('PAID', 'CONFIRMED', 'SHIPPED', 'DELIVERED')
            AND payments IS NOT NULL
            AND payments::text != '[]'
            ORDER BY date_created DESC
            LIMIT 3
        """), {"company_id": company_id})
        
        timezone_data = result3.fetchall()
        
        print(f"   📦 Analisando fuso horário:")
        print()
        
        for row in timezone_data:
            print(f"   🆔 {row.ml_order_id}:")
            print(f"      💰 Total: R$ {row.total_amount}")
            print(f"      📅 Raw: {row.date_approved_raw}")
            print(f"      🌍 UTC: {row.date_approved_utc}")
            print(f"      🇺🇸 UTC-4: {row.date_approved_utc4}")
            print()
        
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
    print("🔍 Debug do Problema de Receita Zerada")
    print("=" * 60)
    print()
    
    success = debug_revenue_issue()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ DEBUG CONCLUÍDO!")
    else:
        print("❌ Erro no debug!")

if __name__ == "__main__":
    main()
