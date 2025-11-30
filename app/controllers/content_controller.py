"""
Controller para Planejamento de Conteúdo
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.content_service import ContentService

logger = logging.getLogger(__name__)


class ContentController:
    """Controller para gerenciar Planejamento de Conteúdo"""
    
    def __init__(self, db: Session):
        self.service = ContentService(db)
        self.db = db
    
    # ========== IDEIAS ==========
    
    def create_idea(self, company_id: int, titulo: str, descricao: Optional[str] = None, tags: Optional[str] = None) -> Dict[str, Any]:
        """Cria uma nova ideia"""
        return self.service.create_idea(company_id, titulo, descricao, tags)
    
    def list_ideas(self, company_id: int, search: Optional[str] = None, is_ai_generated: Optional[int] = None) -> Dict[str, Any]:
        """Lista ideias da empresa"""
        return self.service.list_ideas(company_id, search, is_ai_generated)
    
    def get_idea(self, idea_id: int, company_id: int) -> Dict[str, Any]:
        """Obtém uma ideia específica"""
        return self.service.get_idea(idea_id, company_id)
    
    def update_idea(self, idea_id: int, company_id: int, **kwargs) -> Dict[str, Any]:
        """Atualiza uma ideia"""
        return self.service.update_idea(idea_id, company_id, **kwargs)
    
    def delete_idea(self, idea_id: int, company_id: int) -> Dict[str, Any]:
        """Exclui uma ideia"""
        return self.service.delete_idea(idea_id, company_id)
    
    def convert_idea_to_social(self, idea_id: int, company_id: int, **social_data) -> Dict[str, Any]:
        """Converte uma ideia em post social"""
        return self.service.convert_idea_to_social(idea_id, company_id, **social_data)
    
    def convert_idea_to_blog(self, idea_id: int, company_id: int, **blog_data) -> Dict[str, Any]:
        """Converte uma ideia em post de blog"""
        return self.service.convert_idea_to_blog(idea_id, company_id, **blog_data)
    
    # ========== SOCIAL ==========
    
    def create_social_post(self, company_id: int, **data) -> Dict[str, Any]:
        """Cria um novo post social"""
        return self.service.create_social_post(company_id, **data)
    
    def list_social_posts(self, company_id: int, status: Optional[str] = None, canal: Optional[str] = None, search: Optional[str] = None) -> Dict[str, Any]:
        """Lista posts sociais"""
        return self.service.list_social_posts(company_id, status, canal, search)
    
    def get_social_post(self, post_id: int, company_id: int) -> Dict[str, Any]:
        """Obtém um post social específico"""
        return self.service.get_social_post(post_id, company_id)
    
    def update_social_post(self, post_id: int, company_id: int, **kwargs) -> Dict[str, Any]:
        """Atualiza um post social"""
        return self.service.update_social_post(post_id, company_id, **kwargs)
    
    def delete_social_post(self, post_id: int, company_id: int) -> Dict[str, Any]:
        """Exclui um post social"""
        return self.service.delete_social_post(post_id, company_id)
    
    # ========== BLOG ==========
    
    def create_blog_post(self, company_id: int, **data) -> Dict[str, Any]:
        """Cria um novo post de blog"""
        return self.service.create_blog_post(company_id, **data)
    
    def list_blog_posts(self, company_id: int, status: Optional[str] = None, search: Optional[str] = None) -> Dict[str, Any]:
        """Lista posts do blog"""
        return self.service.list_blog_posts(company_id, status, search)
    
    def get_blog_post(self, post_id: int, company_id: int) -> Dict[str, Any]:
        """Obtém um post de blog específico"""
        return self.service.get_blog_post(post_id, company_id)
    
    def update_blog_post(self, post_id: int, company_id: int, **kwargs) -> Dict[str, Any]:
        """Atualiza um post de blog"""
        return self.service.update_blog_post(post_id, company_id, **kwargs)
    
    def delete_blog_post(self, post_id: int, company_id: int) -> Dict[str, Any]:
        """Exclui um post de blog"""
        return self.service.delete_blog_post(post_id, company_id)
    
    # ========== CALENDÁRIO ==========
    
    def get_calendar_events(self, company_id: int, mes: str, ano: str) -> Dict[str, Any]:
        """Obtém eventos do calendário para um mês/ano"""
        return self.service.get_calendar_events(company_id, mes, ano)
    
    def move_event_date(self, calendar_id: int, company_id: int, nova_data) -> Dict[str, Any]:
        """Move data de publicação de um evento no calendário"""
        return self.service.move_event_date(calendar_id, company_id, nova_data)

