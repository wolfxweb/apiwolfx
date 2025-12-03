#!/usr/bin/env python3
"""
Script para criar tabela de Briefings de Marketing
Execute este script para criar a tabela content_briefings
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


def create_content_briefings_table():
    """Cria a tabela content_briefings no banco de dados"""
    try:
        with engine.begin() as conn:  # begin() faz commit automático
            # Criar ENUMs necessários
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'briefingstatus') THEN
                        CREATE TYPE briefingstatus AS ENUM ('draft', 'researching', 'generating', 'completed', 'error');
                    END IF;
                    
                    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estagiofunil') THEN
                        CREATE TYPE estagiofunil AS ENUM ('topo', 'meio', 'fundo');
                    END IF;
                    
                    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'linhaeditorial') THEN
                        CREATE TYPE linhaeditorial AS ENUM ('educacional', 'informativo', 'vendas', 'bastidores', 'prova_social');
                    END IF;
                END $$;
            """))
            
            # Criar tabela content_briefings
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS content_briefings (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER,  -- Nullable para permitir superadmin
                    user_id INTEGER,
                    
                    -- Informações Gerais
                    nome_empresa_produto VARCHAR(255),
                    publico_alvo TEXT,
                    objetivo_conteudo JSONB, -- array de objetivos selecionados
                    estagio_funil estagiofunil,
                    linha_editorial linhaeditorial,
                    
                    -- Redes Sociais
                    redes_sociais JSONB, -- objeto com plataformas e formatos
                    
                    -- Blog/Artigos
                    blog_config JSONB, -- objeto com palavras-chave, SEO, tamanho
                    
                    -- Material Complementar
                    material_complementar JSONB, -- array de tipos selecionados
                    
                    -- Processamento
                    pesquisa_resultado TEXT,
                    agentes_identificados JSONB, -- array de IDs/nomes de agentes a executar
                    conteudo_gerado JSONB, -- objeto com todo conteúdo gerado
                    status briefingstatus DEFAULT 'draft'::briefingstatus NOT NULL,
                    
                    -- Timestamps
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    
                    CONSTRAINT fk_content_briefings_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                    CONSTRAINT fk_content_briefings_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                )
            """))
            
            # Criar índices
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_content_briefings_company_id ON content_briefings(company_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_content_briefings_user_id ON content_briefings(user_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_content_briefings_status ON content_briefings(status)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_content_briefings_created_at ON content_briefings(created_at)
            """))
            
            logger.info("✅ Tabela content_briefings criada com sucesso!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabela content_briefings: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    create_content_briefings_table()

