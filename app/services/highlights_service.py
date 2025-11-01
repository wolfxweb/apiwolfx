"""
Service para buscar produtos mais vendidos usando a API /highlights do Mercado Livre
"""
import logging
import requests
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class HighlightsService:
    """Service para buscar mais vendidos do Mercado Livre"""
    
    def __init__(self, db: Session):
        self.db = db
        self.base_url = "https://api.mercadolibre.com"
        self.headers = {
            "Accept": "application/json"
        }
    
    def _get_site_id(self, company_id: int) -> str:
        """Busca site_id padrão da empresa"""
        try:
            from app.models.saas_models import MLAccount, MLAccountStatus
            account = self.db.query(MLAccount).filter(
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).first()
            return account.site_id if account else "MLB"
        except:
            return "MLB"
    
    def _get_access_token(self, user_id: int) -> Optional[str]:
        """Busca um token válido do usuário para usar na API"""
        try:
            from app.services.token_manager import TokenManager
            token_manager = TokenManager(self.db)
            return token_manager.get_valid_token(user_id)
        except Exception as e:
            logger.error(f"Erro ao buscar token: {e}")
            return None
    
    def get_category_highlights(self, category_id: str, user_id: int, 
                               attribute: Optional[str] = None, 
                               attribute_value: Optional[str] = None) -> Dict:
        """
        Busca os 20 mais vendidos de uma categoria
        
        Args:
            category_id: ID da categoria
            user_id: ID do usuário logado
            attribute: Atributo para filtrar (ex: BRAND)
            attribute_value: Valor do atributo (ex: ID da marca)
            
        Returns:
            Dict com lista de mais vendidos
        """
        try:
            # Buscar site_id e company_id do usuário
            from app.models.saas_models import MLAccount, MLAccountStatus, User
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or not user.company_id:
                return {
                    "success": False,
                    "error": "Usuário não possui empresa associada",
                    "highlights": []
                }
            
            site_id = self._get_site_id(user.company_id)
            access_token = self._get_access_token(user_id)
            
            if not access_token:
                return {
                    "success": False,
                    "error": "Token de acesso necessário",
                    "highlights": []
                }
            
            # Construir URL
            url = f"{self.base_url}/highlights/{site_id}/category/{category_id}"
            
            # Adicionar parâmetros de atributo se fornecidos
            params = {}
            if attribute and attribute_value:
                params["attribute"] = attribute
                params["attributeValue"] = attribute_value
            
            # Headers com autenticação
            headers = {
                **self.headers,
                "Authorization": f"Bearer {access_token}"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 404:
                return {
                    "success": False,
                    "error": "Categoria não possui listagem de mais vendidos",
                    "highlights": []
                }
            
            if response.status_code != 200:
                error_msg = response.text[:500] if hasattr(response, 'text') else str(response.status_code)
                logger.error(f"Erro ao buscar mais vendidos: {response.status_code} - {error_msg}")
                return {
                    "success": False,
                    "error": f"Erro na API: {response.status_code}",
                    "highlights": []
                }
            
            data = response.json()
            
            # Buscar detalhes dos itens/produtos
            highlights = []
            content = data.get("content", [])
            
            logger.info(f"Processando {len(content)} itens/produtos...")
            
            # Processar em lote para melhor performance
            import concurrent.futures
            
            def fetch_details(item_data):
                item_id = item_data.get("id", "")
                position = item_data.get("position", 0)
                item_type = item_data.get("type", "ITEM")  # ITEM ou PRODUCT ou USER_PRODUCT
                
                try:
                    details = self._get_item_details(item_id, item_type, access_token)
                    return {
                        "id": item_id,
                        "position": position,
                        "type": item_type,
                        "title": details.get("title", ""),
                        "price": details.get("price", 0),
                        "currency_id": details.get("currency_id", "BRL"),
                        "thumbnail": details.get("thumbnail", ""),
                        "permalink": details.get("permalink", ""),
                        "condition": details.get("condition", "new"),
                        "sold_quantity": details.get("sold_quantity", 0),
                        "available_quantity": details.get("available_quantity", 0),
                        "category_id": details.get("category_id", ""),
                        "category_name": details.get("category_name", ""),
                        "seller_id": details.get("seller_id", ""),
                        "seller_nickname": details.get("seller_nickname", "")
                    }
                except Exception as e:
                    logger.warning(f"Erro ao buscar detalhes de {item_type} {item_id}: {e}")
                    return {
                        "id": item_id,
                        "position": position,
                        "type": item_type,
                        "title": "",
                        "price": 0,
                        "currency_id": "BRL",
                        "thumbnail": "",
                        "permalink": "",
                        "condition": "new",
                        "sold_quantity": 0,
                        "available_quantity": 0,
                        "category_id": "",
                        "category_name": "",
                        "seller_id": "",
                        "seller_nickname": ""
                    }
            
            # Primeiro, para produtos catalogados, precisamos obter os itens associados
            # Separar por tipo
            product_ids = [item.get("id", "") for item in content if item.get("type") == "PRODUCT" and item.get("id", "")]
            item_ids = [item.get("id", "") for item in content if item.get("type") == "ITEM" and item.get("id", "") and not item.get("id", "").startswith("MLBU")]
            
            batch_details = {}
            catalog_product_details = {}
            
            # Buscar detalhes dos produtos catalogados
            if product_ids:
                logger.info(f"Buscando detalhes para {len(product_ids)} produtos catalogados...")
                catalog_product_details = self._get_catalog_products_items(product_ids, access_token)
            
            # Buscar detalhes dos itens normais
            if item_ids:
                batch_details = self._get_items_batch(item_ids, access_token, site_id)
            
            # Se a busca funcionou, usar esses dados
            if batch_details or catalog_product_details:
                highlights = []
                for item in content:
                    item_id = item.get("id", "")
                    position = item.get("position", 0)
                    item_type = item.get("type", "ITEM")
                    
                    # Buscar detalhes do lote ou dos produtos catalogados
                    details = {}
                    if item_type == "PRODUCT" and item_id in catalog_product_details:
                        # Para produtos catalogados, usar os detalhes já obtidos
                        details = catalog_product_details[item_id]
                    elif item_type == "ITEM" and item_id in batch_details:
                        # Para itens normais, usar os detalhes do lote
                        details = batch_details[item_id]
                    
                    if not details or not details.get("title"):
                        # Se não encontrou, buscar individualmente
                        logger.debug(f"Buscando individualmente {item_type} {item_id}")
                        details = self._get_item_details(item_id, item_type, access_token)
                    
                    highlights.append({
                        "id": item_id,
                        "position": position,
                        "type": item_type,
                        "title": details.get("title", ""),
                        "price": details.get("price", 0),
                        "currency_id": details.get("currency_id", "BRL"),
                        "thumbnail": details.get("thumbnail", ""),
                        "permalink": details.get("permalink", ""),
                        "condition": details.get("condition", "new"),
                        "sold_quantity": details.get("sold_quantity", 0),
                        "available_quantity": details.get("available_quantity", 0),
                        "category_id": details.get("category_id", ""),
                        "category_name": details.get("category_name", ""),
                        "seller_id": details.get("seller_id", ""),
                        "seller_nickname": details.get("seller_nickname", "")
                    })
            else:
                # Fallback: buscar individualmente em paralelo
                logger.info("Usando busca individual em paralelo...")
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    futures = [executor.submit(fetch_details, item) for item in content]
                    highlights = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # Ordenar por posição novamente (pode ter mudado ordem devido ao paralelismo)
            highlights.sort(key=lambda x: x.get("position", 999))
            
            logger.info(f"Detalhes obtidos para {len([h for h in highlights if h.get('title')])} de {len(highlights)} produtos")
            
            return {
                "success": True,
                "query_data": data.get("query_data", {}),
                "highlights": highlights,
                "total": len(highlights)
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar mais vendidos da categoria: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "highlights": []
            }
    
    def _get_item_details(self, item_id: str, item_type: str, access_token: str) -> Dict:
        """Busca detalhes de um item ou produto"""
        try:
            headers = {
                **self.headers,
                "Authorization": f"Bearer {access_token}"
            }
            
            # Para USER_PRODUCT, tentar buscar primeiro o item associado
            if item_type == "USER_PRODUCT":
                # USER_PRODUCT pode precisar ser buscado de forma diferente
                # Tentar primeiro como item normal
                url = f"{self.base_url}/items/{item_id}"
                logger.debug(f"Buscando detalhes de USER_PRODUCT {item_id} via {url}")
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    return self._parse_item_response(response.json())
                else:
                    # USER_PRODUCT pode não estar disponível via API pública
                    logger.warning(f"USER_PRODUCT {item_id} não encontrado, retornando dados mínimos")
                    return self._empty_details()
            
            # Tentar primeiro como produto catalogado se for tipo PRODUCT
            if item_type == "PRODUCT":
                # Para produtos catalogados, buscar o primeiro item ativo
                url = f"{self.base_url}/products/{item_id}/items"
                logger.debug(f"Buscando itens do produto catalogado {item_id} via {url}")
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    items_data = response.json()
                    # Pegar o primeiro item ativo ou disponível
                    results = items_data.get("results", [])
                    if results:
                        # Filtrar itens ativos (status = active)
                        active_items = [item for item in results if item.get("status") == "active"]
                        if active_items:
                            # Pegar o primeiro item ativo
                            item_data = active_items[0]
                            return self._parse_item_response(item_data)
                        elif results:
                            # Se não tem ativos, pegar o primeiro disponível
                            return self._parse_item_response(results[0])
                
                # Se não encontrou itens, tentar buscar informações do produto diretamente
                url = f"{self.base_url}/products/{item_id}"
                logger.debug(f"Tentando buscar informações do produto {item_id} via {url}")
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    seller = data.get("seller", {})
                    seller_id = ""
                    seller_nickname = ""
                    if isinstance(seller, dict):
                        seller_id = str(seller.get("id", ""))
                        seller_nickname = seller.get("nickname", "")
                    
                    return {
                        "title": data.get("title", ""),
                        "price": float(data.get("price", 0)),
                        "currency_id": data.get("currency_id", "BRL"),
                        "thumbnail": data.get("thumbnail", ""),
                        "permalink": data.get("permalink", ""),
                        "condition": data.get("condition", "new"),
                        "sold_quantity": int(data.get("sold_quantity", 0)),
                        "available_quantity": int(data.get("available_quantity", 0)),
                        "category_id": data.get("category_id", ""),
                        "category_name": "",
                        "seller_id": seller_id,
                        "seller_nickname": seller_nickname
                    }
            
            # Para ITEM ou fallback, buscar como item
            url = f"{self.base_url}/items/{item_id}"
            logger.debug(f"Buscando detalhes de {item_type} {item_id} via {url}")
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                return self._parse_item_response(response.json())
            else:
                error_msg = response.text[:200] if hasattr(response, 'text') else str(response.status_code)
                logger.warning(f"Erro ao buscar detalhes de {item_id}: {response.status_code} - {error_msg}")
                
                # Tentar buscar como item mesmo se for PRODUCT
                if item_type == "PRODUCT" and response.status_code == 404:
                    # Pode ser que seja um produto catalogado, tentar buscar via search
                    logger.debug(f"Tentando buscar produto {item_id} via search")
                    return self._get_product_via_search(item_id, access_token)
                
                return self._empty_details()
        except Exception as e:
            logger.warning(f"Erro ao buscar detalhes de {item_id}: {e}")
            return self._empty_details()
    
    def _parse_item_response(self, data: Dict) -> Dict:
        """Parseia resposta de item da API do ML"""
        seller = data.get("seller", {})
        seller_id = ""
        seller_nickname = ""
        if isinstance(seller, dict):
            seller_id = str(seller.get("id", ""))
            seller_nickname = seller.get("nickname", "")
        
        category_id = data.get("category_id", "")
        category_name = data.get("category_name", "")
        
        result = {
            "title": data.get("title", ""),
            "price": float(data.get("price", 0)),
            "currency_id": data.get("currency_id", "BRL"),
            "thumbnail": data.get("thumbnail", ""),
            "permalink": data.get("permalink", ""),
            "condition": data.get("condition", "new"),
            "sold_quantity": int(data.get("sold_quantity", 0)),
            "available_quantity": int(data.get("available_quantity", 0)),
            "category_id": category_id,
            "category_name": category_name,
            "seller_id": seller_id,
            "seller_nickname": seller_nickname
        }
        
        return result
    
    def _empty_details(self) -> Dict:
        """Retorna estrutura vazia de detalhes"""
        return {
            "title": "",
            "price": 0,
            "currency_id": "BRL",
            "thumbnail": "",
            "permalink": "",
            "condition": "new",
            "sold_quantity": 0,
            "available_quantity": 0,
            "category_id": "",
            "category_name": "",
            "seller_id": "",
            "seller_nickname": ""
        }
    
    def _get_catalog_products_items(self, product_ids: List[str], access_token: str) -> Dict[str, Dict]:
        """Busca os itens e detalhes dos produtos catalogados"""
        product_details = {}
        
        for product_id in product_ids:
            try:
                # Primeiro, buscar informações do produto catalogado
                prod_url = f"{self.base_url}/products/{product_id}"
                headers = {
                    **self.headers,
                    "Authorization": f"Bearer {access_token}"
                }
                
                prod_response = requests.get(prod_url, headers=headers, timeout=15)
                
                if prod_response.status_code == 200:
                    prod_data = prod_response.json()
                    
                    # Buscar itens para obter preço e outros dados
                    items_url = f"{self.base_url}/products/{product_id}/items"
                    items_response = requests.get(items_url, headers=headers, timeout=15)
                    
                    price = 0
                    sold_quantity = 0
                    available_quantity = 0
                    item_id = ""
                    seller_id = ""
                    seller_nickname = ""
                    
                    if items_response.status_code == 200:
                        items_data = items_response.json()
                        results = items_data.get("results", [])
                        if results:
                            # Pegar o primeiro item ativo
                            active_items = [item for item in results if item.get("status") == "active"]
                            item = active_items[0] if active_items else results[0]
                            
                            price = float(item.get("price", 0))
                            item_id = item.get("item_id", "")
                            seller_id = str(item.get("seller_id", ""))
                    
                    # Extrair seller info do item (se disponível) ou do produto
                    seller = prod_data.get("seller", {})
                    if isinstance(seller, dict):
                        seller_id = str(seller.get("id", seller_id))
                        seller_nickname = seller.get("nickname", "")
                    
                    # Produto catalogado usa 'name' ao invés de 'title'
                    title = prod_data.get("name", "") or prod_data.get("title", "")
                    
                    # Extrair thumbnail das pictures (produto catalogado não tem thumbnail direto)
                    thumbnail = ""
                    pictures = prod_data.get("pictures", [])
                    if pictures and len(pictures) > 0:
                        # Pegar a URL da primeira imagem
                        thumbnail = pictures[0].get("url", "")
                    
                    # Construir permalink se não vier
                    permalink = prod_data.get("permalink", "")
                    if not permalink:
                        permalink = f"https://produto.mercadolivre.com.br/{product_id}"
                    
                    # Montar detalhes completos
                    product_details[product_id] = {
                        "title": title,
                        "price": price,
                        "currency_id": prod_data.get("currency_id", "BRL"),
                        "thumbnail": thumbnail,
                        "permalink": permalink,
                        "condition": prod_data.get("condition", "new"),
                        "sold_quantity": int(prod_data.get("sold_quantity", sold_quantity)),
                        "available_quantity": available_quantity,
                        "category_id": prod_data.get("category_id", ""),
                        "category_name": "",
                        "seller_id": seller_id,
                        "seller_nickname": seller_nickname,
                        "_item_id": item_id  # Guardar item_id caso precise depois
                    }
                    
            except Exception as e:
                logger.warning(f"Erro ao buscar detalhes do produto {product_id}: {e}")
        
        logger.info(f"Detalhes obtidos para {len(product_details)} produtos catalogados")
        return product_details
    
    def _get_items_batch(self, item_ids: List[str], access_token: str, site_id: str) -> Dict[str, Dict]:
        """Busca múltiplos itens em lote usando o endpoint /items"""
        try:
            # A API do ML permite buscar até 20 itens por vez usando ?ids=ID1,ID2,...
            # Dividir em lotes de 20
            batch_size = 20
            all_details = {}
            
            for i in range(0, len(item_ids), batch_size):
                batch = item_ids[i:i+batch_size]
                ids_param = ",".join(batch)
                
                url = f"{self.base_url}/items"
                params = {"ids": ids_param}
                headers = {
                    **self.headers,
                    "Authorization": f"Bearer {access_token}"
                }
                
                logger.debug(f"Buscando lote de {len(batch)} itens via {url}")
                response = requests.get(url, params=params, headers=headers, timeout=20)
                
                if response.status_code == 200:
                    items = response.json()
                    for item in items:
                        if isinstance(item, dict) and "code" not in item:  # Sem erro
                            item_id = item.get("id", "")
                            if item_id:
                                all_details[item_id] = self._parse_item_response(item)
                        elif isinstance(item, dict) and item.get("status") == 404:
                            # Item não encontrado, ignorar
                            continue
                else:
                    logger.warning(f"Erro ao buscar lote: {response.status_code}")
            
            logger.info(f"Busca em lote retornou {len(all_details)} itens com sucesso")
            return all_details
            
        except Exception as e:
            logger.warning(f"Erro na busca em lote: {e}")
            return {}
    
    def _get_product_via_search(self, product_id: str, access_token: str) -> Dict:
        """Tenta buscar produto via search quando não encontrado diretamente"""
        try:
            # Buscar via search usando o ID do produto
            url = f"{self.base_url}/sites/MLB/search"
            params = {"ids": product_id}
            headers = {
                **self.headers,
                "Authorization": f"Bearer {access_token}"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("results") and len(data["results"]) > 0:
                    item = data["results"][0]
                    seller = item.get("seller", {})
                    return {
                        "title": item.get("title", ""),
                        "price": float(item.get("price", 0)),
                        "currency_id": item.get("currency_id", "BRL"),
                        "thumbnail": item.get("thumbnail", ""),
                        "permalink": item.get("permalink", ""),
                        "condition": item.get("condition", "new"),
                        "sold_quantity": int(item.get("sold_quantity", 0)),
                        "available_quantity": int(item.get("available_quantity", 0)),
                        "category_id": item.get("category_id", ""),
                        "category_name": "",
                        "seller_id": str(seller.get("id", "")) if isinstance(seller, dict) else "",
                        "seller_nickname": seller.get("nickname", "") if isinstance(seller, dict) else ""
                    }
        except Exception as e:
            logger.debug(f"Erro ao buscar produto via search: {e}")
        
        return {
            "title": "",
            "price": 0,
            "currency_id": "BRL",
            "thumbnail": "",
            "permalink": "",
            "condition": "new",
            "sold_quantity": 0,
            "available_quantity": 0,
            "category_id": "",
            "category_name": "",
            "seller_id": "",
            "seller_nickname": ""
        }
    
    def get_product_position(self, product_id: str, user_id: int) -> Dict:
        """
        Busca posicionamento de um produto específico
        
        Args:
            product_id: ID do produto
            user_id: ID do usuário logado
            
        Returns:
            Dict com posicionamento do produto
        """
        try:
            from app.models.saas_models import User
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or not user.company_id:
                return {
                    "success": False,
                    "error": "Usuário não possui empresa associada"
                }
            
            site_id = self._get_site_id(user.company_id)
            access_token = self._get_access_token(user_id)
            
            if not access_token:
                return {
                    "success": False,
                    "error": "Token de acesso necessário"
                }
            
            url = f"{self.base_url}/highlights/{site_id}/product/{product_id}"
            headers = {
                **self.headers,
                "Authorization": f"Bearer {access_token}"
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 404:
                return {
                    "success": False,
                    "error": "Produto não está na listagem de mais vendidos"
                }
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Erro na API: {response.status_code}"
                }
            
            data = response.json()
            
            return {
                "success": True,
                "dimension": data.get("dimension", ""),
                "category_id": data.get("id", ""),
                "category_name": data.get("label", ""),
                "position": data.get("position", 0)
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar posicionamento do produto: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_item_position(self, item_id: str, user_id: int) -> Dict:
        """
        Busca posicionamento de um item específico
        
        Args:
            item_id: ID do item
            user_id: ID do usuário logado
            
        Returns:
            Dict com posicionamento do item
        """
        try:
            from app.models.saas_models import User
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or not user.company_id:
                return {
                    "success": False,
                    "error": "Usuário não possui empresa associada"
                }
            
            site_id = self._get_site_id(user.company_id)
            access_token = self._get_access_token(user_id)
            
            if not access_token:
                return {
                    "success": False,
                    "error": "Token de acesso necessário"
                }
            
            url = f"{self.base_url}/highlights/{site_id}/item/{item_id}"
            headers = {
                **self.headers,
                "Authorization": f"Bearer {access_token}"
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 404:
                return {
                    "success": False,
                    "error": "Item não está na listagem de mais vendidos"
                }
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Erro na API: {response.status_code}"
                }
            
            data = response.json()
            
            return {
                "success": True,
                "dimension": data.get("dimension", ""),
                "category_id": data.get("id", ""),
                "category_name": data.get("label", ""),
                "position": data.get("position", 0)
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar posicionamento do item: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

