#!/usr/bin/env python3
"""
Testar usando date_approved do pagamento em vez de date_created
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from sqlalchemy import text
from datetime import datetime
import json

def test_payment_dates():
    """Testar usando date_approved do pagamento"""
    print("🔍 Testando Date Approved vs Date Created")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Teste 1: Usando date_created (atual)
        print("📊 Teste 1: Usando date_created (atual)")
        print("-" * 40)
        
        result1 = db.execute(text("""
            SELECT 
                COUNT(*) as total_orders,
                SUM(total_amount) as total_revenue
            FROM ml_orders 
            WHERE company_id = :company_id
            AND date_created >= :start_date
            AND date_created <= :end_date
            AND status IN ('PAID', 'CONFIRMED', 'SHIPPED', 'DELIVERED')
        """), {
            "company_id": company_id,
            "start_date": datetime(2025, 10, 1),
            "end_date": datetime(2025, 10, 31, 23, 59, 59)
        })
        
        data1 = result1.fetchone()
        print(f"   📦 Pedidos: {data1.total_orders}")
        print(f"   💰 Receita: R$ {float(data1.total_revenue or 0):.2f}")
        
        # Teste 2: Usando date_approved do pagamento
        print(f"\n📊 Teste 2: Usando date_approved do pagamento")
        print("-" * 40)
        
        result2 = db.execute(text("""
            SELECT 
                COUNT(*) as total_orders,
                SUM(total_amount) as total_revenue
            FROM ml_orders 
            WHERE company_id = :company_id
            AND status IN ('PAID', 'CONFIRMED', 'SHIPPED', 'DELIVERED')
            AND payments IS NOT NULL
            AND payments::text != '[]'
            AND payments::text != '{}'
        """), {"company_id": company_id})
        
        data2 = result2.fetchone()
        print(f"   📦 Pedidos com pagamento: {data2.total_orders}")
        print(f"   💰 Receita: R$ {float(data2.total_revenue or 0):.2f}")
        
        # Teste 3: Analisar diferenças de data
        print(f"\n📊 Teste 3: Análise de Diferenças de Data")
        print("-" * 40)
        
        result3 = db.execute(text("""
            SELECT 
                ml_order_id,
                date_created,
                date_closed,
                total_amount,
                payments
            FROM ml_orders 
            WHERE company_id = :company_id
            AND status IN ('PAID', 'CONFIRMED', 'SHIPPED', 'DELIVERED')
            AND payments IS NOT NULL
            AND payments::text != '[]'
            ORDER BY date_created DESC
            LIMIT 10
        """), {"company_id": company_id})
        
        orders = result3.fetchall()
        
        print(f"   📦 Analisando {len(orders)} pedidos:")
        print()
        
        for order in orders:
            try:
                payments_data = json.loads(order.payments) if isinstance(order.payments, str) else order.payments
                if isinstance(payments_data, list) and len(payments_data) > 0:
                    payment = payments_data[0]
                    date_approved_str = payment.get('date_approved', '')
                    
                    if date_approved_str:
                        # Converter para datetime
                        date_approved = datetime.fromisoformat(date_approved_str.replace('Z', '+00:00'))
                        
                        # Calcular diferença
                        diff_hours = (order.date_created - date_approved.replace(tzinfo=None)).total_seconds() / 3600
                        
                        print(f"   🆔 {order.ml_order_id}:")
                        print(f"      📅 Created: {order.date_created}")
                        print(f"      💳 Approved: {date_approved}")
                        print(f"      ⏱️  Diferença: {diff_hours:.1f} horas")
                        print(f"      💰 Valor: R$ {order.total_amount}")
                        print()
            except Exception as e:
                print(f"   ❌ Erro ao processar {order.ml_order_id}: {e}")
        
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
    print("🔍 Testando Date Approved vs Date Created")
    print("=" * 60)
    print()
    
    success = test_payment_dates()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE DE DATAS CONCLUÍDO!")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
