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
            
            # Processar condições PRIMEIRO
            content = self._process_conditions(content, context)
            
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
        import re
        
        # Padrão para variáveis aninhadas {{ user.first_name }}
        def replace_nested_var(match):
            var_path = match.group(1).strip()
            parts = var_path.split('.')
            
            # Navegar pela estrutura aninhada
            current = context
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return ""  # Retornar vazio se não encontrar
            
            # Converter None para string vazia
            if current is None:
                return ""
            return str(current)
        
        # Substituir variáveis aninhadas {{ user.first_name }}
        content = re.sub(r'\{\{\s*([^}]+)\s*\}\}', replace_nested_var, content)
        
        return content
    
    def _process_conditions(self, content: str, context: dict) -> str:
        """Processa condições {% if %} no template"""
        import re
        
        # Padrão para {% if variavel %} com suporte a condições aninhadas
        if_pattern = r'{%\s*if\s+([^%]+?)\s*%}(.*?){%\s*endif\s*%}'
        
        def process_if(match):
            condition = match.group(1).strip()
            if_content = match.group(2)
            
            # Processar condições simples (variavel)
            if not '.' in condition and not '==' in condition and not '!=' in condition:
                var_value = context.get(condition)
                if var_value and var_value != "" and var_value != "None" and var_value != []:
                    return if_content
                else:
                    return ""
            
            # Processar condições com comparação (==, !=)
            elif '==' in condition:
                parts = condition.split('==')
                var_name = parts[0].strip()
                var_value = parts[1].strip().strip('"\'')
                context_value = context.get(var_name)
                if str(context_value) == var_value:
                    return if_content
                else:
                    return ""
            
            # Processar condições com !=
            elif '!=' in condition:
                parts = condition.split('!=')
                var_name = parts[0].strip()
                var_value = parts[1].strip().strip('"\'')
                context_value = context.get(var_name)
                if str(context_value) != var_value:
                    return if_content
                else:
                    return ""
            
            return ""
        
        # Processar todas as condições (múltiplas passadas para lidar com aninhamento)
        for _ in range(5):  # Máximo 5 níveis de aninhamento
            new_content = re.sub(if_pattern, process_if, content, flags=re.DOTALL)
            if new_content == content:  # Se não houve mudança, parar
                break
            content = new_content
        
        # Processar loops {% for %}
        content = self._process_loops(content, context)
        
        return content
    
    def _process_loops(self, content: str, context: dict) -> str:
        """Processa loops {% for %} no template"""
        import re
        
        # Padrão para {% for item in lista %}
        for_pattern = r'{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%}(.*?){%\s*endfor\s*%}'
        
        def process_for(match):
            item_name = match.group(1)
            list_name = match.group(2)
            loop_content = match.group(3)
            
            # Obter lista do contexto
            items = context.get(list_name, [])
            if not isinstance(items, list):
                return ""
            
            # Processar cada item da lista
            result = ""
            for item in items:
                # Criar contexto temporário com o item atual
                temp_context = context.copy()
                temp_context[item_name] = item
                
                # Processar conteúdo do loop com o item atual
                item_content = loop_content
                for key, value in temp_context.items():
                    if value is None:
                        value = ""
                    item_content = item_content.replace(f"{{{{ {key} }}}}", str(value))
                    item_content = item_content.replace(f"{{{{{key}}}}}", str(value))
                
                result += item_content
            
            return result
        
        # Processar todos os loops
        content = re.sub(for_pattern, process_for, content, flags=re.DOTALL)
        
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

# Instância global do renderizador
_renderer = TemplateRenderer()

def render_template(template_name: str, **context) -> HTMLResponse:
    """Função de conveniência para renderizar templates"""
    return _renderer.render(template_name, context)
