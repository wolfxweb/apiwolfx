"""
Rotas para gerenciar estoque e depósitos
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Cookie, Body, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.controllers.auth_controller import AuthController
from app.controllers.stock_controller import StockController
from app.views.template_renderer import render_template

logger = logging.getLogger(__name__)

stock_router = APIRouter(prefix="/stock", tags=["Stock"])


@stock_router.post("/warehouses")
async def create_warehouse(
    name: str = Body(..., description="Nome do depósito"),
    type: str = Body(..., description="Tipo: fulfillment ou custom"),
    address: Optional[str] = Body(None, description="Endereço"),
    contact_info: Optional[dict] = Body(None, description="Informações de contato"),
    is_shared: bool = Body(False, description="Se é compartilhado"),
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Cria um novo depósito"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        
        if result.get("error"):
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        current_user = result["user"]
        company_id = current_user["company_id"]
        
        controller = StockController()
        result = controller.create_warehouse(
            company_id=company_id,
            name=name,
            type=type,
            address=address,
            contact_info=contact_info,
            is_shared=is_shared,
            db=db
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return JSONResponse(content=result, status_code=201)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Erro ao criar depósito: {str(e)}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")


@stock_router.get("/warehouses")
async def list_warehouses(
    include_shared: bool = Query(True, description="Incluir depósitos compartilhados"),
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Lista depósitos da empresa"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        
        if result.get("error"):
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        current_user = result["user"]
        company_id = current_user["company_id"]
        
        controller = StockController()
        result = controller.list_warehouses(
            company_id=company_id,
            include_shared=include_shared,
            db=db
        )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar depósitos: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@stock_router.get("/warehouses/{warehouse_id}")
async def get_warehouse(
    warehouse_id: int,
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Obtém um depósito específico"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        
        if result.get("error"):
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        current_user = result["user"]
        company_id = current_user["company_id"]
        
        controller = StockController()
        result = controller.get_warehouse(
            warehouse_id=warehouse_id,
            company_id=company_id,
            db=db
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar depósito: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@stock_router.put("/warehouses/{warehouse_id}")
async def update_warehouse(
    warehouse_id: int,
    name: Optional[str] = Body(None, description="Nome do depósito"),
    address: Optional[str] = Body(None, description="Endereço"),
    contact_info: Optional[dict] = Body(None, description="Informações de contato"),
    status: Optional[str] = Body(None, description="Status: active ou inactive"),
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Atualiza um depósito"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        
        if result.get("error"):
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        current_user = result["user"]
        company_id = current_user["company_id"]
        
        controller = StockController()
        result = controller.update_warehouse(
            warehouse_id=warehouse_id,
            company_id=company_id,
            name=name,
            address=address,
            contact_info=contact_info,
            status=status,
            db=db
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar depósito: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@stock_router.delete("/warehouses/{warehouse_id}")
async def delete_warehouse(
    warehouse_id: int,
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Remove um depósito"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        
        if result.get("error"):
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        current_user = result["user"]
        company_id = current_user["company_id"]
        
        controller = StockController()
        result = controller.delete_warehouse(
            warehouse_id=warehouse_id,
            company_id=company_id,
            db=db
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao remover depósito: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@stock_router.get("/stocks")
async def list_all_stocks(
    warehouse_id: Optional[int] = Query(None, description="Filtrar por depósito"),
    limit: int = Query(20, description="Limite de resultados"),
    offset: int = Query(0, description="Offset"),
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Lista todos os estoques"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        
        if result.get("error"):
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        current_user = result["user"]
        company_id = current_user["company_id"]
        
        controller = StockController()
        result = controller.list_all_stocks(
            company_id=company_id,
            warehouse_id=warehouse_id,
            limit=limit,
            offset=offset,
            db=db
        )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar estoques: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@stock_router.get("/products/{product_id}")
async def get_stock_by_product(
    product_id: int,
    warehouse_id: Optional[int] = Query(None, description="Filtrar por depósito"),
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Obtém estoque por produto"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        
        if result.get("error"):
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        current_user = result["user"]
        company_id = current_user["company_id"]
        
        controller = StockController()
        result = controller.get_stock_by_product(
            company_id=company_id,
            internal_product_id=product_id,
            warehouse_id=warehouse_id,
            db=db
        )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar estoque: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@stock_router.get("/announcements/{ml_item_id}")
async def get_stock_by_announcement(
    ml_item_id: str,
    warehouse_id: Optional[int] = Query(None, description="Filtrar por depósito"),
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Obtém estoque por anúncio"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        
        if result.get("error"):
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        current_user = result["user"]
        company_id = current_user["company_id"]
        
        controller = StockController()
        result = controller.get_stock_by_announcement(
            company_id=company_id,
            ml_item_id=ml_item_id,
            warehouse_id=warehouse_id,
            db=db
        )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar estoque: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@stock_router.put("/stocks/{product_stock_id}/quantity")
async def set_stock_quantity(
    product_stock_id: int,
    new_quantity: float = Body(..., description="Nova quantidade"),
    notes: Optional[str] = Body(None, description="Observações"),
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Define a quantidade absoluta do estoque"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        
        if result.get("error"):
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        current_user = result["user"]
        company_id = current_user["company_id"]
        
        controller = StockController()
        result = controller.set_stock_quantity(
            company_id=company_id,
            product_stock_id=product_stock_id,
            new_quantity=new_quantity,
            notes=notes,
            db=db
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao definir quantidade de estoque: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@stock_router.post("/adjust")
async def adjust_stock(
    warehouse_id: int = Body(..., description="ID do depósito"),
    quantity: float = Body(..., description="Quantidade (positivo para entrada, negativo para saída)"),
    internal_product_id: Optional[int] = Body(None, description="ID do produto interno"),
    ml_item_id: Optional[str] = Body(None, description="ID do anúncio ML"),
    notes: Optional[str] = Body(None, description="Observações"),
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Ajuste manual de estoque"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    if not internal_product_id and not ml_item_id:
        raise HTTPException(status_code=400, detail="Deve fornecer internal_product_id ou ml_item_id")
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        
        if result.get("error"):
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        current_user = result["user"]
        company_id = current_user["company_id"]
        
        controller = StockController()
        result = controller.adjust_stock(
            company_id=company_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            internal_product_id=internal_product_id,
            ml_item_id=ml_item_id,
            notes=notes,
            db=db
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao ajustar estoque: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@stock_router.post("/transfer")
async def transfer_stock(
    from_warehouse_id: int = Body(..., description="ID do depósito de origem"),
    to_warehouse_id: int = Body(..., description="ID do depósito de destino"),
    quantity: float = Body(..., description="Quantidade a transferir"),
    internal_product_id: Optional[int] = Body(None, description="ID do produto interno"),
    ml_item_id: Optional[str] = Body(None, description="ID do anúncio ML"),
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Transfere estoque entre depósitos"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    if not internal_product_id and not ml_item_id:
        raise HTTPException(status_code=400, detail="Deve fornecer internal_product_id ou ml_item_id")
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        
        if result.get("error"):
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        current_user = result["user"]
        company_id = current_user["company_id"]
        
        controller = StockController()
        result = controller.transfer_stock(
            company_id=company_id,
            from_warehouse_id=from_warehouse_id,
            to_warehouse_id=to_warehouse_id,
            quantity=quantity,
            internal_product_id=internal_product_id,
            ml_item_id=ml_item_id,
            db=db
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao transferir estoque: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@stock_router.get("/movements")
async def get_movement_history(
    product_stock_id: Optional[int] = Query(None, description="Filtrar por estoque"),
    warehouse_id: Optional[int] = Query(None, description="Filtrar por depósito"),
    internal_product_id: Optional[int] = Query(None, description="Filtrar por produto"),
    ml_item_id: Optional[str] = Query(None, description="Filtrar por anúncio"),
    movement_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    date_from: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
    limit: int = Query(100, description="Limite de resultados"),
    offset: int = Query(0, description="Offset"),
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Obtém histórico de movimentações"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        
        if result.get("error"):
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        current_user = result["user"]
        company_id = current_user["company_id"]
        
        # Converter strings de data para datetime
        from datetime import datetime
        date_from_dt = None
        date_to_dt = None
        
        if date_from:
            try:
                date_from_dt = datetime.strptime(date_from, "%Y-%m-%d")
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_dt = datetime.strptime(date_to, "%Y-%m-%d")
                # Adicionar 23:59:59 para incluir o dia inteiro
                date_to_dt = date_to_dt.replace(hour=23, minute=59, second=59)
            except ValueError:
                pass
        
        controller = StockController()
        result = controller.get_movement_history(
            company_id=company_id,
            product_stock_id=product_stock_id,
            warehouse_id=warehouse_id,
            internal_product_id=internal_product_id,
            ml_item_id=ml_item_id,
            movement_type=movement_type,
            date_from=date_from_dt,
            date_to=date_to_dt,
            limit=limit,
            offset=offset,
            db=db
        )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@stock_router.get("/products/{internal_product_id}/announcements")
async def get_product_announcements_config(
    internal_product_id: int,
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Lista anúncios de um produto interno e suas configurações de estoque"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        
        if result.get("error"):
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        current_user = result["user"]
        company_id = current_user["company_id"]
        
        controller = StockController()
        result = controller.get_announcement_warehouse_config(
            company_id=company_id,
            internal_product_id=internal_product_id,
            db=db
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar configurações de anúncios: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@stock_router.post("/announcements/{ml_item_id}/warehouse")
async def configure_announcement_warehouse(
    ml_item_id: str,
    internal_product_id: int = Body(..., description="ID do produto interno"),
    warehouse_id: int = Body(..., description="ID do depósito"),
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Configura qual depósito um anúncio específico deve usar"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        
        if result.get("error"):
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        current_user = result["user"]
        company_id = current_user["company_id"]
        
        controller = StockController()
        result = controller.configure_announcement_warehouse(
            company_id=company_id,
            internal_product_id=internal_product_id,
            ml_item_id=ml_item_id,
            warehouse_id=warehouse_id,
            db=db
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao configurar depósito do anúncio: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@stock_router.post("/products/{internal_product_id}/announcements/bulk-warehouse")
async def bulk_configure_announcement_warehouse(
    internal_product_id: int,
    warehouse_id_fulfillment: Optional[int] = Body(None, description="ID do depósito para anúncios Full"),
    warehouse_id_normal: Optional[int] = Body(None, description="ID do depósito para anúncios normais"),
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Configura depósitos em massa para anúncios de um produto interno"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    if not warehouse_id_fulfillment and not warehouse_id_normal:
        raise HTTPException(status_code=400, detail="Deve fornecer pelo menos um depósito (fulfillment ou normal)")
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        
        if result.get("error"):
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        current_user = result["user"]
        company_id = current_user["company_id"]
        
        controller = StockController()
        result = controller.bulk_configure_announcement_warehouse(
            company_id=company_id,
            internal_product_id=internal_product_id,
            warehouse_id_fulfillment=warehouse_id_fulfillment,
            warehouse_id_normal=warehouse_id_normal,
            db=db
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao configurar depósitos em massa: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@stock_router.post("/announcements/bulk-warehouse-all")
async def bulk_configure_all_announcements_warehouse(
    warehouse_id_fulfillment: Optional[int] = Body(None, description="ID do depósito para anúncios Full"),
    warehouse_id_normal: Optional[int] = Body(None, description="ID do depósito para anúncios normais"),
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Configura depósitos em massa para TODOS os anúncios da empresa"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    if not warehouse_id_fulfillment and not warehouse_id_normal:
        raise HTTPException(status_code=400, detail="Deve fornecer pelo menos um depósito (fulfillment ou normal)")
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        
        if result.get("error"):
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        current_user = result["user"]
        company_id = current_user["company_id"]
        
        controller = StockController()
        result = controller.bulk_configure_all_announcements_warehouse(
            company_id=company_id,
            warehouse_id_fulfillment=warehouse_id_fulfillment,
            warehouse_id_normal=warehouse_id_normal,
            db=db
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao configurar todos os anúncios em massa: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@stock_router.delete("/stocks/clear-all")
async def clear_all_stocks(
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Remove todos os estoques da empresa"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        
        if result.get("error"):
            raise HTTPException(status_code=401, detail=result.get("error"))
        
        current_user = result["user"]
        company_id = current_user["company_id"]
        
        controller = StockController()
        result = controller.clear_all_stocks(
            company_id=company_id,
            db=db
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao limpar todos os estoques: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

