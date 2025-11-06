"""
Controller para gerenciar produtos do Mercado Livre
"""
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import Request
from fastapi.responses import HTMLResponse

from app.models.saas_models import MLAccount, MLProduct, User, MLAccountStatus, UserMLAccount
from app.services.ml_product_service import MLProductService
from fastapi.templating import Jinja2Templates
from pathlib import Path

# Configurar templates com Jinja2 nativo
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "views" / "templates")

logger = logging.getLogger(__name__)

class MLProductController:
    """Controller para produtos do Mercado Livre"""
    
    def __init__(self, db: Session):
        self.db = db
        self.product_service = MLProductService(db)
    
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

    async def create_product_in_ml(self, company_id: int, product_data: dict, images: list = None):
        """
        Cria/publica um novo produto no Mercado Livre
        
        Args:
            company_id: ID da empresa
            product_data: Dados do produto (título, preço, categoria, etc)
            images: Lista de imagens do produto
            
        Returns:
            dict: Resultado da operação com success, item_id ou error
        """
        try:
            logger.info(f"🆕 Iniciando cadastro de produto no ML para company {company_id}")
            
            # 1. Buscar token ativo da empresa
            from app.services.token_manager import TokenManager
            from app.models.saas_models import Token, MLAccount
            from datetime import datetime
            
            # Buscar token ativo mais recente
            token = self.db.query(Token).join(MLAccount).filter(
                MLAccount.company_id == company_id,
                Token.is_active == True,
                Token.expires_at > datetime.utcnow()
            ).order_by(Token.expires_at.desc()).first()
            
            if not token:
                logger.error(f"❌ Nenhum token ativo encontrado para company {company_id}")
                return {
                    "success": False,
                    "error": "Nenhuma conta do Mercado Livre conectada ou autorizada. Por favor, conecte uma conta primeiro."
                }
            
            access_token = token.access_token
            ml_account = token.ml_account
            
            logger.info(f"✅ Token encontrado para conta ML: {ml_account.nickname}")
            
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
                
                import requests
                import base64
                
                for idx, image in enumerate(images):
                    try:
                        # Upload de imagem para o ML
                        upload_url = "https://api.mercadolibre.com/pictures/upload"
                        headers = {
                            "Authorization": f"Bearer {access_token}",
                        }
                        
                        # Enviar imagem como multipart/form-data
                        files = {
                            'file': (image.get('filename', f'image_{idx}.jpg'), image.get('content'), 'image/jpeg')
                        }
                        
                        upload_response = requests.post(upload_url, headers=headers, files=files, timeout=30)
                        
                        if upload_response.status_code == 200:
                            upload_data = upload_response.json()
                            image_url = upload_data.get('secure_url') or upload_data.get('variations', [{}])[0].get('secure_url')
                            
                            if image_url:
                                image_urls.append({"source": image_url})
                                logger.info(f"✅ Imagem {idx + 1} enviada com sucesso")
                        else:
                            logger.warning(f"⚠️ Erro ao enviar imagem {idx + 1}: {upload_response.text}")
                            
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
            
            if product_data.get("warranty"):
                item_payload["warranty"] = product_data.get("warranty")
            
            logger.info(f"📦 Payload preparado: {item_payload.get('title')} - R$ {item_payload.get('price')}")
            
            # 5. Criar produto no Mercado Livre
            import requests
            
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
