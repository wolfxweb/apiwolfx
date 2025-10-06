"""
Rotas para gerenciar produtos internos/customizados
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.controllers.auth_controller import get_current_user
from app.controllers.internal_product_controller import InternalProductController

logger = logging.getLogger(__name__)

internal_product_router = APIRouter(prefix="/internal-products", tags=["Internal Products"])


@internal_product_router.post("/")
async def create_internal_product(
    name: str = Body(..., description="Nome do produto interno"),
    internal_sku: str = Body(..., description="SKU interno único"),
    base_product_id: Optional[int] = Body(None, description="ID do produto base do ML (opcional)"),
    description: Optional[str] = Body(None, description="Descrição do produto"),
    cost_price: Optional[float] = Body(None, description="Preço de custo"),
    selling_price: Optional[float] = Body(None, description="Preço de venda"),
    category: Optional[str] = Body(None, description="Categoria"),
    brand: Optional[str] = Body(None, description="Marca"),
    supplier: Optional[str] = Body(None, description="Fornecedor"),
    barcode: Optional[str] = Body(None, description="Código de barras"),
    tax_rate: Optional[float] = Body(None, description="Taxa de imposto (%)"),
    marketing_cost: Optional[float] = Body(None, description="Custo de marketing"),
    other_costs: Optional[float] = Body(None, description="Outros custos"),
    min_stock: Optional[int] = Body(None, description="Estoque mínimo"),
    current_stock: Optional[int] = Body(None, description="Estoque atual"),
    notes: Optional[str] = Body(None, description="Observações"),
    session_token: str = Query(..., description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Cria um novo produto interno"""
    try:
        # Obter usuário atual
        current_user = get_current_user(session_token)
        company_id = current_user["company_id"]
        
        controller = InternalProductController()
        result = controller.create_internal_product(
            company_id=company_id,
            name=name,
            internal_sku=internal_sku,
            base_product_id=base_product_id,
            description=description,
            cost_price=cost_price,
            selling_price=selling_price,
            category=category,
            brand=brand,
            supplier=supplier,
            barcode=barcode,
            tax_rate=tax_rate,
            marketing_cost=marketing_cost,
            other_costs=other_costs,
            min_stock=min_stock,
            current_stock=current_stock,
            notes=notes,
            db=db
        )
        
        return JSONResponse(content=result, status_code=201)
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro ao criar produto interno: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@internal_product_router.get("/list")
async def get_internal_products(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    category: Optional[str] = Query(None, description="Filtrar por categoria"),
    search: Optional[str] = Query(None, description="Buscar por nome, SKU ou descrição"),
    limit: int = Query(50, description="Limite de resultados"),
    offset: int = Query(0, description="Offset para paginação"),
    session_token: str = Query(..., description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Lista produtos internos da empresa"""
    try:
        # Obter usuário atual
        current_user = get_current_user(session_token)
        company_id = current_user["company_id"]
        
        controller = InternalProductController()
        result = controller.get_internal_products(
            company_id=company_id,
            status=status,
            category=category,
            search=search,
            limit=limit,
            offset=offset,
            db=db
        )
        
        return JSONResponse(content=result)
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro ao listar produtos internos: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@internal_product_router.get("/{product_id}")
async def get_internal_product(
    product_id: int,
    session_token: str = Query(..., description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Obtém um produto interno específico"""
    try:
        # Obter usuário atual
        current_user = get_current_user(session_token)
        company_id = current_user["company_id"]
        
        controller = InternalProductController()
        result = controller.get_internal_product(
            product_id=product_id,
            company_id=company_id,
            db=db
        )
        
        return JSONResponse(content=result)
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro ao obter produto interno: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@internal_product_router.put("/{product_id}")
async def update_internal_product(
    product_id: int,
    update_data: dict = Body(..., description="Dados para atualização"),
    session_token: str = Query(..., description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Atualiza um produto interno"""
    try:
        # Obter usuário atual
        current_user = get_current_user(session_token)
        company_id = current_user["company_id"]
        
        controller = InternalProductController()
        result = controller.update_internal_product(
            product_id=product_id,
            company_id=company_id,
            update_data=update_data,
            db=db
        )
        
        return JSONResponse(content=result)
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro ao atualizar produto interno: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@internal_product_router.delete("/{product_id}")
async def delete_internal_product(
    product_id: int,
    session_token: str = Query(..., description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Remove um produto interno"""
    try:
        # Obter usuário atual
        current_user = get_current_user(session_token)
        company_id = current_user["company_id"]
        
        controller = InternalProductController()
        result = controller.delete_internal_product(
            product_id=product_id,
            company_id=company_id,
            db=db
        )
        
        return JSONResponse(content=result)
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro ao remover produto interno: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@internal_product_router.get("/base-products/search")
async def get_base_products(
    search: Optional[str] = Query(None, description="Buscar produtos base"),
    session_token: str = Query(..., description="Token de sessão"),
    db: Session = Depends(get_db)
):
    """Lista produtos do ML que podem ser usados como base"""
    try:
        # Obter usuário atual
        current_user = get_current_user(session_token)
        company_id = current_user["company_id"]
        
        controller = InternalProductController()
        result = controller.get_base_products(
            company_id=company_id,
            search=search,
            db=db
        )
        
        return JSONResponse(content=result)
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro ao listar produtos base: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")
