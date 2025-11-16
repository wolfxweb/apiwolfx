def run(db):
    """
    Atualiza as instruções do agente ID 1 adicionando as regras de identificação de produto,
    apenas se ainda não estiverem presentes.
    """
    try:
        from sqlalchemy import text as sql_text
        # Buscar instruções atuais
        row = db.execute(sql_text("SELECT instructions FROM openai_assistants WHERE id = :id"), {"id": 1}).fetchone()
        if not row:
            print("⚠️ [FIX] Agente ID 1 não encontrado; nada a fazer.")
            return
        current = row[0] or ""
        marker = "[REGRAS DE IDENTIFICAÇÃO DO PRODUTO]"
        if marker in current:
            print("ℹ️ [FIX] Regras já presentes nas instruções do agente 1; nada a fazer.")
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
        new_instructions = (current or "") + append_text
        with db.begin():
            db.execute(
                sql_text("UPDATE openai_assistants SET instructions = :instr WHERE id = :id"),
                {"instr": new_instructions, "id": 1}
            )
        print("✅ [FIX] Instruções do agente 1 atualizadas com regras de identificação de produto.")
    except Exception as e:
        print(f"❌ [FIX] Erro ao atualizar instruções do agente 1: {e}")

