"""
Service para gerenciar mensagens pós-venda do Mercado Livre
"""
import logging
import requests
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.models.saas_models import MLMessageThread, MLMessage, MLMessageThreadStatus, MLMessageType, MLAccount, MLAccountStatus
from app.services.token_manager import TokenManager

logger = logging.getLogger(__name__)

class MLMessagesService:
    """Service para gerenciar mensagens pós-venda do Mercado Livre"""
    
    def __init__(self, db: Session):
        self.db = db
        self.base_url = "https://api.mercadolibre.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def _get_access_token(self, user_id: int) -> Optional[str]:
        """Obtém token válido usando TokenManager"""
        try:
            token_manager = TokenManager(self.db)
            return token_manager.get_valid_token(user_id)
        except Exception as e:
            logger.error(f"Erro ao obter token para user_id {user_id}: {e}")
            return None
    
    def get_reasons_to_communicate(self, access_token: str) -> List[Dict]:
        """Busca os motivos disponíveis para iniciar uma comunicação pós-venda"""
        try:
            url = f"{self.base_url}/messages/options/reasons"
            headers = {
                **self.headers,
                "Authorization": f"Bearer {access_token}"
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erro ao buscar motivos: {response.status_code} - {response.text[:200]}")
                return []
        except Exception as e:
            logger.error(f"Erro ao buscar motivos para comunicar: {e}", exc_info=True)
            return []
    
    def create_message_thread(self, package_id: str, reason: str, message_text: str, access_token: str) -> Dict:
        """Cria uma nova conversa/mensagem pós-venda"""
        try:
            url = f"{self.base_url}/messages/packages/{package_id}"
            headers = {
                **self.headers,
                "Authorization": f"Bearer {access_token}"
            }
            
            payload = {
                "reason": reason,
                "message": {
                    "text": message_text
                }
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            
            if response.status_code == 201 or response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erro ao criar mensagem: {response.status_code} - {response.text[:200]}")
                return {"error": f"Erro {response.status_code}: {response.text[:200]}"}
        except Exception as e:
            logger.error(f"Erro ao criar mensagem pós-venda: {e}", exc_info=True)
            return {"error": str(e)}
    
    def get_thread_messages(self, package_id: str, access_token: str) -> Optional[Dict]:
        """Busca todas as mensagens de uma conversa/pacote"""
        logger.info(f"🌐 ========== BUSCANDO DETALHES DO THREAD NA API ==========")
        logger.info(f"🌐 Package ID: {package_id}")
        logger.info(f"🌐 URL: {self.base_url}/messages/packages/{package_id}")
        
        try:
            url = f"{self.base_url}/messages/packages/{package_id}"
            headers = {
                **self.headers,
                "Authorization": f"Bearer {access_token[:20]}..."  # Log parcial do token
            }
            
            logger.info(f"📤 Enviando requisição GET para {url}")
            logger.info(f"📤 Headers: {dict(headers)}")
            
            response = requests.get(url, headers={
                **self.headers,
                "Authorization": f"Bearer {access_token}"
            }, timeout=15)
            
            logger.info(f"📥 Resposta recebida: Status Code = {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Dados recebidos com sucesso!")
                logger.info(f"📊 Tipo do retorno: {type(data)}")
                if isinstance(data, dict):
                    logger.info(f"📊 Chaves principais: {list(data.keys())}")
                logger.info(f"🌐 ========== THREAD RECEBIDO COM SUCESSO ==========")
                return data
            else:
                logger.error(f"❌ Erro ao buscar mensagens do pacote {package_id}")
                logger.error(f"❌ Status Code: {response.status_code}")
                logger.error(f"❌ Resposta (primeiros 500 caracteres): {response.text[:500]}")
                logger.error(f"🌐 ========== ERRO AO BUSCAR THREAD ==========")
                return None
        except Exception as e:
            logger.error(f"❌ ========== EXCEÇÃO AO BUSCAR THREAD ==========")
            logger.error(f"❌ Package ID: {package_id}")
            logger.error(f"❌ Erro: {str(e)}")
            logger.error(f"❌ Tipo: {type(e).__name__}")
            logger.error(f"❌ Traceback:", exc_info=True)
            logger.error(f"❌ ========== FIM DA EXCEÇÃO ==========")
            return None
    
    def send_message(self, thread_id: str, message_text: str, access_token: str) -> Dict:
        """Envia uma mensagem em uma conversa existente"""
        try:
            url = f"{self.base_url}/messages/packages/{thread_id}"
            headers = {
                **self.headers,
                "Authorization": f"Bearer {access_token}"
            }
            
            payload = {
                "message": {
                    "text": message_text
                }
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            
            if response.status_code == 201 or response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erro ao enviar mensagem: {response.status_code} - {response.text[:200]}")
                return {"error": f"Erro {response.status_code}: {response.text[:200]}"}
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}", exc_info=True)
            return {"error": str(e)}
    
    def get_packages(self, ml_user_id: str, access_token: str, limit: int = 50) -> List[Dict]:
        """Busca todos os pacotes/conversas do vendedor"""
        try:
            url = f"{self.base_url}/messages/packages/search"
            headers = {
                **self.headers,
                "Authorization": f"Bearer {access_token}"
            }
            
            params = {
                "seller_id": ml_user_id,
                "limit": limit
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            else:
                logger.error(f"Erro ao buscar pacotes: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Erro ao buscar pacotes: {e}", exc_info=True)
            return []
    
    def save_thread_to_db(self, thread_data: Dict, company_id: int, ml_account_id: int, ml_user_id: str) -> Optional[MLMessageThread]:
        """Salva ou atualiza uma thread/conversa no banco"""
        logger.info(f"💾 ========== SALVANDO THREAD NO BANCO ==========")
        logger.info(f"💾 Company ID: {company_id}")
        logger.info(f"💾 ML Account ID: {ml_account_id}")
        logger.info(f"💾 ML User ID: {ml_user_id}")
        
        try:
            package_id = thread_data.get("package_id") or thread_data.get("id")
            logger.info(f"💾 Package ID extraído: {package_id}")
            
            if not package_id:
                logger.warning("❌ Thread sem package_id, ignorando...")
                logger.warning(f"❌ Dados recebidos: {list(thread_data.keys())}")
                return None
            
            # Buscar thread existente
            logger.info(f"🔍 Verificando se thread já existe no banco: package_id={package_id}, company_id={company_id}")
            thread = self.db.query(MLMessageThread).filter(
                MLMessageThread.ml_thread_id == str(package_id),
                MLMessageThread.company_id == company_id
            ).first()
            
            if thread:
                logger.info(f"📝 Thread existente encontrada! ID: {thread.id}, atualizando...")
            else:
                logger.info(f"✨ Nova thread, criando...")
            
            buyer_data = thread_data.get("buyer", {})
            buyer_id = str(buyer_data.get("id", "")) if buyer_data else "UNKNOWN"
            buyer_nickname = buyer_data.get("nickname") if buyer_data else None
            
            messages_data = thread_data.get("messages", [])
            last_message = messages_data[-1] if messages_data else {}
            
            order_ids = []
            if thread_data.get("order_ids"):
                order_ids = thread_data["order_ids"]
            elif thread_data.get("orders"):
                order_ids = [o.get("id") for o in thread_data["orders"] if o.get("id")]
            
            if thread:
                # Atualizar thread existente
                thread.ml_package_id = str(package_id)
                thread.ml_buyer_id = buyer_id
                thread.buyer_nickname = buyer_nickname
                thread.status = MLMessageThreadStatus.OPEN if thread_data.get("status") != "closed" else MLMessageThreadStatus.CLOSED
                thread.last_message_date = datetime.fromisoformat(last_message.get("date").replace("Z", "+00:00")) if last_message.get("date") else None
                thread.last_message_text = last_message.get("text") if last_message else None
                thread.order_ids = order_ids
                thread.thread_data = thread_data
                thread.last_sync = datetime.now()
                thread.updated_at = datetime.now()
            else:
                # Criar nova thread
                thread = MLMessageThread(
                    company_id=company_id,
                    ml_account_id=ml_account_id,
                    ml_thread_id=str(package_id),
                    ml_package_id=str(package_id),
                    ml_buyer_id=buyer_id,
                    buyer_nickname=buyer_nickname,
                    reason=thread_data.get("reason"),
                    subject=thread_data.get("subject"),
                    status=MLMessageThreadStatus.OPEN if thread_data.get("status") != "closed" else MLMessageThreadStatus.CLOSED,
                    last_message_date=datetime.fromisoformat(last_message.get("date").replace("Z", "+00:00")) if last_message.get("date") else None,
                    last_message_text=last_message.get("text") if last_message else None,
                    order_ids=order_ids,
                    thread_data=thread_data,
                    last_sync=datetime.now()
                )
                self.db.add(thread)
            
            logger.info(f"💾 Fazendo commit do thread no banco...")
            self.db.commit()
            self.db.refresh(thread)
            
            logger.info(f"✅ Thread commitado! ID no banco: {thread.id}")
            
            # Salvar mensagens individuais
            logger.info(f"📨 Processando {len(messages_data)} mensagens...")
            if messages_data:
                saved_messages = 0
                for idx, msg_data in enumerate(messages_data):
                    logger.info(f"📨 Salvando mensagem {idx + 1}/{len(messages_data)}: message_id={msg_data.get('id')}")
                    saved_msg = self.save_message_to_db(msg_data, thread.id, company_id, ml_user_id)
                    if saved_msg:
                        saved_messages += 1
                
                logger.info(f"✅ {saved_messages}/{len(messages_data)} mensagens salvas com sucesso")
            else:
                logger.info(f"ℹ️ Nenhuma mensagem para salvar")
            
            logger.info(f"💾 ========== THREAD SALVO COM SUCESSO ==========")
            logger.info(f"✅ Thread {package_id} salva/atualizada no banco com ID: {thread.id}")
            return thread
            
        except Exception as e:
            logger.error(f"❌ ========== ERRO AO SALVAR THREAD ==========")
            logger.error(f"❌ Package ID: {package_id}")
            logger.error(f"❌ Company ID: {company_id}")
            logger.error(f"❌ Erro: {str(e)}")
            logger.error(f"❌ Tipo: {type(e).__name__}")
            logger.error(f"❌ Traceback:", exc_info=True)
            self.db.rollback()
            logger.error(f"❌ Rollback executado")
            logger.error(f"❌ ========== FIM DO ERRO ==========")
            return None
    
    def save_message_to_db(self, message_data: Dict, thread_id: int, company_id: int, ml_user_id: str) -> Optional[MLMessage]:
        """Salva ou atualiza uma mensagem individual no banco"""
        try:
            ml_message_id = str(message_data.get("id", ""))
            if not ml_message_id:
                logger.warning("Mensagem sem ID, ignorando...")
                return None
            
            # Buscar mensagem existente
            message = self.db.query(MLMessage).filter(
                MLMessage.ml_message_id == ml_message_id,
                MLMessage.thread_id == thread_id
            ).first()
            
            from_data = message_data.get("from", {})
            to_data = message_data.get("to", {})
            
            from_user_id = str(from_data.get("user_id", from_data.get("id", ""))) if from_data else "UNKNOWN"
            from_nickname = from_data.get("nickname") if from_data else None
            
            to_user_id = str(to_data.get("user_id", to_data.get("id", ""))) if to_data else "UNKNOWN"
            to_nickname = to_data.get("nickname") if to_data else None
            
            is_seller = from_user_id == str(ml_user_id)
            
            message_date = None
            if message_data.get("date"):
                try:
                    message_date = datetime.fromisoformat(message_data.get("date").replace("Z", "+00:00"))
                except:
                    message_date = datetime.now()
            else:
                message_date = datetime.now()
            
            if message:
                # Atualizar mensagem existente
                message.message_text = message_data.get("text", "")
                message.from_nickname = from_nickname
                message.to_nickname = to_nickname
                message.read = message_data.get("read", False)
                message.message_data = message_data
                message.updated_at = datetime.now()
            else:
                # Criar nova mensagem
                message = MLMessage(
                    thread_id=thread_id,
                    company_id=company_id,
                    ml_message_id=ml_message_id,
                    from_user_id=from_user_id,
                    from_nickname=from_nickname,
                    to_user_id=to_user_id,
                    to_nickname=to_nickname,
                    message_text=message_data.get("text", ""),
                    message_type=MLMessageType.TEXT,  # Por enquanto apenas texto
                    is_seller=is_seller,
                    message_date=message_date,
                    read=message_data.get("read", False),
                    message_data=message_data
                )
                self.db.add(message)
            
            self.db.commit()
            self.db.refresh(message)
            
            return message
            
        except Exception as e:
            logger.error(f"Erro ao salvar mensagem no banco: {e}", exc_info=True)
            self.db.rollback()
            return None
    
    def sync_messages(self, company_id: int, user_id: int, ml_account_id: int = None) -> Dict:
        """Sincroniza mensagens pós-venda de todas as contas ML ativas da empresa"""
        try:
            access_token = self._get_access_token(user_id)
            if not access_token:
                return {
                    "success": False,
                    "error": "Token de acesso não encontrado ou expirado",
                    "synced": 0
                }
            
            # Buscar contas ML ativas
            accounts_query = self.db.query(MLAccount).filter(
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            )
            
            if ml_account_id:
                accounts_query = accounts_query.filter(MLAccount.id == ml_account_id)
            
            accounts = accounts_query.all()
            
            if not accounts:
                return {
                    "success": False,
                    "error": "Nenhuma conta ML ativa encontrada",
                    "synced": 0
                }
            
            total_synced = 0
            errors = []
            
            for account in accounts:
                try:
                    ml_user_id = str(account.ml_user_id)
                    
                    # Buscar pacotes/conversas
                    packages = self.get_packages(ml_user_id, access_token)
                    
                    for package_data in packages:
                        try:
                            # Buscar detalhes completos do pacote (mensagens)
                            thread_details = self.get_thread_messages(package_data.get("id"), access_token)
                            if thread_details:
                                package_data.update(thread_details)
                            
                            # Salvar no banco
                            saved = self.save_thread_to_db(package_data, company_id, account.id, ml_user_id)
                            if saved:
                                total_synced += 1
                        except Exception as e:
                            error_msg = f"Erro ao processar pacote {package_data.get('id')}: {str(e)}"
                            logger.error(error_msg)
                            errors.append(error_msg)
                
                except Exception as e:
                    error_msg = f"Erro ao sincronizar conta {account.nickname}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            return {
                "success": True,
                "synced": total_synced,
                "errors": errors if errors else None
            }
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar mensagens: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "synced": 0
            }

