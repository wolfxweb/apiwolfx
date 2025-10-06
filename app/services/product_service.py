"""
Serviço para gerenciar produtos importados
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.saas_models import Product, MLProduct
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
                    company_id=company_id
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
                data = response.json()
                return {
                    "title": data.get("title", ""),
                    "thumbnail": data.get("thumbnail", ""),
                    "sku": data.get("sku", ""),
                    "price": data.get("price", 0),
                    "available_quantity": data.get("available_quantity", 0),
                    "sold_quantity": data.get("sold_quantity", 0),
                    "condition": data.get("condition", ""),
                    "category_id": data.get("category_id", ""),
                    "listing_type_id": data.get("listing_type_id", ""),
                    "permalink": data.get("permalink", "")
                }
            else:
                logger.error(f"Erro ao buscar produto {ml_item_id}: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Erro ao buscar produto {ml_item_id}: {e}")
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

