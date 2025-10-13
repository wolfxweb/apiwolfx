from fastapi import APIRouter, Depends, Request, Query, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from app.routes.auth_routes import auth_router
from app.routes.product_routes import product_router
from app.routes.internal_product_routes import internal_product_router
from app.routes.user_routes import user_router
from app.routes.category_routes import category_router
from app.routes.sku_management_routes import sku_management_router
from app.controllers.auth_controller import get_current_user
from app.views.template_renderer import render_template
from app.services.auto_sync_service import AutoSyncService
from app.services.catalog_monitoring_service import CatalogMonitoringService
from app.config.database import get_db
from sqlalchemy.orm import Session

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

@main_router.get("/internal-products", response_class=HTMLResponse)
async def internal_products_page(request: Request, session_token: str = Cookie(None)):
    """Página de produtos internos - apenas usuários logados"""
    if not session_token:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    try:
        user = get_current_user(session_token)
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

