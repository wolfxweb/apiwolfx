"""
Rotas para análises de mais vendidos do Mercado Livre
"""
from fastapi import APIRouter, Request, Cookie, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging
import requests

from app.config.database import get_db
from app.controllers.auth_controller import AuthController
from app.controllers.highlights_controller import HighlightsController
from app.views.template_renderer import render_template
from app.models.saas_models import MLAccount, MLAccountStatus, User

logger = logging.getLogger(__name__)

highlights_router = APIRouter()

@highlights_router.get("/ml/highlights", response_class=HTMLResponse)
async def highlights_page(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Página principal de mais vendidos"""
    try:
        if not session_token:
            return HTMLResponse(content="<script>window.location.href='/auth/login';</script>", status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return HTMLResponse(content="<script>window.location.href='/auth/login';</script>", status_code=401)
        
        user_data = result["user"]
        
        return render_template("ml_highlights.html", request=request, user=user_data)
        
    except Exception as e:
        logger.error(f"Erro ao carregar página de mais vendidos: {e}")
        return HTMLResponse(content=f"<h1>Erro: {str(e)}</h1>", status_code=500)

@highlights_router.get("/api/ml/highlights/category/{category_id}")
async def get_category_highlights_api(
    category_id: str,
    attribute: Optional[str] = Query(None, description="Atributo para filtrar (ex: BRAND)"),
    attribute_value: Optional[str] = Query(None, description="Valor do atributo (ex: ID da marca)"),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar mais vendidos de uma categoria"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        user_id = user_data["id"]
        
        controller = HighlightsController(db)
        highlights = controller.get_category_highlights(
            category_id=category_id,
            user_id=user_id,
            attribute=attribute,
            attribute_value=attribute_value
        )
        
        return JSONResponse(content=highlights)
        
    except Exception as e:
        logger.error(f"Erro ao buscar mais vendidos: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@highlights_router.get("/api/ml/highlights/product/{product_id}")
async def get_product_position_api(
    product_id: str,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar posicionamento de um produto"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        user_id = user_data["id"]
        
        controller = HighlightsController(db)
        position = controller.get_product_position(product_id=product_id, user_id=user_id)
        
        return JSONResponse(content=position)
        
    except Exception as e:
        logger.error(f"Erro ao buscar posicionamento do produto: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@highlights_router.get("/api/ml/highlights/item/{item_id}")
async def get_item_position_api(
    item_id: str,
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar posicionamento de um item"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        user_id = user_data["id"]
        
        controller = HighlightsController(db)
        position = controller.get_item_position(item_id=item_id, user_id=user_id)
        
        return JSONResponse(content=position)
        
    except Exception as e:
        logger.error(f"Erro ao buscar posicionamento do item: {e}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

@highlights_router.get("/api/ml/highlights/categories")
async def get_categories_api(
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """API para buscar categorias do Mercado Livre"""
    try:
        if not session_token:
            return JSONResponse(content={"error": "Não autenticado"}, status_code=401)
        
        result = AuthController().get_user_by_session(session_token, db)
        if result.get("error"):
            return JSONResponse(content={"error": "Sessão inválida"}, status_code=401)
        
        user_data = result["user"]
        user_id = user_data["id"]
        
        logger.info(f"Buscando categorias para user_id: {user_id}")
        
        # Buscar site_id da empresa do usuário
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"Usuário {user_id} não encontrado")
                return JSONResponse(content={"error": "Usuário não encontrado"}, status_code=404)
            
            if not user.company_id:
                logger.error(f"Usuário {user_id} não possui company_id")
                return JSONResponse(content={"error": "Usuário não possui empresa associada"}, status_code=400)
            
            logger.info(f"Company ID do usuário: {user.company_id}")
            
            account = db.query(MLAccount).filter(
                MLAccount.company_id == user.company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).first()
            
            if account:
                site_id = account.site_id or "MLB"
                logger.info(f"Site ID encontrado: {site_id}")
            else:
                site_id = "MLB"
                logger.warning(f"Nenhuma conta ML ativa encontrada para company_id {user.company_id}, usando MLB como padrão")
            
            # Buscar token do usuário para autenticar requisição
            from app.services.token_manager import TokenManager
            token_manager = TokenManager(db)
            access_token = token_manager.get_valid_token(user_id)
            
            if not access_token:
                logger.warning(f"Token não encontrado para user_id {user_id}, tentando sem autenticação")
            
        except Exception as db_error:
            logger.error(f"Erro ao buscar dados do usuário/conta: {db_error}", exc_info=True)
            return JSONResponse(content={
                "success": False,
                "error": f"Erro ao buscar dados: {str(db_error)}"
            }, status_code=500)
        
        # Buscar categorias do site
        try:
            url = f"https://api.mercadolibre.com/sites/{site_id}/categories"
            logger.info(f"Buscando categorias de {url}")
            
            # Headers com token se disponível
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Accept-Language": "pt-BR,pt;q=0.9"
            }
            
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
            
            # Primeiro tentar buscar todas as categorias via /categories/all
            all_url = f"https://api.mercadolibre.com/sites/{site_id}/categories/all"
            logger.info(f"Buscando todas as categorias via {all_url}")
            all_response = requests.get(all_url, headers=headers, timeout=15)
            
            if all_response.status_code == 200:
                all_categories_raw = all_response.json()
                logger.info(f"Todas as categorias encontradas (tipo: {type(all_categories_raw)})")
                
                # Verificar formato da resposta
                if isinstance(all_categories_raw, list):
                    # Filtrar apenas objetos (dicionários), ignorar strings se houver
                    all_categories = [cat for cat in all_categories_raw if isinstance(cat, dict)]
                    logger.info(f"Categorias válidas (dicionários): {len(all_categories)}")
                elif isinstance(all_categories_raw, dict):
                    # A API /categories/all retorna um dict onde cada chave é o ID da categoria
                    # Converter para lista, garantindo que cada item tenha o campo 'id'
                    all_categories = []
                    for cat_id, cat_data in all_categories_raw.items():
                        if isinstance(cat_data, dict):
                            # Garantir que o ID está no dicionário
                            cat_data['id'] = cat_id
                            all_categories.append(cat_data)
                    logger.info(f"Categorias convertidas do dicionário: {len(all_categories)}")
                else:
                    logger.warning(f"Formato inesperado de categorias: {type(all_categories_raw)}")
                    all_categories = []
                
                if not all_categories:
                    logger.warning("Nenhuma categoria válida encontrada")
                    return JSONResponse(content={
                        "success": False,
                        "error": "Nenhuma categoria válida encontrada"
                    }, status_code=500)
                
                # Extrair parent_id do path_from_root se não estiver presente
                for cat in all_categories:
                    if 'parent_id' not in cat or cat.get('parent_id') is None:
                        path_from_root = cat.get('path_from_root', [])
                        if isinstance(path_from_root, list) and len(path_from_root) > 1:
                            # O parent_id é o penúltimo item no path
                            parent_info = path_from_root[-2]
                            if isinstance(parent_info, dict):
                                cat['parent_id'] = parent_info.get('id')
                            elif isinstance(parent_info, str):
                                cat['parent_id'] = parent_info
                
                # Organizar em estrutura hierárquica
                categories_dict = {cat.get('id'): cat for cat in all_categories if cat.get('id')}
                categories_tree = []
                
                # Primeiro, adicionar todas as categorias principais (sem parent_id)
                for cat in all_categories:
                    if isinstance(cat, dict) and (not cat.get('parent_id') or cat.get('parent_id') == ''):
                        categories_tree.append(cat)
                
                # Ordenar por nome
                categories_tree.sort(key=lambda x: x.get('name', ''))
                
                return JSONResponse(content={
                    "success": True,
                    "site_id": site_id,
                    "categories": all_categories,  # Todas as categorias (incluindo subcategorias)
                    "categories_tree": categories_tree,  # Apenas principais para estrutura
                    "categories_dict": categories_dict  # Dicionário para buscar por ID
                })
            
            # Fallback: tentar /categories (apenas principais)
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Erro na API do ML: {response.status_code} - {response.text[:200]}")
                return JSONResponse(content={
                    "success": False,
                    "error": f"Erro ao buscar categorias na API do Mercado Livre: {response.status_code}"
                }, status_code=500)
            
            categories = response.json()
            
            # Verificar se é lista ou dict
            if isinstance(categories, dict):
                # Se for dict, pode ser que tenha uma chave 'categories'
                if 'categories' in categories:
                    categories = categories['categories']
                elif 'results' in categories:
                    categories = categories['results']
                else:
                    # Se não tem chave esperada, retornar vazio
                    logger.warning(f"Formato inesperado na resposta: {categories.keys()}")
                    categories = []
            
            logger.info(f"Categorias encontradas: {len(categories) if isinstance(categories, list) else 'N/A'}")
            
            # Se veio de /categories, organizar também
            if isinstance(categories, list):
                categories_dict = {cat.get('id'): cat for cat in categories}
                return JSONResponse(content={
                    "success": True,
                    "site_id": site_id,
                    "categories": categories,
                    "categories_tree": categories,  # Neste caso, todas são principais
                    "categories_dict": categories_dict
                })
            
            return JSONResponse(content={
                "success": True,
                "site_id": site_id,
                "categories": categories if isinstance(categories, list) else [],
                "categories_tree": categories if isinstance(categories, list) else [],
                "categories_dict": {}
            })
        except requests.RequestException as req_error:
            logger.error(f"Erro na requisição HTTP: {req_error}", exc_info=True)
            return JSONResponse(content={
                "success": False,
                "error": f"Erro ao conectar com API do Mercado Livre: {str(req_error)}"
            }, status_code=500)
        
    except Exception as e:
        logger.error(f"Erro ao buscar categorias: {e}", exc_info=True)
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Traceback completo: {error_detail}")
        return JSONResponse(content={
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }, status_code=500)

