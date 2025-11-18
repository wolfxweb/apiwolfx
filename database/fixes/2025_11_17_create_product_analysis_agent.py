"""
Script para criar o agente "Analise produto" em produção
Executa automaticamente no startup do container
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def run(db=None):
    """
    Cria o agente "Analise produto" se ainda não existir.
    Também associa as ferramentas necessárias ao agente.
    """
    try:
        if db is None:
            from app.config.database import get_db
            db = next(get_db())
        
        # Verificar se o agente já existe
        check_query = text("""
            SELECT EXISTS(
                SELECT 1 FROM openai_assistants 
                WHERE LOWER(name) LIKE LOWER('%analise%produto%')
            )
        """)
        result = db.execute(check_query).fetchone()
        agent_exists = result[0] if result else False
        
        if agent_exists:
            logger.info("ℹ️ [MIGRATION] Agente 'Analise produto' já existe. Nada a fazer.")
            return {"success": True, "message": "Agente já existe"}
        
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
                'Analise produto',
                'Agente especializado em análise de produtos do Mercado Livre',
                'local_1_' || extract(epoch from now())::bigint,
                'gpt-5-nano',
                :instructions,
                NULL,
                4000,
                '{"reasoning_effort": "low", "verbosity": "medium", "tools": []}'::jsonb,
                'chat',
                'Análise de produtos',
                TRUE,
                NULL,
                NULL,
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
        
        instructions = """Você é um especialista em análise de produtos do Mercado Livre.

[REGRAS DE IDENTIFICAÇÃO DO PRODUTO]
- Antes de qualquer análise, você DEVE identificar o produto alvo.
- Se o usuário informar um código, aceite códigos nos formatos: id interno (numérico), seller_sku (texto) ou ml_item_id (ex.: MLB...).
- Se o usuário NÃO souber o código, peça o NOME do produto.
- Quando o usuário fornecer um NOME, chame a função 'search_products_by_name' para listar até 10 opções, retornando id, título, seller_sku, ml_item_id e preço.
- Mostre as opções para o usuário e peça que ele escolha UMA (pelo id interno, seller_sku ou ml_item_id).
- Apenas após a confirmação/seleção, resolva o produto usando a função 'resolve_product_by_code' e prossiga com as consultas das demais ferramentas usando 'product_id'.
- Se o código fornecido não for encontrado, explique e peça outro código ou nome.

[FERRAMENTAS DISPONÍVEIS]
Você tem acesso às seguintes ferramentas para análise:
- get_orders: Seleciona pedidos com filtros de período, status, item e comprador
- get_product_sales: Lista vendas de um produto no período
- search_products_by_name: Busca produtos pelo nome
- resolve_product_by_code: Resolve produto por código (id, SKU ou ml_item_id)

[INSTRUÇÕES DE USO]
- Use as ferramentas para coletar dados sobre o produto
- Analise os dados coletados e forneça insights acionáveis
- Sempre filtre consultas pelo company_id do usuário logado
- Seja claro e objetivo nas respostas
- Forneça recomendações práticas baseadas nos dados"""
        
        welcome_message = "Olá! Sou o agente de análise de produtos. Para começar, preciso do código do produto (ML item ID) ou do nome do produto. Como posso ajudar?"
        
        with db.begin():
            result = db.execute(insert_query, {
                "instructions": instructions,
                "welcome_message": welcome_message
            })
            agent_id = result.fetchone()[0]
        
        logger.info(f"✅ [MIGRATION] Agente 'Analise produto' criado com sucesso (ID: {agent_id})")
        
        # Associar ferramentas ao agente
        tools_to_associate = [
            'get_orders',
            'get_product_sales',
            'search_products_by_name',
            'resolve_product_by_code'
        ]
        
        associated_count = 0
        for tool_name in tools_to_associate:
            associate_query = text("""
                INSERT INTO openai_agent_tools (agent_id, tool_id, config)
                SELECT :agent_id, t.id, NULL
                FROM openai_tools t
                WHERE t.name = :tool_name AND t.is_active = TRUE
                ON CONFLICT (agent_id, tool_id) DO NOTHING
            """)
            
            with db.begin():
                result = db.execute(associate_query, {
                    "agent_id": agent_id,
                    "tool_name": tool_name
                })
                if result.rowcount > 0:
                    associated_count += 1
                    logger.info(f"✅ [MIGRATION] Ferramenta '{tool_name}' associada ao agente")
        
        logger.info(f"✅ [MIGRATION] {associated_count} ferramenta(s) associada(s) ao agente")
        
        return {
            "success": True,
            "message": f"Agente criado com ID {agent_id} e {associated_count} ferramenta(s) associada(s)"
        }
        
    except Exception as e:
        logger.error(f"❌ [MIGRATION] Erro ao criar agente 'Analise produto': {e}", exc_info=True)
        return {"success": False, "error": str(e)}

