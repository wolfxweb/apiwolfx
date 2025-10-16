"""
Serviço para gerenciar produtos importados
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.saas_models import Product, MLProduct, InternalProduct
from app.services.token_manager import TokenManager
import requests

logger = logging.getLogger(__name__)

class ProductService:
    def __init__(self, db: Session):
        self.db = db

    def import_product(self, ml_item_id: str, company_id: int, user_id: int) -> Dict[str, Any]:
        """
        Importa um produto específico do Mercado Livre
        """
        try:
            # Verificar se já existe
            existing_product = self.db.query(Product).filter(
                and_(
                    Product.ml_item_id == ml_item_id,
                    Product.company_id == company_id
                )
            ).first()

            if existing_product:
                return {
                    "success": False,
                    "error": "Produto já importado",
                    "product": {
                        "id": existing_product.id,
                        "title": existing_product.title,
                        "sku": existing_product.sku
                    }
                }

            # Buscar dados do produto no ML
            product_data = self._fetch_product_from_ml(ml_item_id, user_id)
            if not product_data:
                return {
                    "success": False,
                    "error": "Erro ao buscar dados do produto no Mercado Livre"
                }

            # Criar novo produto
            new_product = Product(
                ml_item_id=ml_item_id,
                title=product_data.get("title", ""),
                thumbnail=product_data.get("thumbnail", ""),
                sku=product_data.get("sku", ""),
                company_id=company_id
            )

            self.db.add(new_product)
            self.db.commit()
            self.db.refresh(new_product)

            return {
                "success": True,
                "message": "Produto importado com sucesso",
                "product": {
                    "id": new_product.id,
                    "ml_item_id": new_product.ml_item_id,
                    "title": new_product.title,
                    "thumbnail": new_product.thumbnail,
                    "sku": new_product.sku
                }
            }

        except Exception as e:
            logger.error(f"Erro ao importar produto {ml_item_id}: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": f"Erro interno: {str(e)}"
            }

    def import_all_products(self, company_id: int, user_id: int) -> Dict[str, Any]:
        """
        Importa todos os produtos da empresa do Mercado Livre
        """
        try:
            # Buscar produtos do ML da empresa
            ml_products = self.db.query(MLProduct).filter(
                MLProduct.company_id == company_id
            ).all()

            if not ml_products:
                return {
                    "success": False,
                    "error": "Nenhum produto encontrado no Mercado Livre"
                }

            imported_count = 0
            skipped_count = 0
            errors = []

            for ml_product in ml_products:
                # Verificar se já existe
                existing = self.db.query(Product).filter(
                    and_(
                        Product.ml_item_id == ml_product.ml_item_id,
                        Product.company_id == company_id
                    )
                ).first()

                if existing:
                    skipped_count += 1
                    continue

                # Buscar dados completos do produto
                product_data = self._fetch_product_from_ml(ml_product.ml_item_id, user_id)
                if not product_data:
                    errors.append(f"Erro ao buscar {ml_product.ml_item_id}")
                    continue

                # Criar produto
                new_product = Product(
                    ml_item_id=ml_product.ml_item_id,
                    title=product_data.get("title", ml_product.title),
                    thumbnail=product_data.get("thumbnail", ""),
                    sku=product_data.get("sku", ""),
                    company_id=company_id,
                    ml_account_id=ml_product.ml_account_id  # Adicionar ml_account_id obrigatório
                )

                self.db.add(new_product)
                imported_count += 1

            self.db.commit()

            return {
                "success": True,
                "message": f"Importação concluída: {imported_count} importados, {skipped_count} já existiam",
                "imported_count": imported_count,
                "skipped_count": skipped_count,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Erro ao importar todos os produtos: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": f"Erro interno: {str(e)}"
            }

    def _fetch_product_from_ml(self, ml_item_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Busca dados completos do produto no Mercado Livre
        """
        try:
            # Obter token válido
            token_manager = TokenManager(self.db)
            token = token_manager.get_valid_token(user_id)
            
            if not token:
                logger.error("Token não encontrado para buscar produto")
                return None

            # Buscar dados do produto
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            response = requests.get(
                f'https://api.mercadolibre.com/items/{ml_item_id}',
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                product_data = response.json()
                
                # Buscar preços promocionais se existirem
                promotional_price = self._get_promotional_price(ml_item_id, headers)
                if promotional_price:
                    product_data['promotional_price'] = promotional_price
                
                return product_data
            else:
                logger.error(f"Erro ao buscar produto {ml_item_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar produto {ml_item_id}: {e}")
            return None

    def get_ml_product_data(self, ml_account_id: int, item_id: str) -> Dict[str, Any]:
        """
        Busca dados atualizados de um produto específico do Mercado Livre
        """
        try:
            # Obter token válido
            from app.services.ml_product_service import MLProductService
            ml_service = MLProductService(self.db)
            token = ml_service.get_active_token(ml_account_id)
            
            if not token:
                return {
                    "success": False,
                    "error": "Token não encontrado para a conta ML"
                }

            # Buscar dados atualizados do produto
            product_data = ml_service.fetch_product_details(item_id, token)
            
            # Processar dados para o formato esperado
            processed_data = {
                "title": product_data.get("title", ""),
                "price": product_data.get("price", 0),
                "promotional_price": product_data.get("promotional_price"),
                "available_quantity": product_data.get("available_quantity", 0),
                "sold_quantity": product_data.get("sold_quantity", 0),
                "status": product_data.get("status", ""),
                "description": product_data.get("description", ""),
                "category_id": product_data.get("category_id", ""),
                "seller_sku": product_data.get("seller_sku", ""),
                "permalink": product_data.get("permalink", ""),
                "thumbnail": product_data.get("thumbnail", "")
            }
            
            return {
                "success": True,
                "data": processed_data
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados do produto {item_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _get_promotional_price(self, ml_item_id: str, headers: dict) -> Optional[float]:
        """
        Busca preço promocional do produto
        """
        try:
            # Buscar informações de preços promocionais
            response = requests.get(
                f'https://api.mercadolibre.com/items/{ml_item_id}/promotions',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                promotions = response.json()
                if promotions and len(promotions) > 0:
                    # Pegar a primeira promoção ativa
                    for promotion in promotions:
                        if promotion.get('status') == 'active':
                            return promotion.get('price')
            
            return None
            
        except Exception as e:
            logger.warning(f"Erro ao buscar preço promocional para {ml_item_id}: {e}")
            return None

    def get_products(self, company_id: int, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        """
        Lista produtos importados da empresa
        """
        try:
            products = self.db.query(Product).filter(
                Product.company_id == company_id
            ).offset(skip).limit(limit).all()

            total = self.db.query(Product).filter(
                Product.company_id == company_id
            ).count()

            return {
                "success": True,
                "products": [
                    {
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
                    for product in products
                ],
                "total": total,
                "skip": skip,
                "limit": limit
            }

        except Exception as e:
            logger.error(f"Erro ao listar produtos: {e}")
            return {
                "success": False,
                "error": f"Erro interno: {str(e)}"
            }

    def update_product(self, product_id: int, company_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza dados de um produto
        """
        try:
            product = self.db.query(Product).filter(
                and_(
                    Product.id == product_id,
                    Product.company_id == company_id
                )
            ).first()

            if not product:
                return {
                    "success": False,
                    "error": "Produto não encontrado"
                }

            # Atualizar campos permitidos
            allowed_fields = ['cost_price', 'tax_rate', 'marketing_cost', 'other_costs', 'notes']
            for field in allowed_fields:
                if field in data:
                    setattr(product, field, data[field])

            self.db.commit()
            self.db.refresh(product)

            return {
                "success": True,
                "message": "Produto atualizado com sucesso",
                "product": {
                    "id": product.id,
                    "ml_item_id": product.ml_item_id,
                    "title": product.title,
                    "cost_price": product.cost_price,
                    "tax_rate": product.tax_rate,
                    "marketing_cost": product.marketing_cost,
                    "other_costs": product.other_costs,
                    "notes": product.notes
                }
            }

        except Exception as e:
            logger.error(f"Erro ao atualizar produto {product_id}: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": f"Erro interno: {str(e)}"
            }

    def import_to_internal_products(self, company_id: int, user_id: int) -> Dict[str, Any]:
        """
        Importa produtos do ML para a tabela internal_products
        """
        try:
            # Buscar produtos do ML da empresa
            ml_products = self.db.query(MLProduct).filter(
                MLProduct.company_id == company_id
            ).all()

            if not ml_products:
                return {
                    "success": False,
                    "error": "Nenhum produto encontrado no Mercado Livre"
                }

            imported_count = 0
            skipped_count = 0
            errors = []

            for ml_product in ml_products:
                # Verificar se já existe produto interno com este ml_item_id
                existing_internal = self.db.query(InternalProduct).filter(
                    and_(
                        InternalProduct.base_product_id == ml_product.id,
                        InternalProduct.company_id == company_id
                    )
                ).first()

                if existing_internal:
                    skipped_count += 1
                    continue

                # Usar SKU do ML se disponível, senão usar ml_item_id como fallback
                internal_sku = ml_product.seller_sku if ml_product.seller_sku else f"ML-{ml_product.ml_item_id}"
                
                # Criar produto interno usando dados já importados
                new_internal_product = InternalProduct(
                    company_id=company_id,
                    base_product_id=ml_product.id,  # Referência ao produto ML
                    name=ml_product.title,
                    description=ml_product.subtitle or "",
                    internal_sku=internal_sku,
                    cost_price=0.0,  # Será preenchido depois
                    selling_price=float(ml_product.price or 0),
                    category=ml_product.category_id or "",
                    brand="",  # Marca não disponível no ML
                    supplier="Mercado Livre",
                    # Usar dados já importados
                    main_image=ml_product.thumbnail or "",
                    current_stock=int(ml_product.available_quantity or 0)
                )

                self.db.add(new_internal_product)
                self.db.flush()  # Para obter o ID do produto criado
                
                # Registrar no sistema de gerenciamento de SKU
                try:
                    from app.services.sku_management_service import SKUManagementService
                    sku_service = SKUManagementService(self.db)
                    
                    # Registrar SKU no sistema de gerenciamento
                    sku_service.register_sku(
                        sku=internal_sku,
                        platform="mercadolivre",
                        platform_item_id=ml_product.ml_item_id,
                        company_id=company_id,
                        product_id=ml_product.id,
                        internal_product_id=new_internal_product.id
                    )
                except Exception as e:
                    logger.warning(f"Erro ao registrar SKU no sistema: {e}")
                    # Não falha a criação do produto se o registro do SKU falhar
                
                imported_count += 1

            self.db.commit()

            return {
                "success": True,
                "message": f"Importação para produtos internos concluída: {imported_count} importados, {skipped_count} já existiam",
                "imported_count": imported_count,
                "skipped_count": skipped_count,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Erro ao importar produtos para internos: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": f"Erro interno: {str(e)}"
            }

    def import_selected_to_internal_products(self, company_id: int, user_id: int, product_ids: list) -> Dict[str, Any]:
        """
        Importa produtos selecionados do ML para a tabela internal_products
        LÓGICA CORRIGIDA: Um SKU = Um produto interno, múltiplos anúncios associados
        """
        try:
            if not product_ids:
                return {
                    "success": False,
                    "error": "Nenhum produto selecionado"
                }

            # Buscar produtos do ML selecionados
            ml_products = self.db.query(MLProduct).filter(
                and_(
                    MLProduct.id.in_(product_ids),
                    MLProduct.company_id == company_id
                )
            ).all()

            if not ml_products:
                return {
                    "success": False,
                    "error": "Nenhum produto encontrado"
                }

            imported_count = 0
            skipped_count = 0
            errors = []
            
            # Agrupar produtos por SKU
            sku_groups = {}
            for ml_product in ml_products:
                internal_sku = ml_product.seller_sku if ml_product.seller_sku else f"ML-{ml_product.ml_item_id}"
                if internal_sku not in sku_groups:
                    sku_groups[internal_sku] = []
                sku_groups[internal_sku].append(ml_product)
            
            # Processar cada grupo de SKU
            for internal_sku, ml_products_group in sku_groups.items():
                # Verificar se já existe produto interno com este SKU
                existing_internal = self.db.query(InternalProduct).filter(
                    and_(
                        InternalProduct.internal_sku == internal_sku,
                        InternalProduct.company_id == company_id
                    )
                ).first()

                if existing_internal:
                    # Produto interno já existe, associar todos os anúncios do grupo
                    for ml_product in ml_products_group:
                        try:
                            from app.services.sku_management_service import SKUManagementService
                            sku_service = SKUManagementService(self.db)
                            
                            # Associar anúncio ao produto interno existente
                            sku_service.register_sku(
                                sku=internal_sku,
                                platform="mercadolivre",
                                platform_item_id=ml_product.ml_item_id,
                                company_id=company_id,
                                product_id=ml_product.id,
                                internal_product_id=existing_internal.id
                            )
                            
                            logger.info(f"Anúncio '{ml_product.ml_item_id}' associado ao produto interno existente '{internal_sku}'")
                            
                        except Exception as e:
                            logger.warning(f"Erro ao associar anúncio ao produto existente: {e}")
                    
                    skipped_count += len(ml_products_group)
                    continue
                
                # Criar novo produto interno (usar dados do primeiro produto do grupo)
                first_product = ml_products_group[0]
                new_internal_product = InternalProduct(
                    company_id=company_id,
                    base_product_id=first_product.id,  # Referência ao primeiro produto ML
                    name=first_product.title,
                    description=first_product.subtitle or "",
                    internal_sku=internal_sku,
                    cost_price=0.0,  # Será preenchido depois
                    selling_price=float(first_product.price or 0),
                    category=first_product.category_id or "",
                    brand="",  # Marca não disponível no ML
                    supplier="Mercado Livre",
                    # Usar dados já importados
                    main_image=first_product.thumbnail or "",
                    current_stock=int(first_product.available_quantity or 0)
                )

                self.db.add(new_internal_product)
                self.db.flush()  # Para obter o ID do produto criado
                
                # Associar todos os anúncios do grupo ao produto interno criado
                for ml_product in ml_products_group:
                    try:
                        from app.services.sku_management_service import SKUManagementService
                        sku_service = SKUManagementService(self.db)
                        
                        # Registrar SKU no sistema de gerenciamento
                        sku_service.register_sku(
                            sku=internal_sku,
                            platform="mercadolivre",
                            platform_item_id=ml_product.ml_item_id,
                            company_id=company_id,
                            product_id=ml_product.id,
                            internal_product_id=new_internal_product.id
                        )
                        
                        logger.info(f"SKU '{internal_sku}' registrado para anúncio '{ml_product.ml_item_id}'")
                        
                    except Exception as e:
                        logger.warning(f"Erro ao registrar SKU no sistema: {e}")
                
                imported_count += 1

            self.db.commit()

            return {
                "success": True,
                "message": f"Importação concluída: {imported_count} produtos internos criados, {skipped_count} anúncios associados",
                "imported_count": imported_count,
                "skipped_count": skipped_count,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Erro ao importar produtos selecionados para internos: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": f"Erro interno: {str(e)}"
            }

