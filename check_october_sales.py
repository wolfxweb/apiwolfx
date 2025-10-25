#!/usr/bin/env python3
"""
Verificar vendas em outubro para validar os dados
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import get_db
from sqlalchemy import text
from datetime import datetime

def check_october_sales():
    """Verifica vendas em outubro"""
    db = next(get_db())
    
    try:
        # Outubro 2025
        start_date = datetime(2025, 10, 1)
        end_date = datetime(2025, 10, 31, 23, 59, 59)
        
        print(f"🔍 Verificando vendas em Outubro 2025")
        print(f"   Período: {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}")
        print()
        
        # Consulta SQL para buscar pedidos em outubro
        query = text("""
            SELECT 
                mo.ml_order_id,
                mo.total_amount,
                mo.order_items,
                mo.date_created,
                mo.status,
                mo.payments
            FROM ml_orders mo
            WHERE mo.company_id = 15
            AND (
                (mo.payments::text != '[]' AND 
                 (mo.payments::jsonb->0->>'date_approved')::timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'America/Manaus' >= :start_date
                 AND (mo.payments::jsonb->0->>'date_approved')::timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'America/Manaus' <= :end_date)
                OR
                (mo.payments::text = '[]' AND mo.date_created >= :start_date AND mo.date_created <= :end_date)
            )
            AND mo.status IN ('PAID', 'CONFIRMED', 'SHIPPED', 'DELIVERED')
            ORDER BY mo.date_created DESC
        """)
        
        result = db.execute(query, {
            "start_date": start_date,
            "end_date": end_date
        })
        orders = result.fetchall()
        
        print(f"📦 Total de pedidos em Outubro: {len(orders)}")
        print()
        
        # Analisar produtos por ML Item ID
        products_summary = {}
        
        for order in orders:
            try:
                import json
                order_items = json.loads(order.order_items) if isinstance(order.order_items, str) else order.order_items
                
                if isinstance(order_items, list):
                    for item in order_items:
                        ml_item_id = item.get('item', {}).get('id')
                        if ml_item_id:
                            if ml_item_id not in products_summary:
                                products_summary[ml_item_id] = {
                                    'title': item.get('item', {}).get('title', 'N/A'),
                                    'quantity': 0,
                                    'orders': 0,
                                    'revenue': 0.0
                                }
                            
                            item_quantity = item.get('quantity', 1)
                            item_unit_price = item.get('unit_price', 0)
                            item_revenue = item_quantity * item_unit_price
                            
                            products_summary[ml_item_id]['quantity'] += item_quantity
                            products_summary[ml_item_id]['orders'] += 1
                            products_summary[ml_item_id]['revenue'] += item_revenue
            except Exception as e:
                print(f"   Erro ao processar pedido {order.ml_order_id}: {e}")
        
        # Ordenar por quantidade vendida
        sorted_products = sorted(
            products_summary.items(),
            key=lambda x: x[1]['quantity'],
            reverse=True
        )
        
        print(f"📊 Top 10 Produtos Vendidos em Outubro:")
        print()
        for i, (ml_item_id, data) in enumerate(sorted_products[:10], 1):
            print(f"{i}. {data['title'][:50]}")
            print(f"   ML Item ID: {ml_item_id}")
            print(f"   Quantidade: {data['quantity']} unidades")
            print(f"   Pedidos: {data['orders']}")
            print(f"   Receita: R$ {data['revenue']:.2f}")
            print()
        
        # Procurar especificamente pelo produto MLB5069302578
        if 'MLB5069302578' in products_summary:
            data = products_summary['MLB5069302578']
            print(f"🎯 Produto MLB5069302578 (Kit Arduino):")
            print(f"   Quantidade vendida: {data['quantity']} unidades")
            print(f"   Número de pedidos: {data['orders']}")
            print(f"   Receita total: R$ {data['revenue']:.2f}")
            print()
        else:
            print(f"⚠️  Produto MLB5069302578 não encontrado nas vendas de Outubro")
            print()
    
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_october_sales()

