"""
Modelos de Planejamento de Conteúdo
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base
import logging
import json

logger = logging.getLogger(__name__)


class ContentIdea(Base):
    """Modelo para ideias de conteúdo"""
    __tablename__ = "content_ideas"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text)
    tags = Column(String(500))  # tags separadas por vírgula
    is_ai_generated = Column(Integer, default=0)  # 0 = manual, 1 = gerada por IA
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


class ContentBriefing(Base):
    """Modelo para briefings de marketing"""
    __tablename__ = "content_briefings"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)  # Nullable para superadmin
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Informações Gerais
    nome_empresa_produto = Column(String(255))
    publico_alvo = Column(Text)
    objetivo_conteudo = Column(JSONB)  # array de objetivos selecionados
    estagio_funil = Column(String(20))  # topo, meio, fundo
    linha_editorial = Column(String(20))  # educacional, informativo, vendas, bastidores, prova_social
    
    # Redes Sociais
    redes_sociais = Column(JSONB)  # objeto com plataformas e formatos
    
    # Blog/Artigos
    blog_config = Column(JSONB)  # objeto com palavras-chave, SEO, tamanho
    
    # Material Complementar
    material_complementar = Column(JSONB)  # array de tipos selecionados
    
    # Processamento
    pesquisa_resultado = Column(Text)
    agentes_identificados = Column(JSONB)  # array de IDs/nomes de agentes a executar
    conteudo_gerado = Column(JSONB)  # objeto com todo conteúdo gerado
    status = Column(String(20), default="draft")  # draft, researching, generating, completed, error
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    company = relationship("Company")
    user = relationship("User", foreign_keys=[user_id])
    
    def to_dict(self):
        """Converte o briefing para dicionário"""
        return {
            "id": self.id,
            "company_id": self.company_id,
            "user_id": self.user_id,
            "nome_empresa_produto": self.nome_empresa_produto,
            "publico_alvo": self.publico_alvo,
            "objetivo_conteudo": json.loads(json.dumps(self.objetivo_conteudo)) if self.objetivo_conteudo else None,
            "estagio_funil": self.estagio_funil,
            "linha_editorial": self.linha_editorial,
            "redes_sociais": json.loads(json.dumps(self.redes_sociais)) if self.redes_sociais else None,
            "blog_config": json.loads(json.dumps(self.blog_config)) if self.blog_config else None,
            "material_complementar": json.loads(json.dumps(self.material_complementar)) if self.material_complementar else None,
            "pesquisa_resultado": self.pesquisa_resultado,
            "agentes_identificados": json.loads(json.dumps(self.agentes_identificados)) if self.agentes_identificados else None,
            "conteudo_gerado": json.loads(json.dumps(self.conteudo_gerado)) if self.conteudo_gerado else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

