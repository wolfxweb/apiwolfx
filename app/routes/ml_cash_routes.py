"""
Rotas para gerenciar lançamentos automáticos no caixa de pedidos ML
"""
from fastapi import APIRouter, Depends, HTTPException, Cookie, Request
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.config.database import get_db
from app.controllers.auth_controller import AuthController
from app.services.ml_cash_service import MLCashService
from app.views.template_renderer import render_template

logger = logging.getLogger(__name__)

# Router para lançamentos no caixa
ml_cash_router = APIRouter()

def get_company_id_from_user(user_data):
    """Extrai company_id dos dados do usuário"""
    return user_data.get("company", {}).get("id")

@ml_cash_router.post("/api/ml-cash/process")
async def process_cash_entries(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Processa lançamentos no caixa para pedidos ML recebidos a partir deste mês
    """
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        if result.get("error"):
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
        
        user_data = result["user"]
        company_id = get_company_id_from_user(user_data)
        
        if not company_id:
            raise HTTPException(status_code=400, detail="Company ID não encontrado")
        
        # Processar lançamentos no caixa
        logger.info(f"🔍 Iniciando processamento de lançamentos para company_id={company_id}")
        cash_service = MLCashService(db)
        result = cash_service.process_cash_entries_for_received_orders(company_id)
        logger.info(f"📊 Resultado do processamento: {result}")
        
        if result.get("success"):
            return JSONResponse(content={
                "success": True,
                "message": result.get("message"),
                "processed_count": result.get("processed_count", 0),
                "total_amount": result.get("total_amount", 0.0)
            })
        else:
            raise HTTPException(status_code=500, detail=result.get("error"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar lançamentos no caixa: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@ml_cash_router.get("/api/ml-cash/pending")
async def get_pending_cash_entries(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Retorna lista de pedidos que podem ser lançados no caixa
    """
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        if result.get("error"):
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
        
        user_data = result["user"]
        company_id = get_company_id_from_user(user_data)
        
        if not company_id:
            raise HTTPException(status_code=400, detail="Company ID não encontrado")
        
        # Buscar pedidos pendentes
        cash_service = MLCashService(db)
        pending_orders = cash_service.get_pending_cash_entries(company_id)
        
        return JSONResponse(content={
            "success": True,
            "pending_orders": pending_orders,
            "count": len(pending_orders)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar pedidos pendentes: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@ml_cash_router.get("/api/ml-cash/status")
async def get_cash_status(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Retorna status dos lançamentos no caixa
    """
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        if result.get("error"):
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
        
        user_data = result["user"]
        company_id = get_company_id_from_user(user_data)
        
        if not company_id:
            raise HTTPException(status_code=400, detail="Company ID não encontrado")
        
        # Buscar estatísticas
        from app.models.saas_models import MLOrder, OrderStatus
        from sqlalchemy import and_, or_, func
        
        # Pedidos recebidos já lançados
        already_processed = db.query(func.count(MLOrder.id)).filter(
            and_(
                MLOrder.company_id == company_id,
                MLOrder.cash_entry_created == True
            )
        ).scalar() or 0
        
        # Pedidos recebidos pendentes de lançamento
        pending_processed = db.query(func.count(MLOrder.id)).filter(
            and_(
                MLOrder.company_id == company_id,
                MLOrder.cash_entry_created == False,
                or_(
                    MLOrder.status == OrderStatus.DELIVERED,
                    and_(
                        MLOrder.status == OrderStatus.PAID,
                        MLOrder.shipping_status == "delivered"
                    )
                )
            )
        ).scalar() or 0
        
        # Valor total já lançado
        total_processed_amount = db.query(func.sum(MLOrder.cash_entry_amount)).filter(
            and_(
                MLOrder.company_id == company_id,
                MLOrder.cash_entry_created == True
            )
        ).scalar() or 0.0
        
        return JSONResponse(content={
            "success": True,
            "status": {
                "already_processed": already_processed,
                "pending_processed": pending_processed,
                "total_processed_amount": float(total_processed_amount)
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar status dos lançamentos: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@ml_cash_router.get("/ml-cash/history", response_class=HTMLResponse)
async def ml_cash_history_page(
    request: Request,
    account_id: Optional[int] = None,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Página de histórico de lançamentos no caixa
    """
    try:
        if not session_token:
            return HTMLResponse(content="""
                <script>
                    alert('Sessão não encontrada. Redirecionando para o login...');
                    window.location.href = '/auth/login';
                </script>
            """, status_code=401)
        
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        if result.get("error"):
            return HTMLResponse(content="""
                <script>
                    alert('Sessão inválida ou expirada. Redirecionando para o login...');
                    window.location.href = '/auth/login';
                </script>
            """, status_code=401)
        
        return render_template("ml_cash_history.html", user=result["user"])
        
    except Exception as e:
        logger.error(f"Erro ao carregar página de histórico: {e}")
        return HTMLResponse(content=f"<h1>Erro interno: {str(e)}</h1>", status_code=500)

@ml_cash_router.get("/api/ml-cash/history")
async def get_cash_history(
    account_id: Optional[int] = None,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Retorna histórico completo de lançamentos no caixa
    """
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        if result.get("error"):
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
        
        user_data = result["user"]
        company_id = get_company_id_from_user(user_data)
        
        if not company_id:
            raise HTTPException(status_code=400, detail="Company ID não encontrado")
        
        # Buscar histórico de lançamentos
        from app.models.saas_models import MLOrder, OrderStatus
        from app.models.financial_models import FinancialAccount
        from sqlalchemy import and_, or_, func, desc
        
        # Query otimizada para buscar pedidos ML da empresa
        filters = [
            MLOrder.company_id == company_id,
            or_(
                MLOrder.status == OrderStatus.DELIVERED,
                and_(
                    MLOrder.status == OrderStatus.PAID,
                    MLOrder.shipping_status == "delivered"
                )
            )
        ]
        
        # Query otimizada com JOIN para buscar dados da conta em uma única consulta
        from sqlalchemy.orm import joinedload
        
        orders_query = db.query(MLOrder).options(
            joinedload(MLOrder.cash_entry_account)
        ).filter(and_(*filters)).order_by(desc(MLOrder.date_closed))
        
        # Limitar resultados para melhor performance (últimos 1000 pedidos)
        orders = orders_query.limit(1000).all()
        
        # Log simplificado para performance
        logger.info(f"🔍 Histórico ML carregado: {len(orders)} pedidos para company_id={company_id}")
        
        # Processar dados para o frontend (otimizado)
        history_data = []
        for order in orders:
            net_amount = float(order.total_amount or 0) - float(order.total_fees or 0)
            
            # Usar dados já carregados com JOIN (sem consulta adicional)
            account_name = None
            if hasattr(order, 'cash_entry_account') and order.cash_entry_account:
                account_name = order.cash_entry_account.account_name
            
            history_data.append({
                "ml_order_id": order.ml_order_id,
                "buyer_nickname": order.buyer_nickname,
                "date_closed": order.date_closed.isoformat() if order.date_closed else None,
                "status": str(order.status),
                "shipping_status": order.shipping_status,
                "total_amount": float(order.total_amount or 0),
                "total_fees": float(order.total_fees or 0),
                "net_amount": net_amount,
                "cash_entry_created": order.cash_entry_created,
                "cash_entry_date": order.cash_entry_date.isoformat() if order.cash_entry_date else None,
                "cash_entry_amount": float(order.cash_entry_amount or 0),
                "cash_entry_account_name": account_name
            })
        
        # Calcular estatísticas
        processed_orders = [o for o in history_data if o["cash_entry_created"]]
        pending_orders = [o for o in history_data if not o["cash_entry_created"]]
        
        summary = {
            "total_processed_amount": sum(o["cash_entry_amount"] for o in processed_orders),
            "pending_count": len(pending_orders),
            "processed_count": len(processed_orders),
            "pending_amount": sum(o["net_amount"] for o in pending_orders)
        }
        
        return JSONResponse(content={
            "success": True,
            "history": history_data,
            "summary": summary
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@ml_cash_router.post("/api/ml-cash/process-single/{order_id}")
async def process_single_cash_entry(
    order_id: str,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Processa lançamento no caixa para um pedido específico
    """
    try:
        if not session_token:
            raise HTTPException(status_code=401, detail="Token de sessão necessário")
        
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        if result.get("error"):
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
        
        user_data = result["user"]
        company_id = get_company_id_from_user(user_data)
        
        if not company_id:
            raise HTTPException(status_code=400, detail="Company ID não encontrado")
        
        # Buscar o pedido específico
        from app.models.saas_models import MLOrder
        order = db.query(MLOrder).filter(
            and_(
                MLOrder.company_id == company_id,
                MLOrder.ml_order_id == order_id
            )
        ).first()
        
        if not order:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")
        
        if order.cash_entry_created:
            raise HTTPException(status_code=400, detail="Pedido já foi lançado no caixa")
        
        # Processar lançamento
        cash_service = MLCashService(db)
        result = cash_service.process_cash_entries_for_received_orders(company_id)
        
        if result.get("success"):
            return JSONResponse(content={
                "success": True,
                "message": f"Pedido {order_id} processado com sucesso",
                "processed_count": result.get("processed_count", 0),
                "total_amount": result.get("total_amount", 0.0)
            })
        else:
            raise HTTPException(status_code=500, detail=result.get("error"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar pedido específico: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
