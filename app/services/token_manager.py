"""
Token Manager - Classe centralizada para gerenciamento de tokens do Mercado Livre
"""
import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.saas_models import Token

logger = logging.getLogger(__name__)

class TokenManager:
    """Gerenciador centralizado de tokens do Mercado Livre"""
    
    def __init__(self, db: Session):
        self.db = db
        self.client_id = "6987936494418444"
        self.client_secret = "puvG9Z7XBgICZg5yK3t0PAXAmnco18Tl"
        self.token_url = "https://api.mercadolibre.com/oauth/token"
    
    def get_valid_token(self, user_id: int) -> Optional[str]:
        """
        Obtém um token válido para o usuário, renovando automaticamente se necessário
        """
        try:
            logger.info(f"Buscando token válido para user_id: {user_id}")
            
            # Buscar company_id do usuário
            company_id = self._get_company_id_by_user(user_id)
            if not company_id:
                logger.error(f"Company ID não encontrado para user_id: {user_id}")
                return None
            
            # Buscar qualquer token do usuário
            token = self._get_any_token(user_id)
            if token:
                # Verificar se o token funciona na API
                if self.test_token(token):
                    logger.info(f"Token válido encontrado para user_id: {user_id}")
                    return token
                else:
                    logger.warning(f"Token inválido na API, renovando para user_id: {user_id}")
            
            # Tentar renovar token
            logger.info(f"Tentando renovar token para user_id: {user_id}")
            new_token = self._refresh_token(user_id)
            
            if new_token:
                logger.info(f"Token renovado com sucesso para user_id: {user_id}")
                return new_token
            
            logger.error(f"Falha ao obter token válido para user_id: {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao obter token válido: {e}")
            return None
    
    def _get_company_id_by_user(self, user_id: int) -> Optional[int]:
        """Busca company_id do usuário"""
        try:
            query = text("SELECT company_id FROM users WHERE id = :user_id")
            result = self.db.execute(query, {"user_id": user_id}).fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Erro ao buscar company_id: {e}")
            return None
    
    def _get_any_token(self, user_id: int) -> Optional[str]:
        """Busca qualquer token do usuário"""
        try:
            query = text("""
                SELECT access_token
                FROM tokens 
                WHERE user_id = :user_id 
                ORDER BY expires_at DESC
                LIMIT 1
            """)
            
            result = self.db.execute(query, {"user_id": user_id}).fetchone()
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Erro ao buscar token: {e}")
            return None
    
    def _refresh_token(self, user_id: int) -> Optional[str]:
        """Renova token usando refresh token"""
        try:
            # Buscar refresh token (não importa se está ativo ou não)
            refresh_query = text("""
                SELECT refresh_token, ml_account_id
                FROM tokens 
                WHERE user_id = :user_id 
                AND refresh_token IS NOT NULL
                ORDER BY expires_at DESC
                LIMIT 1
            """)
            
            refresh_result = self.db.execute(refresh_query, {"user_id": user_id}).fetchone()
            
            if not refresh_result or not refresh_result[0]:
                logger.error(f"Refresh token não encontrado para user_id: {user_id}")
                return None
            
            # Renovar token
            new_token_data = self._call_refresh_api(refresh_result[0])
            if not new_token_data:
                return None
            
            # Salvar novo token
            return self._save_new_token(refresh_result[1], new_token_data, user_id)
            
        except Exception as e:
            logger.error(f"Erro ao renovar token: {e}")
            return None
    
    def _call_refresh_api(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Chama API do Mercado Livre para renovar token"""
        try:
            data = {
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token
            }
            
            headers = {
                "accept": "application/json",
                "content-type": "application/x-www-form-urlencoded"
            }
            
            response = requests.post(self.token_url, data=data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                token_data = response.json()
                logger.info("Token renovado com sucesso via API")
                return token_data
            else:
                logger.error(f"Erro ao renovar token: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Erro na chamada da API de renovação: {e}")
            return None
    
    def _save_new_token(self, ml_account_id: int, token_data: Dict[str, Any], user_id: int) -> Optional[str]:
        """Salva novo token no banco de dados"""
        try:
            # Deletar tokens antigos (mais fácil de gerenciar)
            self.db.execute(text("""
                DELETE FROM tokens 
                WHERE user_id = :user_id
            """), {"user_id": user_id})
            
            # Criar novo token
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
            
            logger.info(f"Novo token salvo para user_id: {user_id} (tokens antigos deletados)")
            return token_data["access_token"]
            
        except Exception as e:
            logger.error(f"Erro ao salvar novo token: {e}")
            self.db.rollback()
            return None
    
    def test_token(self, token: str) -> bool:
        """Testa se o token está funcionando"""
        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get('https://api.mercadolibre.com/users/me', headers=headers, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Erro ao testar token: {e}")
            return False
    
    def test_token_permissions(self, token: str, user_id: str) -> Dict[str, bool]:
        """Testa se o token tem permissões específicas necessárias"""
        permissions = {
            'users_me': False,
            'visits': False,
            'claims': False,
            'orders': False
        }
        
        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Testar /users/me
            response = requests.get('https://api.mercadolibre.com/users/me', headers=headers, timeout=10)
            permissions['users_me'] = response.status_code == 200
            
            # Testar permissão de visitas
            try:
                visits_url = f'https://api.mercadolibre.com/users/{user_id}/items_visits/time_window'
                visits_response = requests.get(visits_url, headers=headers, params={'last': 1, 'unit': 'day'}, timeout=10)
                permissions['visits'] = visits_response.status_code == 200
                if visits_response.status_code != 200:
                    logger.warning(f"Token sem permissão de visitas: {visits_response.status_code}")
            except Exception as e:
                logger.warning(f"Erro ao testar permissão de visitas: {e}")
            
            # Testar permissão de claims
            try:
                claims_url = f'https://api.mercadolibre.com/users/{user_id}/claims/search'
                claims_response = requests.get(claims_url, headers=headers, params={'limit': 1}, timeout=10)
                permissions['claims'] = claims_response.status_code == 200
                if claims_response.status_code != 200:
                    logger.warning(f"Token sem permissão de claims: {claims_response.status_code}")
            except Exception as e:
                logger.warning(f"Erro ao testar permissão de claims: {e}")
            
            # Testar permissão de orders
            try:
                orders_url = f'https://api.mercadolibre.com/orders/search'
                orders_response = requests.get(orders_url, headers=headers, params={'seller': user_id, 'limit': 1}, timeout=10)
                permissions['orders'] = orders_response.status_code == 200
                if orders_response.status_code != 200:
                    logger.warning(f"Token sem permissão de orders: {orders_response.status_code}")
            except Exception as e:
                logger.warning(f"Erro ao testar permissão de orders: {e}")
            
            logger.info(f"Permissões do token: {permissions}")
            return permissions
            
        except Exception as e:
            logger.error(f"Erro ao testar permissões do token: {e}")
            return permissions
    
    def _refresh_token_with_scope(self, user_id: int, scope: str = 'read') -> Optional[str]:
        """Renova token com escopo específico"""
        try:
            logger.info(f"🔄 Renovando token com escopo '{scope}' para user_id: {user_id}")
            
            # Buscar refresh_token do usuário
            refresh_token = self._get_refresh_token(user_id)
            if not refresh_token:
                logger.error(f"Refresh token não encontrado para user_id: {user_id}")
                return None
            
            # Dados para renovação
            data = {
                'grant_type': 'refresh_token',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': refresh_token,
                'scope': scope  # Adicionar escopo específico
            }
            
            response = requests.post(self.token_url, data=data, timeout=30)
            
            if response.status_code == 200:
                token_data = response.json()
                new_access_token = token_data.get('access_token')
                new_refresh_token = token_data.get('refresh_token')
                
                if new_access_token:
                    # Salvar novo token
                    self._save_new_token(user_id, new_access_token, new_refresh_token)
                    logger.info(f"✅ Token renovado com escopo '{scope}' para user_id: {user_id}")
                    return new_access_token
                else:
                    logger.error(f"Token de acesso não encontrado na resposta para user_id: {user_id}")
                    return None
            else:
                logger.error(f"Erro ao renovar token: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao renovar token com escopo: {e}")
            return None