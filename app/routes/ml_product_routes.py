"""
Rotas para produtos do Mercado Livre
"""
import logging
import requests
from fastapi import APIRouter, Depends, Request, Query, HTTPException, Cookie
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.config.database import get_db
from app.controllers.ml_product_controller import MLProductController
from app.controllers.auth_controller import AuthController
from app.models.saas_models import MLProduct, CatalogParticipant

logger = logging.getLogger(__name__)

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
            limit=limit,
            request=request
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
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar contas ML do usuário (filtra por company_id)"""
    try:
        from app.models.saas_models import MLAccount, MLAccountStatus
        
        # Verificar autenticação
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        # Buscar todas as contas ML da empresa do usuário logado
        accounts = db.query(MLAccount).filter(
            MLAccount.company_id == company_id,
            MLAccount.status == MLAccountStatus.ACTIVE
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
        logger.error(f"Erro ao buscar contas ML: {e}")
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
    sku_filter: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
    order: Optional[str] = Query("asc"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=10000),  # Aumentado para 10000 para "Cadastrar Todos"
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
        
        # Filtro por SKU
        if sku_filter and sku_filter.strip():
            search_term = f'%{sku_filter.strip()}%'
            query = query.filter(
                or_(
                    MLProduct.seller_sku.ilike(search_term),
                    MLProduct.title.ilike(search_term)
                )
            )
        
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
                'sold_quantity': MLProduct.sold_quantity,
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
                    "base_price": p.base_price,
                    "original_price": p.original_price,
                    "seller_sku": p.seller_sku,
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

@ml_product_router.get("/analysis/{product_id}", response_class=HTMLResponse)
async def get_product_analysis_page(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Página de análise do produto"""
    try:
        controller = MLProductController(db)
        return controller.get_product_analysis_page(request, user, product_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao carregar análise do produto: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {e}")

@ml_product_router.get("/api/product/{product_id}")
async def get_product_for_analysis(
    product_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """API para buscar dados do produto para análise"""
    try:
        from app.models.saas_models import MLProduct
        
        product = db.query(MLProduct).filter(
            MLProduct.id == product_id,
            MLProduct.company_id == user["company"]["id"]
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
                "subtitle": product.subtitle,
                "price": product.price,
                "currency_id": product.currency_id,
                "status": product.status.value if product.status else None,
                "thumbnail": product.thumbnail,
                "category_id": product.category_id,
                "category_name": product.category_name,
                "condition": product.condition,
                "listing_type_id": product.listing_type_id,
                "buying_mode": product.buying_mode,
                "permalink": product.permalink,
                "available_quantity": product.available_quantity,
                "sold_quantity": product.sold_quantity,
                "shipping": product.shipping,
                "catalog_listing": product.catalog_listing,
                "catalog_product_id": product.catalog_product_id,
                "seller_custom_field": product.seller_custom_field,
                "sku": product.seller_custom_field,  # Alias para compatibilidade
                "seller_sku": product.seller_sku  # SKU do vendedor
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar produto para análise: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Erro interno do servidor: {e}"}
        )

@ml_product_router.get("/api/product/{product_id}/catalog")
async def get_product_catalog_info(
    product_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Busca informações de catálogo do produto usando a API do Mercado Livre"""
    try:
        from app.models.saas_models import MLProduct
        import requests
        
        product = db.query(MLProduct).filter(
            MLProduct.id == product_id,
            MLProduct.company_id == user["company"]["id"]
        ).first()
        
        if not product:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Produto não encontrado"}
            )
        
        if not product.catalog_listing or not product.catalog_product_id:
            return JSONResponse(
                status_code=200,
                content={"success": True, "is_catalog": False, "message": "Produto não é de catálogo"}
            )
        
        # Usar TokenManager para obter token válido
        from app.services.token_manager import TokenManager
        token_manager = TokenManager(db)
        access_token = token_manager.get_valid_token(user["id"])
        
        if not access_token:
            return JSONResponse(
                status_code=401,
                content={"success": False, "error": "Token de acesso não encontrado"}
            )
        
        # Usar a API do Mercado Livre para buscar todos os vendedores do catálogo
        # Endpoint: /products/{catalog_product_id}/items
        api_url = f"https://api.mercadolibre.com/products/{product.catalog_product_id}/items"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(api_url, headers=headers, timeout=30)
        
        if response.status_code == 404:
            return JSONResponse(
                status_code=200,
                content={"success": True, "is_catalog": True, "catalog_products": [], "total_announcers": 0, "message": "Catálogo não encontrado na API"}
            )
        
        response.raise_for_status()
        data = response.json()
        
        catalog_products = []
        if "results" in data:
            for item in data["results"]:
                # Informações de envio detalhadas
                shipping_info = item.get("shipping", {})
                shipping_tags = shipping_info.get("tags", [])
                
                # Informações de vendedor
                seller_info = item.get("seller", {})
                reputation_level = seller_info.get("reputation_level_id", "UNKNOWN")
                
                # Termos de venda
                sale_terms = item.get("sale_terms", [])
                warranty_info = ""
                invoice_info = ""
                for term in sale_terms:
                    if term.get("id") == "WARRANTY_TIME":
                        warranty_info = term.get("value_name", "")
                    elif term.get("id") == "INVOICE":
                        invoice_info = term.get("value_name", "")
                
                # Buscar informações detalhadas do vendedor
                seller_id = item.get("seller_id")
                seller_name = "N/A"
                seller_nickname = "N/A"
                seller_country = "N/A"
                seller_city = "N/A"
                seller_state = "N/A"
                seller_registration_date = "N/A"
                seller_experience = "N/A"
                seller_power_seller = False
                seller_transactions_total = 0
                seller_ratings_positive = 0
                seller_ratings_negative = 0
                seller_ratings_neutral = 0
                seller_mercadopago_accepted = False
                seller_mercadoenvios = "N/A"
                seller_user_type = "N/A"
                seller_tags = []
                
                if seller_id:
                    try:
                        # Chamada para API de usuários
                        user_api_url = f"https://api.mercadolibre.com/users/{seller_id}"
                        user_response = requests.get(user_api_url, headers=headers, timeout=10)
                        
                        if user_response.status_code == 200:
                            user_data = user_response.json()
                            
                            # Informações básicas
                            seller_name = user_data.get("first_name", "N/A")
                            seller_nickname = user_data.get("nickname", "N/A")
                            seller_country = user_data.get("country_id", "N/A")
                            seller_registration_date = user_data.get("registration_date", "N/A")
                            seller_user_type = user_data.get("user_type", "N/A")
                            seller_tags = user_data.get("tags", [])
                            
                            # Endereço
                            address = user_data.get("address", {})
                            seller_city = address.get("city", "N/A")
                            seller_state = address.get("state", "N/A")
                            
                            # Experiência de vendedor
                            seller_experience = user_data.get("seller_experience", "N/A")
                            
                            # Reputação de vendedor
                            seller_reputation = user_data.get("seller_reputation", {})
                            seller_power_seller = seller_reputation.get("power_seller_status") is not None
                            seller_power_seller_status = seller_reputation.get("power_seller_status", None)
                            
                            transactions = seller_reputation.get("transactions", {})
                            seller_transactions_total = transactions.get("total", 0)
                            
                            ratings = transactions.get("ratings", {})
                            seller_ratings_positive = ratings.get("positive", 0)
                            seller_ratings_negative = ratings.get("negative", 0)
                            seller_ratings_neutral = ratings.get("neutral", 0)
                            
                            # Nível de reputação - extrair cor do level_id
                            level_id = seller_reputation.get("level_id", None)
                            seller_reputation_level = None
                            if level_id:
                                # level_id vem como "5_green", "3_yellow", "1_red", etc.
                                if "_green" in level_id:
                                    seller_reputation_level = "GREEN"
                                elif "_yellow" in level_id:
                                    seller_reputation_level = "YELLOW"
                                elif "_red" in level_id:
                                    seller_reputation_level = "RED"
                                else:
                                    # Tentar usar real_level se disponível
                                    real_level = seller_reputation.get("real_level", None)
                                    if real_level:
                                        seller_reputation_level = real_level.upper()
                            
                            # Status e configurações
                            status = user_data.get("status", {})
                            seller_mercadopago_accepted = status.get("mercadopago_tc_accepted", False)
                            seller_mercadoenvios = status.get("mercadoenvios", "N/A")
                            
                    except Exception as e:
                        logger.warning(f"Erro ao buscar dados do vendedor {seller_id}: {e}")
                
                catalog_products.append({
                    "ml_item_id": item.get("item_id"),
                    "title": item.get("title", "Sem título"),
                    "price": item.get("price", 0),
                    "currency_id": item.get("currency_id", "BRL"),
                    "seller_id": item.get("seller_id"),
                    "seller_name": seller_name,
                    "seller_nickname": seller_nickname,
                    "seller_country": seller_country,
                    "seller_city": seller_city,
                    "seller_state": seller_state,
                    "seller_registration_date": seller_registration_date,
                    "seller_experience": seller_experience,
                    "seller_power_seller": seller_power_seller,
                    "seller_power_seller_status": seller_power_seller_status,
                    "seller_reputation_level": seller_reputation_level,
                    "seller_transactions_total": seller_transactions_total,
                    "seller_ratings_positive": seller_ratings_positive,
                    "seller_ratings_negative": seller_ratings_negative,
                    "seller_ratings_neutral": seller_ratings_neutral,
                    "seller_mercadopago_accepted": seller_mercadopago_accepted,
                    "seller_mercadoenvios": seller_mercadoenvios,
                    "seller_user_type": seller_user_type,
                    "seller_tags": seller_tags,
                    "status": "active",  # Assumir ativo se está na API
                    "available_quantity": item.get("available_quantity", 0),
                    "sold_quantity": 0,  # Não disponível na API
                    "permalink": f"https://www.mercadolivre.com.br/{item.get('item_id')}",
                    "thumbnail": item.get("thumbnail", ""),
                    "shipping": shipping_info,
                    "warranty": item.get("warranty", warranty_info),
                    "condition": item.get("condition", "new"),
                    "listing_type_id": item.get("listing_type_id", ""),
                    "official_store_id": item.get("official_store_id"),
                    "tags": item.get("tags", []),
                    "accepts_mercadopago": item.get("accepts_mercadopago", False),
                    "original_price": item.get("original_price"),
                    "category_id": item.get("category_id"),
                    "international_delivery_mode": item.get("international_delivery_mode"),
                    "tier": item.get("tier", ""),
                    "inventory_id": item.get("inventory_id", ""),
                    "deal_ids": item.get("deal_ids", []),
                    "sale_terms": sale_terms,
                    "seller_address": item.get("seller_address", {}),
                    "reputation_level": reputation_level,
                    "shipping_tags": shipping_tags,
                    "warranty_detailed": warranty_info,
                    "invoice_type": invoice_info,
                    "buy_box_winner": item.get("buy_box_winner", False),  # Vencedor do catálogo
                    "position": len(catalog_products) + 1,  # Posição na lista
                    "current_level": item.get("current_level", "unknown"),  # Nível de reputação do item
                    "logistic_type": item.get("logistic_type", "default")  # Tipo de logística
                })
        
        return JSONResponse(content={
            "success": True,
            "is_catalog": True,
            "catalog_product_id": product.catalog_product_id,
            "catalog_products": catalog_products,
            "total_announcers": len(catalog_products),
            "api_source": "mercadolibre"
        })
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na API do Mercado Livre: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Erro na API do Mercado Livre: {str(e)}"}
        )
    except Exception as e:
        logger.error(f"Erro ao buscar informações de catálogo: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Erro interno do servidor: {e}"}
        )

@ml_product_router.get("/api/product/{product_id}/fees")
async def get_product_fees(
    product_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """API para buscar taxas do produto"""
    try:
        from app.models.saas_models import MLProduct
        from app.services.ml_product_service import MLProductService
        
        product = db.query(MLProduct).filter(
            MLProduct.id == product_id,
            MLProduct.company_id == user["company"]["id"]
        ).first()
        
        if not product:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Produto não encontrado"}
            )
        
        service = MLProductService(db)
        
        # Buscar taxas de listagem
        fees_result = service.get_listing_prices(
            product_id=product.ml_item_id,
            price=product.price,
            category_id=product.category_id,
            listing_type_id=product.listing_type_id,
            company_id=user["company"]["id"],
            user_id=user["id"]
        )
        
        return JSONResponse(content={
            "success": True,
            "fees": fees_result
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar taxas do produto: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Erro interno do servidor: {e}"}
        )

@ml_product_router.get("/api/product/{product_id}/shipping")
async def get_product_shipping(
    product_id: int,
    zip_code: str,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """API para buscar opções de envio do produto"""
    try:
        from app.models.saas_models import MLProduct
        from app.services.ml_product_service import MLProductService
        
        product = db.query(MLProduct).filter(
            MLProduct.id == product_id,
            MLProduct.company_id == user["company"]["id"]
        ).first()
        
        if not product:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Produto não encontrado"}
            )
        
        service = MLProductService(db)
        
        # Buscar opções de envio
        shipping_result = service.get_shipping_options(
            product_id=product.ml_item_id,
            zip_code=zip_code,
            ml_account_id=product.ml_account_id
        )
        
        return JSONResponse(content={
            "success": True,
            "shipping": shipping_result
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar opções de envio: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Erro interno do servidor: {e}"}
        )

@ml_product_router.post("/api/product/{product_id}/catalog/sync")
async def sync_catalog_data(
    product_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Sincroniza dados do catálogo e salva no banco de dados"""
    try:
        from app.models.saas_models import MLProduct, CatalogParticipant
        from datetime import datetime
        
        # Buscar produto
        product = db.query(MLProduct).filter(
            MLProduct.id == product_id,
            MLProduct.company_id == user["company"]["id"]
        ).first()
        
        if not product:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Produto não encontrado"}
            )
        
        if not product.catalog_listing or not product.catalog_product_id:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Produto não é de catálogo"}
            )
        
        # Usar TokenManager para obter token válido
        from app.services.token_manager import TokenManager
        token_manager = TokenManager(db)
        access_token = token_manager.get_valid_token(user["id"])
        
        if not access_token:
            return JSONResponse(
                status_code=401,
                content={"success": False, "error": "Token de acesso não encontrado"}
            )
        
        # Buscar dados do catálogo da API
        api_url = f"https://api.mercadolibre.com/products/{product.catalog_product_id}/items"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(api_url, headers=headers, timeout=30)
        
        if response.status_code == 404:
            return JSONResponse(
                status_code=200,
                content={"success": True, "message": "Catálogo não encontrado na API", "synced": 0}
            )
        
        response.raise_for_status()
        data = response.json()
        
        if "results" not in data:
            return JSONResponse(
                status_code=200,
                content={"success": True, "message": "Nenhum participante encontrado", "synced": 0}
            )
        
        # Processar participantes
        current_participants = []
        for index, item in enumerate(data["results"]):
            # Processar informações de envio
            shipping_info = item.get("shipping", {})
            shipping_free = shipping_info.get("free_shipping", False)
            shipping_logistic_type = shipping_info.get("logistic_type", "default")
            shipping_method = shipping_info.get("mode", "standard")  # Usar 'mode' em vez de 'method'
            shipping_tags = shipping_info.get("tags", [])
            
            # Se não tem mode, usar logistic_type do shipping
            if shipping_method == "standard" and shipping_logistic_type != "default":
                shipping_method = shipping_logistic_type
            
            
            # Determinar quem paga o frete baseado nos dados reais da API
            shipping_paid_by = "Comprador"  # Padrão mais realista
            
            # Verificar se há informações específicas sobre pagamento
            if shipping_free:
                # Se é frete grátis, verificar quem está pagando
                if shipping_method in ["fulfillment", "cross_docking"]:
                    # Full e Coleta ML são pagos pelo Mercado Livre
                    shipping_paid_by = "Mercado Livre"
                elif "seller_pays" in shipping_tags or "vendedor_paga" in shipping_tags:
                    # Tags específicas indicam que o vendedor paga
                    shipping_paid_by = "Vendedor"
                else:
                    # Frete grátis sem indicação específica - geralmente vendedor
                    shipping_paid_by = "Vendedor"
            elif shipping_method in ["fulfillment", "cross_docking"]:
                # Full e Coleta ML são sempre pagos pelo Mercado Livre
                shipping_paid_by = "Mercado Livre"
            elif shipping_method in ["me2", "mercadoenvios"]:
                # Mercado Envios pode ser pago pelo comprador ou vendedor
                if "seller_pays" in shipping_tags or "vendedor_paga" in shipping_tags:
                    shipping_paid_by = "Vendedor"
                else:
                    shipping_paid_by = "Comprador"
            else:
                # Para outros métodos, usar padrão mais realista
                shipping_paid_by = "Comprador"
            
            
            
            
            # Buscar informações detalhadas do vendedor
            seller_id = item.get("seller_id")
            seller_name = "N/A"
            seller_nickname = "N/A"
            seller_country = "N/A"
            seller_city = "N/A"
            seller_state = "N/A"
            seller_registration_date = "N/A"
            seller_experience = "N/A"
            seller_power_seller = False
            seller_power_seller_status = None
            seller_reputation_level = None
            seller_transactions_total = 0
            seller_ratings_positive = 0
            seller_ratings_negative = 0
            seller_ratings_neutral = 0
            seller_mercadopago_accepted = False
            seller_mercadoenvios = "N/A"
            seller_user_type = "N/A"
            seller_tags = []
            
            if seller_id:
                try:
                    # Chamada para API de usuários
                    user_api_url = f"https://api.mercadolibre.com/users/{seller_id}"
                    user_response = requests.get(user_api_url, headers=headers, timeout=10)
                    
                    if user_response.status_code == 200:
                        user_data = user_response.json()
                        
                        # Informações básicas
                        seller_name = user_data.get("first_name", "N/A")
                        seller_nickname = user_data.get("nickname", "N/A")
                        seller_country = user_data.get("country_id", "N/A")
                        seller_registration_date = user_data.get("registration_date", "N/A")
                        seller_user_type = user_data.get("user_type", "N/A")
                        seller_tags = user_data.get("tags", [])
                        
                        # Endereço
                        address = user_data.get("address", {})
                        seller_city = address.get("city", "N/A")
                        seller_state = address.get("state", "N/A")
                        
                        # Experiência de vendedor
                        seller_experience = user_data.get("seller_experience", "N/A")
                        
                        # Reputação de vendedor
                        seller_reputation = user_data.get("seller_reputation", {})
                        seller_power_seller = seller_reputation.get("power_seller_status") is not None
                        seller_power_seller_status = seller_reputation.get("power_seller_status", None)
                        
                        transactions = seller_reputation.get("transactions", {})
                        seller_transactions_total = transactions.get("total", 0)
                        
                        ratings = transactions.get("ratings", {})
                        seller_ratings_positive = ratings.get("positive", 0)
                        seller_ratings_negative = ratings.get("negative", 0)
                        seller_ratings_neutral = ratings.get("neutral", 0)
                        
                        # Nível de reputação - extrair cor do level_id
                        level_id = seller_reputation.get("level_id", None)
                        if level_id:
                            if "_green" in level_id:
                                seller_reputation_level = "GREEN"
                            elif "_yellow" in level_id:
                                seller_reputation_level = "YELLOW"
                            elif "_red" in level_id:
                                seller_reputation_level = "RED"
                            else:
                                real_level = seller_reputation.get("real_level", None)
                                if real_level:
                                    seller_reputation_level = real_level.upper()
                        
                        # Status e configurações
                        status = user_data.get("status", {})
                        seller_mercadopago_accepted = status.get("mercadopago_tc_accepted", False)
                        seller_mercadoenvios = status.get("mercadoenvios", "N/A")
                        
                except Exception as e:
                    logger.warning(f"Erro ao buscar dados do vendedor {seller_id}: {e}")
            
            participant_data = {
                "company_id": user["company"]["id"],
                "catalog_product_id": product.catalog_product_id,
                "ml_item_id": item.get("item_id"),
                "seller_id": item.get("seller_id"),
                "title": item.get("title", ""),
                "price": item.get("price", 0),
                "currency_id": item.get("currency_id", "BRL"),
                "status": "active",
                "available_quantity": item.get("available_quantity", 0),
                "sold_quantity": 0,
                "permalink": f"https://www.mercadolivre.com.br/{item.get('item_id')}",
                "thumbnail": item.get("thumbnail", ""),
                "condition": item.get("condition", "new"),
                "listing_type_id": item.get("listing_type_id", ""),
                "official_store_id": item.get("official_store_id"),
                "accepts_mercadopago": item.get("accepts_mercadopago", False),
                "original_price": item.get("original_price"),
                "category_id": item.get("category_id"),
                "logistic_type": shipping_logistic_type,
                "buy_box_winner": item.get("buy_box_winner", False),
                # Informações detalhadas de envio
                "shipping_free": shipping_free,
                "shipping_method": shipping_method,
                "shipping_tags": shipping_tags,
                "shipping_paid_by": shipping_paid_by,
                # Posição no catálogo
                "position": index + 1,
                # Informações detalhadas do vendedor
                "seller_name": seller_name,
                "seller_nickname": seller_nickname,
                "seller_country": seller_country,
                "seller_city": seller_city,
                "seller_state": seller_state,
                "seller_registration_date": seller_registration_date,
                "seller_experience": seller_experience,
                "seller_power_seller": seller_power_seller,
                "seller_power_seller_status": seller_power_seller_status,
                "seller_reputation_level": seller_reputation_level,
                "seller_transactions_total": seller_transactions_total,
                "seller_ratings_positive": seller_ratings_positive,
                "seller_ratings_negative": seller_ratings_negative,
                "seller_ratings_neutral": seller_ratings_neutral,
                "seller_mercadopago_accepted": seller_mercadopago_accepted,
                "seller_mercadoenvios": seller_mercadoenvios,
                "seller_user_type": seller_user_type,
                "seller_tags": seller_tags,
                "last_updated": datetime.utcnow()
            }
            current_participants.append(participant_data)
        
        # Remover participantes que não estão mais no catálogo
        existing_participants = db.query(CatalogParticipant).filter(
            CatalogParticipant.catalog_product_id == product.catalog_product_id,
            CatalogParticipant.company_id == user["company"]["id"]
        ).all()
        
        current_item_ids = [p["ml_item_id"] for p in current_participants]
        for existing in existing_participants:
            if existing.ml_item_id not in current_item_ids:
                db.delete(existing)
        
        # Adicionar/atualizar participantes
        synced_count = 0
        for participant_data in current_participants:
            existing = db.query(CatalogParticipant).filter(
                CatalogParticipant.ml_item_id == participant_data["ml_item_id"]
            ).first()
            
            if existing:
                # Atualizar existente
                for key, value in participant_data.items():
                    if key != "ml_item_id":
                        setattr(existing, key, value)
                existing.last_updated = datetime.utcnow()
            else:
                # Criar novo
                new_participant = CatalogParticipant(**participant_data)
                db.add(new_participant)
            
            synced_count += 1
        
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "message": f"Catálogo sincronizado com sucesso",
            "synced": synced_count,
            "total_participants": len(current_participants)
        })
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na API do Mercado Livre: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Erro na API do Mercado Livre: {str(e)}"}
        )
    except Exception as e:
        logger.error(f"Erro ao sincronizar catálogo: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Erro interno do servidor: {e}"}
        )

