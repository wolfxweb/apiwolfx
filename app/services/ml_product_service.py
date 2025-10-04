"""
Serviço para gerenciar produtos do Mercado Livre
"""
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.saas_models import MLAccount, MLProduct, MLProductSync, Token, MLProductStatus
from app.config.settings import settings

logger = logging.getLogger(__name__)

class MLProductService:
    """Serviço para gerenciar produtos do Mercado Livre"""
    
    def __init__(self, db: Session):
        self.db = db
        self.base_url = "https://api.mercadolibre.com"
    
    def get_active_token(self, ml_account_id: int) -> Optional[str]:
        """Obtém token ativo para a conta ML"""
        try:
            token = self.db.query(Token).filter(
                and_(
                    Token.ml_account_id == ml_account_id,
                    Token.is_active == True,
                    Token.expires_at > datetime.utcnow()
                )
            ).first()
            
            if token:
                return token.access_token
            return None
        except Exception as e:
            logger.error(f"Erro ao obter token ativo: {e}")
            return None
    
    def fetch_user_products(self, ml_account_id: int, limit: int = 50, offset: int = 0) -> Dict:
        """Busca produtos do usuário na API do ML"""
        try:
            token = self.get_active_token(ml_account_id)
            if not token:
                raise Exception("Token ativo não encontrado")
            
            ml_account = self.db.query(MLAccount).filter(MLAccount.id == ml_account_id).first()
            if not ml_account:
                raise Exception("Conta ML não encontrada")
            
            # URL para buscar produtos do usuário
            url = f"{self.base_url}/users/{ml_account.ml_user_id}/items/search"
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "limit": limit,
                "offset": offset,
                "status": "active"  # Apenas produtos ativos
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição para API ML: {e}")
            raise Exception(f"Erro na API do Mercado Livre: {e}")
        except Exception as e:
            logger.error(f"Erro ao buscar produtos do usuário: {e}")
            raise
    
    def fetch_product_details(self, ml_item_id: str, token: str) -> Dict:
        """Busca detalhes completos de um produto"""
        try:
            url = f"{self.base_url}/items/{ml_item_id}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao buscar detalhes do produto {ml_item_id}: {e}")
            raise Exception(f"Erro ao buscar produto: {e}")
    
    def sync_products_incremental(self, ml_account_id: int, company_id: int) -> Dict:
        """Sincronização incremental de produtos"""
        try:
            # Iniciar log de sincronização
            sync_log = MLProductSync(
                ml_product_id=None,  # Será atualizado depois
                company_id=company_id,
                ml_account_id=ml_account_id,
                sync_type="incremental",
                sync_status="running",
                started_at=datetime.utcnow()
            )
            self.db.add(sync_log)
            self.db.commit()
            
            # Buscar produtos na API
            api_data = self.fetch_user_products(ml_account_id)
            products_data = api_data.get("results", [])
            
            items_processed = 0
            items_created = 0
            items_updated = 0
            items_errors = 0
            
            token = self.get_active_token(ml_account_id)
            
            for item_id in products_data:
                try:
                    # Buscar detalhes completos do produto
                    product_details = self.fetch_product_details(item_id, token)
                    
                    # Verificar se produto já existe
                    existing_product = self.db.query(MLProduct).filter(
                        MLProduct.ml_item_id == item_id
                    ).first()
                    
                    if existing_product:
                        # Atualizar produto existente
                        self._update_product_from_api(existing_product, product_details)
                        items_updated += 1
                    else:
                        # Criar novo produto
                        self._create_product_from_api(
                            product_details, ml_account_id, company_id
                        )
                        items_created += 1
                    
                    items_processed += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao processar produto {item_id}: {e}")
                    items_errors += 1
                    continue
            
            # Atualizar log de sincronização
            sync_log.sync_status = "success" if items_errors == 0 else "partial"
            sync_log.items_processed = items_processed
            sync_log.items_created = items_created
            sync_log.items_updated = items_updated
            sync_log.items_errors = items_errors
            sync_log.completed_at = datetime.utcnow()
            
            self.db.commit()
            
            return {
                "success": True,
                "items_processed": items_processed,
                "items_created": items_created,
                "items_updated": items_updated,
                "items_errors": items_errors,
                "sync_log_id": sync_log.id
            }
            
        except Exception as e:
            logger.error(f"Erro na sincronização incremental: {e}")
            
            # Atualizar log com erro
            if 'sync_log' in locals():
                sync_log.sync_status = "error"
                sync_log.error_message = str(e)
                sync_log.completed_at = datetime.utcnow()
                self.db.commit()
            
            raise Exception(f"Erro na sincronização: {e}")
    
    def _create_product_from_api(self, api_data: Dict, ml_account_id: int, company_id: int):
        """Cria produto a partir dos dados da API"""
        try:
            # Mapear dados da API para o modelo
            product = MLProduct(
                company_id=company_id,
                ml_account_id=ml_account_id,
                ml_item_id=api_data.get("id"),
                user_product_id=api_data.get("user_product_id"),
                family_id=api_data.get("family_id"),
                family_name=api_data.get("family_name"),
                title=api_data.get("title"),
                subtitle=api_data.get("subtitle"),
                price=str(api_data.get("price", 0)),
                base_price=str(api_data.get("base_price", 0)),
                original_price=str(api_data.get("original_price", 0)) if api_data.get("original_price") else None,
                currency_id=api_data.get("currency_id"),
                available_quantity=api_data.get("available_quantity", 0),
                sold_quantity=api_data.get("sold_quantity", 0),
                initial_quantity=api_data.get("initial_quantity", 0),
                category_id=api_data.get("category_id"),
                condition=api_data.get("condition"),
                listing_type_id=api_data.get("listing_type_id"),
                buying_mode=api_data.get("buying_mode"),
                permalink=api_data.get("permalink"),
                thumbnail=api_data.get("thumbnail"),
                secure_thumbnail=api_data.get("secure_thumbnail"),
                pictures=self._extract_pictures(api_data.get("pictures", [])),
                status=self._map_status(api_data.get("status")),
                sub_status=api_data.get("sub_status", []),
                start_time=self._parse_datetime(api_data.get("start_time")),
                stop_time=self._parse_datetime(api_data.get("stop_time")),
                end_time=self._parse_datetime(api_data.get("end_time")),
                seller_id=str(api_data.get("seller_id", "")),
                seller_custom_field=api_data.get("seller_custom_field"),
                seller_sku=self._extract_seller_sku(api_data.get("attributes", [])),
                catalog_product_id=api_data.get("catalog_product_id"),
                catalog_listing=api_data.get("catalog_listing", False),
                attributes=api_data.get("attributes", []),
                variations=api_data.get("variations", []),
                tags=api_data.get("tags", []),
                shipping=api_data.get("shipping", {}),
                free_shipping=api_data.get("shipping", {}).get("free_shipping", False),
                differential_pricing=api_data.get("differential_pricing"),
                deal_ids=api_data.get("deal_ids", []),
                last_sync=datetime.utcnow(),
                last_ml_update=self._parse_datetime(api_data.get("last_updated"))
            )
            
            self.db.add(product)
            self.db.commit()
            
            logger.info(f"Produto criado: {product.ml_item_id} - {product.title}")
            
        except Exception as e:
            logger.error(f"Erro ao criar produto: {e}")
            raise
    
    def _update_product_from_api(self, product: MLProduct, api_data: Dict):
        """Atualiza produto existente com dados da API"""
        try:
            # Atualizar campos que podem mudar
            product.title = api_data.get("title", product.title)
            product.price = str(api_data.get("price", product.price))
            product.available_quantity = api_data.get("available_quantity", product.available_quantity)
            product.sold_quantity = api_data.get("sold_quantity", product.sold_quantity)
            product.status = self._map_status(api_data.get("status"), product.status)
            product.sub_status = api_data.get("sub_status", product.sub_status)
            product.pictures = self._extract_pictures(api_data.get("pictures", []))
            product.attributes = api_data.get("attributes", product.attributes)
            product.variations = api_data.get("variations", product.variations)
            product.tags = api_data.get("tags", product.tags)
            product.shipping = api_data.get("shipping", product.shipping)
            product.free_shipping = api_data.get("shipping", {}).get("free_shipping", product.free_shipping)
            product.last_sync = datetime.utcnow()
            product.last_ml_update = self._parse_datetime(api_data.get("last_updated"))
            
            self.db.commit()
            
            logger.info(f"Produto atualizado: {product.ml_item_id} - {product.title}")
            
        except Exception as e:
            logger.error(f"Erro ao atualizar produto: {e}")
            raise
    
    def _extract_pictures(self, pictures_data: List[Dict]) -> List[Dict]:
        """Extrai URLs das imagens"""
        if not pictures_data:
            return []
        
        return [
            {
                "id": pic.get("id"),
                "url": pic.get("url"),
                "secure_url": pic.get("secure_url"),
                "size": pic.get("size"),
                "max_size": pic.get("max_size"),
                "quality": pic.get("quality")
            }
            for pic in pictures_data
        ]
    
    def _extract_seller_sku(self, attributes: List[Dict]) -> Optional[str]:
        """Extrai SKU do vendedor dos atributos"""
        for attr in attributes:
            if attr.get("id") == "SELLER_SKU":
                return attr.get("value_name")
        return None
    
    def _map_status(self, status: str, default_status: MLProductStatus = MLProductStatus.ACTIVE) -> MLProductStatus:
        """Mapeia status da API para enum"""
        status_map = {
            "active": MLProductStatus.ACTIVE,
            "paused": MLProductStatus.PAUSED,
            "closed": MLProductStatus.CLOSED,
            "under_review": MLProductStatus.UNDER_REVIEW,
            "inactive": MLProductStatus.INACTIVE
        }
        return status_map.get(status, default_status)
    
    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Converte string de data para datetime"""
        if not date_str:
            return None
        
        try:
            # Formato ISO 8601 do ML
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None
    
    def get_products_by_account(self, ml_account_id: int, company_id: int, 
                               status: Optional[str] = None, limit: int = 50, offset: int = 0) -> Dict:
        """Busca produtos por conta ML"""
        try:
            query = self.db.query(MLProduct).filter(
                and_(
                    MLProduct.ml_account_id == ml_account_id,
                    MLProduct.company_id == company_id
                )
            )
            
            if status:
                query = query.filter(MLProduct.status == status)
            
            total = query.count()
            products = query.offset(offset).limit(limit).all()
            
            return {
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
                        "condition": p.condition,
                        "thumbnail": p.thumbnail,
                        "permalink": p.permalink,
                        "last_sync": p.last_sync.isoformat() if p.last_sync else None,
                        "created_at": p.created_at.isoformat() if p.created_at else None
                    }
                    for p in products
                ],
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar produtos: {e}")
            raise Exception(f"Erro ao buscar produtos: {e}")
    
    def get_sync_history(self, ml_account_id: int, company_id: int, limit: int = 20) -> List[Dict]:
        """Busca histórico de sincronizações"""
        try:
            sync_logs = self.db.query(MLProductSync).filter(
                and_(
                    MLProductSync.ml_account_id == ml_account_id,
                    MLProductSync.company_id == company_id
                )
            ).order_by(MLProductSync.started_at.desc()).limit(limit).all()
            
            return [
                {
                    "id": log.id,
                    "sync_type": log.sync_type,
                    "sync_status": log.sync_status,
                    "items_processed": log.items_processed,
                    "items_created": log.items_created,
                    "items_updated": log.items_updated,
                    "items_errors": log.items_errors,
                    "error_message": log.error_message,
                    "started_at": log.started_at.isoformat() if log.started_at else None,
                    "completed_at": log.completed_at.isoformat() if log.completed_at else None
                }
                for log in sync_logs
            ]
            
        except Exception as e:
            logger.error(f"Erro ao buscar histórico de sincronização: {e}")
            raise Exception(f"Erro ao buscar histórico: {e}")
