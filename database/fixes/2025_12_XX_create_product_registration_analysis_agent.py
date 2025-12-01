"""
Script para criar o agente "Analise cadastro produto"
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def run(db=None):
    """
    Cria o agente "Analise cadastro produto" se ainda não existir.
    """
    try:
        if db is None:
            from app.config.database import get_db
            db = next(get_db())
        
        # Verificar se o agente já existe
        check_query = text("""
            SELECT EXISTS(
                SELECT 1 FROM openai_assistants 
                WHERE LOWER(name) LIKE LOWER('%analise%cadastro%produto%')
            )
        """)
        result = db.execute(check_query).fetchone()
        agent_exists = result[0] if result else False
        
        if agent_exists:
            logger.info("ℹ️ Agente 'Analise cadastro produto' já existe. Nada a fazer.")
            return {"success": True, "message": "Agente já existe"}
        
        # Instruções do agente
        instructions = """Você é um especialista em otimização de cadastros de produtos no Mercado Livre.

[SUA FUNÇÃO]
Analisar o cadastro completo de um produto e fornecer recomendações específicas para otimização, considerando:
- Título do anúncio (SEO, palavras-chave, limite de 60 caracteres)
- Descrição (completa, informativa, SEO)
- Preço e estratégia de precificação
- Categoria e atributos específicos da categoria
- Características do produto (atributos dinâmicos)
- Variações (se aplicável)
- Imagens e mídia
- Informações de envio e garantia
- Códigos (GTIN, SKU, MPN)

[ANÁLISE ESPECÍFICA POR CATEGORIA]
- Os campos e atributos variam conforme a categoria do produto
- Analise os atributos específicos da categoria recebida
- Identifique atributos obrigatórios que podem estar faltando
- Sugira valores apropriados para atributos baseado nas melhores práticas do ML
- Considere as características específicas da categoria (ex: eletrônicos têm atributos diferentes de roupas)

[FORMATO DE RESPOSTA]
Forneça uma análise estruturada com:
1. **Resumo Executivo**: Pontos principais a otimizar
2. **Título**: Sugestões de melhoria (se necessário)
3. **Descrição**: Recomendações de conteúdo e SEO
4. **Atributos**: 
   - Atributos faltantes que são importantes
   - Valores sugeridos para atributos existentes
   - Atributos que podem melhorar a visibilidade
5. **Precificação**: Análise do preço e sugestões
6. **Variações**: Se aplicável, otimizações nas variações
7. **Outros**: Envio, garantia, códigos, etc.

[REGRAS IMPORTANTES]
- Seja específico e acionável nas recomendações
- Considere as regras do Mercado Livre para cada categoria
- Mantenha o limite de 60 caracteres no título
- Priorize atributos obrigatórios e importantes para SEO
- Sugira melhorias práticas e implementáveis"""

        welcome_message = "Olá! Vou analisar o cadastro do seu produto e fornecer recomendações específicas para otimização. Os dados do cadastro serão fornecidos abaixo."
        
        # Criar o agente
        insert_query = text("""
            INSERT INTO openai_assistants (
                name,
                description,
                assistant_id,
                model,
                instructions,
                temperature,
                max_tokens,
                tools_config,
                interaction_mode,
                use_case,
                memory_enabled,
                memory_data,
                initial_prompt,
                welcome_enabled,
                welcome_use_model,
                welcome_message,
                is_active,
                total_runs,
                total_tokens_used,
                created_at,
                updated_at
            ) VALUES (
                'Analise cadastro produto',
                'Agente especializado em análise e otimização de cadastros de produtos do Mercado Livre',
                'local_analise_cadastro_' || extract(epoch from now())::bigint,
                'gpt-5-nano',
                :instructions,
                NULL,
                4000,
                '{"reasoning_effort": "low", "verbosity": "medium", "tools": []}'::jsonb,
                'chat',
                'Análise de cadastro de produto',
                TRUE,
                NULL,
                :initial_prompt,
                TRUE,
                FALSE,
                :welcome_message,
                TRUE,
                0,
                0,
                NOW(),
                NOW()
            )
            RETURNING id
        """)
        
        initial_prompt = """Analise o cadastro de produto do Mercado Livre abaixo e forneça recomendações específicas de otimização.

Considere:
- Título do anúncio (SEO, palavras-chave, limite de 60 caracteres)
- Descrição (completa, informativa, SEO)
- Preço e estratégia de precificação
- Categoria e atributos específicos da categoria
- Características do produto (atributos dinâmicos que variam por categoria)
- Variações (se aplicável)
- Informações de envio e garantia
- Códigos (GTIN, SKU, MPN)

Os dados completos do produto serão fornecidos abaixo."""
        
        with db.begin():
            result = db.execute(insert_query, {
                "instructions": instructions,
                "initial_prompt": initial_prompt,
                "welcome_message": welcome_message
            })
            agent_id = result.fetchone()[0]
        
        logger.info(f"✅ Agente 'Analise cadastro produto' criado com sucesso (ID: {agent_id})")
        return {"success": True, "agent_id": agent_id}
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar agente: {e}", exc_info=True)
        if db:
            db.rollback()
        return {"success": False, "error": str(e)}

