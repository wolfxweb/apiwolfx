from fastapi import HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from app.services.mercadolibre_service import MercadoLivreService
from app.models.mercadolibre_models import MLToken, MLUser, AuthResponse
from app.views.template_renderer import TemplateRenderer


class AuthController:
    """Controller para autenticação com Mercado Livre"""
    
    def __init__(self):
        self.ml_service = MercadoLivreService()
        self.template_renderer = TemplateRenderer()
    
    def get_login_page(self) -> HTMLResponse:
        """Retorna página inicial com instruções de login"""
        return self.template_renderer.render_home()
    
    def redirect_to_login(self, state: str = None) -> RedirectResponse:
        """Redireciona para o login do Mercado Livre"""
        auth_url = self.ml_service.get_auth_url(state)
        return RedirectResponse(url=auth_url)
    
    async def handle_callback(self, code: str = None, error: str = None, state: str = None) -> HTMLResponse:
        """Processa o callback do Mercado Livre seguindo documentação oficial"""
        
        if error:
            return self.template_renderer.render_error(f"Erro na autorização: {error}", "authorization")
        
        if not code:
            return self.template_renderer.render_error("Nenhum código de autorização foi fornecido", "missing_code")
        
        # Trocar código por token
        token = await self.ml_service.exchange_code_for_token(code)
        
        if not token:
            return self.template_renderer.render_error("Não foi possível trocar o código por token. Verifique se o código não expirou ou já foi usado.", "token_exchange")
        
        # Converter token para dict para o template
        token_data = {
            "access_token": token.access_token,
            "token_type": token.token_type,
            "expires_in": token.expires_in,
            "scope": token.scope,
            "user_id": token.user_id,
            "refresh_token": getattr(token, 'refresh_token', None)
        }
        
        return self.template_renderer.render_login_success(token_data)
    
    async def get_user_info(self, access_token: str = None) -> HTMLResponse:
        """Obtém informações do usuário"""
        if not access_token:
            return self.template_renderer.render_error("Token de acesso necessário. Use: /user?access_token=SEU_TOKEN", "missing_token")
        
        user = await self.ml_service.get_user_info(access_token)
        if not user:
            return self.template_renderer.render_error("Token inválido ou expirado", "invalid_token")
        
        # Converter user para dict para o template
        user_data = {
            "user_id": user.id,
            "nickname": user.nickname,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "country_id": user.country_id,
            "site_id": user.site_id,
            "permalink": user.permalink
        }
        
        return self.template_renderer.render_user_info(user_data)
