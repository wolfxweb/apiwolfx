"""
Serviço para gerenciar produtos do Mercado Livre
"""
import requests
import logging
import json
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
        """Obtém token ativo para a conta ML com renovação automática"""
        try:
            logger.info(f"Buscando token ativo para ml_account_id: {ml_account_id}")
            
            # Primeiro, tentar buscar token válido
            from sqlalchemy import text
            query = text("""
                SELECT access_token, refresh_token, expires_at
                FROM tokens 
                WHERE ml_account_id = :ml_account_id 
                AND is_active = true 
                AND expires_at > NOW()
                ORDER BY expires_at DESC
                LIMIT 1
            """)
            
            result = self.db.execute(query, {"ml_account_id": ml_account_id}).fetchone()
            
            if result:
                logger.info(f"Token encontrado: {result[0][:20]}..., expira em: {result[2]}")
                return result[0]
            
            # Se não encontrou token válido, tentar renovar com refresh token
            logger.info(f"Token expirado para ml_account_id: {ml_account_id}, tentando renovar...")
            
            # Buscar refresh token
            refresh_query = text("""
                SELECT refresh_token, access_token
                FROM tokens 
                WHERE ml_account_id = :ml_account_id 
                AND is_active = true 
                AND refresh_token IS NOT NULL
                ORDER BY expires_at DESC
                LIMIT 1
            """)
            
            refresh_result = self.db.execute(refresh_query, {"ml_account_id": ml_account_id}).fetchone()
            
            if refresh_result and refresh_result[0]:
                # Tentar renovar o token
                new_token = self._refresh_token(refresh_result[0], ml_account_id)
                if new_token:
                    return new_token
            
            logger.warning(f"Nenhum token ativo encontrado para ml_account_id: {ml_account_id}")
            return None
                
        except Exception as e:
            logger.error(f"Erro ao obter token ativo: {e}")
            return None
    
    def _refresh_token(self, refresh_token: str, ml_account_id: int) -> Optional[str]:
        """Tenta renovar token usando refresh token"""
        try:
            import requests
            from datetime import datetime, timedelta
            
            # Dados para renovar token
            data = {
                "grant_type": "refresh_token",
                "client_id": "6987936494418444",
                "client_secret": "puvG9Z7XBgICZg5yK3t0PAXAmnco18Tl",
                "refresh_token": refresh_token
            }
            
            headers = {
                "accept": "application/json",
                "content-type": "application/x-www-form-urlencoded"
            }
            
            response = requests.post("https://api.mercadolibre.com/oauth/token", data=data, headers=headers)
            
            if response.status_code == 200:
                token_data = response.json()
                logger.info(f"Token renovado com sucesso para ml_account_id: {ml_account_id}")
                
                # Desativar tokens antigos
                from sqlalchemy import text
                self.db.execute(text("""
                    UPDATE tokens 
                    SET is_active = false 
                    WHERE ml_account_id = :ml_account_id
                """), {"ml_account_id": ml_account_id})
                
                # Buscar user_id válido da tabela users
                user_query = text("SELECT id FROM users WHERE company_id = (SELECT company_id FROM ml_accounts WHERE id = :ml_account_id) LIMIT 1")
                user_result = self.db.execute(user_query, {"ml_account_id": ml_account_id}).fetchone()
                user_id = user_result[0] if user_result else 1
                
                # Criar novo token
                from app.models.saas_models import Token
                new_token = Token(
                    user_id=user_id,
                    ml_account_id=ml_account_id,
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token"),
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_in=token_data.get("expires_in", 21600),
                    scope=token_data.get("scope", ""),
                    expires_at=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 21600)),
                    is_active=True
                )
                
                self.db.add(new_token)
                self.db.commit()
                
                return token_data["access_token"]
            else:
                logger.error(f"Erro ao renovar token: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao renovar token: {e}")
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
            
            data = response.json()
            
            # Retornar no formato esperado
            return {
                "success": True,
                "products": data.get("results", []),
                "total": data.get("paging", {}).get("total", 0)
            }
            
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
            
            product_data = response.json()
            
            # Buscar informações adicionais (descriptions, warranty, etc.)
            additional_info = self._get_additional_product_info(ml_item_id, headers)
            product_data.update(additional_info)
            
            # Buscar preços promocionais
            price_info = self._get_promotional_prices(ml_item_id, headers)
            if price_info:
                product_data.update(price_info)
            
            return product_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao buscar detalhes do produto {ml_item_id}: {e}")
            raise Exception(f"Erro ao buscar produto: {e}")
    
    def import_bulk_products(self, ml_account_id: int, company_id: int, 
                            product_statuses: list, limit: int = 100) -> Dict:
        """Importa múltiplos produtos do Mercado Livre com filtro de status"""
        try:
            print(f"🔍 SERVICE DEBUG - ml_account_id: {ml_account_id}")
            print(f"🔍 SERVICE DEBUG - company_id: {company_id}")
            print(f"🔍 SERVICE DEBUG - product_statuses: {product_statuses}")
            print(f"🔍 SERVICE DEBUG - limit: {limit}")
            
            # Obter token ativo
            token = self.get_active_token(ml_account_id)
            if not token:
                print(f"❌ SERVICE ERROR - Token não encontrado para ml_account_id: {ml_account_id}")
                return {
                    "success": False,
                    "error": "Token não encontrado ou expirado"
                }
            
            print(f"✅ SERVICE DEBUG - Token encontrado: {token[:20]}...")
            
            # Buscar produtos do usuário com filtro de status
            print(f"🔍 SERVICE DEBUG - Chamando fetch_user_products...")
            products_data = self.fetch_user_products(ml_account_id, limit=limit)
            print(f"🔍 SERVICE DEBUG - Resultado fetch_user_products: {products_data}")
            
            if not products_data.get('success'):
                print(f"❌ SERVICE ERROR - fetch_user_products falhou: {products_data}")
                return {
                    "success": False,
                    "error": "Erro ao buscar produtos do usuário"
                }
            
            products = products_data.get('products', [])
            
            # Como a API já retorna apenas produtos ativos, não precisamos filtrar
            # Vamos usar todos os produtos retornados
            filtered_products = products
            
            if not filtered_products:
                return {
                    "success": False,
                    "error": f"Nenhum produto encontrado com os status selecionados: {', '.join(product_statuses)}"
                }
            
            # Processar produtos
            items_processed = 0
            items_created = 0
            items_updated = 0
            items_errors = 0
            
            for product_id in filtered_products:
                try:
                    # product_id já é o ID do produto (string)
                    
                    # Buscar detalhes completos do produto
                    product_details = self.fetch_product_details(product_id, token)
                    if not product_details:
                        items_errors += 1
                        continue
                    
                    # Verificar se produto já existe
                    existing_product = self.db.query(MLProduct).filter(
                        MLProduct.ml_item_id == product_id
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
                    logger.error(f"Erro ao processar produto {product_details.get('id', 'unknown')}: {e}")
                    items_errors += 1
                    continue
            
            self.db.commit()
            
            return {
                "success": True,
                "message": f"Importação concluída! {items_processed} produtos processados: {items_created} criados, {items_updated} atualizados, {items_errors} erros",
                "items_processed": items_processed,
                "items_created": items_created,
                "items_updated": items_updated,
                "items_errors": items_errors,
                "total_found": len(filtered_products)
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro na importação em massa: {e}")
            return {
                "success": False,
                "error": f"Erro na importação em massa: {str(e)}"
            }
    
    def import_single_product(self, ml_account_id: int, company_id: int, product_id: str) -> Dict:
        """Importa um produto específico do Mercado Livre"""
        try:
            # Obter token ativo
            token = self.get_active_token(ml_account_id)
            if not token:
                return {
                    "success": False,
                    "error": "Token não encontrado ou expirado"
                }
            
            # Buscar detalhes do produto na API do ML
            product_details = self.fetch_product_details(product_id, token)
            if not product_details:
                return {
                    "success": False,
                    "error": "Produto não encontrado no Mercado Livre"
                }
            
            # Verificar se produto já existe
            existing_product = self.db.query(MLProduct).filter(
                MLProduct.ml_item_id == product_id
            ).first()
            
            if existing_product:
                # Atualizar produto existente
                self._update_product_from_api(existing_product, product_details)
                message = f"Produto '{product_details.get('title', product_id)}' atualizado com sucesso!"
                action = "updated"
            else:
                # Criar novo produto
                new_product = self._create_product_from_api(
                    product_details, ml_account_id, company_id
                )
                message = f"Produto '{product_details.get('title', product_id)}' importado com sucesso!"
                action = "created"
            
            self.db.commit()
            
            # Extrair resumo das informações
            product_summary = self._extract_product_summary(product_details)
            
            return {
                "success": True,
                "message": message,
                "action": action,
                "product_id": product_details.get('id'),
                "title": product_details.get('title'),
                "info": product_summary
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao importar produto {product_id}: {e}")
            return {
                "success": False,
                "error": f"Erro ao importar produto: {str(e)}"
            }
    
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
            # Buscar informações adicionais da categoria
            category_info = self._get_category_info(api_data.get("category_id"))
            
            # Processar informações de envio
            shipping_info = self._process_shipping_info(api_data.get("shipping", {}))
            
            # Processar atributos completos
            processed_attributes = self._process_attributes(api_data.get("attributes", []))
            
            # Extrair descrição (pode vir em descriptions array)
            description_text = None
            descriptions = api_data.get("descriptions", [])
            if descriptions and len(descriptions) > 0:
                # Pegar a primeira descrição (geralmente é a principal)
                description_text = descriptions[0].get("plain_text") or descriptions[0].get("text")
            
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
                description=description_text,
                price=str(api_data.get("price", 0)),
                base_price=str(api_data.get("base_price", 0)),
                original_price=str(api_data.get("original_price", 0)) if api_data.get("original_price") else None,
                currency_id=api_data.get("currency_id"),
                sale_terms=api_data.get("sale_terms"),
                warranty=api_data.get("warranty"),
                video_id=api_data.get("video_id"),
                health=api_data.get("health"),
                domain_id=api_data.get("domain_id"),
                available_quantity=api_data.get("available_quantity", 0),
                sold_quantity=api_data.get("sold_quantity", 0),
                initial_quantity=api_data.get("initial_quantity", 0),
                category_id=api_data.get("category_id"),
                category_name=category_info.get("category_name"),
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
                attributes=processed_attributes,
                variations=api_data.get("variations", []),
                tags=api_data.get("tags", []),
                shipping=shipping_info,
                free_shipping=api_data.get("shipping", {}).get("free_shipping", False),
                differential_pricing=api_data.get("differential_pricing"),
                deal_ids=api_data.get("deal_ids", []),
                last_sync=datetime.utcnow(),
                last_ml_update=self._parse_datetime(api_data.get("last_updated"))
            )
            
            self.db.add(product)
            self.db.commit()
            
            logger.info(f"Produto criado com informações completas: {product.ml_item_id} - {product.title}")
            
        except Exception as e:
            logger.error(f"Erro ao criar produto: {e}")
            raise
    
    def _update_product_from_api(self, product: MLProduct, api_data: Dict):
        """Atualiza produto existente com dados da API"""
        try:
            # Buscar informações adicionais da categoria se mudou
            if api_data.get("category_id") != product.category_id:
                category_info = self._get_category_info(api_data.get("category_id"))
            else:
                category_info = {}
            
            # Processar informações de envio
            shipping_info = self._process_shipping_info(api_data.get("shipping", {}))
            
            # Processar atributos completos
            processed_attributes = self._process_attributes(api_data.get("attributes", []))
            
            # Extrair descrição (pode vir em descriptions array)
            description_text = None
            descriptions = api_data.get("descriptions", [])
            if descriptions and len(descriptions) > 0:
                description_text = descriptions[0].get("plain_text") or descriptions[0].get("text")
            
            # Atualizar campos que podem mudar
            product.title = api_data.get("title", product.title)
            product.subtitle = api_data.get("subtitle", product.subtitle)
            product.description = description_text if description_text else product.description
            product.price = str(api_data.get("price", product.price))
            product.available_quantity = api_data.get("available_quantity", product.available_quantity)
            product.sold_quantity = api_data.get("sold_quantity", product.sold_quantity)
            product.status = self._map_status(api_data.get("status"), product.status)
            product.sale_terms = api_data.get("sale_terms", product.sale_terms)
            product.warranty = api_data.get("warranty", product.warranty)
            product.video_id = api_data.get("video_id", product.video_id)
            product.health = api_data.get("health", product.health)
            product.domain_id = api_data.get("domain_id", product.domain_id)
            
            # Atualizar categoria se mudou
            if api_data.get("category_id") != product.category_id:
                product.category_id = api_data.get("category_id", product.category_id)
                product.category_name = category_info.get("category_name")
            product.sub_status = api_data.get("sub_status", product.sub_status)
            product.pictures = self._extract_pictures(api_data.get("pictures", []))
            product.attributes = processed_attributes
            product.variations = api_data.get("variations", product.variations)
            product.tags = api_data.get("tags", product.tags)
            product.shipping = shipping_info
            product.free_shipping = api_data.get("shipping", {}).get("free_shipping", product.free_shipping)
            product.last_sync = datetime.utcnow()
            product.last_ml_update = self._parse_datetime(api_data.get("last_updated"))
            
            self.db.commit()
            
            logger.info(f"Produto atualizado com informações completas: {product.ml_item_id} - {product.title}")
            
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
    
    def _get_category_info(self, category_id: str) -> Dict:
        """Busca informações completas da categoria"""
        try:
            if not category_id:
                return {}
                
            # Buscar informações da categoria via API
            response = requests.get(
                f"https://api.mercadolibre.com/categories/{category_id}",
                timeout=30
            )
            
            if response.status_code == 200:
                category_data = response.json()
                return {
                    "category_name": category_data.get("name"),
                    "category_path": self._extract_category_path(category_data),
                    "domain_id": category_data.get("domain_id"),
                    "attributes_count": len(category_data.get("attributes", [])),
                    "children_categories": len(category_data.get("children_categories", [])),
                    "settings": category_data.get("settings", {})
                }
            else:
                logger.warning(f"Não foi possível buscar categoria {category_id}: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Erro ao buscar categoria {category_id}: {e}")
            return {}
    
    def _extract_category_path(self, category_data: Dict) -> List[Dict]:
        """Extrai o caminho completo da categoria"""
        path = []
        current = category_data
        
        while current:
            path.append({
                "id": current.get("id"),
                "name": current.get("name")
            })
            current = current.get("parent")
            
        return path[::-1]  # Inverter para começar do nível mais alto
    
    def _process_shipping_info(self, shipping_data: Dict) -> Dict:
        """Processa informações completas de envio"""
        try:
            processed = {
                "mode": shipping_data.get("mode"),
                "logistic_type": shipping_data.get("logistic_type"),
                "free_shipping": shipping_data.get("free_shipping", False),
                "local_pick_up": shipping_data.get("local_pick_up", False),
                "store_pick_up": shipping_data.get("store_pick_up", False),
                "tags": shipping_data.get("tags", []),
                "dimensions": shipping_data.get("dimensions"),
                "methods": []
            }
            
            # Processar métodos de envio
            methods = shipping_data.get("methods", [])
            for method in methods:
                method_info = {
                    "id": method.get("id"),
                    "name": method.get("name"),
                    "type": method.get("type"),
                    "deliver_to": method.get("deliver_to"),
                    "company_name": method.get("company_name"),
                    "cost": method.get("cost"),
                    "currency_id": method.get("currency_id"),
                    "estimated_delivery_time": method.get("estimated_delivery_time")
                }
                processed["methods"].append(method_info)
            
            # Determinar tipo de envio principal
            if processed["logistic_type"] == "fulfillment":
                processed["shipping_type"] = "Full Mercado Livre"
            elif processed["logistic_type"] == "cross_docking":
                processed["shipping_type"] = "Mercado Envios"
            elif processed["logistic_type"] == "xd_drop_off":
                processed["shipping_type"] = "Agência"
            elif processed["logistic_type"] == "drop_off":
                processed["shipping_type"] = "Correios"
            else:
                processed["shipping_type"] = "Customizado"
            
            return processed
            
        except Exception as e:
            logger.error(f"Erro ao processar shipping: {e}")
            return shipping_data
    
    def _process_attributes(self, attributes: List[Dict]) -> List[Dict]:
        """Processa atributos completos com informações adicionais"""
        try:
            processed = []
            
            for attr in attributes:
                processed_attr = {
                    "id": attr.get("id"),
                    "name": attr.get("name"),
                    "value_id": attr.get("value_id"),
                    "value_name": attr.get("value_name"),
                    "value_struct": attr.get("value_struct"),
                    "attribute_group_id": attr.get("attribute_group_id"),
                    "attribute_group_name": attr.get("attribute_group_name"),
                    "tags": attr.get("tags", {}),
                    "values": attr.get("values", [])
                }
                
                # Adicionar informações extras se disponíveis
                if attr.get("value_struct"):
                    processed_attr["structured_value"] = self._process_structured_value(attr["value_struct"])
                
                # Identificar se é atributo de catálogo
                if attr.get("tags", {}).get("catalog_listing_required"):
                    processed_attr["is_catalog_required"] = True
                
                # Identificar atributos principais
                if attr.get("attribute_group_id") == "MAIN":
                    processed_attr["is_main_attribute"] = True
                
                processed.append(processed_attr)
            
            return processed
            
        except Exception as e:
            logger.error(f"Erro ao processar atributos: {e}")
            return attributes
    
    def _process_structured_value(self, value_struct: Dict) -> Dict:
        """Processa valores estruturados (ex: dimensões, peso)"""
        try:
            processed = {}
            
            for key, value in value_struct.items():
                if isinstance(value, dict) and "number" in value and "unit" in value:
                    processed[key] = {
                        "value": value["number"],
                        "unit": value["unit"],
                        "display": f"{value['number']} {value['unit']}"
                    }
                else:
                    processed[key] = value
            
            return processed
            
        except Exception as e:
            logger.error(f"Erro ao processar valor estruturado: {e}")
            return value_struct
    
    def _get_additional_product_info(self, product_id: str, headers: Dict) -> Dict:
        """Busca informações adicionais do produto (descriptions, warranty, etc.)"""
        try:
            additional_info = {}
            
            # Buscar descriptions
            descriptions = self._get_product_descriptions(product_id, headers)
            if descriptions:
                additional_info["descriptions"] = descriptions
            
            # Buscar warranty
            warranty = self._get_product_warranty(product_id, headers)
            if warranty:
                additional_info["warranty"] = warranty
            
            # Buscar questions
            questions = self._get_product_questions(product_id, headers)
            if questions:
                additional_info["questions"] = questions
            
            # Buscar reviews
            reviews = self._get_product_reviews(product_id, headers)
            if reviews:
                additional_info["reviews"] = reviews
            
            return additional_info
            
        except Exception as e:
            logger.error(f"Erro ao buscar informações adicionais do produto {product_id}: {e}")
            return {}
    
    def _get_promotional_prices(self, ml_item_id: str, headers: Dict) -> Dict:
        """Busca preços promocionais do produto"""
        try:
            prices_url = f"{self.base_url}/items/{ml_item_id}/prices"
            prices_response = requests.get(prices_url, headers=headers, timeout=10)
            
            if prices_response.status_code == 200:
                prices_data = prices_response.json()
                prices = prices_data.get("prices", [])
                
                # Encontrar preço promocional ativo no marketplace
                promotional_price = None
                standard_price = None
                
                for price in prices:
                    if price.get("type") == "promotion":
                        # Verificar se é para marketplace e está ativo
                        conditions = price.get("conditions", {})
                        context_restrictions = conditions.get("context_restrictions", [])
                        
                        if "channel_marketplace" in context_restrictions:
                            start_time = conditions.get("start_time")
                            end_time = conditions.get("end_time")
                            
                            # Se não tem horários definidos ou está no período ativo
                            if not start_time or not end_time or self._is_promotion_active(start_time, end_time):
                                promotional_price = price
                                break
                    
                    elif price.get("type") == "standard":
                        # Preço padrão como fallback
                        standard_price = price
                
                # Retornar preços processados
                result = {}
                if promotional_price:
                    result["price"] = promotional_price.get("amount")
                    result["base_price"] = promotional_price.get("regular_amount")
                    result["original_price"] = promotional_price.get("regular_amount")
                    result["is_promotional"] = True
                    logger.info(f"Produto {ml_item_id} com preço promocional: {promotional_price.get('amount')} (original: {promotional_price.get('regular_amount')})")
                elif standard_price:
                    result["price"] = standard_price.get("amount")
                    result["base_price"] = standard_price.get("amount")
                    result["original_price"] = None
                    result["is_promotional"] = False
                
                return result
            else:
                logger.warning(f"Erro ao buscar preços para {ml_item_id}: {prices_response.status_code}")
                
        except Exception as e:
            logger.warning(f"Erro ao buscar preços promocionais para {ml_item_id}: {e}")
        
        return {}
    
    def _is_promotion_active(self, start_time: str, end_time: str) -> bool:
        """Verifica se uma promoção está ativa"""
        try:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            
            if start_time:
                start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                if now < start:
                    return False
            
            if end_time:
                end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                if now > end:
                    return False
            
            return True
        except Exception as e:
            logger.warning(f"Erro ao verificar período de promoção: {e}")
            return True  # Em caso de erro, assume que está ativa
    
    def _get_product_descriptions(self, product_id: str, headers: Dict) -> Dict:
        """Busca descrição do produto"""
        try:
            response = requests.get(
                f"https://api.mercadolibre.com/items/{product_id}/description",  # SEM 'S' no final
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                desc_data = response.json()
                # Retornar como array para manter compatibilidade com código existente
                return [desc_data] if desc_data else []
            else:
                logger.warning(f"Não foi possível buscar description para {product_id}: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao buscar description do produto {product_id}: {e}")
            return []
    
    def _get_product_warranty(self, product_id: str, headers: Dict) -> Dict:
        """Busca informações de garantia do produto"""
        try:
            response = requests.get(
                f"https://api.mercadolibre.com/items/{product_id}/warranty",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Não foi possível buscar warranty para {product_id}: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Erro ao buscar warranty do produto {product_id}: {e}")
            return {}
    
    def _get_product_questions(self, product_id: str, headers: Dict) -> List[Dict]:
        """Busca perguntas do produto"""
        try:
            response = requests.get(
                f"https://api.mercadolibre.com/questions/search?item_id={product_id}&limit=10",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("questions", [])
            else:
                logger.warning(f"Não foi possível buscar questions para {product_id}: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao buscar questions do produto {product_id}: {e}")
            return []
    
    def _get_product_reviews(self, product_id: str, headers: Dict) -> Dict:
        """Busca avaliações do produto"""
        try:
            response = requests.get(
                f"https://api.mercadolibre.com/reviews/item/{product_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Não foi possível buscar reviews para {product_id}: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Erro ao buscar reviews do produto {product_id}: {e}")
            return {}
    
    def _extract_product_summary(self, product_data: Dict) -> Dict:
        """Extrai resumo das informações do produto"""
        try:
            # Extrair informações de categoria
            category_info = self._get_category_info(product_data.get("category_id"))
            
            # Extrair informações de shipping
            shipping_info = self._process_shipping_info(product_data.get("shipping", {}))
            
            # Extrair atributos principais
            main_attributes = []
            for attr in product_data.get("attributes", []):
                if attr.get("attribute_group_id") == "MAIN":
                    main_attributes.append({
                        "name": attr.get("name"),
                        "value": attr.get("value_name")
                    })
            
            # Extrair informações de catálogo
            is_catalog = product_data.get("catalog_listing", False)
            catalog_id = product_data.get("catalog_product_id")
            
            return {
                "title": product_data.get("title"),
                "price": product_data.get("price"),
                "currency": product_data.get("currency_id"),
                "status": product_data.get("status"),
                "condition": product_data.get("condition"),
                "category": {
                    "id": product_data.get("category_id"),
                    "name": category_info.get("category_name"),
                    "path": category_info.get("category_path")
                },
                "shipping": {
                    "type": shipping_info.get("shipping_type"),
                    "free_shipping": shipping_info.get("free_shipping"),
                    "logistic_type": shipping_info.get("logistic_type")
                },
                "catalog": {
                    "is_catalog": is_catalog,
                    "catalog_id": catalog_id
                },
                "main_attributes": main_attributes,
                "pictures_count": len(product_data.get("pictures", [])),
                "attributes_count": len(product_data.get("attributes", [])),
                "variations_count": len(product_data.get("variations", []))
            }
            
        except Exception as e:
            logger.error(f"Erro ao extrair resumo do produto: {e}")
            return {
                "title": product_data.get("title", "N/A"),
                "price": product_data.get("price", 0),
                "currency": product_data.get("currency_id", "N/A")
            }
    
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
                        "base_price": p.base_price,
                        "original_price": p.original_price,
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

    def get_listing_prices(self, product_id, price, category_id=None, listing_type_id=None, company_id=None, user_id=None):
        """Busca taxas de listagem do Mercado Livre com informações de frete"""
        try:
            logger.info(f"Buscando listing prices - product_id: {product_id}, price: {price}, category_id: {category_id}, company_id: {company_id}")
            
            if not company_id:
                logger.error("ID da empresa não fornecido")
                return {"success": False, "error": "ID da empresa é obrigatório"}
            
            # Usar TokenManager para obter token válido
            from app.services.token_manager import TokenManager
            token_manager = TokenManager(self.db)
            
            if not user_id:
                logger.error("user_id é obrigatório")
                return {"success": False, "error": "user_id é obrigatório"}
            
            logger.info(f"🔑 Usando TokenManager para user_id: {user_id}")
            token = token_manager.get_valid_token(user_id)
            logger.info(f"🔑 Token obtido: {token[:20] if token else 'None'}...")
            
            if not token:
                logger.error(f"Token não encontrado para company_id: {company_id}")
                return {"success": False, "error": "Token não encontrado"}
            
            # Construir URL da API
            url = f"https://api.mercadolibre.com/sites/MLB/listing_prices"
            params = {"price": price}
            
            if category_id:
                params["category_id"] = category_id
            if listing_type_id:
                params["listing_type_id"] = listing_type_id
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Buscando listing prices para produto {product_id} com preço {price}")
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Resposta da API listing prices: {json.dumps(data, indent=2)}")
                
                # Buscar informações de frete do produto
                shipping_info = self._get_product_shipping_info(product_id, token)
                logger.info(f"Informações de frete: {json.dumps(shipping_info, indent=2) if shipping_info else 'None'}")
                
                # Adicionar informações de frete aos dados das taxas
                if shipping_info:
                    # Se data é uma lista, iterar sobre cada item
                    if isinstance(data, list):
                        for fee_item in data:
                            if isinstance(fee_item, dict):
                                fee_item["shipping_info"] = shipping_info
                                # Calcular valores totais para cada tipo de anúncio
                                fee_item = self._calculate_total_fees(fee_item, price)
                                logger.info(f"Fee item após cálculo: {json.dumps(fee_item, indent=2)}")
                    # Se data é um objeto único, adicionar diretamente
                    elif isinstance(data, dict):
                        data["shipping_info"] = shipping_info
                        data = self._calculate_total_fees(data, price)
                        logger.info(f"Fee data após cálculo: {json.dumps(data, indent=2)}")
                
                logger.info(f"Listing prices encontrados: {len(data) if isinstance(data, list) else 1} tipos de anúncio")
                return {"success": True, "data": data}
            else:
                logger.error(f"Erro na API listing prices: {response.status_code} - {response.text}")
                return {"success": False, "error": f"Erro na API: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Erro ao buscar taxas de listagem: {e}")
            return {"success": False, "error": str(e)}
    
    def _calculate_total_fees(self, fee_data, product_price):
        """Calcula valores totais das taxas para um tipo de anúncio"""
        try:
            sale_fee_details = fee_data.get("sale_fee_details", {})
            shipping_info = fee_data.get("shipping_info", {})
            
            # Converter product_price para float se for string
            try:
                product_price = float(product_price) if product_price else 0
            except (ValueError, TypeError):
                logger.warning(f"Erro ao converter preço do produto: {product_price}")
                product_price = 0
            
            # Extrair valores das taxas e converter para float
            fixed_fee = float(sale_fee_details.get("fixed_fee", 0) or 0)
            percentage_fee = float(sale_fee_details.get("percentage_fee", 0) or 0)
            financing_fee = float(sale_fee_details.get("financing_add_on_fee", 0) or 0)
            listing_fee = float(fee_data.get("listing_fee_amount", 0) or 0)
            
            # Calcular valores em reais
            percentage_amount = (product_price * percentage_fee) / 100 if percentage_fee > 0 else 0
            financing_amount = (product_price * financing_fee) / 100 if financing_fee > 0 else 0
            
            # Calcular totais
            total_sale_fees = fixed_fee + percentage_amount + financing_amount
            total_marketplace_fees = total_sale_fees + listing_fee
            
            # Adicionar custo de frete
            shipping_cost = float(shipping_info.get("shipping_cost", 0) or 0)
            total_cost_with_shipping = total_marketplace_fees + shipping_cost
            
            # Adicionar informações calculadas
            fee_data["calculated_fees"] = {
                "fixed_fee_amount": fixed_fee,
                "percentage_fee_amount": percentage_amount,
                "financing_fee_amount": financing_amount,
                "total_sale_fees": total_sale_fees,
                "total_marketplace_fees": total_marketplace_fees,
                "shipping_cost": shipping_cost,
                "total_cost_with_shipping": total_cost_with_shipping,
                "profit_margin_percentage": ((product_price - total_cost_with_shipping) / product_price * 100) if product_price > 0 else 0,
                "net_profit": product_price - total_cost_with_shipping
            }
            
            return fee_data
            
        except Exception as e:
            logger.error(f"Erro ao calcular taxas totais: {e}")
            return fee_data
    
    def _get_product_shipping_info(self, product_id, token):
        """Busca informações de frete do produto na API do ML"""
        try:
            url = f"https://api.mercadolibre.com/items/{product_id}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Buscando informações de frete para produto {product_id}")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                product_data = response.json()
                shipping_data = product_data.get("shipping", {})
                
                # Calcular custo de frete baseado no modo e dados do produto
                shipping_cost = self._calculate_shipping_cost(shipping_data, product_data)
                
                shipping_info = {
                    "free_shipping": shipping_data.get("free_shipping", False),
                    "mode": shipping_data.get("mode"),
                    "logistic_type": shipping_data.get("logistic_type"),
                    "local_pick_up": shipping_data.get("local_pick_up", False),
                    "store_pick_up": shipping_data.get("store_pick_up", False),
                    "tags": shipping_data.get("tags", []),
                    "methods": shipping_data.get("methods", []),
                    "shipping_cost": shipping_cost
                }
                
                logger.info(f"Informações de frete encontradas: {shipping_info}")
                return shipping_info
            else:
                logger.warning(f"Erro ao buscar informações de frete do produto {product_id}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar informações de frete: {e}")
            return None
    
    def _calculate_shipping_cost(self, shipping_data, product_data):
        """Calcula o custo de frete baseado nos dados do produto"""
        try:
            # Se é frete grátis, retorna 0
            if shipping_data.get("free_shipping", False):
                return 0
            
            mode = shipping_data.get("mode")
            logistic_type = shipping_data.get("logistic_type")
            price = product_data.get("price", 0)
            tags = shipping_data.get("tags", [])
            
            # Verificar se tem mandatory_free_shipping (frete grátis obrigatório)
            if "mandatory_free_shipping" in tags:
                return 0
            
            # Calcular custo baseado no modo e tipo logístico
            if mode == "me2":
                # Mercado Envios 2 - custos baseados na documentação ML
                if logistic_type == "cross_docking":
                    # Cross Docking - custos mais baixos
                    if price <= 79:
                        return 0  # Frete grátis até R$ 79
                    elif price <= 150:
                        return 8.90  # Frete econômico
                    else:
                        return 12.90  # Frete padrão
                        
                elif logistic_type == "drop_off":
                    # Drop Off - custos intermediários
                    if price <= 99:
                        return 0  # Frete grátis até R$ 99
                    elif price <= 200:
                        return 10.90
                    else:
                        return 15.90
                        
                elif logistic_type == "fulfillment":
                    # Fulfillment - custos mais altos mas mais rápido
                    if price <= 149:
                        return 0  # Frete grátis até R$ 149
                    elif price <= 300:
                        return 12.90
                    else:
                        return 18.90
                        
                elif logistic_type == "self_service":
                    # Envios Flex - custos variáveis
                    if price <= 79:
                        return 0
                    elif price <= 150:
                        return 7.90
                    else:
                        return 11.90
                else:
                    # Valor padrão para ME2
                    return 12.90
                    
            elif mode == "me1":
                # Mercado Envios 1 - valores fixos mais baixos
                if price <= 79:
                    return 0  # Frete grátis até R$ 79
                return 8.90  # Valor fixo ME1
                
            elif mode == "custom":
                # Frete customizado - valor estimado baseado no preço
                if price <= 100:
                    return 15.00
                elif price <= 300:
                    return 20.00
                else:
                    return 25.00
                    
            elif mode == "not_specified":
                # Sem modo especificado - valor estimado conservador
                return 12.00
                
            else:
                # Outros modos - valor estimado
                return 12.00
                
        except Exception as e:
            logger.error(f"Erro ao calcular custo de frete: {e}")
            return 12.00  # Valor padrão em caso de erro

    def get_shipping_options(self, product_id, zip_code, ml_account_id=None):
        """Busca opções de envio para um produto"""
        try:
            if not ml_account_id:
                return {"success": False, "error": "ID da conta ML é obrigatório"}
                
            token = self.get_active_token(ml_account_id)
            if not token:
                return {"success": False, "error": "Token não encontrado"}
            
            url = f"https://api.mercadolibre.com/items/{product_id}/shipping_options"
            params = {"zip_code": zip_code}
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return {"success": True, "data": data}
            else:
                return {"success": False, "error": f"Erro na API: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Erro ao buscar opções de envio: {e}")
            return {"success": False, "error": str(e)}
