"""
Atualiza o schema JSON da ferramenta get_orders para incluir os novos parâmetros:
- product_name: busca parcial no título do produto
- seller_sku: busca exata por SKU
- is_catalog: filtro booleano para produtos de catálogo
- limit: torna opcional (remove default obrigatório)
"""
import json
from sqlalchemy import text


def run(db=None):
    """
    Atualiza o json_schema da ferramenta get_orders na tabela openai_tools
    """
    try:
        if db is None:
            from app.config.database import SessionLocal
            db = SessionLocal()
        
        # Novo schema atualizado
        new_schema = {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Data inicial no formato YYYY-MM-DD. Filtra pedidos criados a partir desta data."
                },
                "end_date": {
                    "type": "string",
                    "description": "Data final no formato YYYY-MM-DD. Filtra pedidos criados até esta data."
                },
                "status": {
                    "oneOf": [
                        {"type": "string", "description": "Status único do pedido (ex: 'paid', 'confirmed')"},
                        {"type": "array", "items": {"type": "string"}, "description": "Lista de status para filtrar múltiplos valores"}
                    ],
                    "description": "Filtra pedidos por status. Pode ser uma string única ou array de strings."
                },
                "ml_item_id": {
                    "type": "string",
                    "description": "ID do item no Mercado Livre (ex: 'MLB123456789'). Filtra pedidos que contêm este item."
                },
                "product_name": {
                    "type": "string",
                    "description": "Nome ou parte do nome do produto. Realiza busca parcial no título do produto. Se fornecido, busca produtos correspondentes e filtra pedidos desses produtos."
                },
                "seller_sku": {
                    "type": "string",
                    "description": "SKU do vendedor (código interno do produto). Busca exata por SKU. Se fornecido, busca o produto correspondente e filtra pedidos desse produto."
                },
                "is_catalog": {
                    "type": "boolean",
                    "description": "Filtra pedidos de produtos de catálogo. true = apenas produtos de catálogo, false = apenas produtos não-catálogo, null/omitido = todos os produtos."
                },
                "buyer_nickname": {
                    "type": "string",
                    "description": "Nickname do comprador. Busca parcial (case-insensitive)."
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10000,
                    "description": "Limite de resultados. Se houver filtros além de company_id, o limite é ignorado e todos os resultados são retornados. Se não informado e não houver filtros, aplica limite padrão de segurança (1000)."
                },
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "minimum": 0,
                    "description": "Número de registros a pular (para paginação)."
                }
            }
        }
        
        # Atualizar o schema da ferramenta get_orders
        update_query = text("""
            UPDATE openai_tools
            SET json_schema = CAST(:schema AS JSONB)
            WHERE name = 'get_orders'
            RETURNING id, name
        """)
        
        result = db.execute(update_query, {"schema": json.dumps(new_schema)}).fetchone()
        
        if result:
            tool_id, tool_name = result
            print(f"✅ [FIX] Schema da ferramenta '{tool_name}' (ID: {tool_id}) atualizado com sucesso")
            print(f"   - Novos parâmetros adicionados: product_name, seller_sku, is_catalog")
            print(f"   - Parâmetro 'limit' agora é opcional")
            db.commit()
            return True
        else:
            print("⚠️ [FIX] Ferramenta 'get_orders' não encontrada na tabela openai_tools")
            db.rollback()
            return False
            
    except Exception as e:
        print(f"❌ [FIX] Erro ao atualizar schema da ferramenta get_orders: {e}")
        if db:
            db.rollback()
        raise


if __name__ == "__main__":
    from app.config.database import SessionLocal
    db = SessionLocal()
    try:
        run(db)
    finally:
        db.close()

