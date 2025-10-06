from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from app.routes.auth_routes import auth_router
from app.routes.product_routes import product_router
from app.routes.internal_product_routes import internal_product_router
from app.routes.user_routes import user_router
from app.routes.category_routes import category_router
from app.controllers.auth_controller import get_current_user
from app.views.template_renderer import render_template

# Router principal que agrupa todas as rotas
main_router = APIRouter()

# Incluir todas as rotas
main_router.include_router(auth_router)
main_router.include_router(product_router)
main_router.include_router(internal_product_router)
main_router.include_router(user_router)
main_router.include_router(category_router)

@main_router.get("/products/imported", response_class=HTMLResponse)
async def products_imported_page(request: Request, session_token: str = Query(...)):
    """Página de produtos importados"""
    user = get_current_user(session_token)
    return render_template("products_imported.html", user=user)

@main_router.get("/internal-products", response_class=HTMLResponse)
async def internal_products_page(request: Request, session_token: str = Query(...)):
    """Página de produtos internos"""
    user = get_current_user(session_token)
    return render_template("internal_products.html", user=user)
