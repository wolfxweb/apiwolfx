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
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Erro na API do ML: {response.status_code} - {response.text[:200]}")
                
                # Se 403, tentar buscar categorias principais via /categories/all
                if response.status_code == 403:
                    try:
                        all_url = f"https://api.mercadolibre.com/sites/{site_id}/categories/all"
                        logger.info(f"Tentando buscar via /categories/all: {all_url}")
                        all_response = requests.get(all_url, headers=headers, timeout=10)
                        if all_response.status_code == 200:
                            all_categories = all_response.json()
                            # Filtrar apenas categorias principais (sem pai)
                            main_categories = [cat for cat in all_categories if not cat.get('parent_id')]
                            logger.info(f"Categorias principais encontradas: {len(main_categories)}")
                            return JSONResponse(content={
                                "success": True,
                                "site_id": site_id,
                                "categories": main_categories
                            })
                    except Exception as e2:
                        logger.error(f"Erro ao buscar via /categories/all: {e2}")
                
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
            
            return JSONResponse(content={
                "success": True,
                "site_id": site_id,
                "categories": categories if isinstance(categories, list) else []
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