@ml_product_router.get("/api/product/{product_id}/catalog/database")
async def get_catalog_from_database(
    product_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Busca dados do catálogo salvos no banco de dados"""
    try:
        from app.models.saas_models import MLProduct, CatalogParticipant
        
        # Buscar produto
        product = db.query(MLProduct).filter(
            MLProduct.id == product_id,
            MLProduct.company_id == user["company"]["id"]
        ).first()
        
        if not product:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Produto não encontrado"}
            )
        
        if not product.catalog_listing or not product.catalog_product_id:
            return JSONResponse(
                status_code=200,
                content={"success": True, "is_catalog": False, "message": "Produto não é de catálogo"}
            )
        
        # Buscar participantes do banco de dados
        participants = db.query(CatalogParticipant).filter(
            CatalogParticipant.catalog_product_id == product.catalog_product_id,
            CatalogParticipant.company_id == user["company"]["id"]
        ).order_by(CatalogParticipant.price.asc()).all()
        
        if not participants:
            return JSONResponse(
                status_code=200,
                content={"success": True, "is_catalog": True, "catalog_products": [], "total_announcers": 0, "message": "Nenhum participante encontrado no banco de dados"}
            )
        
        # Converter para formato da API
        catalog_products = []
        for participant in participants:
            catalog_products.append({
                "ml_item_id": participant.ml_item_id,
                "title": participant.title,
                "price": participant.price,
                "currency_id": participant.currency_id,
                "seller_id": participant.seller_id,
                "seller_name": participant.seller_name,
                "seller_nickname": participant.seller_nickname,
                "seller_country": participant.seller_country,
                "seller_city": participant.seller_city,
                "seller_state": participant.seller_state,
                "seller_registration_date": participant.seller_registration_date,
                "seller_experience": participant.seller_experience,
                "seller_power_seller": participant.seller_power_seller,
                "seller_power_seller_status": participant.seller_power_seller_status,
                "seller_reputation_level": participant.seller_reputation_level,
                "seller_transactions_total": participant.seller_transactions_total,
                "seller_ratings_positive": participant.seller_ratings_positive,
                "seller_ratings_negative": participant.seller_ratings_negative,
                "seller_ratings_neutral": participant.seller_ratings_neutral,
                "seller_mercadopago_accepted": participant.seller_mercadopago_accepted,
                "seller_mercadoenvios": participant.seller_mercadoenvios,
                "seller_user_type": participant.seller_user_type,
                "seller_tags": participant.seller_tags or [],
                "status": participant.status,
                "available_quantity": participant.available_quantity,
                "sold_quantity": participant.sold_quantity,
                "permalink": participant.permalink,
                "thumbnail": participant.thumbnail,
                "condition": participant.condition,
                "listing_type_id": participant.listing_type_id,
                "official_store_id": participant.official_store_id,
                "accepts_mercadopago": participant.accepts_mercadopago,
                "original_price": participant.original_price,
                "category_id": participant.category_id,
                "logistic_type": participant.logistic_type,
                "buy_box_winner": participant.buy_box_winner,
                "shipping_free": participant.shipping_free,
                "shipping_method": participant.shipping_method,
                "shipping_tags": participant.shipping_tags or [],
                "shipping_paid_by": participant.shipping_paid_by,
                "position": participant.position,
                "last_updated": participant.last_updated.isoformat() if participant.last_updated else None
            })
        
        return JSONResponse(content={
            "success": True,
            "is_catalog": True,
            "catalog_product_id": product.catalog_product_id,
            "catalog_products": catalog_products,
            "total_announcers": len(catalog_products),
            "last_sync": participants[0].last_updated.isoformat() if participants and participants[0].last_updated else None,
            "data_source": "database"
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar catálogo do banco: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Erro interno do servidor: {e}"}
        )

@ml_product_router.get("/api/product/{product_id}/catalog/filter")
async def filter_catalog_from_database(
    product_id: int,
    position: Optional[str] = Query(None),
    price: Optional[str] = Query(None),
    shipping: Optional[str] = Query(None),
    mercadolider: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Filtrar catálogo diretamente do banco de dados com parâmetros específicos"""
    try:
        # Buscar produto
        product = db.query(MLProduct).filter(
            MLProduct.id == product_id,
            MLProduct.company_id == user["company"]["id"]
        ).first()
        
        if not product:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Produto não encontrado"}
            )
        
        if not product.catalog_listing or not product.catalog_product_id:
            return JSONResponse(
                status_code=200,
                content={"success": True, "is_catalog": False, "message": "Produto não é de catálogo"}
            )
        
        # Query base
        query = db.query(CatalogParticipant).filter(
            CatalogParticipant.catalog_product_id == product.catalog_product_id,
            CatalogParticipant.company_id == user["company"]["id"]
        )
        
        # Aplicar filtros
        if position:
            if position == "1-5":
                query = query.filter(CatalogParticipant.position.between(1, 5))
            elif position == "6-10":
                query = query.filter(CatalogParticipant.position.between(6, 10))
            elif position == "11-20":
                query = query.filter(CatalogParticipant.position.between(11, 20))
            elif position == "21+":
                query = query.filter(CatalogParticipant.position > 20)
        
        if price:
            if price == "0-50":
                query = query.filter(CatalogParticipant.price <= 50)
            elif price == "50-100":
                query = query.filter(CatalogParticipant.price.between(50, 100))
            elif price == "100+":
                query = query.filter(CatalogParticipant.price > 100)
        
        if shipping:
            if shipping == "full":
                query = query.filter(CatalogParticipant.logistic_type == "fulfillment")
            elif shipping == "correios":
                query = query.filter(CatalogParticipant.logistic_type.in_(["xd_drop_off", "drop_off"]))
            elif shipping == "coleta":
                query = query.filter(CatalogParticipant.logistic_type == "cross_docking")
            elif shipping == "mercado_envios":
                query = query.filter(CatalogParticipant.logistic_type == "me2")
            elif shipping == "frete_gratis":
                query = query.filter(CatalogParticipant.shipping_free == True)
        
        if mercadolider:
            if mercadolider == "platinum":
                query = query.filter(CatalogParticipant.seller_power_seller_status == "platinum")
            elif mercadolider == "gold":
                query = query.filter(CatalogParticipant.seller_power_seller_status == "gold")
            elif mercadolider == "silver":
                query = query.filter(CatalogParticipant.seller_power_seller_status == "silver")
            elif mercadolider == "sem_medalha":
                query = query.filter(
                    (CatalogParticipant.seller_power_seller_status == None) |
                    (CatalogParticipant.seller_power_seller_status == "N/A") |
                    (CatalogParticipant.seller_power_seller_status.notin_(["platinum", "gold", "silver"]))
                )
        
        # Executar query
        participants = query.order_by(CatalogParticipant.position.asc()).all()
        
        if not participants:
            return JSONResponse(
                status_code=200,
                content={"success": True, "is_catalog": True, "catalog_products": [], "total_announcers": 0, "message": "Nenhum resultado encontrado com os filtros aplicados"}
            )
        
        # Converter para formato da API (usar a mesma estrutura do endpoint sem filtros)
        catalog_products = []
        for participant in participants:
            catalog_products.append({
                "ml_item_id": participant.ml_item_id,
                "title": participant.title,
                "price": participant.price,
                "currency_id": participant.currency_id,
                "seller_id": participant.seller_id,
                "seller_name": participant.seller_name,
                "seller_nickname": participant.seller_nickname,
                "seller_country": participant.seller_country,
                "seller_city": participant.seller_city,
                "seller_state": participant.seller_state,
                "seller_registration_date": participant.seller_registration_date,
                "seller_experience": participant.seller_experience,
                "seller_power_seller": participant.seller_power_seller,
                "seller_power_seller_status": participant.seller_power_seller_status,
                "seller_reputation_level": participant.seller_reputation_level,
                "seller_transactions_total": participant.seller_transactions_total,
                "seller_ratings_positive": participant.seller_ratings_positive,
                "seller_ratings_negative": participant.seller_ratings_negative,
                "seller_ratings_neutral": participant.seller_ratings_neutral,
                "seller_mercadopago_accepted": participant.seller_mercadopago_accepted,
                "seller_mercadoenvios": participant.seller_mercadoenvios,
                "seller_user_type": participant.seller_user_type,
                "seller_tags": participant.seller_tags or [],
                "status": participant.status,
                "available_quantity": participant.available_quantity,
                "sold_quantity": participant.sold_quantity,
                "permalink": participant.permalink,
                "thumbnail": participant.thumbnail,
                "condition": participant.condition,
                "listing_type_id": participant.listing_type_id,
                "official_store_id": participant.official_store_id,
                "accepts_mercadopago": participant.accepts_mercadopago,
                "original_price": participant.original_price,
                "category_id": participant.category_id,
                "logistic_type": participant.logistic_type,
                "buy_box_winner": participant.buy_box_winner,
                "shipping_free": participant.shipping_free,
                "shipping_method": participant.shipping_method,
                "shipping_tags": participant.shipping_tags or [],
                "shipping_paid_by": participant.shipping_paid_by,
                "position": participant.position,
                "last_updated": participant.last_updated.isoformat() if participant.last_updated else None
            })
        
        return JSONResponse(content={
            "success": True,
            "is_catalog": True,
            "catalog_product_id": product.catalog_product_id,
            "catalog_products": catalog_products,
            "total_announcers": len(catalog_products),
            "filters_applied": {
                "position": position,
                "price": price,
                "shipping": shipping,
                "mercadolider": mercadolider
            },
            "data_source": "database_filtered"
        })
        
    except Exception as e:
        logger.error(f"Erro ao filtrar catálogo: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Erro interno: {str(e)}"}
        )

