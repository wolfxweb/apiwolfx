"""
Controller para gerenciar produtos do Mercado Livre
"""
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from fastapi import Request
from fastapi.responses import HTMLResponse

from app.models.saas_models import (
    MLAccount,
    MLProduct,
    Token,
    User,
    MLAccountStatus,
    UserMLAccount,
    MLProductStatus,
)
from app.services.ml_product_service import MLProductService
from fastapi.templating import Jinja2Templates
from pathlib import Path
import requests
import mimetypes
import time

# Configurar templates com Jinja2 nativo
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "views" / "templates")

logger = logging.getLogger(__name__)

class MLProductController:
    """Controller para produtos do Mercado Livre"""
    
    def __init__(self, db: Session):
        self.db = db
        self.product_service = MLProductService(db)

    def _get_valid_token_for_account(self, company_id: int, ml_account_id: int):
        from app.models.saas_models import Token, MLAccount
        from datetime import datetime

        query = (
            self.db.query(Token)
            .join(MLAccount)
            .filter(
                MLAccount.company_id == company_id,
                MLAccount.id == ml_account_id,
                Token.is_active == True,
                Token.expires_at > datetime.utcnow(),
            )
        )

        token = query.order_by(Token.expires_at.desc()).first()
        if not token:
            logger.warning(
                "⚠️ Nenhum token válido encontrado para ml_account_id=%s (company=%s)",
                ml_account_id,
                company_id,
            )
        return token

    def _hydrate_product_from_ml_api(self, company_id: int, product: Dict[str, Any]) -> Dict[str, Any]:
        ml_item_id = product.get("ml_item_id")
        ml_account_id = product.get("ml_account_id")

        if not ml_item_id or not ml_account_id:
            return product

        token = self._get_valid_token_for_account(company_id, ml_account_id)
        if not token:
            return product

        headers = {"Authorization": f"Bearer {token.access_token}"}

        try:
            item_url = f"https://api.mercadolibre.com/items/{ml_item_id}"
            item_response = requests.get(item_url, headers=headers, timeout=30)
            if item_response.status_code == 200:
                item_data = item_response.json()

                product["title"] = item_data.get("title", product.get("title"))
                product["price"] = item_data.get("price", product.get("price"))
                product["available_quantity"] = item_data.get("available_quantity", product.get("available_quantity"))
                product["listing_type_id"] = item_data.get("listing_type_id", product.get("listing_type_id"))
                product["condition"] = item_data.get("condition", product.get("condition"))
                product["category_id"] = item_data.get("category_id", product.get("category_id"))
                product["catalog_product_id"] = item_data.get("catalog_product_id", product.get("catalog_product_id"))
                product["catalog_listing"] = item_data.get("catalog_listing", product.get("catalog_listing"))
                product["permalink"] = item_data.get("permalink", product.get("permalink"))
                product["seller_custom_field"] = item_data.get("seller_custom_field", product.get("seller_custom_field"))
                product["seller_sku"] = item_data.get("seller_sku", product.get("seller_sku"))
                product["shipping"] = item_data.get("shipping", product.get("shipping") or {})
                product["free_shipping"] = product["shipping"].get("free_shipping", product.get("free_shipping"))
                product["pictures"] = item_data.get("pictures", product.get("pictures") or [])
                product["attributes"] = item_data.get("attributes", product.get("attributes") or [])
                product["sale_terms"] = item_data.get("sale_terms", product.get("sale_terms") or [])
                product["status"] = item_data.get("status", product.get("status"))
                product["variations"] = item_data.get("variations", product.get("variations") or [])
                product["warranty"] = item_data.get("warranty", product.get("warranty"))

                description_url = f"https://api.mercadolibre.com/items/{ml_item_id}/description"
                desc_response = requests.get(description_url, headers=headers, timeout=30)
                if desc_response.status_code == 200:
                    desc_data = desc_response.json()
                    product["description"] = desc_data.get("plain_text") or desc_data.get("text") or product.get("description")

                category_id = product.get("category_id")
                if category_id:
                    try:
                        cat_response = requests.get(
                            f"https://api.mercadolibre.com/categories/{category_id}",
                            timeout=15,
                        )
                        if cat_response.status_code == 200:
                            cat_data = cat_response.json()
                            product["category_name"] = cat_data.get("name", product.get("category_name"))
                    except Exception as cat_exc:
                        logger.warning("⚠️ Erro ao buscar categoria %s: %s", category_id, cat_exc)

            else:
                logger.warning(
                    "⚠️ Não foi possível buscar dados do item %s no ML: %s - %s",
                    ml_item_id,
                    item_response.status_code,
                    item_response.text,
                )
        except Exception as exc:
            logger.warning("⚠️ Erro ao sincronizar dados do item %s com a API ML: %s", ml_item_id, exc)

        return product

    def _fetch_category_attributes(
        self,
        company_id: int,
        category_id: str,
        ml_account_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        if not category_id:
            return None

        query = (
            self.db.query(Token)
            .join(MLAccount)
            .filter(
                MLAccount.company_id == company_id,
                Token.is_active == True,
                Token.expires_at > datetime.utcnow(),
            )
        )
        if ml_account_id:
            query = query.filter(MLAccount.id == ml_account_id)

        token = query.order_by(Token.expires_at.desc()).first()

        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token.access_token}"

        try:
            response = requests.get(
                f"https://api.mercadolibre.com/categories/{category_id}/attributes",
                headers=headers,
                timeout=15,
            )
            if response.status_code != 200:
                logger.warning(
                    "⚠️ Não foi possível buscar atributos da categoria %s: %s",
                    category_id,
                    response.status_code,
                )
                return None

            attributes_data = response.json()
            main_attributes: List[Dict[str, Any]] = []
            other_attributes: List[Dict[str, Any]] = []

            def tag_bool(tags_obj, key: str) -> bool:
                if isinstance(tags_obj, dict):
                    return bool(tags_obj.get(key))
                if isinstance(tags_obj, list):
                    return key in tags_obj
                return False

            for attr in attributes_data:
                tags = attr.get("tags", {})

                if tag_bool(tags, "hidden") or tag_bool(tags, "read_only"):
                    continue

                is_required = (
                    bool(attr.get("required"))
                    or tag_bool(tags, "required")
                    or tag_bool(tags, "mandatory")
                    or tag_bool(tags, "catalog_required")
                )

                attr["__is_required"] = is_required

                if tag_bool(tags, "fixed"):
                    continue

                if is_required or attr.get("attribute_group_id") == "MAIN":
                    main_attributes.append(attr)
                else:
                    other_attributes.append(attr)

            return {
                "main_attributes": main_attributes,
                "other_attributes": other_attributes,
            }
        except Exception as exc:
            logger.warning("⚠️ Erro ao carregar atributos da categoria %s: %s", category_id, exc)
            return None

    @staticmethod
    def _extract_warranty_context(sale_terms: Optional[List[Dict[str, Any]]]) -> Dict[str, Optional[str]]:
        context = {
            "type": "none",
            "duration_value": "",
            "duration_unit": "",
        }

        if not sale_terms:
            return context

        warranty_type_map = {
            "6150835": "none",
            "2230280": "seller",
            "2230281": "factory",
        }

        for term in sale_terms:
            term_id = term.get("id")
            value_id = term.get("value_id")
            value_name = term.get("value_name", "")

            if term_id == "WARRANTY_TYPE":
                if value_id in warranty_type_map:
                    context["type"] = warranty_type_map[value_id]
                elif value_name:
                    lowered = value_name.lower()
                    if "vendedor" in lowered:
                        context["type"] = "seller"
                    elif "fábrica" in lowered or "fabrica" in lowered:
                        context["type"] = "factory"
                    elif "sem garantia" in lowered:
                        context["type"] = "none"

            elif term_id == "WARRANTY_TIME" and value_name:
                match = re.search(r"(\d+)", value_name)
                if match:
                    context["duration_value"] = match.group(1)

                lowered = value_name.lower()
                if "dia" in lowered:
                    context["duration_unit"] = "dias"
                elif "mes" in lowered:
                    context["duration_unit"] = "meses"
                elif "ano" in lowered:
                    context["duration_unit"] = "anos"

        return context

    @staticmethod
    def _build_warranty_terms(
        warranty_type: Optional[str],
        time_value: Optional[str],
        time_unit: Optional[str],
    ) -> Dict[str, Any]:
        warranty_type_normalized = (warranty_type or "none").lower()
        sale_terms: List[Dict[str, Any]] = []
        warranty_display = ""

        warranty_map = {
            "none": {"value_id": "6150835", "label": "Sem garantia"},
            "seller": {"value_id": "2230280", "label": "Garantia do vendedor"},
            "factory": {"value_id": "2230281", "label": "Garantia de fábrica"},
        }

        if warranty_type_normalized in warranty_map:
            meta = warranty_map[warranty_type_normalized]
            sale_terms.append(
                {
                    "id": "WARRANTY_TYPE",
                    "value_id": meta["value_id"],
                    "value_name": meta["label"],
                }
            )
            warranty_display = meta["label"]

            if warranty_type_normalized in {"seller", "factory"}:
                if time_value:
                    try:
                        time_int = int(float(str(time_value)))
                        if time_int < 0:
                            raise ValueError("Negative warranty duration")
                    except (TypeError, ValueError) as exc:
                        logger.warning("⚠️ Tempo de garantia inválido: %s (%s)", time_value, exc)
                        time_int = None

                    if time_int:
                        normalized_unit = (time_unit or "").lower()
                        unit_labels = {
                            "dias": ("dia", "dias"),
                            "dia": ("dia", "dias"),
                            "mes": ("mês", "meses"),
                            "meses": ("mês", "meses"),
                            "ano": ("ano", "anos"),
                            "anos": ("ano", "anos"),
                        }

                        if normalized_unit in unit_labels:
                            singular, plural = unit_labels[normalized_unit]
                            label = singular if time_int == 1 else plural
                            time_display = f"{time_int} {label}"
                            sale_terms.append(
                                {
                                    "id": "WARRANTY_TIME",
                                    "value_name": time_display,
                                }
                            )
                            warranty_display = f"{warranty_display} - {time_display}"
                        else:
                            logger.warning(
                                "⚠️ Unidade de tempo de garantia não reconhecida: %s",
                                time_unit,
                            )

        return {
            "sale_terms": sale_terms,
            "warranty_display": warranty_display,
        }
    
    def get_products_page(self, company_id: int, user_data: dict = None, ml_account_id: Optional[int] = None, 
                         status: Optional[str] = None, page: int = 1, limit: int = 20, request=None) -> str:
        """Renderiza página de produtos ML"""
        try:
            user_id = user_data.get('id') if user_data else None
            
            # Buscar contas ML que o usuário tem permissão de acessar
            if user_id:
                ml_accounts = self.db.query(MLAccount).join(UserMLAccount).filter(
                    MLAccount.company_id == company_id,
                    MLAccount.status == MLAccountStatus.ACTIVE,
                    UserMLAccount.user_id == user_id,
                    UserMLAccount.can_read == True
                ).all()
            else:
                # Fallback para admin - buscar todas as contas da empresa
                ml_accounts = self.db.query(MLAccount).filter(
                    MLAccount.company_id == company_id,
                    MLAccount.status == MLAccountStatus.ACTIVE
                ).all()
            
            if not ml_accounts:
                return templates.TemplateResponse('ml_products.html', {
                    "request": request,
                    "user": user_data,
                    "ml_accounts": [],
                    "products": [],
                    "total_products": 0,
                    "current_account": None,
                    "current_status": status,
                    "page": page,
                    "limit": limit,
                    "error": 'Nenhuma conta ML ativa encontrada'
                })
            
            # Se não especificou conta, usar a primeira
            if not ml_account_id:
                ml_account_id = ml_accounts[0].id
            
            # Buscar produtos
            offset = (page - 1) * limit
            products_data = self.product_service.get_products_by_account(
                ml_account_id, company_id, status, limit, offset
            )
            
            # Buscar conta atual
            current_account = next((acc for acc in ml_accounts if acc.id == ml_account_id), None)
            
            return templates.TemplateResponse('ml_products.html', {
                "request": request,
                "user": user_data,
                "ml_accounts": [
                    {
                        'id': acc.id,
                        'nickname': acc.nickname,
                        'email': acc.email,
                        'country_id': acc.country_id
                    }
                    for acc in ml_accounts
                ],
                "products": products_data['products'],
                "total_products": products_data['total'],
                "current_account": {
                    'id': current_account.id,
                    'nickname': current_account.nickname,
                    'email': current_account.email
                } if current_account else None,
                "current_status": status,
                "page": page,
                "limit": limit,
                "has_next": (offset + limit) < products_data['total'],
                "has_prev": page > 1,
                "next_page": page + 1 if (offset + limit) < products_data['total'] else None,
                "prev_page": page - 1 if page > 1 else None
            })
            
        except Exception as e:
            logger.error(f"Erro ao renderizar página de produtos: {e}")
            return templates.TemplateResponse('ml_products.html', {
                "request": request,
                "user": user_data,
                "ml_accounts": [],
                "products": [],
                "total_products": 0,
                "error": f'Erro ao carregar produtos: {str(e)}'
            })
    
    def sync_products(self, company_id: int, ml_account_id: int, user_id: int) -> Dict:
        """Inicia sincronização de produtos"""
        try:
            # Verificar se conta ML pertence à empresa
            ml_account = self.db.query(MLAccount).filter(
                MLAccount.id == ml_account_id,
                MLAccount.company_id == company_id
            ).first()
            
            if not ml_account:
                return {
                    'success': False,
                    'error': 'Conta ML não encontrada ou não pertence à empresa'
                }
            
            # Verificar se a conta ML pertence à empresa do usuário
            ml_account = self.db.query(MLAccount).filter(
                MLAccount.id == ml_account_id,
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).first()
            
            if not ml_account:
                return {
                    'success': False,
                    'error': 'Conta ML não encontrada ou não pertence à sua empresa'
                }
            
            # Iniciar sincronização
            result = self.product_service.sync_products_incremental(ml_account_id, company_id)
            
            return {
                'success': True,
                'message': 'Sincronização iniciada com sucesso',
                'data': result
            }
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar produtos: {e}")
            return {
                'success': False,
                'error': f'Erro na sincronização: {str(e)}'
            }
    
    def import_products(self, company_id: int, ml_account_id: int, user_id: int, 
                       import_type: str, product_id: str = None, 
                       product_statuses: list = None, limit: int = 100) -> Dict:
        """Importa produtos do Mercado Livre (individual ou em massa)"""
        try:
            # Verificar se conta ML pertence à empresa
            ml_account = self.db.query(MLAccount).filter(
                MLAccount.id == ml_account_id,
                MLAccount.company_id == company_id
            ).first()
            
            if not ml_account:
                return {
                    'success': False,
                    'error': 'Conta ML não encontrada ou não pertence à empresa'
                }
            
            # Verificar se a conta ML pertence à empresa do usuário
            ml_account = self.db.query(MLAccount).filter(
                MLAccount.id == ml_account_id,
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).first()
            
            if not ml_account:
                return {
                    'success': False,
                    'error': 'Conta ML não encontrada ou não pertence à sua empresa'
                }
            
            if import_type == 'single':
                # Importação de produto individual
                if not product_id:
                    return {
                        'success': False,
                        'error': 'ID do produto é obrigatório para importação individual'
                    }
                
                result = self.product_service.import_single_product(ml_account_id, company_id, product_id)
                
                return {
                    'success': result['success'],
                    'message': result.get('message', 'Produto importado com sucesso'),
                    'data': result
                }
            
            elif import_type == 'bulk':
                # Importação em massa
                if not product_statuses:
                    return {
                        'success': False,
                        'error': 'Status dos produtos é obrigatório para importação em massa'
                    }
                
                result = self.product_service.import_bulk_products(
                    ml_account_id, company_id, product_statuses, limit
                )
                
                return {
                    'success': result['success'],
                    'message': result.get('message', 'Importação em massa realizada com sucesso'),
                    'data': result
                }
            
            else:
                return {
                    'success': False,
                    'error': 'Tipo de importação inválido'
                }
            
        except Exception as e:
            logger.error(f"Erro ao importar produtos: {e}")
            return {
                'success': False,
                'error': f'Erro na importação: {str(e)}'
            }
    
    def get_product_details(self, company_id: int, product_id: int) -> Dict:
        """Busca detalhes de um produto"""
        try:
            product = self.db.query(MLProduct).filter(
                MLProduct.id == product_id,
                MLProduct.company_id == company_id
            ).first()
            
            if not product:
                return {
                    'success': False,
                    'error': 'Produto não encontrado'
                }
            
            return {
                'success': True,
                'product': {
                    'id': product.id,
                    'ml_item_id': product.ml_item_id,
                    'title': product.title,
                    'subtitle': product.subtitle,
                    'description': product.description,  # Campo de descrição adicionado
                    'price': product.price,
                    'base_price': product.base_price,
                    'original_price': product.original_price,
                    'currency_id': product.currency_id,
                    'available_quantity': product.available_quantity,
                    'sold_quantity': product.sold_quantity,
                    'initial_quantity': product.initial_quantity,
                    'category_id': product.category_id,
                    'condition': product.condition,
                    'listing_type_id': product.listing_type_id,
                    'buying_mode': product.buying_mode,
                    'permalink': product.permalink,
                    'thumbnail': product.thumbnail,
                    'secure_thumbnail': product.secure_thumbnail,
                    'pictures': product.pictures or [],
                    'status': product.status.value if product.status else None,
                    'sub_status': product.sub_status or [],
                    'start_time': product.start_time.isoformat() if product.start_time else None,
                    'stop_time': product.stop_time.isoformat() if product.stop_time else None,
                    'end_time': product.end_time.isoformat() if product.end_time else None,
                    'seller_id': product.seller_id,
                    'seller_custom_field': product.seller_custom_field,
                    'seller_sku': product.seller_sku,
                    'ml_account_id': product.ml_account_id,
                    'catalog_product_id': product.catalog_product_id,
                    'catalog_listing': product.catalog_listing,
                    'attributes': product.attributes or [],
                    'variations': product.variations or [],
                    'tags': product.tags or [],
                    'shipping': product.shipping or {},
                    'free_shipping': product.free_shipping,
                    'differential_pricing': product.differential_pricing,
                    'deal_ids': product.deal_ids or [],
                    'user_product_id': product.user_product_id,
                    'family_id': product.family_id,
                    'family_name': product.family_name,
                    # Campos críticos adicionais
                    'sale_terms': product.sale_terms or [],
                    'warranty': product.warranty,
                    'video_id': product.video_id,
                    'health': product.health,
                    'domain_id': product.domain_id,
                    # Timestamps
                    'last_sync': product.last_sync.isoformat() if product.last_sync else None,
                    'last_ml_update': product.last_ml_update.isoformat() if product.last_ml_update else None,
                    'created_at': product.created_at.isoformat() if product.created_at else None,
                    'updated_at': product.updated_at.isoformat() if product.updated_at else None
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes do produto: {e}")
            return {
                'success': False,
                'error': f'Erro ao buscar produto: {str(e)}'
            }
    
    def get_sync_history(self, company_id: int, ml_account_id: int, user_id: int) -> Dict:
        """Busca histórico de sincronizações"""
        try:
            # Verificar se conta ML pertence à empresa
            ml_account = self.db.query(MLAccount).filter(
                MLAccount.id == ml_account_id,
                MLAccount.company_id == company_id
            ).first()
            
            if not ml_account:
                return {
                    'success': False,
                    'error': 'Conta ML não encontrada'
                }
            
            # Verificar permissões do usuário para esta conta ML
            user_account = self.db.query(UserMLAccount).filter(
                UserMLAccount.user_id == user_id,
                UserMLAccount.ml_account_id == ml_account_id,
                UserMLAccount.can_read == True
            ).first()
            
            if not user_account:
                return {
                    'success': False,
                    'error': 'Usuário não tem permissão para acessar esta conta ML'
                }
            
            history = self.product_service.get_sync_history(ml_account_id, company_id)
            
            return {
                'success': True,
                'history': history
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar histórico: {e}")
            return {
                'success': False,
                'error': f'Erro ao buscar histórico: {str(e)}'
            }
    
    def get_products_stats(self, company_id: int, ml_account_id: Optional[int] = None) -> Dict:
        """Busca estatísticas de produtos"""
        try:
            query = self.db.query(MLProduct).filter(MLProduct.company_id == company_id)
            
            if ml_account_id:
                query = query.filter(MLProduct.ml_account_id == ml_account_id)
            
            total_products = query.count()
            active_products = query.filter(MLProduct.status == "active").count()
            paused_products = query.filter(MLProduct.status == "paused").count()
            closed_products = query.filter(MLProduct.status == "closed").count()
            
            # Buscar contas ML
            ml_accounts = self.db.query(MLAccount).filter(
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).all()
            
            return {
                'success': True,
                'stats': {
                    'total_products': total_products,
                    'active_products': active_products,
                    'paused_products': paused_products,
                    'closed_products': closed_products,
                    'total_accounts': len(ml_accounts)
                },
                'accounts': [
                    {
                        'id': acc.id,
                        'nickname': acc.nickname,
                        'email': acc.email,
                        'country_id': acc.country_id
                    }
                    for acc in ml_accounts
                ]
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar estatísticas: {e}")
            return {
                'success': False,
                'error': f'Erro ao buscar estatísticas: {str(e)}'
            }
    
    def get_product_details_page(self, request: Request, user: Dict, product_id: int) -> HTMLResponse:
        """Renderiza página de detalhes do produto"""
        try:
            # Buscar detalhes do produto
            product_result = self.get_product_details(user["company"]["id"], product_id)
            
            if not product_result['success']:
                return HTMLResponse(
                    content=f"<h1>Produto não encontrado</h1><p>{product_result.get('error', 'Erro desconhecido')}</p>",
                    status_code=404
                )
            
            product = product_result['product']
            
            # Renderizar template
            from app.views.template_renderer import templates
            
            return templates.TemplateResponse(
                "ml_product_details_simple.html",
                {
                    "product": product,
                    "user": user,
                    "request": request
                }
            )
            
        except Exception as e:
            logger.error(f"Erro ao renderizar página de detalhes: {e}")
            return HTMLResponse(
                content=f"<h1>Erro</h1><p>{str(e)}</p>",
                status_code=500
            )

    def get_product_edit_page(self, request: Request, user: Dict, product_id: int) -> HTMLResponse:
        """Renderiza página de edição do produto"""
        try:
            product_result = self.get_product_details(user["company"]["id"], product_id)

            if not product_result.get("success"):
                return HTMLResponse(
                    content=f"<h1>Produto não encontrado</h1><p>{product_result.get('error', 'Erro desconhecido')}</p>",
                    status_code=404,
                )

            product = product_result["product"]
            company_id = user["company"]["id"]
            product = self._hydrate_product_from_ml_api(company_id, product)
            category_attributes = self._fetch_category_attributes(
                company_id,
                product.get("category_id"),
                product.get("ml_account_id"),
            )
            warranty_context = self._extract_warranty_context(product.get("sale_terms", []))
            status_options = [
                {"value": "active", "label": "Ativo"},
                {"value": "paused", "label": "Pausado"},
                {"value": "closed", "label": "Finalizado"},
            ]
 
            return templates.TemplateResponse(
                "ml_product_create.html",
                {
                    "request": request,
                    "user": user,
                    "product": product,
                    "product_json": product,
                    "warranty_context": warranty_context,
                    "is_edit": True,
                    "category_attributes": category_attributes,
                    "status_options": status_options,
                },
            )

        except Exception as e:
            logger.error(f"Erro ao renderizar página de edição: {e}", exc_info=True)
            return HTMLResponse(
                content=f"<h1>Erro</h1><p>{str(e)}</p>",
                status_code=500,
            )

    def delete_products(self, company_id: int, user_id: int, delete_all: bool = False, product_ids: list = []) -> Dict:
        """Remove produtos da base de dados"""
        try:
            from app.models.saas_models import MLProduct
            
            if delete_all:
                # Remover todos os produtos da empresa
                deleted_count = self.db.query(MLProduct).filter(
                    MLProduct.company_id == company_id
                ).delete()
                
                self.db.commit()
                
                return {
                    'success': True,
                    'message': f'{deleted_count} produto(s) removido(s) com sucesso',
                    'deleted_count': deleted_count,
                    'action': 'delete_all'
                }
            
            elif product_ids:
                # Remover produtos específicos
                if not isinstance(product_ids, list):
                    product_ids = [product_ids]
                
                # Verificar se os produtos pertencem à empresa
                products_to_delete = self.db.query(MLProduct).filter(
                    MLProduct.id.in_(product_ids),
                    MLProduct.company_id == company_id
                ).all()
                
                if not products_to_delete:
                    return {
                        'success': False,
                        'error': 'Nenhum produto encontrado ou você não tem permissão para removê-los'
                    }
                
                # Remover produtos
                for product in products_to_delete:
                    self.db.delete(product)
                
                self.db.commit()
                
                return {
                    'success': True,
                    'message': f'{len(products_to_delete)} produto(s) removido(s) com sucesso',
                    'deleted_count': len(products_to_delete),
                    'deleted_products': [p.id for p in products_to_delete],
                    'action': 'delete_selected'
                }
            
            else:
                return {
                    'success': False,
                    'error': 'Nenhuma opção de remoção especificada'
                }
                
        except Exception as e:
            logger.error(f"Erro ao remover produtos: {e}")
            self.db.rollback()
            return {
                'success': False,
                'error': f'Erro ao remover produtos: {str(e)}'
            }

    def get_product_analysis_page(self, request, user, product_id):
        """Renderiza a página de análise do produto"""
        try:
            # Buscar dados do produto
            product = self.db.query(MLProduct).filter(
                MLProduct.id == product_id,
                MLProduct.company_id == user["company"]["id"]
            ).first()
            
            if not product:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Produto não encontrado")
            
            return templates.TemplateResponse("ml_product_analysis.html", {
                "request": request,
                "user": user,
                "product": product,
                "product_id": product_id
            })
        except Exception as e:
            logger.error(f"Erro ao renderizar página de análise: {e}")
            raise

    async def create_product_in_ml(self, company_id: int, product_data: dict, images: list = None, ml_account_id: int = None):
        """
        Cria/publica um novo produto no Mercado Livre
        
        Args:
            company_id: ID da empresa
            product_data: Dados do produto (título, preço, categoria, etc)
            images: Lista de imagens do produto
            ml_account_id: ID da conta ML específica (opcional, usa primeira ativa se não fornecido)
            
        Returns:
            dict: Resultado da operação com success, item_id ou error
        """
        try:
            logger.info(f"🆕 Iniciando cadastro de produto no ML para company {company_id}, ml_account_id: {ml_account_id}")
            
            # 1. Buscar token ativo da empresa
            from app.services.token_manager import TokenManager
            from app.models.saas_models import Token, MLAccount
            from datetime import datetime
            
            # Buscar token ativo mais recente para a conta especificada ou qualquer conta ativa
            query = self.db.query(Token).join(MLAccount).filter(
                MLAccount.company_id == company_id,
                Token.is_active == True,
                Token.expires_at > datetime.utcnow()
            )
            
            # Se ml_account_id foi especificado, filtrar por ele
            if ml_account_id:
                query = query.filter(MLAccount.id == ml_account_id)
                logger.info(f"🔍 Buscando token para conta ML específica: {ml_account_id}")
            
            token = query.order_by(Token.expires_at.desc()).first()
            
            if not token:
                error_msg = f"Nenhum token ativo encontrado para company {company_id}"
                if ml_account_id:
                    error_msg += f" e conta ML {ml_account_id}"
                logger.error(f"❌ {error_msg}")
                return {
                    "success": False,
                    "error": "Nenhuma conta do Mercado Livre conectada ou autorizada. Por favor, conecte uma conta primeiro."
                }
            
            access_token = token.access_token
            ml_account = token.ml_account
            
            logger.info(f"✅ Token encontrado para conta ML: {ml_account.nickname} (ID: {ml_account.id})")
            
            # 2. Validar dados obrigatórios
            required_fields = ["title", "category_id", "price", "available_quantity", "condition", "listing_type_id"]
            missing_fields = [field for field in required_fields if not product_data.get(field)]
            
            if missing_fields:
                return {
                    "success": False,
                    "error": f"Campos obrigatórios faltando: {', '.join(missing_fields)}"
                }
            
            # 3. Fazer upload das imagens primeiro (se houver)
            image_urls = []
            if images:
                logger.info(f"📸 Fazendo upload de {len(images)} imagem(ns)...")
                
                
                max_upload_attempts = 3
                for idx, image in enumerate(images):
                    try:
                        upload_url = "https://api.mercadolibre.com/pictures/upload"
                        headers = {
                            "Authorization": f"Bearer {access_token}",
                        }
                        filename = image.get('filename', f'image_{idx}.jpg')
                        content_bytes = image.get('content')
                        content_type = image.get('content_type')
                        
                        if not content_bytes:
                            logger.warning(f"⚠️ Imagem {idx + 1} sem conteúdo, ignorando")
                            continue

                        max_size = 10 * 1024 * 1024
                        if len(content_bytes) > max_size:
                            logger.warning(f"⚠️ Imagem {idx + 1} ultrapassa 10 MB, ignorando ({len(content_bytes)} bytes)")
                            continue

                        allowed_types = {'image/jpeg', 'image/png'}
                        if not content_type or content_type not in allowed_types:
                            guessed_type, _ = mimetypes.guess_type(filename)
                            if guessed_type in allowed_types:
                                content_type = guessed_type
                            else:
                                logger.warning(f"⚠️ Imagem {idx + 1} com tipo não suportado ({content_type or 'desconhecido'}), ignorando")
                                continue
                        
                        files = {
                            'file': (filename, content_bytes, content_type)
                        }

                        upload_succeeded = False

                        for attempt in range(1, max_upload_attempts + 1):
                            upload_response = requests.post(upload_url, headers=headers, files=files, timeout=30)

                            if upload_response.status_code == 200:
                                upload_data = upload_response.json()
                                image_url = upload_data.get('secure_url') or upload_data.get('variations', [{}])[0].get('secure_url')

                                if image_url:
                                    image_urls.append({"source": image_url})
                                    logger.info(f"✅ Imagem {idx + 1} enviada com sucesso na tentativa {attempt}: {image_url}")
                                    upload_succeeded = True
                                else:
                                    logger.warning(f"⚠️ Upload da imagem {idx + 1} na tentativa {attempt} retornou sem URL válida: {upload_data}")
                                break

                            if upload_response.status_code in (500, 502, 503, 504):
                                logger.warning(
                                    f"⚠️ Erro temporário ao enviar imagem {idx + 1} (tentativa {attempt}/{max_upload_attempts}):"
                                    f" status={upload_response.status_code}, corpo={upload_response.text}"
                                )
                                if attempt < max_upload_attempts:
                                    time.sleep(attempt * 2)
                                continue

                            logger.warning(
                                f"⚠️ Erro ao enviar imagem {idx + 1}: status={upload_response.status_code}, corpo={upload_response.text}"
                            )
                            break

                        if not upload_succeeded:
                            fallback_url = image.get("source_url")
                            if fallback_url:
                                image_urls.append({"source": fallback_url})
                                logger.info(f"🔁 Usando URL pública alternativa para imagem {idx + 1}: {fallback_url}")
                            else:
                                logger.error(f"❌ Não foi possível enviar a imagem {idx + 1} após {max_upload_attempts} tentativas")
                            continue
                         
                    except Exception as img_error:
                        logger.error(f"❌ Erro ao processar imagem {idx + 1}: {img_error}")
            
            # 4. Montar payload do produto
            item_payload = {
                "title": product_data.get("title"),
                "category_id": product_data.get("category_id"),
                "price": float(product_data.get("price")),
                "currency_id": "BRL",
                "available_quantity": int(product_data.get("available_quantity")),
                "condition": product_data.get("condition"),
                "listing_type_id": product_data.get("listing_type_id"),
                "buying_mode": "buy_it_now",
            }
            
            # Adicionar descrição se fornecida
            if product_data.get("description"):
                item_payload["description"] = {
                    "plain_text": product_data.get("description")
                }
            
            # Adicionar imagens se houver
            if image_urls:
                item_payload["pictures"] = image_urls
            
            # Adicionar campos opcionais
            if product_data.get("seller_custom_field"):
                item_payload["seller_custom_field"] = product_data.get("seller_custom_field")
            
            # 4.5. Configurar envio (shipping)
            shipping_mode = product_data.get("shipping_mode", "me2")
            free_shipping = product_data.get("free_shipping", True)
            
            shipping_config = {
                "mode": shipping_mode,
                "free_shipping": free_shipping
            }
            
            length = product_data.get("package_length")
            width = product_data.get("package_width")
            height = product_data.get("package_height")
            weight = product_data.get("package_weight")
            
            if length and width and height and weight:
                try:
                    length_int = int(round(float(length)))
                    width_int = int(round(float(width)))
                    height_int = int(round(float(height)))
                    weight_int = int(round(float(weight)))
                    dimensions_string = f"{length_int}x{width_int}x{height_int},{weight_int}"
                    shipping_config["dimensions"] = dimensions_string
                    logger.info(f"📐 Dimensões do pacote formatadas: {dimensions_string}")
                except Exception as dim_error:
                    logger.warning(f"⚠️ Não foi possível formatar as dimensões: {dim_error}")
            else:
                logger.info("ℹ️ Dimensões incompletas - campo dimensions não será enviado")
            
            if shipping_config.get("dimensions"):
                item_payload["shipping"] = shipping_config
            else:
                item_payload["shipping"] = shipping_config
            
            logger.info(f"🚚 Configuração de envio: mode={shipping_mode}, free_shipping={free_shipping}")
 
            # 4.6. Termos de venda (garantia)
            warranty_terms = self._build_warranty_terms(
                product_data.get("warranty_type"),
                product_data.get("warranty_time_value"),
                product_data.get("warranty_time_unit"),
            )
            sale_terms = warranty_terms.get("sale_terms", [])
            warranty_display = product_data.get("warranty") or warranty_terms.get("warranty_display", "")

            if sale_terms:
                item_payload["sale_terms"] = sale_terms
                logger.info(f"🛡️ Termos de garantia aplicados: {sale_terms}")

            product_data["warranty"] = warranty_display

            # 4.7. Adicionar atributos (fiscais + categoria)
            attributes = []
            
            # Dados fiscais obrigatórios
            if product_data.get("gtin"):
                attributes.append({
                    "id": "GTIN",
                    "value_name": product_data.get("gtin")
                })
                logger.info(f"📊 GTIN adicionado: {product_data.get('gtin')}")
            
            if product_data.get("mpn"):
                attributes.append({
                    "id": "MPN",
                    "value_name": product_data.get("mpn")
                })
            
            # Atributos dinâmicos da categoria
            if product_data.get("attributes"):
                attributes.extend(product_data.get("attributes"))
                logger.info(f"📋 {len(product_data.get('attributes'))} atributos da categoria adicionados")
            
            if attributes:
                item_payload["attributes"] = attributes
            
            # 4.8. Adicionar dados fiscais detalhados (sale_terms)
            # Outros sale_terms específicos permanecem desativados
            
            logger.info(f"📦 Payload preparado: {item_payload.get('title')} - R$ {item_payload.get('price')}")
            
            # 5. Criar produto no Mercado Livre
            
            create_url = "https://api.mercadolibre.com/items"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(create_url, json=item_payload, headers=headers, timeout=30)
            
            if response.status_code in [200, 201]:
                item_data = response.json()
                item_id = item_data.get("id")
                
                logger.info(f"🎉 Produto criado com sucesso no ML! ID: {item_id}")
                
                # 6. Salvar produto no banco de dados local
                try:
                    new_product = MLProduct(
                        ml_item_id=item_id,
                        ml_account_id=ml_account.id,
                        company_id=company_id,
                        title=item_data.get("title"),
                        price=item_data.get("price"),
                        available_quantity=item_data.get("available_quantity"),
                        sold_quantity=item_data.get("sold_quantity", 0),
                        status=item_data.get("status", "active").upper(),
                        condition=item_data.get("condition"),
                        listing_type_id=item_data.get("listing_type_id"),
                        category_id=item_data.get("category_id"),
                        thumbnail=item_data.get("thumbnail"),
                        permalink=item_data.get("permalink"),
                        seller_custom_field=item_data.get("seller_custom_field")
                    )
                    
                    self.db.add(new_product)
                    self.db.commit()
                    
                    logger.info(f"💾 Produto salvo no banco de dados local")
                    
                except Exception as db_error:
                    logger.error(f"⚠️ Erro ao salvar produto no banco: {db_error}")
                    # Não falhar a operação por causa disso
                
                return {
                    "success": True,
                    "item_id": item_id,
                    "permalink": item_data.get("permalink"),
                    "message": f"Produto criado com sucesso! ID: {item_id}"
                }
                
            else:
                error_msg = response.text
                logger.error(f"❌ Erro ao criar produto no ML: {response.status_code} - {error_msg}")
                
                try:
                    error_data = response.json()
                    if "message" in error_data:
                        error_msg = error_data["message"]
                    elif "error" in error_data:
                        error_msg = error_data["error"]
                except:
                    pass
                
                return {
                    "success": False,
                    "error": f"Erro ao publicar no Mercado Livre: {error_msg}"
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao criar produto no ML: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Erro interno ao criar produto: {str(e)}"
            }

    async def update_product_in_ml(
        self,
        company_id: int,
        product_id: int,
        product_data: Dict[str, Any],
        images: Optional[List[Dict[str, Any]]] = None,
        existing_pictures: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Atualiza um produto existente no Mercado Livre"""
        try:
            ml_product = (
                self.db.query(MLProduct)
                .filter(
                    MLProduct.id == product_id,
                    MLProduct.company_id == company_id,
                )
                .first()
            )

            if not ml_product:
                return {"success": False, "error": "Produto não encontrado"}

            if not ml_product.ml_item_id:
                return {"success": False, "error": "Produto sem item_id do Mercado Livre"}

            token = self._get_valid_token_for_account(company_id, ml_product.ml_account_id)

            if not token:
                logger.error(
                    "❌ Nenhum token ativo para atualizar o produto %s (account %s)",
                    ml_product.ml_item_id,
                    ml_product.ml_account_id,
                )
                return {
                    "success": False,
                    "error": "Nenhum token ativo encontrado para a conta deste anúncio. Reautentique a conta do Mercado Livre.",
                }

            images = images or []
            existing_pictures = existing_pictures or []

            payload: Dict[str, Any] = {}

            title = (product_data.get("title") or "").strip()
            if title:
                payload["title"] = title[:60]

            category_id = (product_data.get("category_id") or "").strip()
            if category_id:
                payload["category_id"] = category_id

            listing_type_id = (product_data.get("listing_type_id") or "").strip()
            if listing_type_id:
                payload["listing_type_id"] = listing_type_id

            condition = (product_data.get("condition") or "").strip()
            if condition:
                payload["condition"] = condition

            seller_custom_field = (product_data.get("seller_custom_field") or "").strip()
            if seller_custom_field:
                payload["seller_custom_field"] = seller_custom_field

            price = product_data.get("price")
            if price not in (None, ""):
                try:
                    price_value = float(str(price).replace(',', '.'))
                    if price_value < 0:
                        raise ValueError("Preço negativo")
                    payload["price"] = round(price_value, 2)
                except (TypeError, ValueError):
                    return {"success": False, "error": "Preço inválido informado."}

            available_quantity = product_data.get("available_quantity")
            if available_quantity not in (None, ""):
                try:
                    quantity_value = int(float(available_quantity))
                    if quantity_value < 0:
                        raise ValueError("Quantidade negativa")
                    payload["available_quantity"] = quantity_value
                except (TypeError, ValueError):
                    return {"success": False, "error": "Quantidade disponível inválida."}

            shipping_mode = product_data.get("shipping_mode") or ml_product.shipping.get("mode") if ml_product.shipping else None
            free_shipping = bool(product_data.get("free_shipping"))
            shipping_config: Dict[str, Any] = {}
            if shipping_mode:
                shipping_config["mode"] = shipping_mode
            shipping_config["free_shipping"] = free_shipping

            dimensions_parts = []
            for dim_key in ("package_length", "package_width", "package_height"):
                dim_value = product_data.get(dim_key)
                if dim_value not in (None, ""):
                    try:
                        dimensions_parts.append(str(int(float(dim_value))))
                    except (ValueError, TypeError):
                        logger.warning("⚠️ Dimensão inválida para %s: %s", dim_key, dim_value)

            weight_value = product_data.get("package_weight")
            weight_part = None
            if weight_value not in (None, ""):
                try:
                    weight_part = str(int(float(weight_value)))
                except (ValueError, TypeError):
                    logger.warning("⚠️ Peso inválido informado: %s", weight_value)

            if dimensions_parts and weight_part:
                shipping_config["dimensions"] = "x".join(dimensions_parts) + f",{weight_part}"

            if shipping_config:
                payload["shipping"] = shipping_config

            pictures_payload: List[Dict[str, Any]] = []
            for url in existing_pictures:
                if url:
                    pictures_payload.append({"source": url})

            image_urls: List[Dict[str, str]] = []
            if images:
                logger.info("📸 Atualizando %d nova(s) imagem(ns) para o item", len(images))
                upload_url = "https://api.mercadolibre.com/pictures/upload"
                headers_upload = {"Authorization": f"Bearer {token.access_token}"}
                max_upload_attempts = 3

                for idx, image in enumerate(images):
                    content_bytes = image.get("content")
                    if not content_bytes:
                        logger.warning("⚠️ Imagem %s sem conteúdo, ignorando", idx)
                        continue

                    filename = image.get("filename") or f"image_{idx}.jpg"
                    content_type = image.get("content_type")
                    allowed_types = {'image/jpeg', 'image/png'}
                    if content_type not in allowed_types:
                        guessed_type, _ = mimetypes.guess_type(filename)
                        if guessed_type in allowed_types:
                            content_type = guessed_type
                        else:
                            content_type = 'image/jpeg'

                    files = {'file': (filename, content_bytes, content_type)}
                    upload_success = False

                    for attempt in range(1, max_upload_attempts + 1):
                        upload_response = requests.post(upload_url, headers=headers_upload, files=files, timeout=30)
                        if upload_response.status_code == 200:
                            upload_data = upload_response.json()
                            image_url = upload_data.get('secure_url') or upload_data.get('variations', [{}])[0].get('secure_url')
                            if image_url:
                                image_urls.append({"source": image_url})
                                logger.info("✅ Imagem %s atualizada com sucesso na tentativa %s", idx + 1, attempt)
                                upload_success = True
                                break
                        elif upload_response.status_code in (500, 502, 503, 504):
                            logger.warning(
                                "⚠️ Erro temporário ao enviar imagem %s (tentativa %s/%s): %s",
                                idx + 1,
                                attempt,
                                max_upload_attempts,
                                upload_response.status_code,
                            )
                            time.sleep(attempt)
                            continue
                        else:
                            logger.warning(
                                "⚠️ Erro ao enviar imagem %s: status=%s, corpo=%s",
                                idx + 1,
                                upload_response.status_code,
                                upload_response.text,
                            )
                            break

                    if not upload_success:
                        fallback_url = image.get("source_url")
                        if fallback_url:
                            image_urls.append({"source": fallback_url})
                            logger.info("🔁 Usando URL alternativa para imagem %s: %s", idx + 1, fallback_url)

            if pictures_payload or image_urls:
                payload["pictures"] = pictures_payload + image_urls

            attributes_payload: List[Dict[str, Any]] = []
            if product_data.get("attributes"):
                attributes_payload.extend(product_data["attributes"])

            if attributes_payload:
                attributes_payload = [attr for attr in attributes_payload if attr.get("id") not in {"GTIN", "MPN"}]

            if product_data.get("gtin"):
                attributes_payload.append({"id": "GTIN", "value_name": product_data.get("gtin")})

            if product_data.get("mpn"):
                attributes_payload.append({"id": "MPN", "value_name": product_data.get("mpn")})

            if attributes_payload:
                payload["attributes"] = attributes_payload

            warranty_data = self._build_warranty_terms(
                product_data.get("warranty_type"),
                product_data.get("warranty_time_value"),
                product_data.get("warranty_time_unit"),
            )
            sale_terms = warranty_data.get("sale_terms", [])
            warranty_display = product_data.get("warranty") or warranty_data.get("warranty_display", "")
            if sale_terms:
                payload["sale_terms"] = sale_terms

            if not payload:
                return {"success": False, "error": "Nenhum dado para atualizar."}

            headers = {
                "Authorization": f"Bearer {token.access_token}",
                "Content-Type": "application/json",
            }

            update_url = f"https://api.mercadolibre.com/items/{ml_product.ml_item_id}"
            response = requests.put(update_url, json=payload, headers=headers, timeout=30)

            if response.status_code not in (200, 201):
                logger.error(
                    "❌ Erro ao atualizar item %s: %s - %s",
                    ml_product.ml_item_id,
                    response.status_code,
                    response.text,
                )
                try:
                    error_data = response.json()
                    message = error_data.get("message") or error_data.get("error") or response.text
                except Exception:
                    message = response.text
                return {"success": False, "error": f"Erro ao atualizar anúncio: {message}"}

            updated_item = response.json()

            description_text = product_data.get("description")
            if description_text is not None:
                try:
                    desc_response = requests.put(
                        f"https://api.mercadolibre.com/items/{ml_product.ml_item_id}/description",
                        headers=headers,
                        json={"plain_text": description_text},
                        timeout=30,
                    )
                    if desc_response.status_code not in (200, 201):
                        logger.warning(
                            "⚠️ Não foi possível atualizar a descrição: %s - %s",
                            desc_response.status_code,
                            desc_response.text,
                        )
                except Exception as desc_exc:
                    logger.warning("⚠️ Erro ao atualizar descrição: %s", desc_exc)

            if "title" in payload:
                ml_product.title = payload["title"]
            if "price" in payload:
                ml_product.price = f"{payload['price']:.2f}"
            if "available_quantity" in payload:
                ml_product.available_quantity = payload["available_quantity"]
            if "listing_type_id" in payload:
                ml_product.listing_type_id = payload["listing_type_id"]
            if "condition" in payload:
                ml_product.condition = payload["condition"]
            if "category_id" in payload:
                ml_product.category_id = payload["category_id"]
            if "seller_custom_field" in payload:
                ml_product.seller_custom_field = payload["seller_custom_field"]
            if payload.get("shipping"):
                ml_product.free_shipping = payload["shipping"].get("free_shipping", ml_product.free_shipping)
                ml_product.shipping = payload["shipping"]
            if payload.get("pictures"):
                ml_product.pictures = payload["pictures"]
                if payload["pictures"]:
                    ml_product.thumbnail = payload["pictures"][0].get("source")
            if attributes_payload:
                ml_product.attributes = attributes_payload
            if sale_terms:
                ml_product.sale_terms = sale_terms
            if warranty_display:
                ml_product.warranty = warranty_display
            if description_text is not None:
                ml_product.description = description_text

            ml_product.last_ml_update = datetime.utcnow()
            ml_product.updated_at = datetime.utcnow()

            if updated_item.get("permalink"):
                ml_product.permalink = updated_item.get("permalink")

            self.db.commit()

            return {
                "success": True,
                "item_id": ml_product.ml_item_id,
                "message": "Anúncio atualizado com sucesso.",
                "updated_item": updated_item,
            }

        except Exception as exc:
            logger.error("❌ Erro ao atualizar produto: %s", exc, exc_info=True)
            self.db.rollback()
            return {"success": False, "error": f"Erro interno ao atualizar produto: {exc}"}
