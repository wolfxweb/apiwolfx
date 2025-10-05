from fastapi import APIRouter, Depends, Request, Cookie, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging
import csv
import io
import json
from datetime import datetime

from app.config.database import get_db
from app.controllers.ml_orders_controller import MLOrdersController
from app.controllers.auth_controller import AuthController

ml_orders_router = APIRouter()

@ml_orders_router.get("/orders", response_class=HTMLResponse)
async def orders_list(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Lista de pedidos do Mercado Libre"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    
    from app.views.template_renderer import render_template
    return render_template("ml_orders.html", user=user_data)

@ml_orders_router.get("/orders/{ml_order_id}", response_class=HTMLResponse)
async def order_details_page(
    ml_order_id: int,
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de detalhes de um pedido específico"""
    try:
        if not session_token:
            return RedirectResponse(url="/auth/login", status_code=302)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return RedirectResponse(url="/auth/login", status_code=302)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        # Buscar o pedido pelo ml_order_id primeiro
        from app.models.saas_models import MLOrder
        order = db.query(MLOrder).filter(
            MLOrder.ml_order_id == ml_order_id,
            MLOrder.company_id == company_id
        ).first()
        
        if not order:
            from app.views.template_renderer import render_template
            return render_template("error.html", error_message="Pedido não encontrado", back_url="/ml/orders")
        
        # Buscar detalhes do pedido usando o ID interno
        controller = MLOrdersController(db)
        order_details = controller.get_order_details(company_id, order.id)
        
        if not order_details.get("success"):
            from app.views.template_renderer import render_template
            return render_template("error.html", error_message=order_details.get("error", "Pedido não encontrado"), back_url="/ml/orders")
        
        from app.views.template_renderer import render_template
        return render_template("ml_order_details.html", request=request, user=user_data, order=order_details.get("order"))
        
    except Exception as e:
        logging.error(f"Erro na página de detalhes do pedido: {e}")
        from app.views.template_renderer import render_template
        return render_template("error.html", error_message="Erro ao carregar detalhes do pedido", back_url="/ml/orders")

@ml_orders_router.get("/api/orders")
async def get_orders_api(
    ml_account_id: Optional[int] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    status_filter: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar orders"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = MLOrdersController(db)
        data = controller.get_orders_list(
            company_id=company_id,
            ml_account_id=ml_account_id,
            limit=limit,
            offset=offset,
            status_filter=status_filter,
            date_from=date_from,
            date_to=date_to
        )
        
        return JSONResponse(content=data)
        
    except Exception as e:
        logging.error(f"Erro no endpoint orders: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ml_orders_router.get("/api/orders/sync")
async def sync_orders_api(
    ml_account_id: Optional[int] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para sincronizar orders da API do Mercado Libre (apenas recentes)"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = MLOrdersController(db)
        result = controller.sync_orders(company_id=company_id, ml_account_id=ml_account_id, is_full_import=False)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logging.error(f"Erro no endpoint sync orders: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ml_orders_router.get("/api/orders/import")
async def import_orders_api(
    ml_account_id: Optional[int] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para importar TODOS os orders da API do Mercado Libre"""
    try:
        logging.info(f"Iniciando importação - ml_account_id: {ml_account_id}")
        
        if not session_token:
            logging.warning("Sessão não encontrada")
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            logging.warning(f"Erro de autenticação: {result.get('error')}")
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        logging.info(f"Usuário autenticado - company_id: {company_id}")
        
        controller = MLOrdersController(db)
        logging.info("Iniciando sync_orders...")
        result = controller.sync_orders(company_id=company_id, ml_account_id=ml_account_id, is_full_import=True)
        logging.info(f"Resultado do sync_orders: {result}")
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logging.error(f"Erro no endpoint import orders: {e}", exc_info=True)
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ml_orders_router.get("/api/orders/{order_id}")
async def get_order_details_api(
    order_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar detalhes de uma order específica"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = MLOrdersController(db)
        result = controller.get_order_details(company_id=company_id, order_id=order_id)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logging.error(f"Erro no endpoint order details: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ml_orders_router.get("/api/orders/summary")
async def get_orders_summary_api(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar resumo de orders"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = MLOrdersController(db)
        result = controller.get_orders_summary(company_id=company_id)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logging.error(f"Erro no endpoint orders summary: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ml_orders_router.post("/api/orders/delete")
async def delete_orders_api(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para remover pedidos selecionados"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        # Obter dados do corpo da requisição
        body = await request.json()
        order_ids = body.get("order_ids", [])
        
        if not order_ids:
            return JSONResponse(content={
                "success": False,
                "error": "Nenhum pedido selecionado"
            }, status_code=400)
        
        controller = MLOrdersController(db)
        result = controller.delete_orders(company_id=company_id, order_ids=order_ids)
        
        if result.get("success"):
            return JSONResponse(content=result)
        else:
            return JSONResponse(content=result, status_code=400)
        
    except Exception as e:
        logging.error(f"Erro no endpoint delete orders: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@ml_orders_router.post("/api/orders/delete-all")
async def delete_all_orders_api(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para remover todos os pedidos da empresa"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = MLOrdersController(db)
        result = controller.delete_all_orders(company_id=company_id)
        
        if result.get("success"):
            return JSONResponse(content=result)
        else:
            return JSONResponse(content=result, status_code=400)
        
    except Exception as e:
        logging.error(f"Erro no endpoint delete all orders: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)
