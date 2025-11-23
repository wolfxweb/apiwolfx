from fastapi import APIRouter, Depends, Request, Query, Cookie, BackgroundTasks
from typing import Optional
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.routes.auth_routes import auth_router
from app.routes.product_routes import product_router
from app.routes.internal_product_routes import internal_product_router
from app.routes.user_routes import user_router
from app.routes.category_routes import category_router
from app.routes.sku_management_routes import sku_management_router
from app.controllers.auth_controller import get_current_user, AuthController
from app.views.template_renderer import render_template
from app.services.auto_sync_service import AutoSyncService
from app.services.catalog_monitoring_service import CatalogMonitoringService
from app.config.database import get_db
from sqlalchemy.orm import Session
import logging

# Router principal que agrupa todas as rotas
main_router = APIRouter()

# Incluir todas as rotas
main_router.include_router(auth_router)
main_router.include_router(product_router)
main_router.include_router(internal_product_router)
main_router.include_router(user_router)
main_router.include_router(category_router)
main_router.include_router(sku_management_router)

@main_router.get("/products/imported", response_class=HTMLResponse)
async def products_imported_page(request: Request, session_token: str = Cookie(None)):
    """Página de produtos importados - apenas usuários logados"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    try:
        user = get_current_user(session_token)
        return render_template("products_imported.html", user=user)
    except Exception:
        # Se token expirado ou inválido, redirecionar para login
        return RedirectResponse(url="/auth/login", status_code=302)

@main_router.post("/company/toggle-ml-orders-receivables")
async def toggle_ml_orders_receivables(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Altera configuração de considerar pedidos ML como contas a receber"""
    from app.controllers.auth_controller import AuthController
    
    if not session_token:
        return {"success": False, "error": "Sessão não encontrada"}
    
    auth_controller = AuthController()
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        return {"success": False, "error": "Sessão inválida"}
    
    user_data = result["user"]
    company_id = user_data.get("company_id")
    
    try:
        # Buscar empresa
        from app.models.saas_models import Company
        company = db.query(Company).filter(Company.id == company_id).first()
        
        if not company:
            return {"success": False, "error": "Empresa não encontrada"}
        
        # Alternar configuração
        company.ml_orders_as_receivables = not company.ml_orders_as_receivables
        db.commit()
        
        return {
            "success": True, 
            "message": f"Configuração alterada para: {'Ativado' if company.ml_orders_as_receivables else 'Desativado'}",
            "ml_orders_as_receivables": company.ml_orders_as_receivables
        }
        
    except Exception as e:
        db.rollback()
        return {"success": False, "error": f"Erro interno: {str(e)}"}

@main_router.get("/internal-products", response_class=HTMLResponse)
async def internal_products_page(request: Request, session_token: str = Cookie(None), db: Session = Depends(get_db)):
    """Página de produtos internos - apenas usuários logados"""
    from app.controllers.auth_controller import AuthController
    
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    try:
        auth_controller = AuthController()
        result = auth_controller.get_user_by_session(session_token, db)
        if result.get("error"):
            return RedirectResponse(url="/auth/login", status_code=302)
        
        # Verificar se plano está inativo e redirecionar para profile
        if result.get("should_redirect_to_profile"):
            return RedirectResponse(url="/auth/profile", status_code=302)
        
        user = result["user"]
        return render_template("internal_products.html", user=user)
    except Exception:
        # Se token expirado ou inválido, redirecionar para login
        return RedirectResponse(url="/auth/login", status_code=302)

# Endpoint temporário para testar sincronização
@main_router.get("/api/test/sync")
async def test_sync(db: Session = Depends(get_db)):
    """Endpoint temporário para testar sincronização manual"""
    try:
        auto_sync = AutoSyncService()
        
        # Testar sincronização recente
        result_recent = auto_sync.sync_recent_orders()
        
        return {
            "success": True,
            "message": "Teste de sincronização executado",
            "recent_sync": result_recent,
            "timestamp": "2025-01-13T12:57:00"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": "2025-01-13T12:57:00"
        }

@main_router.get("/api/test/catalog-monitoring")
async def test_catalog_monitoring(db: Session = Depends(get_db)):
    """Endpoint temporário para testar monitoramento de catálogo"""
    try:
        catalog_service = CatalogMonitoringService(db)
        result = catalog_service.collect_catalog_data_for_all_active()
        
        return {
            "success": True,
            "message": "Teste de monitoramento de catálogo executado",
            "result": result,
            "timestamp": "2025-01-13T12:57:00"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": "2025-01-13T12:57:00"
        }

@main_router.get("/orders/sync")
async def sync_orders_api(
    background_tasks: BackgroundTasks,
    ml_account_id: Optional[int] = Query(None),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    API para sincronizar orders da API do Mercado Libre (em background)
    Rota alternativa para /ml/api/orders/sync - permite acesso via /api/orders/sync
    """
    try:
        logging.info(f"🔍 SYNC ENDPOINT (/api/orders/sync): Recebeu requisição")
        
        if not session_token:
            logging.warning("❌ Sem session_token")
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            logging.warning(f"❌ Sessão inválida: {result.get('error')}")
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        logging.info(f"✅ Usuário autenticado: company_id={company_id}")
        logging.info(f"🚀 Iniciando sincronização em background...")
        
        # Adicionar tarefa em background
        from app.config.database import SessionLocal
        from app.controllers.ml_orders_controller import MLOrdersController
        
        def sync_in_background():
            """Executa sincronização em background"""
            db_bg = SessionLocal()
            try:
                controller = MLOrdersController(db_bg)
                result = controller.sync_orders(company_id=company_id, ml_account_id=ml_account_id, is_full_import=False)
                logging.info(f"✅ BACKGROUND SYNC CONCLUÍDA: {result.get('total_saved', 0)} novos, {result.get('total_updated', 0)} atualizados")
            except Exception as e:
                logging.error(f"❌ BACKGROUND SYNC ERRO: {e}", exc_info=True)
            finally:
                db_bg.close()
        
        background_tasks.add_task(sync_in_background)
        
        # Retornar imediatamente
        response_data = {
            "success": True,
            "message": "Sincronização iniciada em background. Aguarde alguns minutos e atualize a página.",
            "status": "processing"
        }
        
        logging.info(f"✅ Retornando resposta imediata")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logging.error(f"Erro no endpoint sync orders: {e}", exc_info=True)
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

