"""
Script para criar tabelas de Planejamento de Conteúdo
"""
import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from app.config.database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_content_tables():
    """Cria todas as tabelas de Planejamento de Conteúdo no banco de dados"""
    try:
        with engine.begin() as conn:  # begin() faz commit automático
            # Criar tabela content_ideas
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS content_ideas (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL,
                    titulo VARCHAR(255) NOT NULL,
                    descricao TEXT,
                    tags VARCHAR(500),
                    is_ai_generated INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_content_ideas_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
                )
            """))
            
            # Adicionar coluna is_ai_generated se não existir (para tabelas já criadas)
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'content_ideas' AND column_name = 'is_ai_generated'
                    ) THEN
                        ALTER TABLE content_ideas ADD COLUMN is_ai_generated INTEGER DEFAULT 0;
                    END IF;
                END $$;
            """))
            
            # Criar índices para content_ideas
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_content_ideas_company_id ON content_ideas(company_id)
            """))
            
            # Criar tabela content_social
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS content_social (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL,
                    titulo VARCHAR(255) NOT NULL,
                    canal VARCHAR(50),
                    tipo VARCHAR(50),
                    data_publicacao TIMESTAMP WITH TIME ZONE,
                    status VARCHAR(20) DEFAULT 'draft',
                    responsavel_id INTEGER,
                    copy TEXT,
                    anexos TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_content_social_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                    CONSTRAINT fk_content_social_responsavel FOREIGN KEY (responsavel_id) REFERENCES users(id) ON DELETE SET NULL
                )
            """))
            
            # Criar índices para content_social
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_content_social_company_id ON content_social(company_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_content_social_data_publicacao ON content_social(data_publicacao)
            """))
            
            # Criar tabela content_blog
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS content_blog (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL,
                    titulo VARCHAR(255) NOT NULL,
                    subtitulo VARCHAR(500),
                    slug VARCHAR(255),
                    data_publicacao TIMESTAMP WITH TIME ZONE,
                    status VARCHAR(20) DEFAULT 'draft',
                    responsavel_id INTEGER,
                    conteudo_html TEXT,
                    tags VARCHAR(500),
                    anexos TEXT,
                    seo_title VARCHAR(255),
                    seo_description TEXT,
                    seo_keywords VARCHAR(500),
                    featured_image VARCHAR(500),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_content_blog_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                    CONSTRAINT fk_content_blog_responsavel FOREIGN KEY (responsavel_id) REFERENCES users(id) ON DELETE SET NULL
                )
            """))
            
            # Criar índices para content_blog
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_content_blog_company_id ON content_blog(company_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_content_blog_slug ON content_blog(slug)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_content_blog_data_publicacao ON content_blog(data_publicacao)
            """))
            
            # Criar unique constraint para slug por company_id
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint 
                        WHERE conname = 'uq_content_blog_company_slug'
                    ) THEN
                        ALTER TABLE content_blog 
                        ADD CONSTRAINT uq_content_blog_company_slug 
                        UNIQUE (company_id, slug);
                    END IF;
                END $$;
            """))
            
            # Criar tabela content_calendar
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS content_calendar (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL,
                    referencia_id INTEGER NOT NULL,
                    tipo VARCHAR(20) NOT NULL,
                    data_publicacao TIMESTAMP WITH TIME ZONE NOT NULL,
                    CONSTRAINT fk_content_calendar_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
                )
            """))
            
            # Criar índices para content_calendar
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_content_calendar_company_id ON content_calendar(company_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_content_calendar_data_publicacao ON content_calendar(data_publicacao)
            """))
            
            logger.info("✅ Tabelas de Planejamento de Conteúdo criadas com sucesso!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas de Planejamento de Conteúdo: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    create_content_tables()

