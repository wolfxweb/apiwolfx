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
                        "seller_nickname": details.get("seller_nickname", ""),
                        "visits": details.get("visits", 0)
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
                        "seller_nickname": "",
                        "visits": 0
                    }
            
            # Primeiro, para produtos catalogados, precisamos obter os itens associados
            # Separar por tipo
            product_ids = [item.get("id", "") for item in content if item.get("type") == "PRODUCT" and item.get("id", "")]
            # Incluir ITEM e USER_PRODUCT na busca em lote (via search público funciona melhor)
            item_ids = [item.get("id", "") for item in content 
                       if item.get("type") in ["ITEM", "USER_PRODUCT"] 
                       and item.get("id", "")]
            
            batch_details = {}
            catalog_product_details = {}
            
            # Buscar detalhes dos produtos catalogados
            if product_ids:
                logger.info(f"Buscando detalhes para {len(product_ids)} produtos catalogados...")
                catalog_product_details = self._get_catalog_products_items(product_ids, access_token)
            
            # Buscar detalhes dos itens normais (ITEM e USER_PRODUCT) via search público
            if item_ids:
                logger.info(f"Buscando detalhes para {len(item_ids)} itens (ITEM/USER_PRODUCT)...")
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
                        logger.debug(f"Usando detalhes de lote para PRODUCT {item_id}")
                    elif item_type in ["ITEM", "USER_PRODUCT"]:
                        # Para itens normais e USER_PRODUCT
                        if item_id in batch_details:
                            details = batch_details[item_id]
                            logger.debug(f"Usando detalhes de lote para {item_type} {item_id}")
                        
                        # Se não encontrou no lote ou está vazio, buscar individualmente
                        if not details or not details.get("title") or not details.get("price"):
                            logger.info(f"Item {item_id} (tipo: {item_type}) não encontrado no lote ou incompleto, buscando individualmente...")
                            
                            # Tentar primeiro via search público (funciona melhor para ITEM e USER_PRODUCT)
                            details = self._get_item_via_search(item_id, site_id)
                            
                            # Se ainda não encontrou, tentar método normal com token
                            if not details or not details.get("title"):
                                logger.debug(f"Tentando buscar {item_type} {item_id} via /items com token")
                                details = self._get_item_details(item_id, item_type, access_token)
                            
                            # Se ainda não encontrou após todas as tentativas, construir dados mínimos com permalink
                            if not details or not details.get("title"):
                                logger.warning(f"Não foi possível obter detalhes via API para {item_type} {item_id}. Construindo permalink manualmente.")
                                details = self._empty_details()
                                # Construir permalink manualmente - formato padrão do ML
                                if item_type in ["ITEM", "USER_PRODUCT"]:
                                    # Para ITEM e USER_PRODUCT, formato é: https://produto.mercadolivre.com.br/MLB-{id}
                                    item_suffix = item_id.replace("MLB", "").replace("MLBU", "")
                                    details["permalink"] = f"https://produto.mercadolivre.com.br/MLB-{item_suffix}"
                                else:
                                    # Para PRODUCT, formato é diferente
                                    details["permalink"] = f"https://produto.mercadolivre.com.br/{item_id}"
                                details["id"] = item_id  # Garantir que o ID está presente
                    else:
                        # Fallback para outros tipos
                        if not details or not details.get("title"):
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
                        "seller_nickname": details.get("seller_nickname", ""),
                        "visits": details.get("visits", 0)
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
        
        # Garantir que permalink está correto
        item_permalink = data.get("permalink", "")
        if not item_permalink:
            item_id_from_data = data.get("id", "")
            if item_id_from_data:
                item_permalink = f"https://produto.mercadolivre.com.br/MLB-{item_id_from_data}"
        elif not item_permalink.startswith("http"):
            item_permalink = f"https://{item_permalink}" if not item_permalink.startswith("//") else f"https:{item_permalink}"
        
        result = {
            "title": data.get("title", ""),
            "price": float(data.get("price", 0)),
            "currency_id": data.get("currency_id", "BRL"),
            "thumbnail": data.get("thumbnail", ""),
            "permalink": item_permalink.strip() if item_permalink else "",
            "condition": data.get("condition", "new"),
            "sold_quantity": int(data.get("sold_quantity", 0)),
            "available_quantity": int(data.get("available_quantity", 0)),
            "category_id": category_id,
            "category_name": category_name,
            "seller_id": seller_id,
            "seller_nickname": seller_nickname,
            "visits": 0  # Visitas não estão disponíveis na API pública de highlights
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
                    
                    sold_quantity_from_item = 0
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
                            
                            # Tentar buscar sold_quantity e permalink via search público (mais confiável)
                            item_permalink_from_search = ""
                            if item_id:
                                try:
                                    search_url = f"{self.base_url}/sites/MLB/search"
                                    search_params = {"ids": item_id}
                                    search_response = requests.get(search_url, params=search_params, timeout=10)
                                    if search_response.status_code == 200:
                                        search_data = search_response.json()
                                        search_results = search_data.get("results", [])
                                        if search_results:
                                            search_item = search_results[0]
                                            sold_quantity_from_item = int(search_item.get("sold_quantity", 0))
                                            item_permalink_from_search = search_item.get("permalink", "")
                                except:
                                    pass
                    
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
                    
                    # Usar permalink do item específico se encontrado (mais preciso), senão usar do produto
                    permalink = item_permalink_from_search
                    if not permalink:
                        permalink = prod_data.get("permalink", "")
                    if not permalink:
                        # Fallback: construir URL do item se tiver item_id
                        # Formato correto do ML: https://produto.mercadolivre.com.br/MLB-{item_id}
                        if item_id:
                            # Remover "MLB" se já estiver no início do item_id
                            clean_item_id = item_id.replace("MLB", "").lstrip("-")
                            permalink = f"https://produto.mercadolivre.com.br/MLB-{clean_item_id}"
                        else:
                            # Se não tem item_id, tentar construir URL do produto catalogado
                            permalink = f"https://produto.mercadolivre.com.br/{product_id}"
                    
                    # Garantir que o permalink está completo (com https://)
                    if permalink:
                        if not permalink.startswith("http"):
                            permalink = f"https://{permalink}" if not permalink.startswith("//") else f"https:{permalink}"
                        # Remover espaços ou caracteres inválidos
                        permalink = permalink.strip()
                    
                    # Usar sold_quantity do item se encontrado, senão tentar do produto
                    final_sold_quantity = sold_quantity_from_item or int(prod_data.get("sold_quantity", sold_quantity))
                    
                    # Montar detalhes completos
                    product_details[product_id] = {
                        "title": title,
                        "price": price,
                        "currency_id": prod_data.get("currency_id", "BRL"),
                        "thumbnail": thumbnail,
                        "permalink": permalink,
                        "condition": prod_data.get("condition", "new"),
                        "sold_quantity": final_sold_quantity,
                        "available_quantity": available_quantity,
                        "category_id": prod_data.get("category_id", ""),
                        "category_name": "",
                        "seller_id": seller_id,
                        "seller_nickname": seller_nickname,
                        "visits": 0,  # Visitas não estão disponíveis na API pública de highlights
                        "_item_id": item_id  # Guardar item_id caso precise depois
                    }
                    
            except Exception as e:
                logger.warning(f"Erro ao buscar detalhes do produto {product_id}: {e}")
        
        logger.info(f"Detalhes obtidos para {len(product_details)} produtos catalogados")
        return product_details
    
    def _get_items_batch(self, item_ids: List[str], access_token: str, site_id: str) -> Dict[str, Dict]:
        """Busca múltiplos itens em lote usando search público (mais confiável para sold_quantity)"""
        try:
            # Usar search público que retorna sold_quantity
            # A API do ML permite buscar até 20 itens por vez usando ?ids=ID1,ID2,...
            batch_size = 20
            all_details = {}
            
            for i in range(0, len(item_ids), batch_size):
                batch = item_ids[i:i+batch_size]
                ids_param = ",".join(batch)
                
                # Tentar search primeiro (público, tem sold_quantity)
                search_url = f"{self.base_url}/sites/{site_id}/search"
                search_params = {"ids": ids_param}
                headers_public = {
                    **self.headers
                }
                
                logger.debug(f"Buscando lote de {len(batch)} itens via search: {ids_param[:100]}")
                search_response = requests.get(search_url, params=search_params, headers=headers_public, timeout=20)
                
                if search_response.status_code == 200:
                    search_data = search_response.json()
                    search_results = search_data.get("results", [])
                    logger.debug(f"Search retornou {len(search_results)} resultados para o lote")
                    
                    for item in search_results:
                        item_id = item.get("id", "")
                        if item_id:
                            # Parsear item da busca
                            seller = item.get("seller", {})
                            # Garantir que permalink está correto
                            item_permalink = item.get("permalink", "")
                            if not item_permalink:
                                # Construir permalink se não vier
                                item_permalink = f"https://produto.mercadolivre.com.br/MLB-{item_id}"
                            elif not item_permalink.startswith("http"):
                                item_permalink = f"https://{item_permalink}" if not item_permalink.startswith("//") else f"https:{item_permalink}"
                            
                            title = item.get("title", "")
                            price = float(item.get("price", 0))
                            thumbnail = item.get("thumbnail", "")
                            
                            logger.debug(f"Item {item_id}: title='{title[:50]}', price={price}, thumbnail={'sim' if thumbnail else 'não'}")
                            
                            all_details[item_id] = {
                                "title": title,
                                "price": price,
                                "currency_id": item.get("currency_id", "BRL"),
                                "thumbnail": thumbnail,
                                "permalink": item_permalink.strip(),
                                "condition": item.get("condition", "new"),
                                "sold_quantity": int(item.get("sold_quantity", 0)),
                                "available_quantity": int(item.get("available_quantity", 0)),
                                "category_id": item.get("category_id", ""),
                                "category_name": "",
                                "seller_id": str(seller.get("id", "")) if isinstance(seller, dict) else "",
                                "seller_nickname": seller.get("nickname", "") if isinstance(seller, dict) else "",
                                "visits": 0  # Visitas não estão disponíveis na API pública
                            }
                
                # Se search falhou ou retornou poucos resultados, tentar /items com token como fallback
                if search_response.status_code != 200 or len(all_details) < len(batch) * 0.5:
                    missing_ids = [item_id for item_id in batch if item_id not in all_details]
                    if missing_ids:
                        logger.debug(f"Search não retornou todos os itens ({len(missing_ids)} faltando), tentando /items com token")
                        url = f"{self.base_url}/items"
                        params = {"ids": ",".join(missing_ids)}
                        headers = {
                            **self.headers,
                            "Authorization": f"Bearer {access_token}"
                        }
                        
                        response = requests.get(url, params=params, headers=headers, timeout=20)
                        
                        if response.status_code == 200:
                            items = response.json()
                            for item in items:
                                if isinstance(item, dict) and "code" not in item:
                                    item_id = item.get("id", "")
                                    if item_id and item_id not in all_details:
                                        details = self._parse_item_response(item)
                                        details["visits"] = 0
                                        all_details[item_id] = details
                                        logger.debug(f"Item {item_id} encontrado via /items com token")
            
            logger.info(f"Busca em lote retornou {len(all_details)} itens de {len(item_ids)} solicitados")
            return all_details
            
        except Exception as e:
            logger.error(f"Erro na busca em lote: {e}", exc_info=True)
            return {}
    
    def _get_item_via_search(self, item_id: str, site_id: str) -> Dict:
        """Busca item via search público (funciona melhor que /items para alguns casos)"""
        try:
            search_url = f"{self.base_url}/sites/{site_id}/search"
            search_params = {"ids": item_id}
            headers_public = {
                **self.headers
            }
            
            response = requests.get(search_url, params=search_params, headers=headers_public, timeout=15)
            
            if response.status_code == 200:
                search_data = response.json()
                search_results = search_data.get("results", [])
                if search_results:
                    item = search_results[0]
                    seller = item.get("seller", {})
                    
                    item_permalink = item.get("permalink", "")
                    if not item_permalink:
                        item_permalink = f"https://produto.mercadolivre.com.br/MLB-{item_id}"
                    elif not item_permalink.startswith("http"):
                        item_permalink = f"https://{item_permalink}" if not item_permalink.startswith("//") else f"https:{item_permalink}"
                    
                    return {
                        "title": item.get("title", ""),
                        "price": float(item.get("price", 0)),
                        "currency_id": item.get("currency_id", "BRL"),
                        "thumbnail": item.get("thumbnail", ""),
                        "permalink": item_permalink.strip(),
                        "condition": item.get("condition", "new"),
                        "sold_quantity": int(item.get("sold_quantity", 0)),
                        "available_quantity": int(item.get("available_quantity", 0)),
                        "category_id": item.get("category_id", ""),
                        "category_name": "",
                        "seller_id": str(seller.get("id", "")) if isinstance(seller, dict) else "",
                        "seller_nickname": seller.get("nickname", "") if isinstance(seller, dict) else "",
                        "visits": 0
                    }
        except Exception as e:
            logger.debug(f"Erro ao buscar item via search: {e}")
        
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

