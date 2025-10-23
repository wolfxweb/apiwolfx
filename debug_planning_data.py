#!/usr/bin/env python3
"""
Script para debugar dados de planejamento
"""

import sys
import os
sys.path.append('/app')

from app.config.database import get_db
from app.models.database_models import MLOrder, AccountReceivable
from sqlalchemy import and_
from datetime import datetime

def debug_planning_data():
    db = next(get_db())
    
    print("🔍 DEBUG - Verificando dados no banco...")
    
    # 1. Verificar todos os pedidos ML
    all_orders = db.query(MLOrder).all()
    print(f"📊 Total de pedidos ML no banco: {len(all_orders)}")
    
    if all_orders:
        print("📋 Primeiros 3 pedidos ML:")
        for order in all_orders[:3]:
            print(f"  - ID: {order.id}, Company: {order.company_id}, Status: {order.status}, Amount: {order.total_amount}, Date: {order.date_created}")
    
    # 2. Verificar todas as contas a receber
    all_receivables = db.query(AccountReceivable).all()
    print(f"📊 Total de contas a receber no banco: {len(all_receivables)}")
    
    if all_receivables:
        print("📋 Primeiras 3 contas a receber:")
        for receivable in all_receivables[:3]:
            print(f"  - ID: {receivable.id}, Company: {receivable.company_id}, Status: {receivable.status}, Amount: {receivable.amount}, Date: {receivable.due_date}")
    
    # 3. Verificar company_ids únicos
    unique_company_ids_orders = db.query(MLOrder.company_id).distinct().all()
    unique_company_ids_receivables = db.query(AccountReceivable.company_id).distinct().all()
    
    print(f"🏢 Company IDs com pedidos ML: {[c[0] for c in unique_company_ids_orders]}")
    print(f"🏢 Company IDs com contas a receber: {[c[0] for c in unique_company_ids_receivables]}")
    
    # 4. Testar com company_id = 1 (assumindo que existe)
    test_company_id = 1
    print(f"\n🧪 Testando com company_id = {test_company_id}")
    
    # Pedidos ML para 2025
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2026, 1, 1)
    
    orders_2025 = db.query(MLOrder).filter(
        and_(
            MLOrder.company_id == test_company_id,
            MLOrder.date_created >= start_date,
            MLOrder.date_created < end_date,
            MLOrder.status.in_(['paid', 'confirmed'])
        )
    ).all()
    
    print(f"📊 Pedidos ML para 2025 (company_id={test_company_id}): {len(orders_2025)}")
    
    # Contas a receber para 2025
    receivables_2025 = db.query(AccountReceivable).filter(
        and_(
            AccountReceivable.company_id == test_company_id,
            AccountReceivable.due_date >= start_date,
            AccountReceivable.due_date < end_date,
            AccountReceivable.status.in_(['pending', 'paid'])
        )
    ).all()
    
    print(f"📊 Contas a receber para 2025 (company_id={test_company_id}): {len(receivables_2025)}")
    
    # 5. Verificar status únicos
    unique_status_orders = db.query(MLOrder.status).distinct().all()
    unique_status_receivables = db.query(AccountReceivable.status).distinct().all()
    
    print(f"📋 Status únicos em pedidos ML: {[s[0] for s in unique_status_orders]}")
    print(f"📋 Status únicos em contas a receber: {[s[0] for s in unique_status_receivables]}")

if __name__ == "__main__":
    debug_planning_data()
