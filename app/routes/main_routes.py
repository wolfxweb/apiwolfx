from fastapi import APIRouter
from app.routes.auth_routes import auth_router
from app.routes.product_routes import product_router
from app.routes.user_routes import user_router
from app.routes.category_routes import category_router

# Router principal que agrupa todas as rotas
main_router = APIRouter()

# Incluir todas as rotas
main_router.include_router(auth_router)
main_router.include_router(product_router)
main_router.include_router(user_router)
main_router.include_router(category_router)
