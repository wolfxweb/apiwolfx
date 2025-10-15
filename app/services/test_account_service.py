"""
Serviço para gerenciar contas de teste do Mercado Pago
"""
import requests
import logging
from typing import Dict, Any, List
from app.config.settings import settings

logger = logging.getLogger(__name__)


class TestAccountService:
    """Serviço para gerenciar contas de teste do Mercado Pago"""
    
    def __init__(self):
        self.base_url = settings.mp_base_url
        self.access_token = settings.mp_access_token
        
    def create_test_account(self, account_type: str = "buyer", 
                          country: str = "BR", 
                          description: str = "Conta de Teste") -> Dict[str, Any]:
        """
        Cria uma conta de teste no Mercado Pago
        
        Args:
            account_type: "seller", "buyer" ou "integrator"
            country: Código do país (BR, AR, MX, etc.)
            description: Descrição da conta
            
        Returns:
            Dict com dados da conta de teste criada
        """
        try:
            url = f"{self.base_url}/users/test_user"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "site_id": self._get_site_id(country),
                "description": f"{description} - {account_type.title()}"
            }
            
            logger.info(f"🔄 Criando conta de teste: {account_type} para {country}")
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 201:
                account_data = response.json()
                logger.info(f"✅ Conta {account_type} criada: {account_data.get('nickname', 'N/A')}")
                
                # Adicionar informações específicas da conta
                account_data['account_type'] = account_type
                account_data['country'] = country
                account_data['test_cards'] = self._get_test_cards(country)
                
                return account_data
            else:
                logger.error(f"❌ Erro ao criar conta {account_type}: {response.status_code} - {response.text}")
                return {"error": f"Erro {response.status_code}: {response.text}"}
                
        except Exception as e:
            logger.error(f"❌ Erro ao criar conta de teste: {e}")
            return {"error": str(e)}
    
    def _get_site_id(self, country: str) -> str:
        """Converte código do país para site_id do Mercado Livre"""
        site_mapping = {
            "BR": "MLB",  # Brasil
            "AR": "MLA",  # Argentina
            "MX": "MLM",  # México
            "CL": "MLC",  # Chile
            "CO": "MCO",  # Colômbia
            "PE": "MPE",  # Peru
            "UY": "MLU",  # Uruguai
        }
        return site_mapping.get(country, "MLB")
    
    def _get_test_cards(self, country: str) -> Dict[str, Any]:
        """Retorna cartões de teste específicos do país"""
        test_cards = {
            "BR": {
                "approved": {
                    "number": "4235647728025682",
                    "security_code": "123",
                    "expiration_month": "11",
                    "expiration_year": "2025",
                    "cardholder": {
                        "name": "APRO",
                        "identification": {
                            "type": "CPF",
                            "number": "12345678901"
                        }
                    }
                },
                "rejected": {
                    "number": "4000000000000002",
                    "security_code": "123",
                    "expiration_month": "11",
                    "expiration_year": "2025",
                    "cardholder": {
                        "name": "OTHE",
                        "identification": {
                            "type": "CPF",
                            "number": "12345678901"
                        }
                    }
                },
                "pending": {
                    "number": "4000000000000119",
                    "security_code": "123",
                    "expiration_month": "11",
                    "expiration_year": "2025",
                    "cardholder": {
                        "name": "PEND",
                        "identification": {
                            "type": "CPF",
                            "number": "12345678901"
                        }
                    }
                }
            }
        }
        return test_cards.get(country, test_cards["BR"])
    
    def get_test_cards(self, country: str = "BR") -> Dict[str, Any]:
        """Retorna cartões de teste para o país especificado"""
        return self._get_test_cards(country)
    
    def setup_test_environment(self) -> Dict[str, Any]:
        """
        Configura ambiente completo de teste com todas as contas necessárias
        """
        try:
            logger.info("🚀 Configurando ambiente de teste completo...")
            
            # Criar contas de teste
            seller_account = self.create_test_account("seller", "BR", "Vendedor Principal")
            buyer_account = self.create_test_account("buyer", "BR", "Comprador Teste")
            
            # Verificar se as contas foram criadas com sucesso
            if seller_account.get("error") or buyer_account.get("error"):
                return {
                    "error": "Erro ao criar contas de teste",
                    "seller_error": seller_account.get("error"),
                    "buyer_error": buyer_account.get("error")
                }
            
            # Retornar ambiente configurado
            return {
                "message": "Ambiente de teste configurado com sucesso",
                "accounts": {
                    "seller": seller_account,
                    "buyer": buyer_account
                },
                "test_cards": buyer_account.get("test_cards", {}),
                "instructions": {
                    "seller_login": f"Use User ID: {seller_account.get('id')}",
                    "buyer_login": f"Use User ID: {buyer_account.get('id')}",
                    "test_payment": "Use os cartões de teste fornecidos",
                    "authentication": "Para login, use os últimos 6 dígitos do User ID"
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar ambiente de teste: {e}")
            return {"error": str(e)}


# Instância global do serviço
test_account_service = TestAccountService()
