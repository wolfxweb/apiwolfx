"""
Rotas para produtos do Mercado Livre
"""
from fastapi import APIRouter, Depends, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.config.database import get_db
from app.controllers.ml_product_controller import MLProductController
from app.controllers.auth_controller import AuthController

ml_product_router = APIRouter(prefix="/products", tags=["ML Products"])

def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Obtém usuário atual da sessão"""
    session_token = request.cookies.get('session_token')
    if not session_token:
        raise HTTPException(status_code=401, detail="Sessão não encontrada")
    
    auth_controller = AuthController()
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail=result["error"])
    
    return result["user"]

@ml_product_router.get("/", response_class=HTMLResponse)
async def ml_products_page(
    request: Request,
    ml_account_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    shipping_type: Optional[str] = Query(None),
    catalog_listing: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Página de produtos ML"""
    try:
        controller = MLProductController(db)
        return controller.get_products_page(
            company_id=user["company"]["id"],
            user_data=user,
            ml_account_id=ml_account_id,
            status=status,
            page=page,
            limit=limit
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Erro ao carregar produtos: {str(e)}"}
        )

@ml_product_router.get("/sync/{ml_account_id}")
async def sync_products(
    ml_account_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Sincronizar produtos de uma conta ML"""
    try:
        controller = MLProductController(db)
        result = controller.sync_products(
            company_id=user["company"]["id"],
            ml_account_id=ml_account_id,
            user_id=user["id"]
        )
        
        if result['success']:
            return JSONResponse(content=result)
        else:
            return JSONResponse(
                status_code=400,
                content=result
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Erro na sincronização: {str(e)}"}
        )

@ml_product_router.post("/import")
async def import_product(
    request: Request,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Importar produtos do Mercado Livre (individual ou em massa)"""
    try:
        # Obter dados do corpo da requisição
        body = await request.json()
        
        # Log dos dados recebidos para debug
        print(f"🔍 DEBUG - Dados recebidos: {body}")
        print(f"🔍 DEBUG - Usuário: {user}")
        
        ml_account_id = body.get("ml_account_id")
        import_type = body.get("import_type", "single")
        
        if not ml_account_id:
            print(f"❌ ERRO - ml_account_id não fornecido: {ml_account_id}")
            return JSONResponse(
                status_code=400,
                content={"error": "ml_account_id é obrigatório"}
            )
        
        controller = MLProductController(db)
        
        if import_type == "single":
            product_id = body.get("product_id")
            if not product_id:
                return JSONResponse(
                    status_code=400,
                    content={"error": "product_id é obrigatório para importação individual"}
                )
            
            result = controller.import_products(
                company_id=user["company"]["id"],
                ml_account_id=ml_account_id,
                user_id=user["id"],
                import_type=import_type,
                product_id=product_id
            )
        
        elif import_type == "bulk":
            product_statuses = body.get("product_statuses", [])
            limit = body.get("limit", 100)
            
            print(f"🔍 DEBUG - product_statuses: {product_statuses}")
            print(f"🔍 DEBUG - limit: {limit}")
            
            if not product_statuses:
                print(f"❌ ERRO - product_statuses vazio: {product_statuses}")
                return JSONResponse(
                    status_code=400,
                    content={"error": "product_statuses é obrigatório para importação em massa"}
                )
            
            result = controller.import_products(
                company_id=user["company"]["id"],
                ml_account_id=ml_account_id,
                user_id=user["id"],
                import_type=import_type,
                product_statuses=product_statuses,
                limit=limit
            )
        
        else:
            return JSONResponse(
                status_code=400,
                content={"error": "import_type deve ser 'single' ou 'bulk'"}
            )
        
        if result['success']:
            return JSONResponse(content=result)
        else:
            return JSONResponse(
                status_code=400,
                content=result
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Erro na importação: {str(e)}"}
        )


@ml_product_router.get("/sync-history/{ml_account_id}")
async def get_sync_history(
    ml_account_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Buscar histórico de sincronizações"""
    try:
        controller = MLProductController(db)
        result = controller.get_sync_history(
            company_id=user["company"]["id"],
            ml_account_id=ml_account_id,
            user_id=user["id"]
        )
        
        if result['success']:
            return JSONResponse(content=result)
        else:
            return JSONResponse(
                status_code=404,
                content=result
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Erro ao buscar histórico: {str(e)}"}
        )

@ml_product_router.get("/stats")
async def get_products_stats(
    request: Request,
    ml_account_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Buscar estatísticas de produtos"""
    try:
        controller = MLProductController(db)
        result = controller.get_products_stats(
            company_id=user["company"]["id"],
            ml_account_id=ml_account_id
        )
        
        if result['success']:
            return JSONResponse(content=result)
        else:
            return JSONResponse(
                status_code=500,
                content=result
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Erro ao buscar estatísticas: {str(e)}"}
        )

@ml_product_router.get("/api/accounts")
async def get_ml_accounts(
    request: Request,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """API para buscar contas ML do usuário"""
    try:
        from app.models.saas_models import MLAccount, UserMLAccount, MLAccountStatus
        
        # Buscar contas ML que o usuário tem permissão de acessar
        accounts = db.query(MLAccount).join(UserMLAccount).filter(
            MLAccount.company_id == user["company"]["id"],
            MLAccount.status == MLAccountStatus.ACTIVE,
            UserMLAccount.user_id == user["id"],
            UserMLAccount.can_read == True
        ).all()
        
        return JSONResponse(content={
            "success": True,
            "accounts": [
                {
                    "id": acc.id,
                    "nickname": acc.nickname,
                    "email": acc.email,
                    "country_id": acc.country_id,
                    "site_id": acc.site_id,
                    "is_primary": acc.is_primary,
                    "status": acc.status.value if hasattr(acc.status, 'value') else str(acc.status),
                    "last_sync": acc.last_sync.isoformat() if acc.last_sync else None,
                    "created_at": acc.created_at.isoformat() if acc.created_at else None
                }
                for acc in accounts
            ],
            "total_accounts": len(accounts)
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Erro ao buscar contas: {str(e)}"}
        )

@ml_product_router.get("/api/filter-options")
async def get_filter_options(
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """API para buscar opções de filtros"""
    try:
        from sqlalchemy import distinct, func
        from app.models.saas_models import MLProduct
        
        # Buscar categorias únicas
        categories = db.query(
            MLProduct.category_id,
            MLProduct.category_name
        ).filter(
            MLProduct.company_id == user["company"]["id"],
            MLProduct.category_id.isnot(None)
        ).distinct().all()
        
        # Buscar tipos de envio únicos
        shipping_types = db.query(
            MLProduct.shipping.op('->>')('shipping_type').label('shipping_type')
        ).filter(
            MLProduct.company_id == user["company"]["id"],
            MLProduct.shipping.isnot(None)
        ).distinct().all()
        
        return JSONResponse(content={
            "success": True,
            "categories": [
                {
                    "id": cat.category_id,
                    "name": cat.category_name or cat.category_id
                }
                for cat in categories
            ],
            "shipping_types": [
                {
                    "value": st.shipping_type,
                    "label": st.shipping_type
                }
                for st in shipping_types if st.shipping_type
            ]
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Erro ao buscar opções: {str(e)}"}
        )

@ml_product_router.get("/api/search")
async def search_products(
    request: Request,
    q: Optional[str] = Query(None),
    ml_account_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    shipping_type: Optional[str] = Query(None),
    catalog_listing: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
    order: Optional[str] = Query("asc"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """API para buscar produtos com filtros"""
    try:
        from sqlalchemy import and_, or_
        from app.models.saas_models import MLProduct
        
        query = db.query(MLProduct).filter(MLProduct.company_id == user["company"]["id"])
        
        if ml_account_id and ml_account_id.strip():
            try:
                account_id = int(ml_account_id)
                query = query.filter(MLProduct.ml_account_id == account_id)
            except ValueError:
                pass  # Ignorar se não for um inteiro válido
        
        if status:
            try:
                from app.models.saas_models import MLProductStatus
                status_enum = MLProductStatus(status)
                query = query.filter(MLProduct.status == status_enum)
            except ValueError:
                # Se o status não for válido, ignorar o filtro
                pass
        
        if category_id:
            query = query.filter(MLProduct.category_id == category_id)
        
        if shipping_type:
            # Filtrar por tipo de envio no campo JSON shipping
            query = query.filter(MLProduct.shipping.op('->>')('shipping_type') == shipping_type)
        
        if catalog_listing:
            # Filtrar por produtos de catálogo
            if catalog_listing.lower() == 'true':
                query = query.filter(MLProduct.catalog_listing == True)
            elif catalog_listing.lower() == 'false':
                query = query.filter(MLProduct.catalog_listing == False)
        
        if q:
            query = query.filter(
                or_(
                    MLProduct.title.ilike(f"%{q}%"),
                    MLProduct.ml_item_id.ilike(f"%{q}%")
                )
            )
        
        # Aplicar ordenação
        if sort and order:
            # Mapear campos de ordenação
            sort_mapping = {
                'title': MLProduct.title,
                'price': MLProduct.price,
                'available_quantity': MLProduct.available_quantity,
                'status': MLProduct.status
            }
            
            if sort in sort_mapping:
                sort_column = sort_mapping[sort]
                if order.lower() == 'desc':
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())
            else:
                # Ordenação padrão por ID
                query = query.order_by(MLProduct.id.desc())
        else:
            # Ordenação padrão por ID
            query = query.order_by(MLProduct.id.desc())
        
        total = query.count()
        offset = (page - 1) * limit
        products = query.offset(offset).limit(limit).all()
        
        # Não precisamos mais buscar nomes das categorias da API
        # pois agora estão salvos no banco de dados
        
        return JSONResponse(content={
            "success": True,
            "products": [
                {
                    "id": p.id,
                    "ml_item_id": p.ml_item_id,
                    "title": p.title,
                    "price": p.price,
                    "currency_id": p.currency_id,
                    "available_quantity": p.available_quantity,
                    "sold_quantity": p.sold_quantity,
                    "status": p.status.value if p.status else None,
                    "category_id": p.category_id,
                    "category_name": p.category_name,
                    "condition": p.condition,
                    "thumbnail": p.thumbnail,
                    "permalink": p.permalink,
                    "shipping": p.shipping,
                    "catalog_product_id": p.catalog_product_id,
                    "catalog_listing": p.catalog_listing,
                    "last_sync": p.last_sync.isoformat() if p.last_sync else None
                }
                for p in products
            ],
            "total": total,
            "page": page,
            "limit": limit,
            "has_next": (offset + limit) < total,
            "has_prev": page > 1
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Erro na busca: {str(e)}"}
        )

@ml_product_router.get("/details/{product_id}", response_class=HTMLResponse)
async def ml_product_details_page(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Página de detalhes do produto (sem autenticação temporariamente)"""
    try:
        controller = MLProductController(db)
        # Criar usuário mock para teste
        mock_user = {
            "id": 1,
            "company": {"id": 15}
        }
        return controller.get_product_details_page(request, mock_user, product_id)
    except Exception as e:
        return HTMLResponse(
            content=f"<h1>Erro</h1><p>{str(e)}</p>",
            status_code=500
        )

@ml_product_router.get("/test-details/{product_id}", response_class=HTMLResponse)
async def test_product_details_page(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Teste de página de detalhes do produto (sem autenticação)"""
    try:
        controller = MLProductController(db)
        # Criar usuário mock para teste
        mock_user = {
            "id": 1,
            "company": {"id": 15}
        }
        return controller.get_product_details_page(request, mock_user, product_id)
    except Exception as e:
        return HTMLResponse(
            content=f"<h1>Erro</h1><p>{str(e)}</p>",
            status_code=500
        )

@ml_product_router.post("/delete")
async def delete_products(
    body: dict,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove produtos da base de dados"""
    try:
        print(f"🔍 DEBUG DELETE - Dados recebidos: {body}")
        print(f"🔍 DEBUG DELETE - Usuário: {user}")
        
        delete_all = body.get("delete_all", False)
        product_ids = body.get("product_ids", [])
        
        controller = MLProductController(db)
        
        result = controller.delete_products(
            company_id=user["company"]["id"],
            user_id=user["id"],
            delete_all=delete_all,
            product_ids=product_ids
        )
        
        if result['success']:
            return JSONResponse(content=result)
        else:
            return JSONResponse(
                status_code=400,
                content=result
            )
            
    except Exception as e:
        print(f"❌ ERRO DELETE: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Erro ao remover produtos: {str(e)}"}
        )