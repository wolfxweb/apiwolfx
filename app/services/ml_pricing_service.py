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
    
    def calculate_ml_fees(self, user_id: int, price: float, category_id: str = None) -> Dict[str, Any]:
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
            total_fees = fixed_fee + percentage_amount + listing_fee
            
            return {
                "listing_type": pricing_data.get("listing_type_name", "Clássico"),
                "fixed_fee": fixed_fee,
                "percentage_fee": percentage_fee,
                "percentage_amount": percentage_amount,
                "listing_fee": listing_fee,
                "total_fees": total_fees,
                "currency": pricing_data.get("currency_id", "BRL"),
                "source": "api"
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular taxas ML: {e}")
            return self._get_default_fees(price)
    
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
        total_fees = fixed_fee + percentage_amount
        
        return {
            "listing_type": "Clássico",
            "fixed_fee": fixed_fee,
            "percentage_fee": percentage_fee,
            "percentage_amount": percentage_amount,
            "listing_fee": 0,
            "total_fees": total_fees,
            "currency": "BRL",
            "source": "fallback"
        }
