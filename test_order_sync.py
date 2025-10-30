#!/usr/bin/env python3
"""
Script para testar sincronização de pedido específico
"""
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/apiwolfx")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

try:
    order_id = "2000008568258421"
    
    print(f"🔍 TESTANDO SINCRONIZAÇÃO DO PEDIDO: {order_id}\n")
    print("="*80)
    
    # 1. Verificar pedido ANTES da sincronização
    print("\n📋 1. PEDIDO:")
    print("-"*80)
    
    query = text("""
        SELECT 
            ml_order_id,
            order_id,
            status,
            shipping_status,
            shipping_type,
            shipping_date,
            invoice_emitted,
            invoice_number,
            pack_id,
            shipping_id,
            date_closed,
            updated_at,
            shipping_details
        FROM ml_orders 
        WHERE ml_order_id = :order_id
        LIMIT 1
    """)
    
    result = session.execute(query, {"order_id": order_id}).fetchone()
    
    if not result:
        print(f"❌ Pedido {order_id} não encontrado no banco de dados")
        session.close()
        sys.exit(1)
    
    print(f"ML Order ID: {result.ml_order_id}")
    print(f"Order ID: {result.order_id}")
    print(f"Status: {result.status}")
    print(f"Shipping Status: {result.shipping_status}")
    print(f"Shipping Type: {result.shipping_type}")
    print(f"Shipping Date: {result.shipping_date}")
    print(f"Invoice Emitted: {result.invoice_emitted}")
    print(f"Invoice Number: {result.invoice_number}")
    print(f"Pack ID: {result.pack_id}")
    print(f"Shipping ID: {result.shipping_id}")
    print(f"Date Closed: {result.date_closed}")
    print(f"Updated At: {result.updated_at}")
    
    # Verificar shipping_details
    print("\n📦 SHIPPING DETAILS:")
    print("-"*80)
    
    if result.shipping_details:
        import json
        details = json.loads(result.shipping_details) if isinstance(result.shipping_details, str) else result.shipping_details
        
        print(f"Status: {details.get('status')}")
        print(f"Substatus: {details.get('substatus')}")
        print(f"Logistic Type: {details.get('logistic_type')}")
        
        logistic = details.get('logistic', {})
        if logistic:
            print(f"Logistic Mode: {logistic.get('mode')}")
            print(f"Logistic Type (nested): {logistic.get('type')}")
    else:
        print("⚠️ shipping_details está vazio ou não existe")
    
    print("\n" + "="*80)
    print("✅ Teste concluído!")
    
finally:
    session.close()

