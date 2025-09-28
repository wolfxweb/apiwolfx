from fastapi import APIRouter, Query, HTTPException
from typing import List
from app.services.mercadolibre_service import MercadoLivreService
from app.models.mercadolibre_models import MLCategory

# Router para rotas de categorias
category_router = APIRouter(prefix="/categories", tags=["Categories"])

# Instância do serviço
ml_service = MercadoLivreService()


@category_router.get("/", response_model=List[MLCategory])
async def get_categories(site_id: str = Query("MLB", description="ID do site")):
    """Obtém lista de categorias do site"""
    categories = await ml_service.get_categories(site_id)
    if not categories:
        raise HTTPException(status_code=400, detail="Erro ao obter categorias")
    return categories


@category_router.get("/{category_id}", response_model=MLCategory)
async def get_category(category_id: str):
    """Obtém detalhes de uma categoria específica"""
    category = await ml_service.get_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    return category