@ml_product_router.get("/api/product/{product_id}/ai-analysis/history")
async def get_ai_analysis_history(
    product_id: int,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Busca histórico de análises de IA de um produto"""
    try:
        # Verificar autenticação
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        from app.models.saas_models import AIProductAnalysis
        from sqlalchemy import desc
        
        # Buscar análises deste produto
        analyses = db.query(AIProductAnalysis).filter(
            AIProductAnalysis.ml_product_id == product_id,
            AIProductAnalysis.company_id == company_id
        ).order_by(desc(AIProductAnalysis.created_at)).all()
        
        analyses_list = []
        for analysis in analyses:
            analyses_list.append({
                "id": analysis.id,
                "ml_product_id": analysis.ml_product_id,
                "analysis_content": analysis.analysis_content,
                "model_used": analysis.model_used,
                "prompt_tokens": analysis.prompt_tokens,
                "completion_tokens": analysis.completion_tokens,
                "total_tokens": analysis.total_tokens,
                "created_at": analysis.created_at.isoformat() if analysis.created_at else None
            })
        
        return JSONResponse(content={
            "success": True,
            "analyses": analyses_list,
            "total": len(analyses_list)
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar histórico de análises: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Erro interno: {str(e)}"}
        )

@ml_product_router.get("/api/product/{product_id}/advertising-metrics")
async def get_product_advertising_metrics(
    product_id: int,
    days: int = 30,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Busca métricas de Product Ads (publicidade) para um produto específico"""
    try:
        # Verificar autenticação
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        from app.models.saas_models import MLProduct
        
        # Buscar produto
        product = db.query(MLProduct).filter(
            MLProduct.id == product_id,
            MLProduct.company_id == company_id
        ).first()
        
        if not product:
            return JSONResponse(content={"error": "Produto não encontrado"}, status_code=404)
        
        # Buscar métricas de Product Ads
        from app.services.ml_product_ads_service import MLProductAdsService
        ads_service = MLProductAdsService(db)
        
        metrics = ads_service.get_product_advertising_metrics(
            ml_item_id=product.ml_item_id,
            ml_account_id=product.ml_account_id,
            days=days
        )
        
        return JSONResponse(content={
            "success": True,
            "metrics": metrics
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar métricas de publicidade: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Erro interno: {str(e)}"}
        )

@ml_product_router.post("/api/product/{product_id}/ai-analysis")
async def ai_analyze_product(
    product_id: int,
    request_body: dict = {},
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Analisa produto usando ChatGPT"""
    try:
        # Verificar autenticação
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        company_id = user_data["company"]["id"]
        
        logger.info(f"Iniciando análise IA para produto {product_id}")
        
        # Pegar dados enviados do frontend
        catalog_data = request_body.get("catalog_data", None)
        pricing_analysis = request_body.get("pricing_analysis", None)
        
        # Chamar serviço de IA
        from app.services.ai_analysis_service import AIAnalysisService
        ai_service = AIAnalysisService(db)
        analysis_result = ai_service.analyze_product(product_id, company_id, catalog_data, pricing_analysis)
        
        return JSONResponse(content=analysis_result)
        
    except Exception as e:
        logger.error(f"Erro no endpoint de análise IA: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Erro interno: {str(e)}"}
        )