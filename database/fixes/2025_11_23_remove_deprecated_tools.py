"""
Script para remover/desativar ferramentas antigas não utilizadas do banco de dados.
Este script deve ser executado durante o startup da aplicação, antes do seed de novas ferramentas.
"""
import logging
from sqlalchemy import text
from app.config.database import get_db

logger = logging.getLogger(__name__)

# Lista de ferramentas antigas que devem ser desativadas/removidas
DEPRECATED_TOOLS = [
    "get_ml_order_status",
    "get_product_info"
]


def run(db=None):
    """Desativa ferramentas antigas não utilizadas no banco de dados"""
    try:
        if db is None:
            db = next(get_db())
        
        logger.info(f"🧹 Removendo/desativando {len(DEPRECATED_TOOLS)} ferramentas antigas...")
        
        for tool_name in DEPRECATED_TOOLS:
            try:
                # Primeiro, desativar a ferramenta
                result = db.execute(
                    text(
                        """
                        UPDATE openai_tools 
                        SET is_active = FALSE 
                        WHERE name = :name
                        """
                    ), {"name": tool_name}
                )
                
                if result.rowcount > 0:
                    logger.info(f"✅ Ferramenta '{tool_name}' desativada")
                    
                    # Desativar handlers associados
                    db.execute(
                        text(
                            """
                            UPDATE openai_tool_handlers 
                            SET is_active = FALSE 
                            WHERE tool_id IN (
                                SELECT id FROM openai_tools WHERE name = :name
                            )
                            """
                        ), {"name": tool_name}
                    )
                    
                    # Remover associações com agentes (opcional - pode manter para histórico)
                    # db.execute(
                    #     text(
                    #         """
                    #         DELETE FROM openai_agent_tools 
                    #         WHERE tool_id IN (
                    #             SELECT id FROM openai_tools WHERE name = :name
                    #         )
                    #         """
                    #     ), {"name": tool_name}
                    # )
                else:
                    logger.debug(f"ℹ️ Ferramenta '{tool_name}' não encontrada no banco (já removida ou nunca existiu)")
                    
            except Exception as e:
                logger.error(f"❌ Erro ao desativar ferramenta '{tool_name}': {e}", exc_info=True)
                # Continuar com as outras ferramentas mesmo se uma falhar
                continue
        
        db.commit()
        logger.info(f"✅ Limpeza de ferramentas antigas concluída")
        return {"success": True, "tools_deactivated": len(DEPRECATED_TOOLS)}
        
    except Exception as e:
        logger.error(f"❌ Erro ao remover ferramentas antigas: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return {"success": False, "error": str(e)}

