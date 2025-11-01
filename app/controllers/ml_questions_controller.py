"""
Controller para gerenciar perguntas do Mercado Livre
"""
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.services.ml_questions_service import MLQuestionsService
from app.models.saas_models import MLQuestion, MLQuestionStatus, MLAccount, MLAccountStatus, User
from app.services.token_manager import TokenManager

logger = logging.getLogger(__name__)

class MLQuestionsController:
    """Controller para gerenciar perguntas"""
    
    def __init__(self, db: Session):
        self.db = db
        self.service = MLQuestionsService(db)
    
    def get_questions(self, company_id: int, ml_account_id: Optional[int] = None, 
                     status: Optional[str] = None, limit: int = 50) -> Dict:
        """Lista perguntas da empresa"""
        try:
            query = self.db.query(MLQuestion).filter(MLQuestion.company_id == company_id)
            
            if ml_account_id:
                query = query.filter(MLQuestion.ml_account_id == ml_account_id)
            
            if status:
                try:
                    status_enum = MLQuestionStatus[status]
                    query = query.filter(MLQuestion.status == status_enum)
                except KeyError:
                    pass
            
            questions = query.order_by(MLQuestion.question_date.desc()).limit(limit).all()
            
            return {
                "success": True,
                "questions": [self._question_to_dict(q) for q in questions],
                "total": len(questions)
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
    
    def sync_questions(self, company_id: int, ml_account_id: int, user_id: int, status: Optional[str] = None) -> Dict:
        """Sincroniza perguntas com o Mercado Livre"""
        try:
            result = self.service.sync_questions(company_id, ml_account_id, user_id, status)
            return result
        except Exception as e:
            logger.error(f"Erro ao sincronizar perguntas: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_notification(self, resource: str, ml_user_id: int, company_id: int) -> bool:
        """Processa notificação de pergunta (chamado pelo notification controller)"""
        try:
            # Extrair question_id do resource: "/questions/123456789"
            question_id = int(resource.split("/")[-1])
            
            # Buscar conta ML
            ml_account = self.db.query(MLAccount).filter(
                MLAccount.company_id == company_id,
                MLAccount.ml_user_id == str(ml_user_id),
                MLAccount.status == MLAccountStatus.ACTIVE
            ).first()
            
            if not ml_account:
                logger.warning(f"Conta ML não encontrada para ml_user_id: {ml_user_id}")
                return False
            
            # Obter token
            token_manager = TokenManager(self.db)
            user = self.db.query(User).filter(User.company_id == company_id).first()
            if not user:
                logger.warning(f"Usuário não encontrado para company_id: {company_id}")
                return False
            
            access_token = token_manager.get_valid_token(user.id)
            if not access_token:
                logger.warning(f"Token não encontrado para company_id: {company_id}")
                return False
            
            # Buscar detalhes da pergunta na API
            question_data = self.service.get_question_details(question_id, access_token)
            
            if question_data:
                # Salvar/atualizar no banco
                result = self.service.save_question_to_db(question_data, company_id, ml_account.id)
                
                if result:
                    logger.info(f"✅ Pergunta {question_id} processada e salva no banco")
                    return True
                else:
                    logger.error(f"❌ Erro ao salvar pergunta {question_id} no banco")
                    return False
            else:
                logger.error(f"❌ Erro ao buscar pergunta {question_id} da API")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar notificação de pergunta: {e}", exc_info=True)
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

