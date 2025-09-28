from fastapi import APIRouter, Query
from app.controllers.auth_controller import AuthController

# Router para rotas de autenticação
auth_router = APIRouter(prefix="", tags=["Authentication"])

# Instância do controller
auth_controller = AuthController()


@auth_router.get("/")
async def get_login_page():
    """Página inicial com instruções de login"""
    return auth_controller.get_login_page()


@auth_router.get("/login")
async def login(state: str = None):
    """Redireciona para o login do Mercado Livre"""
    return auth_controller.redirect_to_login(state)


@auth_router.get("/callback")
async def callback(code: str = None, error: str = None, state: str = None):
    """Recebe o callback do Mercado Livre"""
    return await auth_controller.handle_callback(code, error, state)


@auth_router.get("/user")
async def get_user_info(access_token: str = Query(None, description="Token de acesso")):
    """Obtém informações do usuário"""
    return await auth_controller.get_user_info(access_token)
