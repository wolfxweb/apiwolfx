"""
Rotas para expedição e notas fiscais
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Cookie, Query
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import io
import logging
import httpx

from app.config.database import get_db
from app.controllers.shipment_controller import ShipmentController
from app.controllers.auth_controller import AuthController
from app.services.token_manager import TokenManager
from app.views.template_renderer import render_template

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shipments", tags=["Expedição"])

@router.get("/", response_class=HTMLResponse)
async def shipments_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página de expedição de produtos"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    result = AuthController().get_user_by_session(session_token, db)
    if result.get("error"):
        return RedirectResponse(url="/auth/login", status_code=302)
    
    user_data = result["user"]
    return render_template("shipments.html", user=user_data)

@router.get("/pending")
async def list_pending_shipments(
    request: Request,
    search: Optional[str] = Query(""),
    invoice_status: Optional[str] = Query(""),
    status: Optional[str] = Query(""),
    page: Optional[int] = Query(1, ge=1),
    limit: Optional[int] = Query(100, ge=1, le=5000),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Lista pedidos para expedição com filtros e paginação"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = ShipmentController(db)
        result = controller.list_pending_shipments(
            company_id, 
            search=search, 
            invoice_status=invoice_status,
            status=status,
            page=page,
            limit=limit,
            start_date=start_date,
            end_date=end_date
        )
        
        return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@router.post("/sync-invoices")
async def sync_invoice_status(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Sincroniza status das notas fiscais com o Mercado Livre"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        # Buscar token de acesso usando TokenManager
        token_manager = TokenManager(db)
        
        # Buscar um usuário ativo da empresa
        from app.models.saas_models import User
        user_db = db.query(User).filter(
            User.company_id == company_id,
            User.is_active == True
        ).first()
        
        if not user_db:
            return JSONResponse(content={"error": "Nenhum usuário ativo encontrado para esta empresa"}, status_code=404)
        
        access_token = token_manager.get_valid_token(user_db.id)
        
        if not access_token:
            return JSONResponse(content={"error": "Token de acesso inválido ou expirado"}, status_code=401)
        
        controller = ShipmentController(db)
        result = controller.sync_invoices(company_id, access_token)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@router.post("/sync-single-invoice/{order_id}")
async def sync_single_order_invoice(
    order_id: str,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Sincroniza nota fiscal de um pedido específico"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        # Buscar token de acesso usando TokenManager
        token_manager = TokenManager(db)
        
        # Buscar um usuário ativo da empresa
        from app.models.saas_models import User
        user_db = db.query(User).filter(
            User.company_id == company_id,
            User.is_active == True
        ).first()
        
        if not user_db:
            return JSONResponse(content={"error": "Nenhum usuário ativo encontrado para esta empresa"}, status_code=404)
        
        access_token = token_manager.get_valid_token(user_db.id)
        
        if not access_token:
            return JSONResponse(content={"error": "Token de acesso inválido ou expirado"}, status_code=401)
        
        controller = ShipmentController(db)
        result = controller.sync_single_order_invoice(order_id, company_id, access_token)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@router.post("/bulk-update")
async def bulk_update_orders(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Atualiza múltiplos pedidos em lote"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔄 [BULK UPDATE] Recebida requisição de atualização em lote")
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        # Obter dados da requisição
        body = await request.json()
        order_ids = body.get("order_ids", [])
        
        logger.info(f"📋 [BULK UPDATE] Recebidos {len(order_ids)} pedidos para atualizar: {order_ids}")
        
        if not order_ids:
            return JSONResponse(content={"error": "Nenhum pedido selecionado"}, status_code=400)
        
        # Buscar token de acesso usando TokenManager
        token_manager = TokenManager(db)
        
        # Buscar um usuário ativo da empresa
        from app.models.saas_models import User
        user_db = db.query(User).filter(
            User.company_id == company_id,
            User.is_active == True
        ).first()
        
        if not user_db:
            return JSONResponse(content={"error": "Nenhum usuário ativo encontrado para esta empresa"}, status_code=404)
        
        access_token = token_manager.get_valid_token(user_db.id)
        
        if not access_token:
            return JSONResponse(content={"error": "Token de acesso inválido ou expirado"}, status_code=401)
        
        controller = ShipmentController(db)
        
        # Processar cada pedido
        results = []
        for order_id in order_ids:
            try:
                result = controller.sync_single_order_invoice(order_id, company_id, access_token)
                results.append(result)
                logger.info(f"✅ Result for order {order_id}: success={result.get('success')}, error={result.get('error')}, message={result.get('message')}")
            except Exception as e:
                logger.error(f"❌ Error processing order {order_id}: {e}")
                results.append({"success": False, "error": str(e)})
        
        # Contar sucessos e falhas
        success_count = sum(1 for r in results if r.get("success"))
        failure_count = len(results) - success_count
        
        logger.info(f"📊 Total: {len(results)}, Success: {success_count}, Failure: {failure_count}")
        
        return JSONResponse(content={
            "success": True,
            "message": f"Atualizados {success_count} pedidos com sucesso, {failure_count} falharam",
            "total": len(order_ids),
            "success_count": success_count,
            "failure_count": failure_count,
            "results": results
        })
        
    except Exception as e:
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@router.get("/download-invoice/{order_id}")
async def download_invoice(
    order_id: str,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Download da nota fiscal do pedido"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        # Buscar pedido no banco
        from app.models.saas_models import MLOrder
        order = db.query(MLOrder).filter(
            MLOrder.ml_order_id == order_id,
            MLOrder.company_id == company_id
        ).first()
        
        if not order:
            return JSONResponse(content={"error": "Pedido não encontrado"}, status_code=404)
        
        if not order.invoice_pdf_url:
            return JSONResponse(content={"error": "Nota fiscal não disponível"}, status_code=404)
        
        # Buscar token de acesso
        token_manager = TokenManager(db)
        from app.models.saas_models import User
        user_db = db.query(User).filter(
            User.company_id == company_id,
            User.is_active == True
        ).first()
        
        if not user_db:
            return JSONResponse(content={"error": "Usuário não encontrado"}, status_code=404)
        
        access_token = token_manager.get_valid_token(user_db.id)
        if not access_token:
            return JSONResponse(content={"error": "Token inválido"}, status_code=401)
        
        # Baixar PDF da API do Mercado Livre
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(order.invoice_pdf_url, headers=headers, timeout=30.0)
            
            if response.status_code != 200:
                logger.error(f"Erro ao baixar PDF: {response.status_code}")
                return JSONResponse(content={"error": "Erro ao baixar nota fiscal"}, status_code=500)
            
            # Preparar nome do arquivo
            invoice_filename = f"NF-{order_id}"
            if order.invoice_number:
                invoice_filename = f"NF-{order.invoice_number}"
                if order.invoice_series:
                    invoice_filename = f"NF-{order.invoice_number}-{order.invoice_series}"
            
            invoice_filename += ".pdf"
            
            # Retornar arquivo como download
            return StreamingResponse(
                io.BytesIO(response.content),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{invoice_filename}"'
                }
            )
    
    except Exception as e:
        logger.error(f"Erro ao baixar nota fiscal: {e}")
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@router.get("/stats")
async def get_stats(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Retorna estatísticas dos pedidos"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = ShipmentController(db)
        result = controller.get_stats(company_id)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@router.get("/tab-counts")
async def get_tab_counts(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Retorna contadores de pedidos por status para as abas"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        controller = ShipmentController(db)
        result = controller.get_tab_counts(company_id)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(content={
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@router.post("/sync-recent")
async def sync_recent_orders(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Sincroniza pedidos dos últimos 2 dias com o Mercado Livre"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        # Buscar token de acesso usando TokenManager
        token_manager = TokenManager(db)
        
        # Buscar um usuário ativo da empresa
        from app.models.saas_models import User
        user_db = db.query(User).filter(
            User.company_id == company_id,
            User.is_active == True
        ).first()
        
        if not user_db:
            return JSONResponse(content={"error": "Nenhum usuário ativo encontrado para esta empresa"}, status_code=404)
        
        access_token = token_manager.get_valid_token(user_db.id)
        
        if not access_token:
            return JSONResponse(content={"error": "Token de acesso inválido ou expirado"}, status_code=401)
        
        # Usar o MLOrdersController para sincronizar pedidos
        from app.controllers.ml_orders_controller import MLOrdersController
        controller = MLOrdersController(db)
        
        # Sincronizar pedidos dos últimos 2 dias
        result = controller.sync_orders(company_id=company_id, ml_account_id=None, is_full_import=False, days_back=2)
        
        return JSONResponse(content={
            "success": True,
            "message": f"{result.get('total_saved', 0)} novos pedidos, {result.get('total_updated', 0)} pedidos atualizados",
            **result
        })
        
    except Exception as e:
        logger.error(f"Erro ao sincronizar pedidos recentes: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

