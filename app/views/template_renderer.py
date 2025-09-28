from fastapi.responses import HTMLResponse
from pathlib import Path
import re
import os

class TemplateRenderer:
    """Renderizador de templates HTML moderno"""
    
    def __init__(self):
        self.templates_dir = Path(__file__).parent / "templates"
    
    def render(self, template_name: str, context: dict = None) -> HTMLResponse:
        """Renderiza um template HTML com sistema de herança"""
        if context is None:
            context = {}
        
        template_path = self.templates_dir / template_name
        
        if not template_path.exists():
            return HTMLResponse(f"<h1>Template não encontrado: {template_name}</h1>", status_code=404)
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Processar herança de templates
            content = self._process_extends(content)
            
            # Substituir variáveis no template
            content = self._replace_variables(content, context)
            
            return HTMLResponse(content)
        except Exception as e:
            return HTMLResponse(f"<h1>Erro ao renderizar template: {e}</h1>", status_code=500)
    
    def _process_extends(self, content: str) -> str:
        """Processa herança de templates ({% extends %})"""
        # Verificar se há extends
        extends_match = re.search(r'{%\s*extends\s+["\']([^"\']+)["\']\s*%}', content)
        if not extends_match:
            return content
        
        parent_template = extends_match.group(1)
        parent_path = self.templates_dir / parent_template
        
        if not parent_path.exists():
            return content
        
        # Ler template pai
        with open(parent_path, 'r', encoding='utf-8') as f:
            parent_content = f.read()
        
        # Processar blocos
        content = self._process_blocks(content, parent_content)
        
        return content
    
    def _process_blocks(self, child_content: str, parent_content: str) -> str:
        """Processa blocos do template filho no template pai"""
        # Extrair blocos do template filho
        blocks = {}
        block_pattern = r'{%\s*block\s+(\w+)\s*%}(.*?){%\s*endblock\s*%}'
        
        for match in re.finditer(block_pattern, child_content, re.DOTALL):
            block_name = match.group(1)
            block_content = match.group(2).strip()
            blocks[block_name] = block_content
        
        # Substituir blocos no template pai
        def replace_block(match):
            block_name = match.group(1)
            default_content = match.group(2)
            
            if block_name in blocks:
                return blocks[block_name]
            return default_content
        
        # Padrão para blocos no template pai
        parent_block_pattern = r'{%\s*block\s+(\w+)\s*%}(.*?){%\s*endblock\s*%}'
        result = re.sub(parent_block_pattern, replace_block, parent_content, flags=re.DOTALL)
        
        return result
    
    def _replace_variables(self, content: str, context: dict) -> str:
        """Substitui variáveis no template"""
        # Substituir variáveis simples {{ variavel }}
        for key, value in context.items():
            content = content.replace(f"{{{{ {key} }}}}", str(value))
            content = content.replace(f"{{{{{key}}}}}", str(value))
        
        return content
    
    def render_home(self) -> HTMLResponse:
        """Renderiza a página home"""
        return self.render("home.html")
    
    def render_login_success(self, token_data: dict) -> HTMLResponse:
        """Renderiza página de sucesso no login"""
        context = {
            "access_token": token_data.get("access_token", ""),
            "token_type": token_data.get("token_type", ""),
            "expires_in": token_data.get("expires_in", ""),
            "scope": token_data.get("scope", ""),
            "user_id": token_data.get("user_id", ""),
            "refresh_token": token_data.get("refresh_token", "")
        }
        return self.render("login_success.html", context)
    
    def render_user_info(self, user_data: dict) -> HTMLResponse:
        """Renderiza página com informações do usuário"""
        context = {
            "user_id": user_data.get("id", ""),
            "nickname": user_data.get("nickname", ""),
            "email": user_data.get("email", ""),
            "first_name": user_data.get("first_name", ""),
            "last_name": user_data.get("last_name", ""),
            "country_id": user_data.get("country_id", ""),
            "site_id": user_data.get("site_id", ""),
            "permalink": user_data.get("permalink", "")
        }
        return self.render("user_info.html", context)
    
    def render_error(self, error_message: str, error_type: str = "error") -> HTMLResponse:
        """Renderiza página de erro"""
        context = {
            "error_message": error_message,
            "error_type": error_type
        }
        return self.render("error.html", context)
