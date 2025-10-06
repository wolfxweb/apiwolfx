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
            
            # Tentar obter token ativo
            token = self._get_active_token(user_id)
            if token:
                logger.info(f"Token ativo encontrado para user_id: {user_id}")
                return token
            
            # Se não encontrou token ativo, tentar renovar
            logger.info(f"Token expirado, tentando renovar para user_id: {user_id}")
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
    
    def _get_active_token(self, user_id: int) -> Optional[str]:
        """Busca token válido e o ativa automaticamente se necessário"""
        try:
            # Primeiro, tentar buscar token ativo
            query = text("""
                SELECT access_token, expires_at, id
                FROM tokens 
                WHERE user_id = :user_id 
                AND is_active = true 
                AND expires_at > NOW()
                ORDER BY expires_at DESC
                LIMIT 1
            """)
            
            result = self.db.execute(query, {"user_id": user_id}).fetchone()
            
            if result:
                logger.info(f"Token ativo encontrado para user_id: {user_id}")
                return result[0]
            
            # Se não encontrou token ativo, buscar qualquer token válido (não expirado)
            query_inactive = text("""
                SELECT access_token, expires_at, id
                FROM tokens 
                WHERE user_id = :user_id 
                AND expires_at > NOW()
                ORDER BY expires_at DESC
                LIMIT 1
            """)
            
            result_inactive = self.db.execute(query_inactive, {"user_id": user_id}).fetchone()
            
            if result_inactive:
                # Ativar o token encontrado
                token_id = result_inactive[2]
                self.db.execute(text("""
                    UPDATE tokens 
                    SET is_active = true 
                    WHERE id = :token_id
                """), {"token_id": token_id})
                self.db.commit()
                
                logger.info(f"Token ativado automaticamente para user_id: {user_id}")
                return result_inactive[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar token ativo: {e}")
            return None
    
    def _refresh_token(self, user_id: int) -> Optional[str]:
        """Renova token usando refresh token"""
        try:
            # Buscar refresh token
            refresh_query = text("""
                SELECT refresh_token, ml_account_id
                FROM tokens 
                WHERE user_id = :user_id 
                AND is_active = true 
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