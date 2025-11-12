"""
Controller para gerenciar mensagens pós-venda do Mercado Livre
"""
import logging
from datetime import datetime
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.models.saas_models import MLMessageThread, MLMessage, MLAccount, MLAccountStatus, MLMessageThreadStatus
from app.services.ml_messages_service import MLMessagesService
from app.services.token_manager import TokenManager
from app.utils.notification_logger import global_logger

logger = logging.getLogger(__name__)

class MLMessagesController:
    """Controller para gerenciar mensagens pós-venda do Mercado Livre"""
    
    def __init__(self, db: Session):
        self.db = db
        self.service = MLMessagesService(db)
    
    def get_threads(self, company_id: int, ml_account_id: Optional[int] = None,
                   status: Optional[str] = None, limit: int = 50) -> Dict:
        """Lista conversas/threads da empresa"""
        try:
            query = self.db.query(MLMessageThread).filter(
                MLMessageThread.company_id == company_id
            )
            
            if ml_account_id:
                # Garantir que a conta ML pertence à empresa do usuário logado
                ml_account = self.db.query(MLAccount).filter(
                    MLAccount.id == ml_account_id,
                    MLAccount.company_id == company_id
                ).first()
                
                if not ml_account:
                    return {
                        "success": False,
                        "error": f"Conta ML {ml_account_id} não encontrada ou não pertence à sua empresa",
                        "threads": [],
                        "total": 0
                    }
                
                query = query.filter(MLMessageThread.ml_account_id == ml_account_id)
            
            if status:
                try:
                    status_enum = MLMessageThreadStatus[status.upper()] if isinstance(status, str) else status
                    query = query.filter(MLMessageThread.status == status_enum)
                except (KeyError, AttributeError):
                    pass
            
            threads = (
                query.order_by(desc(MLMessageThread.last_message_date))
                .limit(limit)
                .all()
            )

            result_threads = [self._thread_to_dict(t) for t in threads]

            # Se não houver conversas válidas (sem mensagens), tentar sincronizar rapidamente
            if not result_threads:
                logger.info(
                    "Nenhuma conversa encontrada localmente. Tentando sincronizar mensagens."
                )
                try:
                    sync_result = self.service.sync_messages(
                        company_id=company_id,
                        user_id=None,
                        ml_account_id=ml_account_id,
                        fetch_all=False,
                    )
                    logger.info("Resultado da sincronização rápida: %s", sync_result)
                    # Recarregar threads após sincronização rápida
                    threads = (
                        query.order_by(desc(MLMessageThread.last_message_date))
                        .limit(limit)
                        .all()
                    )
                except Exception as sync_error:
                    logger.exception(
                        "Erro ao sincronizar mensagens automaticamente: %s",
                        sync_error,
                    )

            return {
                "success": True,
                "threads": [self._thread_to_dict(t) for t in threads],
                "total": len(threads)
            }
        except Exception as e:
            logger.error(f"Erro ao listar threads: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "threads": [],
                "total": 0
            }

    def _ensure_thread_details(self, thread: MLMessageThread) -> bool:
        """Garante que a thread possui dados essenciais do comprador e mensagens"""
        updated = False

        needs_buyer = not thread.buyer_nickname or not thread.ml_buyer_id
        needs_messages = not thread.messages
        needs_last_message = not thread.last_message_text

        if not (needs_buyer or needs_messages or needs_last_message):
            return False

        ml_account = (
            self.db.query(MLAccount)
            .filter(MLAccount.id == thread.ml_account_id)
            .first()
        )
        if not ml_account:
            return False

        token_manager = TokenManager(self.db)
        token_record = token_manager.get_token_record_for_account(
            thread.ml_account_id, ml_account.company_id
        )
        if not token_record:
            return False

        try:
            thread_details = self.service.get_thread_messages(
                thread.ml_package_id,
                token_record.access_token,
                seller_id=str(ml_account.ml_user_id),
            )
        except Exception:
            logger.exception(
                "Erro ao buscar detalhes da thread %s", thread.id
            )
            return False

        if not thread_details:
            return False

        messages_data = thread_details.get("messages", [])
        buyer_data = thread_details.get("buyer", {})

        if needs_buyer and buyer_data:
            buyer_id = buyer_data.get("id")
            nickname = buyer_data.get("nickname")
            if buyer_id:
                thread.ml_buyer_id = str(buyer_id)
                updated = True
            if nickname:
                thread.buyer_nickname = nickname
                updated = True

        if messages_data:
            for msg_data in messages_data:
                saved_msg = self.service.save_message_to_db(
                    msg_data,
                    thread.id,
                    thread.company_id,
                    str(ml_account.ml_user_id),
                )
                if saved_msg:
                    updated = True

            last_message = messages_data[-1]
            last_text = last_message.get("text")
            last_date = last_message.get("date")
            if last_text:
                thread.last_message_text = last_text
                updated = True
            if last_date:
                try:
                    thread.last_message_date = datetime.fromisoformat(
                        last_date.replace("Z", "+00:00")
                    )
                    updated = True
                except ValueError:
                    pass

        if updated:
            thread.updated_at = datetime.utcnow()
            thread.last_sync = datetime.utcnow()

        return updated

    def get_thread(self, thread_id: int, company_id: int) -> Dict:
        """Obtém detalhes de uma thread/conversa"""
        try:
            thread = self.db.query(MLMessageThread).filter(
                MLMessageThread.id == thread_id,
                MLMessageThread.company_id == company_id
            ).first()
            
            if not thread:
                return {
                    "success": False,
                    "error": "Conversa não encontrada"
                }
            
            # Buscar mensagens da thread
            messages = self.db.query(MLMessage).filter(
                MLMessage.thread_id == thread_id
            ).order_by(MLMessage.message_date).all()
            
            thread_dict = self._thread_to_dict(thread)
            thread_dict["messages"] = [self._message_to_dict(m) for m in messages]
            
            return {
                "success": True,
                "thread": thread_dict
            }
        except Exception as e:
            logger.error(f"Erro ao buscar thread {thread_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_message(self, package_id: str, reason: str, message_text: str,
                      company_id: int, user_id: int) -> Dict:
        """Cria uma nova mensagem pós-venda"""
        try:
            access_token = self.service._get_access_token(user_id, ml_account.id, company_id)
            if not access_token:
                return {
                    "success": False,
                    "error": "Token de acesso não encontrado ou expirado"
                }
            
            # Buscar account ML baseado no package/thread criado
            ml_accounts = self.db.query(MLAccount).filter(
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            ).all()
            
            if not ml_accounts:
                return {
                    "success": False,
                    "error": "Nenhuma conta ML ativa encontrada"
                }
            
            ml_account = ml_accounts[0]  # Usar primeira conta ativa
            seller_id = str(ml_account.ml_user_id)
            # buyer_id precisa ser fornecido pelo frontend ou extraído do package_id/order_id
            # Por enquanto, vamos tentar sem buyer_id primeiro e deixar o serviço buscar
            buyer_id = None  # Será necessário obter do frontend ou da API
            
            result = self.service.create_message_thread(
                package_id, 
                reason, 
                message_text, 
                access_token,
                seller_id=seller_id,
                buyer_id=buyer_id
            )
            
            if "error" in result:
                return {
                    "success": False,
                    "error": result["error"]
                }
            
            # Tentar salvar no banco se possível
            try:
                self.service.save_thread_to_db(result, company_id, ml_account.id, seller_id)
            except Exception as e:
                logger.warning(f"Erro ao salvar thread no banco: {e}")
            
            return {
                "success": True,
                "thread": result
            }
        except Exception as e:
            logger.error(f"Erro ao criar mensagem: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def send_message(self, thread_id: int, message_text: str,
                    company_id: int, user_id: int) -> Dict:
        """Envia uma mensagem em uma conversa existente"""
        try:
            # Buscar thread no banco
            thread = self.db.query(MLMessageThread).filter(
                MLMessageThread.id == thread_id,
                MLMessageThread.company_id == company_id
            ).first()
            
            if not thread:
                return {
                    "success": False,
                    "error": "Conversa não encontrada"
                }
            
            access_token = self.service._get_access_token(user_id)
            if not access_token:
                return {
                    "success": False,
                    "error": "Token de acesso não encontrado ou expirado"
                }
            
            # Obter seller_id e buyer_id da thread
            ml_account = self.db.query(MLAccount).filter(
                MLAccount.id == thread.ml_account_id
            ).first()
            
            if not ml_account:
                return {
                    "success": False,
                    "error": "Conta ML não encontrada"
                }
            
            seller_id = str(ml_account.ml_user_id)
            buyer_id = str(thread.ml_buyer_id) if thread.ml_buyer_id else None
            
            result = self.service.send_message(
                thread.ml_package_id, 
                message_text, 
                access_token,
                seller_id=seller_id,
                buyer_id=buyer_id
            )
            
            if "error" in result:
                return {
                    "success": False,
                    "error": result["error"]
                }
            
            # Atualizar thread e mensagens no banco
            try:
                # Buscar detalhes atualizados
                thread_details = self.service.get_thread_messages(thread.ml_package_id, access_token, seller_id=seller_id)
                if thread_details:
                    thread_data = {"id": thread.ml_package_id, "package_id": thread.ml_package_id}
                    thread_data.update(thread_details)
                    self.service.save_thread_to_db(thread_data, company_id, thread.ml_account_id, str(ml_account.ml_user_id))
            except Exception as e:
                logger.warning(f"Erro ao atualizar thread no banco: {e}")
            
            return {
                "success": True,
                "message": result
            }
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def sync_messages(self, company_id: int, user_id: int, ml_account_id: int = None,
                     date_from: Optional[str] = None, date_to: Optional[str] = None,
                     fetch_all: bool = True) -> Dict:
        """
        Sincroniza mensagens pós-venda
        
        Args:
            company_id: ID da empresa
            user_id: ID do usuário
            ml_account_id: ID específico da conta ML (opcional)
            date_from: Data inicial para filtrar mensagens (formato ISO: YYYY-MM-DD)
            date_to: Data final para filtrar mensagens (formato ISO: YYYY-MM-DD)
            fetch_all: Se True, busca todas as páginas disponíveis (padrão: True)
        """
        try:
            result = self.service.sync_messages(
                company_id, 
                user_id, 
                ml_account_id,
                date_from=date_from,
                date_to=date_to,
                fetch_all=fetch_all
            )
            
            global_logger.log_event(
                event_type="messages_synced",
                data={
                    "company_id": company_id,
                    "ml_account_id": ml_account_id,
                    "synced_count": result.get("synced", 0),
                    "processed_count": result.get("processed", 0),
                    "date_from": date_from,
                    "date_to": date_to,
                    "fetch_all": fetch_all,
                    "errors": result.get("errors"),
                    "description": f"Sincronização de mensagens concluída: {result.get('synced', 0)}/{result.get('processed', 0)} conversas"
                },
                company_id=company_id,
                success=result.get("success", False),
                error_message=result.get("error")
            )
            
            return result
        except Exception as e:
            logger.error(f"Erro ao sincronizar mensagens: {e}", exc_info=True)
            global_logger.log_event(
                event_type="messages_sync_error",
                data={
                    "company_id": company_id,
                    "error": str(e)
                },
                company_id=company_id,
                success=False,
                error_message=str(e)
            )
            return {
                "success": False,
                "error": str(e),
                "synced": 0
            }
    
    def get_reasons(self, user_id: int, ml_account_id: Optional[int] = None) -> Dict:
        """Obtém motivos disponíveis para iniciar comunicação"""
        try:
            account = None
            company_id = None
            if ml_account_id:
                account = (
                    self.db.query(MLAccount)
                    .filter(MLAccount.id == ml_account_id)
                    .first()
                )
                if not account:
                    return {
                        "success": False,
                        "error": "Conta ML não encontrada",
                        "reasons": []
                    }
                company_id = account.company_id

            access_token = self.service._get_access_token(user_id, ml_account_id, company_id)
            if not access_token:
                return {
                    "success": False,
                    "error": "Token de acesso não encontrado ou expirado",
                    "reasons": []
                }
            
            reasons = self.service.get_reasons_to_communicate(access_token)
            
            return {
                "success": True,
                "reasons": reasons
            }
        except Exception as e:
            logger.error(f"Erro ao buscar motivos: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "reasons": []
            }
    
    def delete_thread(self, thread_id: int, company_id: int) -> Dict:
        """Remove uma conversa e suas mensagens do banco"""
        try:
            thread = (
                self.db.query(MLMessageThread)
                .filter(
                    MLMessageThread.id == thread_id,
                    MLMessageThread.company_id == company_id,
                )
                .first()
            )

            if not thread:
                return {
                    "success": False,
                    "error": "Conversa não encontrada",
                }

            self.db.delete(thread)
            self.db.commit()

            return {"success": True}
        except Exception as e:
            logger.error(f"Erro ao remover thread {thread_id}: {e}", exc_info=True)
            self.db.rollback()
            return {
                "success": False,
                "error": str(e),
            }

    def _thread_to_dict(self, thread: MLMessageThread) -> Dict:
        """Converte thread para dicionário"""
        return {
            "id": thread.id,
            "ml_thread_id": thread.ml_thread_id,
            "ml_package_id": thread.ml_package_id,
            "ml_account_id": thread.ml_account_id,
            "ml_buyer_id": thread.ml_buyer_id,
            "buyer_nickname": thread.buyer_nickname,
            "reason": thread.reason,
            "subject": thread.subject,
            "status": thread.status.value if thread.status else "open",
            "last_message_date": thread.last_message_date.isoformat() if thread.last_message_date else None,
            "last_message_text": thread.last_message_text,
            "order_ids": thread.order_ids if thread.order_ids else [],
            "created_at": thread.created_at.isoformat() if thread.created_at else None,
            "updated_at": thread.updated_at.isoformat() if thread.updated_at else None,
            "message_count": len(thread.messages) if thread.messages else 0
        }
    
    def _message_to_dict(self, message: MLMessage) -> Dict:
        """Converte mensagem para dicionário"""
        return {
            "id": message.id,
            "ml_message_id": message.ml_message_id,
            "from_user_id": message.from_user_id,
            "from_nickname": message.from_nickname,
            "to_user_id": message.to_user_id,
            "to_nickname": message.to_nickname,
            "message_text": message.message_text,
            "message_type": message.message_type.value if message.message_type else "text",
            "is_seller": message.is_seller,
            "message_date": message.message_date.isoformat() if message.message_date else None,
            "read": message.read,
            "created_at": message.created_at.isoformat() if message.created_at else None
        }
    
    def process_notification(self, resource: str, ml_user_id: int, company_id: int) -> Dict:
        """Processa notificação de nova mensagem"""
        try:
            package_id = (resource.split('/')[-1] if resource else '').strip()
            if not package_id:
                logger.error(f"❌ Package ID vazio ou inválido: {resource}")
                return {"success": False, "error": "Package ID inválido"}

            logger.info(f"📦 Package ID normalizado: {package_id}")

            ml_account = self.db.query(MLAccount).filter(
                MLAccount.ml_user_id == str(ml_user_id),
                MLAccount.company_id == company_id
            ).first()

            if not ml_account:
                logger.error(
                    "❌ MLAccount não encontrado para ml_user_id: %s, company_id: %s",
                    ml_user_id,
                    company_id,
                )
                return {"success": False, "error": "Conta ML não encontrada"}

            existing_thread = self.db.query(MLMessageThread).filter(
                MLMessageThread.ml_thread_id == str(package_id),
                MLMessageThread.company_id == company_id
            ).first()

            token_manager = TokenManager(self.db)
            token_record = token_manager.get_token_record_for_account(ml_account.id, company_id)
            access_token = token_record.access_token if token_record else None

            if not access_token:
                logger.warning(
                    "⚠️ Token indisponível para ml_account_id=%s. Criando registro básico do thread.",
                    ml_account.id,
                )
                if existing_thread:
                    return {"success": True, "thread_id": existing_thread.id, "pending_sync": True}

                stub_data = {
                    "id": package_id,
                    "package_id": package_id,
                    "status": "open",
                    "reason": "post_sale",
                    "subject": None,
                    "buyer": {},
                    "messages": [],
                    "orders": [],
                    "metadata": {
                        "pending_sync": True,
                        "created_at": datetime.utcnow().isoformat(),
                        "source": "notification_stub",
                        "details": "token_unavailable"
                    }
                }
                saved_stub = self.service.save_thread_to_db(stub_data, company_id, ml_account.id, str(ml_user_id))
                if saved_stub:
                    global_logger.log_event(
                        event_type="message_notification_stub",
                        data={
                            "ml_package_id": package_id,
                            "ml_account_id": ml_account.id,
                            "thread_id": saved_stub.id,
                            "description": "Thread criado sem detalhes por ausência de token",
                        },
                        company_id=company_id,
                        success=True,
                    )
                    return {"success": True, "thread_id": saved_stub.id, "pending_sync": True}
                return {"success": False, "error": "Thread não pôde ser registrado"}

            logger.info(f"✅ Token válido obtido (ml_account_id={ml_account.id})")

            seller_id = str(ml_account.ml_user_id)
            thread_details = self.service.get_thread_messages(package_id, access_token, seller_id=seller_id)

            if thread_details:
                logger.info("✅ Detalhes do thread recebidos da API; salvando informações completas")
                thread_data = {"id": package_id, "package_id": package_id}
                thread_data.update(thread_details)
                thread_data.setdefault("metadata", {})
                thread_data["metadata"].update({
                    "pending_sync": False,
                    "last_sync": datetime.utcnow().isoformat(),
                    "source": "notification_fetch"
                })

                saved = self.service.save_thread_to_db(thread_data, company_id, ml_account.id, str(ml_user_id))
                if saved:
                    global_logger.log_event(
                        event_type="message_notification_processed",
                        data={
                            "ml_package_id": package_id,
                            "ml_account_id": ml_account.id,
                            "action": "created" if not existing_thread else "updated",
                            "thread_id": saved.id,
                            "description": f"Thread {package_id} sincronizado com sucesso"
                        },
                        company_id=company_id,
                        success=True
                    )
                    return {"success": True, "thread_id": saved.id}
                logger.error("❌ Falha ao salvar thread completo no banco")
            else:
                logger.warning(
                    "⚠️ API não retornou detalhes para o pacote %s. Criando registro básico.",
                    package_id,
                )
                if existing_thread:
                    return {"success": True, "thread_id": existing_thread.id, "pending_sync": True}

                stub_data = {
                    "id": package_id,
                    "package_id": package_id,
                    "status": "open",
                    "reason": "post_sale",
                    "subject": None,
                    "buyer": {},
                    "messages": [],
                    "orders": [],
                    "metadata": {
                        "pending_sync": True,
                        "created_at": datetime.utcnow().isoformat(),
                        "source": "notification_stub",
                        "details": "api_unavailable"
                    }
                }
                saved_stub = self.service.save_thread_to_db(stub_data, company_id, ml_account.id, str(ml_user_id))
                if saved_stub:
                    global_logger.log_event(
                        event_type="message_notification_stub",
                        data={
                            "ml_package_id": package_id,
                            "ml_account_id": ml_account.id,
                            "thread_id": saved_stub.id,
                            "description": "Thread criado sem detalhes (API indisponível)",
                        },
                        company_id=company_id,
                        success=True,
                    )
                    return {"success": True, "thread_id": saved_stub.id, "pending_sync": True}

            return {"success": False, "error": "Falha ao processar notificação"}
            
        except Exception as e:
            logger.error(f"❌ ========== EXCEÇÃO EM process_notification ==========")
            logger.error(f"❌ Package ID: {resource}")
            logger.error(f"❌ ML User ID: {ml_user_id}")
            logger.error(f"❌ Company ID: {company_id}")
            logger.error(f"❌ Erro: {str(e)}")
            logger.error(f"❌ Tipo: {type(e).__name__}")
            logger.error(f"❌ Traceback completo:", exc_info=True)
            
            global_logger.log_event(
                event_type="message_notification_error",
                data={
                    "ml_package_id": resource,
                    "ml_user_id": ml_user_id,
                    "company_id": company_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                company_id=company_id,
                success=False,
                error_message=str(e)
            )
            logger.error(f"❌ ========== FIM DA EXCEÇÃO ==========")
            return {
                "success": False,
                "error": str(e)
            }

