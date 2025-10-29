#!/usr/bin/env python3
"""
Script para verificar e sincronizar um pedido específico
"""
import os
import sys
import logging
import requests
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.saas_models import MLOrder, OrderStatus
from app.services.token_manager import TokenManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Configuração do banco de dados
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:97452c28f62db6d77be083917b698660@pgadmin.wolfx.com.br:5432/comercial"
)

# Configuração da API do Mercado Livre
ML_API_BASE_URL = "https://api.mercadolibre.com"


def check_order_in_db(order_id):
    """
    Verifica o pedido no banco de dados
    """
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text('''
            SELECT 
                id, ml_order_id, order_id, status, shipping_status, 
                shipping_type, shipping_id, pack_id, date_created, 
                date_closed, total_amount, buyer_first_name, buyer_nickname,
                shipping_details, sale_id
            FROM ml_orders 
            WHERE order_id = :order_id OR ml_order_id = :order_id
        '''), {'order_id': order_id})
        
        order = result.fetchone()
        if order:
            print('📦 PEDIDO ENCONTRADO NO BANCO:')
            print(f'   ID: {order[0]}')
            print(f'   ML Order ID: {order[1]}')
            print(f'   Order ID: {order[2]}')
            print(f'   Status: {order[3]}')
            print(f'   Shipping Status: {order[4]}')
            print(f'   Shipping Type: {order[5]}')
            print(f'   Shipping ID: {order[6]}')
            print(f'   Pack ID: {order[7]}')
            print(f'   Data Criação: {order[8]}')
            print(f'   Data Fechamento: {order[9]}')
            print(f'   Total: R$ {order[10]}')
            print(f'   Comprador: {order[11]} ({order[12]})')
            print(f'   Sale ID: {order[14]}')
            
            # Verificar shipping_details
            shipping_details = order[13]
            if shipping_details:
                print(f'   📦 Shipping Details disponível: {type(shipping_details)}')
                if isinstance(shipping_details, dict):
                    print(f'   📦 Status: {shipping_details.get("status")}')
                    print(f'   📦 Substatus: {shipping_details.get("substatus")}')
                    print(f'   📦 Tracking Method: {shipping_details.get("tracking_method")}')
                    print(f'   📦 Logistic Type: {shipping_details.get("logistic_type")}')
            else:
                print('   ❌ Shipping Details: NULL')
            
            return order
        else:
            print('❌ Pedido não encontrado no banco')
            return None


def sync_specific_order(order_id, access_token):
    """
    Sincroniza um pedido específico
    """
    try:
        logger.info(f"🔄 Sincronizando pedido {order_id}")
        
        # 1. Buscar pedido na API do ML
        order_url = f"{ML_API_BASE_URL}/orders/{order_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(order_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"❌ Erro ao buscar pedido {order_id}: HTTP {response.status_code}")
            return False
        
        order_data = response.json()
        
        print(f"\n📦 DADOS DO PEDIDO NA API ML:")
        print(f"   Status: {order_data.get('status')}")
        print(f"   Date Closed: {order_data.get('date_closed')}")
        print(f"   Total Amount: R$ {order_data.get('total_amount')}")
        
        # Verificar shipping
        shipping = order_data.get("shipping", {})
        if shipping:
            print(f"   📦 Shipping Status: {shipping.get('status')}")
            print(f"   📦 Shipping ID: {shipping.get('id')}")
            print(f"   📦 Logistic Type: {shipping.get('logistic_type')}")
        
        # Verificar pack_id
        pack_id = order_data.get("pack_id")
        if pack_id:
            print(f"   📦 Pack ID: {pack_id}")
        
        # 2. Buscar detalhes do shipment se tiver shipping_id
        shipping_id = shipping.get("id")
        if shipping_id:
            try:
                shipment_url = f"{ML_API_BASE_URL}/shipments/{shipping_id}"
                shipment_headers = {
                    **headers,
                    "x-format-new": "true"
                }
                shipment_response = requests.get(shipment_url, headers=shipment_headers, timeout=30)
                
                if shipment_response.status_code == 200:
                    shipment_data = shipment_response.json()
                    
                    print(f"\n📦 DADOS DO SHIPMENT:")
                    print(f"   Status: {shipment_data.get('status')}")
                    print(f"   Substatus: {shipment_data.get('substatus')}")
                    print(f"   Logistic Type: {shipment_data.get('logistic_type')}")
                    print(f"   Tracking Method: {shipment_data.get('tracking_method')}")
                    print(f"   Tracking Number: {shipment_data.get('tracking_number')}")
                    print(f"   Date Created: {shipment_data.get('date_created')}")
                    
                    # Status History
                    status_history = shipment_data.get("status_history", {})
                    if status_history:
                        print(f"   📅 Status History:")
                        for key, value in status_history.items():
                            if value:
                                print(f"     {key}: {value}")
                    
                    # Substatus History
                    substatus_history = shipment_data.get("substatus_history", [])
                    if substatus_history:
                        print(f"   📋 Substatus History ({len(substatus_history)} entradas):")
                        for entry in substatus_history[-5:]:  # Últimos 5
                            print(f"     {entry.get('date')}: {entry.get('status')} - {entry.get('substatus')}")
                    
                    # Shipping Option
                    shipping_option = shipment_data.get("shipping_option", {})
                    if shipping_option:
                        estimated_delivery = shipping_option.get("estimated_delivery_final", {})
                        estimated_date = estimated_delivery.get("date")
                        if estimated_date:
                            print(f"   📅 Data Entrega Estimada: {estimated_date}")
                
            except Exception as e:
                logger.error(f"❌ Erro ao buscar shipment {shipping_id}: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao sincronizar pedido {order_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """
    Função principal
    """
    order_id = "2000012389815946"
    
    print(f"🔍 Verificando pedido {order_id}")
    
    # 1. Verificar no banco
    order = check_order_in_db(order_id)
    
    if not order:
        print("❌ Pedido não encontrado no banco. Finalizando.")
        return
    
    # 2. Conectar ao banco para buscar token
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Buscar token de acesso
        token_manager = TokenManager(db)
        
        # Buscar um usuário ativo da empresa
        from app.models.saas_models import User
        user = db.query(User).filter(
            User.company_id == order[0],  # company_id do pedido
            User.is_active == True
        ).first()
        
        if not user:
            print(f"❌ Nenhum usuário ativo encontrado para empresa {order[0]}")
            return
        
        access_token = token_manager.get_valid_token(user.id)
        
        if not access_token:
            print(f"❌ Token de acesso inválido ou expirado")
            return
        
        print(f"✅ Token obtido para empresa {order[0]}")
        
        # 3. Sincronizar pedido
        sync_specific_order(order_id, access_token)
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
