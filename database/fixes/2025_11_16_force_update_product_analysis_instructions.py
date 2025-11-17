def run(db):
    """
    Força a atualização das instruções do agente de 'Análise de produto' para
    instruir o fluxo de identificação (código ou nome) e uso das ferramentas.
    - Procura por agente ativo cujo nome contenha 'analise' e 'produto'.
    - Se não encontrar, tenta o agente ID 1.
    - Acrescenta o bloco se ainda não estiver presente.
    """
    try:
        from sqlalchemy import text as sql_text
        # Encontrar agente por nome
        row = db.execute(sql_text(
            """
            SELECT id, instructions FROM openai_assistants
            WHERE is_active = TRUE AND lower(name) LIKE '%analise%' AND lower(name) LIKE '%produto%'
            ORDER BY id ASC LIMIT 1
            """
        )).fetchone()
        target_id = None
        current_instructions = None
        if row:
            target_id = row[0]
            current_instructions = row[1] or ""
        else:
            # fallback para ID 1
            r2 = db.execute(sql_text("SELECT id, instructions FROM openai_assistants WHERE id = 1")).fetchone()
            if r2:
                target_id = r2[0]
                current_instructions = r2[1] or ""
        
        if not target_id:
            print("⚠️ [FIX] Nenhum agente de análise de produto encontrado (e ID 1 ausente).")
            return
        
        marker = "[REGRAS DE IDENTIFICAÇÃO DO PRODUTO]"
        if marker in (current_instructions or ""):
            print(f"ℹ️ [FIX] Regras já presentes nas instruções do agente {target_id}; nada a fazer.")
            return
        
        append_text = (
            "\n\n[REGRAS DE IDENTIFICAÇÃO DO PRODUTO]\n"
            "- Antes de qualquer análise, você DEVE identificar o produto alvo.\n"
            "- Se o usuário informar um código, aceite códigos nos formatos: id interno (numérico), seller_sku (texto) ou ml_item_id (ex.: MLB...).\n"
            "- Se o usuário NÃO souber o código, peça o NOME do produto.\n"
            "- Quando o usuário fornecer um NOME, chame a função 'search_products_by_name' para listar até 10 opções, retornando id, título, seller_sku, ml_item_id e preço.\n"
            "- Mostre as opções para o usuário e peça que ele escolha UMA (pelo id interno, seller_sku ou ml_item_id).\n"
            "- Apenas após a confirmação/seleção, resolva o produto usando a função 'resolve_product_by_code' e prossiga com as consultas das demais ferramentas usando 'product_id'.\n"
            "- Se o código fornecido não for encontrado, explique e peça outro código ou nome.\n"
        )
        
        new_instructions = (current_instructions or "") + append_text
        with db.begin():
            db.execute(
                sql_text("UPDATE openai_assistants SET instructions = :instr WHERE id = :id"),
                {"instr": new_instructions, "id": target_id}
            )
        print(f"✅ [FIX] Instruções do agente {target_id} atualizadas com regras de identificação de produto.")
    except Exception as e:
        print(f"❌ [FIX] Erro ao forçar atualização de instruções: {e}")

