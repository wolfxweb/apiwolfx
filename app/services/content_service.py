"""
Serviço para gerenciar Planejamento de Conteúdo
"""
import logging
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from app.models.content_models import ContentIdea, ContentSocial, ContentBlog, ContentCalendar
from app.models.saas_models import User

logger = logging.getLogger(__name__)


class ContentService:
    """Serviço para gerenciar Planejamento de Conteúdo"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========== IDEIAS ==========
    
    def create_idea(self, company_id: int, titulo: str, descricao: Optional[str] = None, tags: Optional[str] = None, is_ai_generated: int = 0) -> Dict[str, Any]:
        """Cria uma nova ideia"""
        try:
            idea = ContentIdea(
                company_id=company_id,
                titulo=titulo,
                descricao=descricao,
                tags=tags,
                is_ai_generated=is_ai_generated
            )
            self.db.add(idea)
            self.db.commit()
            self.db.refresh(idea)
            
            return {
                "success": True,
                "data": {
                    "id": idea.id,
                    "titulo": idea.titulo,
                    "descricao": idea.descricao,
                    "tags": idea.tags,
                    "created_at": idea.created_at.isoformat() if idea.created_at else None
                }
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar ideia: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def list_ideas(self, company_id: Optional[int], search: Optional[str] = None, is_ai_generated: Optional[int] = None) -> Dict[str, Any]:
        """Lista ideias da empresa (ou todas se company_id for None para superadmin)"""
        try:
            query = self.db.query(ContentIdea)
            
            # Filtrar por company_id apenas se fornecido (superadmin pode passar None)
            if company_id is not None:
                query = query.filter(ContentIdea.company_id == company_id)
            
            if is_ai_generated is not None:
                query = query.filter(ContentIdea.is_ai_generated == is_ai_generated)
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        ContentIdea.titulo.ilike(search_term),
                        ContentIdea.descricao.ilike(search_term),
                        ContentIdea.tags.ilike(search_term)
                    )
                )
            
            ideas = query.order_by(desc(ContentIdea.created_at)).all()
            
            return {
                "success": True,
                "data": [
                    {
                        "id": idea.id,
                        "company_id": idea.company_id,
                        "titulo": idea.titulo,
                        "descricao": idea.descricao,
                        "tags": idea.tags,
                        "is_ai_generated": idea.is_ai_generated or 0,
                        "created_at": idea.created_at.isoformat() if idea.created_at else None,
                        "updated_at": idea.updated_at.isoformat() if idea.updated_at else None
                    }
                    for idea in ideas
                ]
            }
        except Exception as e:
            logger.error(f"Erro ao listar ideias: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_idea(self, idea_id: int, company_id: int) -> Dict[str, Any]:
        """Obtém uma ideia específica"""
        try:
            idea = self.db.query(ContentIdea).filter(
                ContentIdea.id == idea_id,
                ContentIdea.company_id == company_id
            ).first()
            
            if not idea:
                return {"success": False, "error": "Ideia não encontrada"}
            
            return {
                "success": True,
                "data": {
                    "id": idea.id,
                    "titulo": idea.titulo,
                    "descricao": idea.descricao,
                    "tags": idea.tags,
                    "created_at": idea.created_at.isoformat() if idea.created_at else None,
                    "updated_at": idea.updated_at.isoformat() if idea.updated_at else None
                }
            }
        except Exception as e:
            logger.error(f"Erro ao obter ideia: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def update_idea(self, idea_id: int, company_id: int, **kwargs) -> Dict[str, Any]:
        """Atualiza uma ideia"""
        try:
            idea = self.db.query(ContentIdea).filter(
                ContentIdea.id == idea_id,
                ContentIdea.company_id == company_id
            ).first()
            
            if not idea:
                return {"success": False, "error": "Ideia não encontrada"}
            
            for key, value in kwargs.items():
                if hasattr(idea, key) and value is not None:
                    setattr(idea, key, value)
            
            self.db.commit()
            self.db.refresh(idea)
            
            return {
                "success": True,
                "data": {
                    "id": idea.id,
                    "titulo": idea.titulo,
                    "descricao": idea.descricao,
                    "tags": idea.tags,
                    "updated_at": idea.updated_at.isoformat() if idea.updated_at else None
                }
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar ideia: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def delete_idea(self, idea_id: int, company_id: int) -> Dict[str, Any]:
        """Exclui uma ideia"""
        try:
            idea = self.db.query(ContentIdea).filter(
                ContentIdea.id == idea_id,
                ContentIdea.company_id == company_id
            ).first()
            
            if not idea:
                return {"success": False, "error": "Ideia não encontrada"}
            
            self.db.delete(idea)
            self.db.commit()
            
            return {"success": True, "message": "Ideia excluída com sucesso"}
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao excluir ideia: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def convert_idea_to_social(self, idea_id: int, company_id: int, **social_data) -> Dict[str, Any]:
        """Converte uma ideia em post social"""
        try:
            idea = self.db.query(ContentIdea).filter(
                ContentIdea.id == idea_id,
                ContentIdea.company_id == company_id
            ).first()
            
            if not idea:
                return {"success": False, "error": "Ideia não encontrada"}
            
            # Criar post social com dados da ideia
            social_post = ContentSocial(
                company_id=company_id,
                titulo=social_data.get("titulo", idea.titulo),
                canal=social_data.get("canal"),
                tipo=social_data.get("tipo"),
                data_publicacao=social_data.get("data_publicacao"),
                status=social_data.get("status", "draft"),
                responsavel_id=social_data.get("responsavel_id"),
                copy=social_data.get("copy", idea.descricao),
                anexos=social_data.get("anexos")
            )
            
            self.db.add(social_post)
            self.db.commit()
            self.db.refresh(social_post)
            
            # Sincronizar com calendário
            self.sync_to_calendar(social_post.id, company_id, "social")
            
            return {
                "success": True,
                "data": {
                    "id": social_post.id,
                    "titulo": social_post.titulo,
                    "canal": social_post.canal,
                    "tipo": social_post.tipo,
                    "data_publicacao": social_post.data_publicacao.isoformat() if social_post.data_publicacao else None
                }
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao converter ideia para social: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def convert_idea_to_blog(self, idea_id: int, company_id: int, **blog_data) -> Dict[str, Any]:
        """Converte uma ideia em post de blog"""
        try:
            idea = self.db.query(ContentIdea).filter(
                ContentIdea.id == idea_id,
                ContentIdea.company_id == company_id
            ).first()
            
            if not idea:
                return {"success": False, "error": "Ideia não encontrada"}
            
            # Gerar slug único
            slug = self.generate_slug(blog_data.get("titulo", idea.titulo), company_id)
            
            # Criar post de blog com dados da ideia
            blog_post = ContentBlog(
                company_id=company_id,
                titulo=blog_data.get("titulo", idea.titulo),
                subtitulo=blog_data.get("subtitulo"),
                slug=slug,
                data_publicacao=blog_data.get("data_publicacao"),
                status=blog_data.get("status", "draft"),
                responsavel_id=blog_data.get("responsavel_id"),
                conteudo_html=blog_data.get("conteudo_html", idea.descricao or ""),
                tags=blog_data.get("tags", idea.tags),
                anexos=blog_data.get("anexos"),
                seo_title=blog_data.get("seo_title", blog_data.get("titulo", idea.titulo)),
                seo_description=blog_data.get("seo_description"),
                seo_keywords=blog_data.get("seo_keywords"),
                featured_image=blog_data.get("featured_image")
            )
            
            # Gerar SEO description se vazio
            if not blog_post.seo_description and blog_post.conteudo_html:
                blog_post.seo_description = self.generate_seo_description(blog_post.conteudo_html)
            
            self.db.add(blog_post)
            self.db.commit()
            self.db.refresh(blog_post)
            
            # Sincronizar com calendário
            self.sync_to_calendar(blog_post.id, company_id, "blog")
            
            return {
                "success": True,
                "data": {
                    "id": blog_post.id,
                    "titulo": blog_post.titulo,
                    "slug": blog_post.slug,
                    "data_publicacao": blog_post.data_publicacao.isoformat() if blog_post.data_publicacao else None
                }
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao converter ideia para blog: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    # ========== SOCIAL ==========
    
    def create_social_post(self, company_id: int, **data) -> Dict[str, Any]:
        """Cria um novo post social"""
        try:
            social_post = ContentSocial(
                company_id=company_id,
                titulo=data.get("titulo"),
                canal=data.get("canal"),
                tipo=data.get("tipo"),
                data_publicacao=data.get("data_publicacao"),
                status=data.get("status", "draft"),
                responsavel_id=data.get("responsavel_id"),
                copy=data.get("copy"),
                anexos=json.dumps(data.get("anexos", [])) if data.get("anexos") else None
            )
            
            self.db.add(social_post)
            self.db.commit()
            self.db.refresh(social_post)
            
            # Sincronizar com calendário
            self.sync_to_calendar(social_post.id, company_id, "social")
            
            return {
                "success": True,
                "data": {
                    "id": social_post.id,
                    "titulo": social_post.titulo,
                    "canal": social_post.canal,
                    "tipo": social_post.tipo,
                    "data_publicacao": social_post.data_publicacao.isoformat() if social_post.data_publicacao else None,
                    "status": social_post.status
                }
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar post social: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def list_social_posts(self, company_id: int, status: Optional[str] = None, canal: Optional[str] = None, search: Optional[str] = None) -> Dict[str, Any]:
        """Lista posts sociais"""
        try:
            query = self.db.query(ContentSocial).filter(ContentSocial.company_id == company_id)
            
            if status:
                query = query.filter(ContentSocial.status == status)
            
            if canal:
                query = query.filter(ContentSocial.canal == canal)
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        ContentSocial.titulo.ilike(search_term),
                        ContentSocial.copy.ilike(search_term)
                    )
                )
            
            posts = query.order_by(desc(ContentSocial.data_publicacao)).all()
            
            return {
                "success": True,
                "data": [
                    {
                        "id": post.id,
                        "titulo": post.titulo,
                        "canal": post.canal,
                        "tipo": post.tipo,
                        "data_publicacao": post.data_publicacao.isoformat() if post.data_publicacao else None,
                        "status": post.status,
                        "responsavel_id": post.responsavel_id,
                        "copy": post.copy,
                        "anexos": json.loads(post.anexos) if post.anexos else []
                    }
                    for post in posts
                ]
            }
        except Exception as e:
            logger.error(f"Erro ao listar posts sociais: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_social_post(self, post_id: int, company_id: int) -> Dict[str, Any]:
        """Obtém um post social específico"""
        try:
            post = self.db.query(ContentSocial).filter(
                ContentSocial.id == post_id,
                ContentSocial.company_id == company_id
            ).first()
            
            if not post:
                return {"success": False, "error": "Post social não encontrado"}
            
            return {
                "success": True,
                "data": {
                    "id": post.id,
                    "titulo": post.titulo,
                    "canal": post.canal,
                    "tipo": post.tipo,
                    "data_publicacao": post.data_publicacao.isoformat() if post.data_publicacao else None,
                    "status": post.status,
                    "responsavel_id": post.responsavel_id,
                    "copy": post.copy,
                    "anexos": json.loads(post.anexos) if post.anexos else [],
                    "created_at": post.created_at.isoformat() if post.created_at else None,
                    "updated_at": post.updated_at.isoformat() if post.updated_at else None
                }
            }
        except Exception as e:
            logger.error(f"Erro ao obter post social: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def update_social_post(self, post_id: int, company_id: int, **kwargs) -> Dict[str, Any]:
        """Atualiza um post social"""
        try:
            post = self.db.query(ContentSocial).filter(
                ContentSocial.id == post_id,
                ContentSocial.company_id == company_id
            ).first()
            
            if not post:
                return {"success": False, "error": "Post social não encontrado"}
            
            for key, value in kwargs.items():
                if hasattr(post, key) and value is not None:
                    if key == "anexos" and isinstance(value, list):
                        setattr(post, key, json.dumps(value))
                    else:
                        setattr(post, key, value)
            
            self.db.commit()
            self.db.refresh(post)
            
            # Atualizar calendário se data mudou
            if "data_publicacao" in kwargs:
                self.sync_to_calendar(post_id, company_id, "social")
            
            return {
                "success": True,
                "data": {
                    "id": post.id,
                    "titulo": post.titulo,
                    "canal": post.canal,
                    "tipo": post.tipo,
                    "data_publicacao": post.data_publicacao.isoformat() if post.data_publicacao else None,
                    "status": post.status
                }
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar post social: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def delete_social_post(self, post_id: int, company_id: int) -> Dict[str, Any]:
        """Exclui um post social"""
        try:
            post = self.db.query(ContentSocial).filter(
                ContentSocial.id == post_id,
                ContentSocial.company_id == company_id
            ).first()
            
            if not post:
                return {"success": False, "error": "Post social não encontrado"}
            
            # Remover do calendário
            self.db.query(ContentCalendar).filter(
                ContentCalendar.company_id == company_id,
                ContentCalendar.referencia_id == post_id,
                ContentCalendar.tipo == "social"
            ).delete()
            
            self.db.delete(post)
            self.db.commit()
            
            return {"success": True, "message": "Post social excluído com sucesso"}
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao excluir post social: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    # ========== BLOG ==========
    
    def generate_slug(self, titulo: str, company_id: int) -> str:
        """Gera um slug único a partir do título"""
        # Converter para lowercase, remover acentos, substituir espaços por hífens
        slug = titulo.lower()
        slug = re.sub(r'[àáâãäå]', 'a', slug)
        slug = re.sub(r'[èéêë]', 'e', slug)
        slug = re.sub(r'[ìíîï]', 'i', slug)
        slug = re.sub(r'[òóôõö]', 'o', slug)
        slug = re.sub(r'[ùúûü]', 'u', slug)
        slug = re.sub(r'[ç]', 'c', slug)
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'\s+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')
        
        # Verificar unicidade
        base_slug = slug
        counter = 1
        while True:
            existing = self.db.query(ContentBlog).filter(
                ContentBlog.company_id == company_id,
                ContentBlog.slug == slug
            ).first()
            
            if not existing:
                break
            
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug
    
    def generate_seo_description(self, conteudo_html: str) -> str:
        """Gera descrição SEO a partir do conteúdo HTML"""
        # Remover tags HTML
        text = re.sub(r'<[^>]+>', '', conteudo_html)
        # Remover espaços extras
        text = re.sub(r'\s+', ' ', text).strip()
        # Pegar primeiros 160 caracteres
        return text[:160] if text else ""
    
    def create_blog_post(self, company_id: int, **data) -> Dict[str, Any]:
        """Cria um novo post de blog"""
        try:
            # Gerar slug se não fornecido
            slug = data.get("slug")
            if not slug:
                slug = self.generate_slug(data.get("titulo", ""), company_id)
            
            # Gerar SEO description se vazio
            seo_description = data.get("seo_description")
            if not seo_description and data.get("conteudo_html"):
                seo_description = self.generate_seo_description(data.get("conteudo_html"))
            
            blog_post = ContentBlog(
                company_id=company_id,
                titulo=data.get("titulo"),
                subtitulo=data.get("subtitulo"),
                slug=slug,
                data_publicacao=data.get("data_publicacao"),
                status=data.get("status", "draft"),
                responsavel_id=data.get("responsavel_id"),
                conteudo_html=data.get("conteudo_html"),
                tags=data.get("tags"),
                anexos=json.dumps(data.get("anexos", [])) if data.get("anexos") else None,
                seo_title=data.get("seo_title", data.get("titulo")),
                seo_description=seo_description,
                seo_keywords=data.get("seo_keywords"),
                featured_image=data.get("featured_image")
            )
            
            self.db.add(blog_post)
            self.db.commit()
            self.db.refresh(blog_post)
            
            # Sincronizar com calendário
            self.sync_to_calendar(blog_post.id, company_id, "blog")
            
            return {
                "success": True,
                "data": {
                    "id": blog_post.id,
                    "titulo": blog_post.titulo,
                    "slug": blog_post.slug,
                    "data_publicacao": blog_post.data_publicacao.isoformat() if blog_post.data_publicacao else None,
                    "status": blog_post.status
                }
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar post de blog: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def list_blog_posts(self, company_id: int, status: Optional[str] = None, search: Optional[str] = None) -> Dict[str, Any]:
        """Lista posts do blog"""
        try:
            query = self.db.query(ContentBlog).filter(ContentBlog.company_id == company_id)
            
            if status:
                query = query.filter(ContentBlog.status == status)
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        ContentBlog.titulo.ilike(search_term),
                        ContentBlog.subtitulo.ilike(search_term),
                        ContentBlog.conteudo_html.ilike(search_term),
                        ContentBlog.tags.ilike(search_term)
                    )
                )
            
            posts = query.order_by(desc(ContentBlog.data_publicacao)).all()
            
            return {
                "success": True,
                "data": [
                    {
                        "id": post.id,
                        "titulo": post.titulo,
                        "subtitulo": post.subtitulo,
                        "slug": post.slug,
                        "data_publicacao": post.data_publicacao.isoformat() if post.data_publicacao else None,
                        "status": post.status,
                        "responsavel_id": post.responsavel_id,
                        "tags": post.tags,
                        "anexos": json.loads(post.anexos) if post.anexos else []
                    }
                    for post in posts
                ]
            }
        except Exception as e:
            logger.error(f"Erro ao listar posts do blog: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_blog_post(self, post_id: int, company_id: int) -> Dict[str, Any]:
        """Obtém um post de blog específico"""
        try:
            post = self.db.query(ContentBlog).filter(
                ContentBlog.id == post_id,
                ContentBlog.company_id == company_id
            ).first()
            
            if not post:
                return {"success": False, "error": "Post de blog não encontrado"}
            
            return {
                "success": True,
                "data": {
                    "id": post.id,
                    "titulo": post.titulo,
                    "subtitulo": post.subtitulo,
                    "slug": post.slug,
                    "data_publicacao": post.data_publicacao.isoformat() if post.data_publicacao else None,
                    "status": post.status,
                    "responsavel_id": post.responsavel_id,
                    "conteudo_html": post.conteudo_html,
                    "tags": post.tags,
                    "anexos": json.loads(post.anexos) if post.anexos else [],
                    "seo_title": post.seo_title,
                    "seo_description": post.seo_description,
                    "seo_keywords": post.seo_keywords,
                    "featured_image": post.featured_image,
                    "created_at": post.created_at.isoformat() if post.created_at else None,
                    "updated_at": post.updated_at.isoformat() if post.updated_at else None
                }
            }
        except Exception as e:
            logger.error(f"Erro ao obter post de blog: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def update_blog_post(self, post_id: int, company_id: int, **kwargs) -> Dict[str, Any]:
        """Atualiza um post de blog"""
        try:
            post = self.db.query(ContentBlog).filter(
                ContentBlog.id == post_id,
                ContentBlog.company_id == company_id
            ).first()
            
            if not post:
                return {"success": False, "error": "Post de blog não encontrado"}
            
            # Se título mudou e slug não foi fornecido, gerar novo slug
            if "titulo" in kwargs and "slug" not in kwargs:
                kwargs["slug"] = self.generate_slug(kwargs["titulo"], company_id)
            
            # Gerar SEO description se conteúdo mudou
            if "conteudo_html" in kwargs and not kwargs.get("seo_description"):
                kwargs["seo_description"] = self.generate_seo_description(kwargs["conteudo_html"])
            
            for key, value in kwargs.items():
                if hasattr(post, key) and value is not None:
                    if key == "anexos" and isinstance(value, list):
                        setattr(post, key, json.dumps(value))
                    else:
                        setattr(post, key, value)
            
            # Se seo_title vazio, usar título
            if not post.seo_title:
                post.seo_title = post.titulo
            
            self.db.commit()
            self.db.refresh(post)
            
            # Atualizar calendário se data mudou
            if "data_publicacao" in kwargs:
                self.sync_to_calendar(post_id, company_id, "blog")
            
            return {
                "success": True,
                "data": {
                    "id": post.id,
                    "titulo": post.titulo,
                    "slug": post.slug,
                    "data_publicacao": post.data_publicacao.isoformat() if post.data_publicacao else None,
                    "status": post.status
                }
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar post de blog: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def delete_blog_post(self, post_id: int, company_id: int) -> Dict[str, Any]:
        """Exclui um post de blog"""
        try:
            post = self.db.query(ContentBlog).filter(
                ContentBlog.id == post_id,
                ContentBlog.company_id == company_id
            ).first()
            
            if not post:
                return {"success": False, "error": "Post de blog não encontrado"}
            
            # Remover do calendário
            self.db.query(ContentCalendar).filter(
                ContentCalendar.company_id == company_id,
                ContentCalendar.referencia_id == post_id,
                ContentCalendar.tipo == "blog"
            ).delete()
            
            self.db.delete(post)
            self.db.commit()
            
            return {"success": True, "message": "Post de blog excluído com sucesso"}
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao excluir post de blog: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    # ========== CALENDÁRIO ==========
    
    def sync_to_calendar(self, referencia_id: int, company_id: int, tipo: str):
        """Sincroniza post social ou blog com calendário"""
        try:
            # Verificar se já existe entrada no calendário
            existing = self.db.query(ContentCalendar).filter(
                ContentCalendar.company_id == company_id,
                ContentCalendar.referencia_id == referencia_id,
                ContentCalendar.tipo == tipo
            ).first()
            
            # Buscar data de publicação do post original
            if tipo == "social":
                post = self.db.query(ContentSocial).filter(
                    ContentSocial.id == referencia_id,
                    ContentSocial.company_id == company_id
                ).first()
                data_publicacao = post.data_publicacao if post else None
            else:  # blog
                post = self.db.query(ContentBlog).filter(
                    ContentBlog.id == referencia_id,
                    ContentBlog.company_id == company_id
                ).first()
                data_publicacao = post.data_publicacao if post else None
            
            if not data_publicacao:
                return
            
            if existing:
                # Atualizar data
                existing.data_publicacao = data_publicacao
            else:
                # Criar nova entrada
                calendar_entry = ContentCalendar(
                    company_id=company_id,
                    referencia_id=referencia_id,
                    tipo=tipo,
                    data_publicacao=data_publicacao
                )
                self.db.add(calendar_entry)
            
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao sincronizar com calendário: {e}", exc_info=True)
    
    def get_calendar_events(self, company_id: int, mes: str, ano: str) -> Dict[str, Any]:
        """Obtém eventos do calendário para um mês/ano"""
        try:
            # Parsear mês e ano
            try:
                month = int(mes)
                year = int(ano)
            except:
                return {"success": False, "error": "Mês ou ano inválido"}
            
            # Buscar eventos do mês
            from datetime import date
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)
            
            events = self.db.query(ContentCalendar).filter(
                ContentCalendar.company_id == company_id,
                ContentCalendar.data_publicacao >= start_date,
                ContentCalendar.data_publicacao < end_date
            ).order_by(ContentCalendar.data_publicacao).all()
            
            # Buscar dados completos dos posts
            events_data = []
            for event in events:
                if event.tipo == "social":
                    post = self.db.query(ContentSocial).filter(
                        ContentSocial.id == event.referencia_id,
                        ContentSocial.company_id == company_id
                    ).first()
                    if post:
                        events_data.append({
                            "id": event.id,
                            "tipo": "social",
                            "referencia_id": event.referencia_id,
                            "titulo": post.titulo,
                            "canal": post.canal,
                            "status": post.status,
                            "data_publicacao": event.data_publicacao.isoformat() if event.data_publicacao else None
                        })
                else:  # blog
                    post = self.db.query(ContentBlog).filter(
                        ContentBlog.id == event.referencia_id,
                        ContentBlog.company_id == company_id
                    ).first()
                    if post:
                        events_data.append({
                            "id": event.id,
                            "tipo": "blog",
                            "referencia_id": event.referencia_id,
                            "titulo": post.titulo,
                            "status": post.status,
                            "data_publicacao": event.data_publicacao.isoformat() if event.data_publicacao else None
                        })
            
            return {
                "success": True,
                "data": events_data
            }
        except Exception as e:
            logger.error(f"Erro ao obter eventos do calendário: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def move_event_date(self, calendar_id: int, company_id: int, nova_data: datetime) -> Dict[str, Any]:
        """Move data de publicação de um evento no calendário"""
        try:
            event = self.db.query(ContentCalendar).filter(
                ContentCalendar.id == calendar_id,
                ContentCalendar.company_id == company_id
            ).first()
            
            if not event:
                return {"success": False, "error": "Evento não encontrado"}
            
            # Atualizar data no calendário
            event.data_publicacao = nova_data
            
            # Atualizar data no post original
            if event.tipo == "social":
                post = self.db.query(ContentSocial).filter(
                    ContentSocial.id == event.referencia_id,
                    ContentSocial.company_id == company_id
                ).first()
                if post:
                    post.data_publicacao = nova_data
            else:  # blog
                post = self.db.query(ContentBlog).filter(
                    ContentBlog.id == event.referencia_id,
                    ContentBlog.company_id == company_id
                ).first()
                if post:
                    post.data_publicacao = nova_data
            
            self.db.commit()
            
            return {
                "success": True,
                "data": {
                    "id": event.id,
                    "data_publicacao": nova_data.isoformat()
                }
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao mover data do evento: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

