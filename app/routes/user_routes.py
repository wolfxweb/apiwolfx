from fastapi import APIRouter, Query, HTTPException
from typing import List
from app.services.mercadolibre_service import MercadoLivreService
from app.models.mercadolibre_models import MLUser, MLItem

# Router para rotas de usuários
user_router = APIRouter(prefix="/users", tags=["Users"])

# Instância do serviço
ml_service = MercadoLivreService()


@user_router.get("/me", response_model=MLUser)
async def get_user_info(access_token: str = Query(..., description="Token de acesso")):
    """Obtém informações do usuário autenticado"""
    user = await ml_service.get_user_info(access_token)
    if not user:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    return user


@user_router.get("/{user_id}/items", response_model=List[MLItem])
async def get_user_items(
    user_id: int,
    access_token: str = Query(..., description="Token de acesso"),
    status: str = Query("active", description="Status dos itens"),
    limit: int = Query(50, description="Número de resultados", ge=1, le=50)
):
    """Obtém itens de um usuário específico"""
    items = await ml_service.get_user_items(user_id, access_token, status, limit)
    if not items:
        raise HTTPException(status_code=404, detail="Usuário não encontrado ou sem itens")
    return items
