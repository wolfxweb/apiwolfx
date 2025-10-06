"""
Rotas para gerenciar produtos importados
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Cookie
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.controllers.auth_controller import get_current_user
from app.services.product_service import ProductService

logger = logging.getLogger(__name__)

product_router = APIRouter()

@product_router.get("/api/products")
async def get_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Lista produtos importados da empresa"""
    try:
        service = ProductService(db)
        result = service.get_products(
            company_id=user["company"]["id"],
            skip=skip,
            limit=limit
        )
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Erro ao listar produtos: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Erro interno do servidor"}
        )

@product_router.post("/api/products/import/{ml_item_id}")
async def import_single_product(
    ml_item_id: str,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Importa um produto específico do Mercado Livre"""
    try:
        service = ProductService(db)
        result = service.import_product(
            ml_item_id=ml_item_id,
            company_id=user["company"]["id"],
            user_id=user["id"]
        )
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            return JSONResponse(
                status_code=400,
                content=result
            )
        
    except Exception as e:
        logger.error(f"Erro ao importar produto {ml_item_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Erro interno do servidor"}
        )

@product_router.post("/api/products/import-all")
async def import_all_products(
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Importa todos os produtos da empresa do Mercado Livre"""
    try:
        service = ProductService(db)
        result = service.import_all_products(
            company_id=user["company"]["id"],
            user_id=user["id"]
        )
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            return JSONResponse(
                status_code=400,
                content=result
            )
        
    except Exception as e:
        logger.error(f"Erro ao importar todos os produtos: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Erro interno do servidor"}
        )

@product_router.post("/api/products/import-to-internal")
async def import_to_internal_products(
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Importa produtos do ML para produtos internos"""
    try:
        service = ProductService(db)
        result = service.import_to_internal_products(
            company_id=user["company"]["id"],
            user_id=user["id"]
        )
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            return JSONResponse(
                status_code=400,
                content=result
            )
        
    except Exception as e:
        logger.error(f"Erro ao importar produtos para internos: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Erro interno do servidor"}
        )

@product_router.post("/api/products/import-selected-to-internal")
async def import_selected_to_internal_products(
    request_data: dict = Body(..., description="Dados da requisição"),
    session_token: str = Cookie(None, description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Importa produtos selecionados do ML para produtos internos"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Token de sessão não fornecido")
    
    try:
        # Obter usuário atual
        current_user = get_current_user(session_token)
        company_id = current_user["company_id"]
        user_id = current_user["id"]
        
        # Extrair product_ids do request_data
        product_ids = request_data.get("product_ids", [])
        
        if not product_ids:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Nenhum produto selecionado"}
            )
        
        service = ProductService(db)
        result = service.import_selected_to_internal_products(
            company_id=company_id,
            user_id=user_id,
            product_ids=product_ids
        )
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            return JSONResponse(
                status_code=400,
                content=result
            )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro ao importar produtos selecionados para internos: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Erro interno do servidor"}
        )

@product_router.put("/api/products/{product_id}")
async def update_product(
    product_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Atualiza dados de um produto"""
    try:
        service = ProductService(db)
        result = service.update_product(
            product_id=product_id,
            company_id=user["company"]["id"],
            data=data
        )
        
        if result["success"]:
            return JSONResponse(content=result)
        else:
            return JSONResponse(
                status_code=400,
                content=result
            )
        
    except Exception as e:
        logger.error(f"Erro ao atualizar produto {product_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Erro interno do servidor"}
        )

@product_router.get("/api/products/{product_id}")
async def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Obtém dados de um produto específico"""
    try:
        from app.models.saas_models import Product
        from sqlalchemy import and_
        
        product = db.query(Product).filter(
            and_(
                Product.id == product_id,
                Product.company_id == user["company"]["id"]
            )
        ).first()
        
        if not product:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Produto não encontrado"}
            )
        
        return JSONResponse(content={
            "success": True,
            "product": {
                "id": product.id,
                "ml_item_id": product.ml_item_id,
                "title": product.title,
                "thumbnail": product.thumbnail,
                "sku": product.sku,
                "cost_price": product.cost_price,
                "tax_rate": product.tax_rate,
                "marketing_cost": product.marketing_cost,
                "other_costs": product.other_costs,
                "notes": product.notes,
                "created_at": product.created_at.isoformat() if product.created_at else None,
                "updated_at": product.updated_at.isoformat() if product.updated_at else None
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar produto {product_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Erro interno do servidor"}
        )