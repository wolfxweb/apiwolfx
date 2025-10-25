#!/usr/bin/env python3
"""
Corrigir filtro de data para usar date_approved do pagamento
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from sqlalchemy import text
from datetime import datetime
import json

def test_corrected_dates():
    """Testar usando date_approved do pagamento"""
    print("🔧 Testando Filtro de Data Corrigido")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Teste: Outubro 2025 usando date_approved
        print("📊 Teste: Outubro 2025 usando date_approved")
        print("-" * 40)
        
        # Buscar pedidos onde date_approved está em outubro 2025
        result = db.execute(text("""
            SELECT 
                ml_order_id,
                date_created,
                total_amount,
                payments
            FROM ml_orders 
            WHERE company_id = :company_id
            AND status IN ('PAID', 'CONFIRMED', 'SHIPPED', 'DELIVERED')
            AND payments IS NOT NULL
            AND payments::text != '[]'
            ORDER BY date_created DESC
            LIMIT 20
        """), {"company_id": company_id})
        
        orders = result.fetchall()
        
        print(f"📦 Analisando {len(orders)} pedidos:")
        print()
        
        october_orders = []
        total_revenue = 0
        
        for order in orders:
            try:
                payments_data = json.loads(order.payments) if isinstance(order.payments, str) else order.payments
                if isinstance(payments_data, list) and len(payments_data) > 0:
                    payment = payments_data[0]
                    date_approved_str = payment.get('date_approved', '')
                    
                    if date_approved_str:
                        # Converter para datetime
                        date_approved = datetime.fromisoformat(date_approved_str.replace('Z', '+00:00'))
                        
                        # Verificar se está em outubro 2025
                        if date_approved.year == 2025 and date_approved.month == 10:
                            october_orders.append(order)
                            total_revenue += float(order.total_amount or 0)
                            
                            print(f"   ✅ {order.ml_order_id}:")
                            print(f"      📅 Created: {order.date_created}")
                            print(f"      💳 Approved: {date_approved}")
                            print(f"      💰 Valor: R$ {order.total_amount}")
                            print()
            except Exception as e:
                print(f"   ❌ Erro ao processar {order.ml_order_id}: {e}")
        
        print(f"📊 Resultado Final:")
        print(f"   📦 Pedidos em Outubro 2025: {len(october_orders)}")
        print(f"   💰 Receita Total: R$ {total_revenue:.2f}")
        
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
    print("🔧 Testando Filtro de Data Corrigido")
    print("=" * 60)
    print()
    
    success = test_corrected_dates()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE DE DATA CORRIGIDA CONCLUÍDO!")
    else:
        print("❌ Erro no teste!")

if __name__ == "__main__":
    main()
