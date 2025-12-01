"""
Script para atualizar o initial_prompt do agente "Analise cadastro produto"
para enfatizar a análise de atributos vazios e características secundárias.
"""
import logging
from sqlalchemy import text
from app.config.database import get_db

logger = logging.getLogger(__name__)

def run(db=None):
    """
    Atualiza o initial_prompt do agente para enfatizar análise de atributos vazios.
    """
    try:
        if db is None:
            db = next(get_db())
        
        # Novo initial_prompt com foco em atributos vazios
        new_initial_prompt = """Analise o cadastro de produto do Mercado Livre abaixo e forneça recomendações específicas de otimização.

⚠️ ATENÇÃO ESPECIAL: Este cadastro contém atributos dinâmicos que variam por categoria.
Alguns atributos podem estar VAZIOS e PRECISAM ser preenchidos para melhorar a relevância do produto.

Considere TODOS os aspectos:
- Título do anúncio (SEO, palavras-chave, limite de 60 caracteres)
- Descrição (completa, informativa, SEO)
- Preço e estratégia de precificação
- Categoria e atributos específicos da categoria
- ⚠️ Características do produto (atributos dinâmicos - PRINCIPAIS E SECUNDÁRIOS)
  * Analise TODOS os atributos, especialmente os que estão VAZIOS
  * Para cada atributo vazio, sugira um valor apropriado baseado nas melhores práticas
  * Atributos secundários são CRÍTICOS para melhorar a visibilidade no Mercado Livre
- Variações (se aplicável)
- Informações de envio e garantia
- Códigos (GTIN, SKU, MPN)

Os dados completos do produto serão fornecidos abaixo, incluindo uma lista de atributos vazios que precisam ser preenchidos."""
        
        update_query = text("""
            UPDATE openai_assistants 
            SET initial_prompt = :new_prompt,
                updated_at = NOW()
            WHERE LOWER(name) LIKE LOWER('%analise%cadastro%produto%')
            RETURNING id, name
        """)
        
        result = db.execute(update_query, {"new_prompt": new_initial_prompt}).fetchone()
        db.commit()
        
        if result:
            logger.info(f"✅ Agente 'Analise cadastro produto' atualizado com novo initial_prompt (ID: {result[0]}, Nome: {result[1]})")
            return {"success": True, "message": "Agente atualizado com sucesso", "agent_id": result[0]}
        else:
            logger.warning("⚠️ Agente 'Analise cadastro produto' não encontrado")
            return {"success": False, "error": "Agente não encontrado"}
            
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar agente: {e}", exc_info=True)
        if db:
            db.rollback()
        return {"success": False, "error": str(e)}

