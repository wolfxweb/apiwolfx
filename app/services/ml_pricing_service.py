"""
Serviço para buscar taxas reais do Mercado Livre via API listing_prices
"""
import requests
import logging
from typing import Dict, Any, Optional
from app.services.token_manager import TokenManager

logger = logging.getLogger(__name__)

class MLPricingService:
    """Serviço para buscar taxas reais do Mercado Livre"""
    
    def __init__(self, db_session):
        self.db = db_session
        self.token_manager = TokenManager(db_session)
    
    def get_listing_prices(self, user_id: int, price: float, category_id: str = None, listing_type_id: str = "gold_special") -> Optional[Dict[str, Any]]:
        """
        Busca as taxas reais do Mercado Livre via API listing_prices
        
        Args:
            user_id: ID do usuário
            price: Preço do produto
            category_id: ID da categoria (opcional)
            listing_type_id: Tipo de publicação (default: gold_special - Clássico)
        
        Returns:
            Dict com as taxas ou None se erro
        """
        try:
            # Obter token válido
            access_token = self.token_manager.get_valid_token(user_id)
            if not access_token:
                logger.error("Token não encontrado para buscar listing prices")
                return None
            
            # Construir URL da API
            url = "https://api.mercadolibre.com/sites/MLB/listing_prices"
            params = {
                "price": price,
                "listing_type_id": listing_type_id
            }
            
            if category_id:
                params["category_id"] = category_id
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Buscando listing prices para preço: {price}, categoria: {category_id}, listing_type: {listing_type_id}")
            
            # Fazer requisição
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Listing prices obtidas com sucesso: {data}")
                return data
            else:
                logger.error(f"Erro ao buscar listing prices: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar listing prices: {e}")
            return None
    
    def calculate_ml_fees(self, user_id: int, price: float, category_id: str = None, item_id: str = None) -> Dict[str, Any]:
        """
        Calcula as taxas do Mercado Livre baseado nas taxas reais da API
        
        Args:
            user_id: ID do usuário
            price: Preço do produto
            category_id: ID da categoria
        
        Returns:
            Dict com as taxas calculadas
        """
        try:
            # Buscar taxas reais
            listing_prices = self.get_listing_prices(user_id, price, category_id)
            
            if not listing_prices:
                logger.warning("Não foi possível obter taxas reais, usando valores padrão")
                return self._get_default_fees(price)
            
            # Processar dados da API
            if isinstance(listing_prices, list) and len(listing_prices) > 0:
                # Pegar o primeiro resultado (gold_special - Clássico)
                pricing_data = listing_prices[0]
            else:
                pricing_data = listing_prices
            
            # Extrair taxas
            sale_fee_details = pricing_data.get("sale_fee_details", {})
            listing_fee_details = pricing_data.get("listing_fee_details", {})
            
            # Taxa fixa de venda (só existe em alguns sites como MLA)
            fixed_fee = sale_fee_details.get("fixed_fee", 0)
            
            # Taxa percentual
            percentage_fee = sale_fee_details.get("percentage_fee", 0)
            
            # Taxa de publicação
            listing_fee = pricing_data.get("listing_fee_amount", 0)
            
            # Calcular valores monetários
            percentage_amount = (price * percentage_fee / 100) if percentage_fee > 0 else 0
            
            # Buscar dados de shipping se item_id disponível
            shipping_data = None
            if item_id:
                shipping_data = self.get_shipping_cost(user_id, item_id)
            
            # Calcular frete baseado na regra do Mercado Livre
            shipping_cost = self._calculate_shipping_cost(price, shipping_data)
            
            total_fees = fixed_fee + percentage_amount + listing_fee + shipping_cost
            
            return {
                "listing_type": pricing_data.get("listing_type_name", "Clássico"),
                "fixed_fee": fixed_fee,
                "percentage_fee": percentage_fee,
                "percentage_amount": percentage_amount,
                "listing_fee": listing_fee,
                "shipping_cost": shipping_cost,
                "total_fees": total_fees,
                "currency": pricing_data.get("currency_id", "BRL"),
                "source": "api"
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular taxas ML: {e}")
            return self._get_default_fees(price)
    
    def get_shipping_cost(self, user_id: int, item_id: str, zip_code: str = "01310-100") -> Dict[str, Any]:
        """
        Busca o custo real do frete via API do Mercado Livre
        
        Args:
            user_id: ID do usuário
            item_id: ID do item no Mercado Livre
            zip_code: CEP de destino (default: São Paulo)
        
        Returns:
            Dict com informações do frete
        """
        try:
            # Obter token válido
            access_token = self.token_manager.get_valid_token(user_id)
            if not access_token:
                logger.error("Token não encontrado para buscar shipping options")
                return {"error": "Token não encontrado"}
            
            # Construir URL da API
            url = f"https://api.mercadolibre.com/items/{item_id}/shipping_options"
            params = {"zip_code": zip_code}
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Buscando shipping options para item: {item_id}, CEP: {zip_code}")
            
            # Fazer requisição
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Shipping options obtidas com sucesso: {data}")
                return data
            else:
                logger.error(f"Erro ao buscar shipping options: {response.status_code} - {response.text}")
                return {"error": f"Erro na API: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Erro ao buscar shipping options: {e}")
            return {"error": str(e)}
    
    def _calculate_shipping_cost(self, price: float, shipping_data: Dict[str, Any] = None) -> float:
        """
        Calcula o custo do frete baseado na regra do Mercado Livre
        
        Args:
            price: Preço do produto
            shipping_data: Dados da API de shipping (opcional)
        
        Returns:
            Custo do frete (estimativa)
        """
        # Se temos dados da API de shipping, usar os dados reais
        if shipping_data and not shipping_data.get("error"):
            options = shipping_data.get("options", [])
            if options:
                first_option = options[0]
                # Se o comprador paga (cost > 0), o vendedor não paga nada
                if first_option.get("cost", 0) > 0:
                    return 0.0  # Comprador paga, vendedor não paga
                else:
                    # Se o frete é gratuito para o comprador, o vendedor paga
                    return first_option.get("list_cost", 0)
        
        # Fallback: estimativa baseada na regra do Mercado Livre
        # Regra do Mercado Livre: frete gratuito obrigatório para produtos >= R$ 79,90
        # MAS o vendedor ainda paga a tarifa do Mercado Envios
        if price >= 79.90:
            # Para produtos acima de R$ 79,90, o vendedor paga a tarifa do Mercado Envios
            # Baseado no exemplo: R$ 11,97 para produto de R$ 95,95
            return 12.0  # Estimativa da tarifa do Mercado Envios
        else:
            # Para produtos abaixo de R$ 79,90, o comprador geralmente paga
            return 0.0  # Comprador paga, vendedor não paga
    
    def _get_default_fees(self, price: float) -> Dict[str, Any]:
        """
        Retorna taxas padrão como fallback
        """
        # Valores baseados na documentação e experiência comum
        if price < 79.90:
            # Produtos abaixo de R$ 79,90: taxa fixa + percentual
            fixed_fee = 6.25
            percentage_fee = 13.0
        else:
            # Produtos acima de R$ 79,90: apenas percentual
            fixed_fee = 0
            percentage_fee = 12.0
        
        percentage_amount = (price * percentage_fee / 100)
        shipping_cost = self._calculate_shipping_cost(price)
        total_fees = fixed_fee + percentage_amount + shipping_cost
        
        return {
            "listing_type": "Clássico",
            "fixed_fee": fixed_fee,
            "percentage_fee": percentage_fee,
            "percentage_amount": percentage_amount,
            "listing_fee": 0,
            "shipping_cost": shipping_cost,
            "total_fees": total_fees,
            "currency": "BRL",
            "source": "fallback"
        }
