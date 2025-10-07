"""
Rotas para buscar taxas reais do Mercado Livre
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.services.ml_pricing_service import MLPricingService
from app.controllers.auth_controller import AuthController
from fastapi import Request

router = APIRouter()

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Obtém usuário atual da sessão"""
    session_token = request.cookies.get('session_token')
    if not session_token:
        raise HTTPException(status_code=401, detail="Sessão não encontrada")
    
    auth_controller = AuthController()
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail=result["error"])
    
    return result["user"]

@router.get("/fees")
async def get_ml_fees(
    price: float = Query(..., description="Preço do produto"),
    category_id: str = Query(None, description="ID da categoria"),
    listing_type_id: str = Query("gold_special", description="Tipo de publicação"),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Obtém as taxas reais do Mercado Livre para um produto
    
    Args:
        price: Preço do produto
        category_id: ID da categoria (opcional)
        listing_type_id: Tipo de publicação (default: gold_special)
        db: Sessão do banco de dados
        user: Usuário logado
    
    Returns:
        Taxas do Mercado Livre calculadas
    """
    try:
        service = MLPricingService(db)
        fees = service.calculate_ml_fees(
            user_id=user["id"],
            price=price,
            category_id=category_id
        )
        
        return {
            "success": True,
            "fees": fees
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/listing-prices")
async def get_listing_prices(
    price: float = Query(..., description="Preço do produto"),
    category_id: str = Query(None, description="ID da categoria"),
    listing_type_id: str = Query("gold_special", description="Tipo de publicação"),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Obtém os dados brutos da API listing_prices do Mercado Livre
    
    Args:
        price: Preço do produto
        category_id: ID da categoria (opcional)
        listing_type_id: Tipo de publicação
        db: Sessão do banco de dados
        user: Usuário logado
    
    Returns:
        Dados brutos da API listing_prices
    """
    try:
        service = MLPricingService(db)
        listing_prices = service.get_listing_prices(
            user_id=user["id"],
            price=price,
            category_id=category_id,
            listing_type_id=listing_type_id
        )
        
        if listing_prices:
            return {
                "success": True,
                "listing_prices": listing_prices
            }
        else:
            return {
                "success": False,
                "error": "Não foi possível obter dados da API"
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
