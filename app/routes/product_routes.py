from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.services.mercadolibre_service import MercadoLivreService
from app.models.mercadolibre_models import MLSearchResponse, MLItem

# Router para rotas de produtos
product_router = APIRouter(prefix="/products", tags=["Products"])

# Instância do serviço
ml_service = MercadoLivreService()


@product_router.get("/search", response_model=MLSearchResponse)
async def search_products(
    q: str = Query(..., description="Termo de busca"),
    site_id: str = Query("MLB", description="ID do site (MLB, MLA, etc.)"),
    limit: int = Query(50, description="Número de resultados", ge=1, le=50),
    access_token: Optional[str] = Query(None, description="Token de acesso (opcional)")
):
    """Busca produtos no Mercado Livre"""
    results = await ml_service.search_items(q, access_token, site_id, limit)
    if not results:
        raise HTTPException(status_code=400, detail="Erro na busca")
    return results


@product_router.get("/{item_id}", response_model=MLItem)
async def get_product(
    item_id: str,
    access_token: Optional[str] = Query(None, description="Token de acesso (opcional)")
):
    """Obtém detalhes de um produto específico"""
    item = await ml_service.get_item(item_id, access_token)
    if not item:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return item
