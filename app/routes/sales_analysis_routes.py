from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import json
from collections import Counter
from datetime import datetime, timedelta

from app.config.database import get_db
from app.models.saas_models import MLOrder
from app.controllers.auth_controller import AuthController

router = APIRouter()

def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Obtém usuário atual da sessão"""
    session_token = request.cookies.get('session_token')
    if not session_token:
        raise HTTPException(status_code=401, detail="Sessão não encontrada")
    
    auth_controller = AuthController()
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail=result["error"])
    
    return result["user"]

@router.get("/api/sales/analysis/product/{ml_item_id}")
async def get_product_sales_analysis(
    ml_item_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Análise de vendas por ML item ID e company_id
    """
    try:
        company_id = current_user["company"]["id"]
        
        # Buscar pedidos que contenham o ML item ID
        orders = db.query(MLOrder).filter(
            MLOrder.company_id == company_id,
            MLOrder.order_items.isnot(None)
        ).all()
        
        found_orders = []
        for order in orders:
            if order.order_items:
                try:
                    items = json.loads(order.order_items) if isinstance(order.order_items, str) else order.order_items
                    if isinstance(items, list):
                        for item in items:
                            item_data = item.get('item', {})
                            item_id = item_data.get('id', '')
                            if item_id == ml_item_id:
                                found_orders.append((order, item))
                except Exception:
                    continue
        
        if not found_orders:
            return {
                "success": False,
                "message": f"Nenhum pedido encontrado para o produto {ml_item_id}",
                "analysis": None
            }
        
        # Calcular estatísticas
        stats = calculate_sales_stats(found_orders)
        
        # Preparar pedidos recentes (últimos 10)
        recent_orders = []
        for order, item in sorted(found_orders, key=lambda x: x[0].date_created, reverse=True)[:10]:
            # Extrair ml_item_id do item
            item_data = item.get('item', {})
            ml_item_id = item_data.get('id', '')
            
            recent_orders.append({
                "ml_order_id": str(order.ml_order_id),
                "ml_item_id": ml_item_id,
                "date_created": order.date_created.isoformat(),
                "buyer_nickname": order.buyer_nickname,
                "unit_price": item.get("unit_price", 0),
                "quantity": item.get("quantity", 0),
                "status": order.status.name if order.status else "UNKNOWN"
            })
        
        analysis = {
            "stats": stats,
            "recent_orders": recent_orders,
            "total_found": len(found_orders)
        }
        
        return {
            "success": True,
            "message": f"Análise de vendas para produto {ml_item_id}",
            "analysis": analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao analisar vendas do produto: {str(e)}")

@router.get("/api/sales/analysis/sku/{sku}")
async def get_sku_sales_analysis(
    sku: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Análise de vendas por SKU e company_id
    """
    try:
        company_id = current_user["company"]["id"]
        
        # Buscar pedidos que contenham o SKU
        orders = db.query(MLOrder).filter(
            MLOrder.company_id == company_id,
            MLOrder.order_items.isnot(None)
        ).all()
        
        found_orders = []
        for order in orders:
            if order.order_items:
                try:
                    items = json.loads(order.order_items) if isinstance(order.order_items, str) else order.order_items
                    if isinstance(items, list):
                        for item in items:
                            item_data = item.get('item', {})
                            seller_sku = item_data.get('seller_sku', '')
                            if seller_sku == sku:
                                found_orders.append((order, item))
                except Exception:
                    continue
        
        if not found_orders:
            return {
                "success": False,
                "message": f"Nenhum pedido encontrado para o SKU {sku}",
                "analysis": None
            }
        
        # Calcular estatísticas
        stats = calculate_sales_stats(found_orders)
        
        # Preparar todos os pedidos ordenados por data
        all_orders = []
        for order, item in sorted(found_orders, key=lambda x: x[0].date_created, reverse=True):
            # Extrair ml_item_id do item
            item_data = item.get('item', {})
            ml_item_id = item_data.get('id', '')
            
            all_orders.append({
                "ml_order_id": str(order.ml_order_id),
                "ml_item_id": ml_item_id,
                "date_created": order.date_created.isoformat(),
                "buyer_nickname": order.buyer_nickname,
                "unit_price": item.get("unit_price", 0),
                "quantity": item.get("quantity", 0),
                "status": order.status.name if order.status else "UNKNOWN"
            })
        
        analysis = {
            "stats": stats,
            "orders": all_orders,
            "total_found": len(found_orders)
        }
        
        return {
            "success": True,
            "message": f"Análise de vendas para SKU {sku}",
            "analysis": analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao analisar vendas do SKU: {str(e)}")

def calculate_sales_stats(found_orders):
    """Calcula estatísticas de vendas a partir dos pedidos encontrados"""
    if not found_orders:
        return {}
    
    prices = []
    quantities = []
    revenues = []
    status_counts = Counter()
    
    for order, item in found_orders:
        unit_price = item.get("unit_price", 0)
        quantity = item.get("quantity", 0)
        revenue = unit_price * quantity
        
        prices.append(unit_price)
        quantities.append(quantity)
        revenues.append(revenue)
        
        if order.status:
            status_counts[order.status.name] += 1
    
    total_orders = len(found_orders)
    total_quantity = sum(quantities)
    total_revenue = sum(revenues)
    
    avg_price = sum(prices) / len(prices) if prices else 0
    min_price = min(prices) if prices else 0
    max_price = max(prices) if prices else 0
    
    paid_orders = status_counts.get("PAID", 0)
    cancelled_orders = status_counts.get("CANCELLED", 0)
    
    return {
        "total_orders": total_orders,
        "total_quantity": total_quantity,
        "total_revenue": total_revenue,
        "avg_price": avg_price,
        "min_price": min_price,
        "max_price": max_price,
        "paid_orders": paid_orders,
        "cancelled_orders": cancelled_orders
    }
