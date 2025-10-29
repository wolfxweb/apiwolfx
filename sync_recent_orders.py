#!/usr/bin/env python3
"""
Script para sincronizar pedidos dos últimos 7 dias e corrigir campos faltantes
Atualiza: shipping_status, shipping_id, shipping_method, shipping_details, shipping_type, etc.
"""
import os
import sys
import logging
import requests
from datetime import datetime, timedelta
from sqlalchemy import create_engine
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


def sync_order(order, access_token, db, company_id):
    """
    Sincroniza um pedido específico atualizando todos os campos de shipping
    """
    try:
        order_id_for_logs = str(order.order_id)
        logger.info(f"🔄 Sincronizando pedido {order_id_for_logs} (ML Order ID: {order.ml_order_id})")
        
        # 1. Buscar pedido atualizado na API do ML
        order_url = f"{ML_API_BASE_URL}/orders/{order.order_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(order_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.warning(f"⚠️ Erro ao buscar pedido {order_id_for_logs}: HTTP {response.status_code}")
            return False
        
        order_data = response.json()
        
        # 2. Atualizar dados básicos
        shipping = order_data.get("shipping", {})
        shipping_status = shipping.get("status")
        shipping_id = shipping.get("id")
        
        if shipping_status:
            order.shipping_status = shipping_status
            logger.info(f"  ✅ shipping_status atualizado: {shipping_status}")
        
        if shipping_id:
            order.shipping_id = str(shipping_id)
            logger.info(f"  ✅ shipping_id atualizado: {shipping_id}")
        
        # 3. Verificar pack_id
        pack_id = order_data.get("pack_id")
        if pack_id:
            order.pack_id = str(pack_id)
            if not order.shipping_type:
                order.shipping_type = "fulfillment"
                logger.info(f"  ✅ Identificado como FULFILLMENT (pack_id: {pack_id})")
        
        # 4. Atualizar sale_id se não existir (verificar se o campo existe)
        sale_id = order_data.get("sale_id") or order_data.get("id")
        if sale_id and hasattr(order, 'sale_id') and not order.sale_id:
            order.sale_id = str(sale_id)
            logger.info(f"  ✅ sale_id atualizado: {sale_id}")
        
        # 5. Buscar detalhes completos do shipment se tiver shipping_id
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
                    
                    # Salvar shipping_details completo
                    order.shipping_details = shipment_data
                    
                    # Extrair logistic_type
                    logistic_type = shipment_data.get("logistic_type")
                    if not logistic_type:
                        logistic = shipment_data.get("logistic", {})
                        logistic_type = logistic.get("type") if logistic else None
                    
                    if logistic_type:
                        order.shipping_type = logistic_type
                        order.shipping_method = logistic_type
                        logger.info(f"  ✅ shipping_type e shipping_method atualizados: {logistic_type}")
                    
                    # Atualizar shipping_date
                    shipping_date = shipment_data.get("date_created")
                    if shipping_date:
                        try:
                            order.shipping_date = datetime.fromisoformat(shipping_date.replace('Z', '+00:00'))
                            logger.info(f"  ✅ shipping_date atualizado: {shipping_date}")
                        except Exception as e:
                            logger.warning(f"  ⚠️ Erro ao parsear shipping_date: {e}")
                    
                    # Atualizar estimated_delivery_date
                    shipping_option = shipment_data.get("shipping_option", {})
                    estimated_delivery = shipping_option.get("estimated_delivery_final", {})
                    estimated_date = estimated_delivery.get("date")
                    if estimated_date:
                        try:
                            order.estimated_delivery_date = datetime.fromisoformat(estimated_date.replace('Z', '+00:00'))
                            logger.info(f"  ✅ estimated_delivery_date atualizado: {estimated_date}")
                        except Exception as e:
                            logger.warning(f"  ⚠️ Erro ao parsear estimated_delivery_date: {e}")
                    
                    # Extrair tracking_method
                    tracking_method = shipment_data.get("tracking_method")
                    if tracking_method:
                        logger.info(f"  📦 Tracking Method: {tracking_method}")
                    
                    # Extrair status_history (datas importantes)
                    status_history = shipment_data.get("status_history", {})
                    if status_history:
                        logger.info(f"  📅 Status History encontrado:")
                        for key, value in status_history.items():
                            if value:
                                logger.info(f"    {key}: {value}")
                    
                    # Extrair substatus_history
                    substatus_history = shipment_data.get("substatus_history", [])
                    if substatus_history:
                        logger.info(f"  📋 Substatus History ({len(substatus_history)} entradas):")
                        for entry in substatus_history[-3:]:  # Mostrar apenas os 3 últimos
                            logger.info(f"    {entry.get('date')}: {entry.get('status')} - {entry.get('substatus')}")
                    
                    # Log do substatus atual se existir
                    substatus = shipment_data.get("substatus")
                    if substatus:
                        logger.info(f"  📦 Substatus atual: {substatus}")
                    
                    # Log do tracking_number se existir
                    tracking_number = shipment_data.get("tracking_number")
                    if tracking_number:
                        logger.info(f"  🚚 Tracking Number: {tracking_number}")
                
            except Exception as e:
                logger.warning(f"  ⚠️ Erro ao buscar detalhes do shipment {shipping_id}: {e}")
        
        # 6. Se não identificamos shipping_type ainda, verificar shipping básico
        if not order.shipping_type and shipping:
            logistic_type = shipping.get("logistic_type")
            if logistic_type:
                order.shipping_type = logistic_type
                order.shipping_method = logistic_type
                logger.info(f"  ✅ shipping_type do shipping básico: {logistic_type}")
        
        # 7. Se ainda não identificamos, buscar do produto
        if not order.shipping_type:
            try:
                order_items = order_data.get("order_items", [])
                if order_items:
                    first_item = order_items[0].get("item", {})
                    item_id = first_item.get("id")
                    
                    if item_id:
                        item_url = f"{ML_API_BASE_URL}/items/{item_id}"
                        item_response = requests.get(item_url, headers=headers, timeout=30)
                        
                        if item_response.status_code == 200:
                            item_data = item_response.json()
                            item_shipping = item_data.get("shipping", {})
                            item_logistic_type = item_shipping.get("logistic_type")
                            
                            if item_logistic_type:
                                order.shipping_type = item_logistic_type
                                order.shipping_method = item_logistic_type
                                logger.info(f"  ✅ shipping_type do produto: {item_logistic_type}")
                            
                            # Verificar tags
                            tags = item_data.get("tags", [])
                            if not order.shipping_type and ("fulfillment" in tags or "meli_fulfillment" in tags or "FULL" in tags):
                                order.shipping_type = "fulfillment"
                                order.shipping_method = "fulfillment"
                                logger.info(f"  ✅ shipping_type identificado pelas tags do produto: fulfillment")
            except Exception as e:
                logger.warning(f"  ⚠️ Erro ao buscar produto: {e}")
        
        db.commit()
        logger.info(f"✅ Pedido {order_id_for_logs} sincronizado com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao sincronizar pedido {order.order_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
        return False


def main():
    """
    Função principal: sincroniza pedidos dos últimos 7 dias
    """
    try:
        # Conectar ao banco
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            # Calcular data limite (últimos 7 dias)
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
            
            logger.info(f"🔄 Iniciando sincronização de pedidos dos últimos 7 dias")
            logger.info(f"   Período: {start_date.date()} até {end_date.date()}")
            
            # Buscar pedidos dos últimos 7 dias
            orders = db.query(MLOrder).filter(
                MLOrder.created_at >= start_date,
                MLOrder.created_at <= end_date
            ).order_by(MLOrder.created_at.desc()).all()
            
            total_orders = len(orders)
            logger.info(f"📦 Encontrados {total_orders} pedidos para sincronizar")
            
            if total_orders == 0:
                logger.info("✅ Nenhum pedido encontrado. Finalizando.")
                return
            
            # Agrupar por company_id para obter tokens
            orders_by_company = {}
            for order in orders:
                if order.company_id not in orders_by_company:
                    orders_by_company[order.company_id] = []
                orders_by_company[order.company_id].append(order)
            
            logger.info(f"📊 Pedidos distribuídos em {len(orders_by_company)} empresa(s)")
            
            # Sincronizar por empresa
            total_synced = 0
            total_errors = 0
            
            for company_id, company_orders in orders_by_company.items():
                logger.info(f"\n🏢 Processando empresa {company_id} ({len(company_orders)} pedidos)")
                
                # Buscar token de acesso para esta empresa
                token_manager = TokenManager(db)
                
                # Buscar um usuário ativo da empresa
                from app.models.saas_models import User
                user = db.query(User).filter(
                    User.company_id == company_id,
                    User.is_active == True
                ).first()
                
                if not user:
                    logger.error(f"❌ Nenhum usuário ativo encontrado para empresa {company_id}")
                    total_errors += len(company_orders)
                    continue
                
                access_token = token_manager.get_valid_token(user.id)
                
                if not access_token:
                    logger.error(f"❌ Token de acesso inválido ou expirado para empresa {company_id}")
                    total_errors += len(company_orders)
                    continue
                
                logger.info(f"✅ Token obtido para empresa {company_id}")
                
                # Sincronizar cada pedido
                company_synced = 0
                company_errors = 0
                
                for idx, order in enumerate(company_orders, 1):
                    logger.info(f"  [{idx}/{len(company_orders)}] Processando pedido {order.order_id}...")
                    
                    if sync_order(order, access_token, db, company_id):
                        company_synced += 1
                        total_synced += 1
                    else:
                        company_errors += 1
                        total_errors += 1
                    
                    # Commit após cada pedido para garantir que não perca dados
                    db.commit()
                    
                    # Pequeno delay para não sobrecarregar a API
                    import time
                    time.sleep(0.5)
                    
                    # Log de progresso a cada 10 pedidos
                    if idx % 10 == 0:
                        logger.info(f"  💾 Progresso: {idx}/{len(company_orders)} pedidos processados")
                
                logger.info(f"✅ Empresa {company_id}: {company_synced} sincronizados, {company_errors} erros")
            
            logger.info(f"\n✅ Sincronização concluída!")
            logger.info(f"   Total processado: {total_orders}")
            logger.info(f"   ✅ Sincronizados com sucesso: {total_synced}")
            logger.info(f"   ❌ Erros: {total_errors}")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Erro fatal na sincronização: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()

