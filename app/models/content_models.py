"""
Modelos de Planejamento de Conteúdo
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base
import logging

logger = logging.getLogger(__name__)


class ContentIdea(Base):
    """Modelo para ideias de conteúdo"""
    __tablename__ = "content_ideas"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text)
    tags = Column(String(500))  # tags separadas por vírgula
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamento (sem back_populates por enquanto)
    company = relationship("Company")


class ContentSocial(Base):
    """Modelo para posts sociais"""
    __tablename__ = "content_social"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    titulo = Column(String(255), nullable=False)
    canal = Column(String(50))  # Instagram, Facebook, Twitter, LinkedIn, etc.
    tipo = Column(String(50))  # Post, Story, Reels, etc.
    data_publicacao = Column(DateTime(timezone=True), index=True)
    status = Column(String(20), default="draft")  # draft, scheduled, published, cancelled
    responsavel_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    copy = Column(Text)  # texto do post
    anexos = Column(Text)  # JSON como string - array de objetos com filename, url, type
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company")
    responsavel = relationship("User", foreign_keys=[responsavel_id])


class ContentBlog(Base):
    """Modelo para posts do blog"""
    __tablename__ = "content_blog"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    titulo = Column(String(255), nullable=False)
    subtitulo = Column(String(500))
    slug = Column(String(255), index=True)  # único por company_id
    data_publicacao = Column(DateTime(timezone=True), index=True)
    status = Column(String(20), default="draft")  # draft, scheduled, published, archived
    responsavel_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    conteudo_html = Column(Text)  # conteúdo HTML do artigo
    tags = Column(String(500))  # tags separadas por vírgula
    anexos = Column(Text)  # JSON como string - array de objetos
    seo_title = Column(String(255))
    seo_description = Column(Text)
    seo_keywords = Column(String(500))  # keywords separadas por vírgula
    featured_image = Column(String(500))  # URL da imagem destacada
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Unique constraint para slug por company_id
    __table_args__ = (
        UniqueConstraint('company_id', 'slug', name='uq_content_blog_company_slug'),
    )
    
    # Relacionamentos
    company = relationship("Company")
    responsavel = relationship("User", foreign_keys=[responsavel_id])


class ContentCalendar(Base):
    """Modelo para visualização do calendário (referência a Social ou Blog)"""
    __tablename__ = "content_calendar"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    referencia_id = Column(Integer, nullable=False)  # ID do post social ou blog
    tipo = Column(String(20), nullable=False)  # "social" ou "blog"
    data_publicacao = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Relacionamento
    company = relationship("Company")

