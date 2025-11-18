"""
Script para adicionar instrução de responder sempre em português ao agente "Analise produto"
Executa automaticamente no startup do container
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def run(db=None):
    """
    Adiciona instrução para o agente sempre responder em português e traduzir status.
    - Procura por agente ativo cujo nome contenha 'analise' e 'produto'.
    - Se não encontrar, tenta o agente ID 1.
    - Adiciona o bloco de instrução de idioma se ainda não estiver presente.
    """
    try:
        if db is None:
            from app.config.database import get_db
            db = next(get_db())
        
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
            logger.info("⚠️ [MIGRATION] Nenhum agente de análise de produto encontrado (e ID 1 ausente).")
            return {"success": True, "message": "Agente não encontrado"}
        
        marker = "[IDIOMA]"
        if marker in (current_instructions or ""):
            logger.info(f"ℹ️ [MIGRATION] Instrução de idioma já presente nas instruções do agente {target_id}; nada a fazer.")
            return {"success": True, "message": "Instrução já presente"}
        
        # Adicionar seção de idioma de forma compatível com o estilo do prompt atual
        append_text = (
            "\n\n[IDIOMA]\n"
            "- IMPORTANTE: Sempre responda em PORTUGUÊS BRASILEIRO. Nunca use inglês nas respostas.\n"
            "- Traduza todos os status de pedidos para português:\n"
            "  PENDING→Pendente, CONFIRMED→Confirmado, PAID→Pago, PARTIALLY_PAID→Parcialmente Pago,\n"
            "  SHIPPED→Enviado, DELIVERED→Entregue, CANCELLED→Cancelado, PENDING_CANCEL→Cancelamento Pendente,\n"
            "  REFUNDED→Reembolsado, PARTIALLY_REFUNDED→Parcialmente Reembolsado, INVALID→Inválido,\n"
            "  READY_TO_PREPARE→Pronto para Preparar.\n"
            "- Formate valores monetários em R$ e datas em DD/MM/YYYY.\n"
            "- Todas as respostas, perguntas e análises devem ser em português brasileiro."
        )
        
        new_instructions = (current_instructions or "") + append_text
        
        with db.begin():
            db.execute(
                sql_text("UPDATE openai_assistants SET instructions = :instr WHERE id = :id"),
                {"instr": new_instructions, "id": target_id}
            )
        
        logger.info(f"✅ [MIGRATION] Instrução de idioma adicionada ao agente {target_id}.")
        return {"success": True, "message": f"Instrução adicionada ao agente {target_id}"}
        
    except Exception as e:
        logger.error(f"❌ [MIGRATION] Erro ao adicionar instrução de idioma: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

