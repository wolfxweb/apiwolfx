"""
Controller para gerenciar perguntas do Mercado Livre
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.services.ml_questions_service import MLQuestionsService
from app.models.saas_models import MLQuestion, MLQuestionStatus, MLAccount, MLAccountStatus, User
from app.services.token_manager import TokenManager
from app.utils.notification_logger import global_logger

logger = logging.getLogger(__name__)

class MLQuestionsController:
    """Controller para gerenciar perguntas"""
    
    def __init__(self, db: Session):
        self.db = db
        self.service = MLQuestionsService(db)
    
    def get_questions(
        self,
        company_id: int,
        ml_account_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> Dict:
        """Lista perguntas da empresa (garantindo que ml_account_id pertence ao company_id)"""
        try:
            query = self.db.query(MLQuestion).filter(MLQuestion.company_id == company_id)
            
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
                        "questions": [],
                        "total": 0
                    }
                
                query = query.filter(MLQuestion.ml_account_id == ml_account_id)
            
            if status:
                try:
                    status_enum = MLQuestionStatus[status]
                    query = query.filter(MLQuestion.status == status_enum)
                except KeyError:
                    pass
            
            total_items = query.count()
            questions = (
                query.order_by(MLQuestion.question_date.desc())
                .limit(limit)
                .all()
            )
            
            return {
                "success": True,
                "questions": [self._question_to_dict(q) for q in questions],
                "total": total_items,
            }
        except Exception as e:
            logger.error(f"Erro ao listar perguntas: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "questions": []
            }
    
    def get_question(self, question_id: int, company_id: int) -> Dict:
        """Obtém detalhes de uma pergunta"""
        try:
            question = self.db.query(MLQuestion).filter(
                MLQuestion.id == question_id,
                MLQuestion.company_id == company_id
            ).first()
            
            if not question:
                return {
                    "success": False,
                    "error": "Pergunta não encontrada"
                }
            
            return {
                "success": True,
                "question": self._question_to_dict(question)
            }
        except Exception as e:
            logger.error(f"Erro ao buscar pergunta: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def answer_question(self, question_id: int, answer_text: str, company_id: int, user_id: int) -> Dict:
        """Responde uma pergunta"""
        try:
            # Buscar pergunta
            question = self.db.query(MLQuestion).filter(
                MLQuestion.id == question_id,
                MLQuestion.company_id == company_id
            ).first()
            
            if not question:
                return {
                    "success": False,
                    "error": "Pergunta não encontrada"
                }
            
            # Obter token
            token_manager = TokenManager(self.db)
            access_token = token_manager.get_valid_token(user_id)
            
            if not access_token:
                return {
                    "success": False,
                    "error": "Token de acesso não encontrado"
                }
            
            # Responder via API
            result = self.service.answer_question(question.ml_question_id, answer_text, access_token)
            
            if result:
                # Atualizar no banco
                from datetime import datetime
                now = datetime.now()
                question.answer_text = answer_text
                question.status = MLQuestionStatus.ANSWERED
                question.answer_status = "ACTIVE"
                question.answered_at = now
                question.answer_date = now
                question.updated_at = now
                
                # Buscar dados atualizados da API
                updated_data = self.service.get_question_details(question.ml_question_id, access_token)
                if updated_data:
                    self.service.save_question_to_db(updated_data, company_id, question.ml_account_id)
                
                self.db.commit()
                
                return {
                    "success": True,
                    "message": "Pergunta respondida com sucesso"
                }
            else:
                return {
                    "success": False,
                    "error": "Erro ao responder pergunta na API do Mercado Livre"
                }
                
        except Exception as e:
            logger.error(f"Erro ao responder pergunta: {e}", exc_info=True)
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def sync_questions(self, company_id: int, user_id: int, ml_account_id: Optional[int] = None, status: Optional[str] = None) -> Dict:
        """Sincroniza perguntas com o Mercado Livre (todas as contas ou uma conta específica)"""
        try:
            result = self.service.sync_questions(company_id, user_id, ml_account_id, status)
            return result
        except Exception as e:
            logger.error(f"Erro ao sincronizar perguntas: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_notification(self, resource: str, ml_user_id: int, company_id: int) -> bool:
        """Processa notificação de pergunta (chamado pelo notification controller)"""
        question_id = None
        ml_account_id = None
        
        try:
            # Extrair question_id do resource: "/questions/123456789"
            question_id = int(resource.split("/")[-1])
            
            logger.info(f"❓ Processando notificação de pergunta - Question ID: {question_id}, ML User ID: {ml_user_id}, Company ID: {company_id}")
            
            # Buscar conta ML
            ml_account = self.db.query(MLAccount).filter(
                MLAccount.company_id == company_id,
                MLAccount.ml_user_id == str(ml_user_id),
                MLAccount.status == MLAccountStatus.ACTIVE
            ).first()
            
            if not ml_account:
                error_msg = f"Conta ML não encontrada para ml_user_id: {ml_user_id}, company_id: {company_id}"
                logger.warning(error_msg)
                global_logger.log_event(
                    event_type="question_processed",
                    data={
                        "question_id": question_id,
                        "ml_account_id": None,
                        "action": "error",
                        "description": error_msg
                    },
                    company_id=company_id,
                    success=False,
                    error_message=error_msg
                )
                return False
            
            ml_account_id = ml_account.id
            logger.info(f"✅ Conta ML encontrada: ID {ml_account_id}, Nickname: {ml_account.nickname}")
            
            # Obter token
            token_manager = TokenManager(self.db)
            user = self.db.query(User).filter(User.company_id == company_id).first()
            if not user:
                error_msg = f"Usuário não encontrado para company_id: {company_id}"
                logger.warning(error_msg)
                global_logger.log_event(
                    event_type="question_processed",
                    data={
                        "question_id": question_id,
                        "ml_account_id": ml_account_id,
                        "action": "error",
                        "description": error_msg
                    },
                    company_id=company_id,
                    success=False,
                    error_message=error_msg
                )
                return False
            
            logger.info(f"✅ Usuário encontrado: ID {user.id}, Email: {user.email}")
            
            access_token = token_manager.get_valid_token(user.id)
            if not access_token:
                error_msg = f"Token não encontrado para company_id: {company_id}, user_id: {user.id}"
                logger.warning(error_msg)
                global_logger.log_event(
                    event_type="question_processed",
                    data={
                        "question_id": question_id,
                        "ml_account_id": ml_account_id,
                        "action": "error",
                        "description": error_msg
                    },
                    company_id=company_id,
                    success=False,
                    error_message=error_msg
                )
                return False
            
            logger.info(f"✅ Token obtido com sucesso (tamanho: {len(access_token)} caracteres)")
            
            # Buscar detalhes da pergunta na API
            logger.info(f"📡 Buscando detalhes da pergunta {question_id} na API do Mercado Livre...")
            question_data = self.service.get_question_details(question_id, access_token)
            
            if not question_data:
                error_msg = f"Falha ao buscar detalhes da pergunta {question_id} na API do Mercado Livre"
                logger.error(error_msg)
                global_logger.log_event(
                    event_type="question_processed",
                    data={
                        "question_id": question_id,
                        "ml_account_id": ml_account_id,
                        "action": "error",
                        "description": error_msg
                    },
                    company_id=company_id,
                    success=False,
                    error_message=error_msg
                )
                return False
            
            logger.info(f"✅ Dados da pergunta recebidos da API - Status: {question_data.get('status')}, Item ID: {question_data.get('item', {}).get('id') if isinstance(question_data.get('item'), dict) else 'N/A'}")
            
            # Salvar/atualizar no banco
            logger.info(f"💾 Salvando/atualizando pergunta no banco de dados...")
            result = self.service.save_question_to_db(question_data, company_id, ml_account.id)
            
            if result:
                action = "created" if not result.id or result.id == 0 else "updated"
                logger.info(f"✅ Pergunta {question_id} processada e salva no banco - Ação: {action}, DB ID: {result.id if result else 'N/A'}")
                
                # Log detalhado de sucesso usando o logger global
                question_details = {}
                if question_data:
                    question_details = {
                        "item_id": question_data.get("item", {}).get("id") if isinstance(question_data.get("item"), dict) else None,
                        "item_title": question_data.get("item", {}).get("title") if isinstance(question_data.get("item"), dict) else None,
                        "status": question_data.get("status"),
                        "has_answer": bool(question_data.get("answer")),
                        "buyer_nickname": question_data.get("from", {}).get("nickname") if isinstance(question_data.get("from"), dict) else None
                    }
                
                global_logger.log_event(
                    event_type="question_processed",
                    data={
                        "question_id": question_id,
                        "ml_account_id": ml_account_id,
                        "action": action,
                        "db_id": result.id if result else None,
                        "description": f"Pergunta {question_id} {action} com sucesso",
                        **question_details
                    },
                    company_id=company_id,
                    success=True,
                    error_message=None
                )
                return True
            else:
                error_msg = f"Falha ao salvar pergunta {question_id} no banco de dados"
                logger.warning(error_msg)
                global_logger.log_event(
                    event_type="question_processed",
                    data={
                        "question_id": question_id,
                        "ml_account_id": ml_account_id,
                        "action": "error",
                        "description": error_msg
                    },
                    company_id=company_id,
                    success=False,
                    error_message=error_msg
                )
                return False
                
        except ValueError as e:
            error_msg = f"Erro ao extrair question_id do resource '{resource}': {e}"
            logger.error(error_msg)
            global_logger.log_event(
                event_type="question_processed",
                data={
                    "question_id": question_id or 0,
                    "ml_account_id": ml_account_id,
                    "action": "error",
                    "description": error_msg
                },
                company_id=company_id,
                success=False,
                error_message=error_msg
            )
            return False
        except Exception as e:
            error_msg = f"Erro ao processar notificação de pergunta: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            global_logger.log_event(
                event_type="question_processed",
                data={
                    "question_id": question_id or 0,
                    "ml_account_id": ml_account_id,
                    "action": "error",
                    "description": error_msg
                },
                company_id=company_id,
                success=False,
                error_message=error_msg
            )
            return False
    
    def _question_to_dict(self, question: MLQuestion) -> Dict:
        """Converte modelo MLQuestion para dicionário"""
        from datetime import datetime
        
        def format_date(dt):
            if dt:
                if isinstance(dt, datetime):
                    return dt.isoformat()
                return str(dt)
            return None
        
        return {
            "id": question.id,
            "ml_question_id": question.ml_question_id,
            "ml_item_id": question.ml_item_id,
            "ml_account_id": question.ml_account_id,
            "ml_buyer_id": question.ml_buyer_id,
            "ml_seller_id": question.ml_seller_id,
            "item_title": question.item_title,
            "item_thumbnail": question.item_thumbnail,
            "question_text": question.question_text,
            "status": question.status.value if question.status else None,
            "answer_text": question.answer_text,
            "answer_status": question.answer_status,
            "buyer_nickname": question.buyer_nickname,
            "buyer_answered_questions": question.buyer_answered_questions,
            "question_date": format_date(question.question_date),
            "answered_at": format_date(question.answered_at),
            "created_at": format_date(question.created_at),
            "updated_at": format_date(question.updated_at),
            "deleted_from_list": question.deleted_from_list,
            "hold": question.hold
        }

    def _ensure_question_item_details(self, question: MLQuestion, company_id: int) -> bool:
        """Garante que a pergunta possui dados essenciais do produto e comprador"""
        try:
            needs_title = not question.item_title or not question.item_title.strip()
            needs_thumbnail = not question.item_thumbnail or not question.item_thumbnail.strip()
            needs_buyer = not question.buyer_nickname or not question.buyer_nickname.strip() or not question.ml_buyer_id

            if not (needs_title or needs_thumbnail or needs_buyer):
                return False

            if not question.ml_item_id:
                # Ainda podemos tentar preencher via question details
                needs_item_id = True
            else:
                needs_item_id = False

            token_manager = TokenManager(self.db)
            token_record = token_manager.get_token_record_for_account(question.ml_account_id, company_id)
            if not token_record:
                logger.debug(
                    "Token não encontrado para enriquecer pergunta %s (ml_account_id=%s)",
                    question.id,
                    question.ml_account_id,
                )
                return False

            # Buscar detalhes completos da pergunta quando faltarem dados do comprador ou item
            question_data = None
            buyer_updated = False
            if needs_buyer or needs_item_id or needs_title or needs_thumbnail:
                question_data = self.service.get_question_details(question.ml_question_id, token_record.access_token)
                if question_data:
                    from_data = question_data.get("from", {})
                    if from_data:
                        if needs_buyer and from_data.get("nickname"):
                            question.buyer_nickname = from_data.get("nickname")
                            buyer_updated = True
                        if from_data.get("id"):
                            question.ml_buyer_id = str(from_data.get("id"))
                            buyer_updated = True
                    if not question.question_text and question_data.get("text"):
                        question.question_text = question_data.get("text")
                    if (needs_item_id or not question.ml_item_id) and question_data.get("item_id"):
                        question.ml_item_id = str(question_data.get("item_id"))
                    # Algumas respostas trazem campos básicos do item
                    item_block = question_data.get("item") if isinstance(question_data.get("item"), dict) else None
                    if item_block:
                        if needs_title and item_block.get("title"):
                            question.item_title = item_block.get("title")
                            needs_title = False
                        if needs_thumbnail and item_block.get("thumbnail"):
                            question.item_thumbnail = item_block.get("thumbnail")
                            needs_thumbnail = False

            # Após possível hidratação, reavaliar se ainda precisamos buscar o item completo
            if not question.ml_item_id:
                return buyer_updated

            item_data = None
            if needs_title or needs_thumbnail:
                item_data = self.service.get_item_details(question.ml_item_id, token_record.access_token)
                if not item_data:
                    return buyer_updated

            updated = False
            if item_data:
                if needs_title and item_data.get("title"):
                    question.item_title = item_data["title"]
                    updated = True

                if needs_thumbnail:
                    thumb = item_data.get("secure_thumbnail") or item_data.get("thumbnail")
                    if not thumb and item_data.get("pictures"):
                        first_pic = item_data["pictures"][0]
                        thumb = first_pic.get("secure_url") or first_pic.get("url")
                    if thumb:
                        question.item_thumbnail = thumb
                        updated = True

            if buyer_updated:
                updated = True

            if updated:
                question.updated_at = datetime.utcnow()
                return True
            return False
        except Exception as e:
            logger.error("Erro ao enriquecer dados da pergunta %s: %s", question.id, e, exc_info=True)
            return False

