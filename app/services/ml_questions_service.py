"""
Service para gerenciar perguntas do Mercado Livre
"""
import logging
import requests
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.saas_models import MLQuestion, MLQuestionStatus, MLAccount, MLAccountStatus, User
from app.services.token_manager import TokenManager

logger = logging.getLogger(__name__)

class MLQuestionsService:
    """Service para gerenciar perguntas do Mercado Livre"""
    
    def __init__(self, db: Session):
        self.db = db
        self.base_url = "https://api.mercadolibre.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
    
    def get_question_details(self, question_id: int, access_token: str) -> Dict:
        """Busca detalhes de uma pergunta específica"""
        try:
            url = f"{self.base_url}/questions/{question_id}"
            headers = {
                **self.headers,
                "Authorization": f"Bearer {access_token}"
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erro ao buscar pergunta {question_id}: {response.status_code} - {response.text[:200]}")
                return {}
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes da pergunta {question_id}: {e}", exc_info=True)
            return {}
    
    def get_questions_from_item(self, item_id: str, access_token: str) -> List[Dict]:
        """Busca perguntas de um item específico"""
        try:
            url = f"{self.base_url}/questions/search"
            headers = {
                **self.headers,
                "Authorization": f"Bearer {access_token}"
            }
            
            params = {"item": item_id}
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("questions", [])
            elif response.status_code == 404:
                logger.info(
                    "Nenhuma pergunta encontrada para o item %s (404). Resposta: %s",
                    item_id,
                    response.text[:200] if hasattr(response, "text") else "",
                )
                return []
            else:
                logger.error(
                    "Erro ao buscar perguntas do item %s: %s - %s",
                    item_id,
                    response.status_code,
                    response.text[:200] if hasattr(response, "text") else "",
                )
                return []
        except Exception as e:
            logger.error(f"Erro ao buscar perguntas do item {item_id}: {e}", exc_info=True)
            return []
    
    def get_all_questions(self, ml_user_id: str, access_token: str, status: str = None, limit: int = 50) -> List[Dict]:
        """Busca todas as perguntas do vendedor"""
        try:
            url = f"{self.base_url}/questions/search"
            headers = {
                **self.headers,
                "Authorization": f"Bearer {access_token}"
            }
            
            params = {
                "seller_id": ml_user_id,
                "limit": limit
            }
            if status:
                params["status"] = status
            
            all_questions = []
            offset = 0
            
            while True:
                params["offset"] = offset
                response = requests.get(url, headers=headers, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    questions = data.get("questions", [])
                    
                    if not questions:
                        break
                    
                    all_questions.extend(questions)
                    total = data.get("total", 0)
                    
                    offset += len(questions)
                    if offset >= total:
                        break
                else:
                    if response.status_code == 404:
                        logger.info(
                            "Nenhuma pergunta encontrada (404) para usuário %s com status %s. Resposta: %s",
                            ml_user_id,
                            params.get("status"),
                            response.text[:200] if hasattr(response, "text") else "",
                        )
                        break
                    logger.error(
                        "Erro ao buscar perguntas para usuário %s: %s - %s",
                        ml_user_id,
                        response.status_code,
                        response.text[:200] if hasattr(response, "text") else "",
                    )
                    break
            
            return all_questions
        except Exception as e:
            logger.error(f"Erro ao buscar todas as perguntas: {e}", exc_info=True)
            return []
    
    def answer_question(self, question_id: int, answer_text: str, access_token: str) -> Dict:
        """Responde uma pergunta"""
        try:
            url = f"{self.base_url}/answers"
            headers = {
                **self.headers,
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "question_id": question_id,
                "text": answer_text
            }
            response = requests.post(url, headers=headers, json=data, timeout=15)
            
            if response.status_code in (200, 201):
                result = response.json()
                logger.info(f"✅ Pergunta {question_id} respondida com sucesso")
                return {"success": True, "data": result}
            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    if error_data.get("error") == "not_unanswered_question":
                        logger.warning(
                            "⚠️ Pergunta %s já foi respondida ou não está mais disponível para resposta.",
                            question_id,
                        )
                        return {
                            "success": False,
                            "message": "Pergunta já foi respondida ou não está mais disponível para resposta.",
                            "code": "not_unanswered_question",
                        }
                except Exception:
                    pass
                logger.error(f"Erro ao responder pergunta {question_id}: {response.status_code} - {response.text[:200]}")
                return {
                    "success": False,
                    "message": response.text,
                    "code": "api_error",
                    "status_code": response.status_code,
                }
            else:
                logger.error(f"Erro ao responder pergunta {question_id}: {response.status_code} - {response.text[:200]}")
                return {
                    "success": False,
                    "message": response.text,
                    "code": "api_error",
                    "status_code": response.status_code,
                }
        except Exception as e:
            logger.error(f"Erro ao responder pergunta {question_id}: {e}", exc_info=True)
            return {}
    
    def get_item_details(self, item_id: str, access_token: str) -> Optional[Dict]:
        """Busca detalhes de um item para enriquecer a pergunta"""
        try:
            if not item_id:
                return None

            url = f"{self.base_url}/items/{item_id}"
            headers = {
                **self.headers,
                "Authorization": f"Bearer {access_token}"
            }

            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    "Erro ao buscar detalhes do item %s: %s - %s",
                    item_id,
                    response.status_code,
                    response.text[:200]
                )
                return None
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes do item {item_id}: {e}", exc_info=True)
            return None

    def save_question_to_db(self, question_data: Dict, company_id: int, ml_account_id: int) -> Optional[MLQuestion]:
        """Salva ou atualiza pergunta no banco"""
        try:
            ml_question_id = question_data.get("id")
            if not ml_question_id:
                logger.warning("Dados da pergunta não contêm ID")
                return None
            
            # Buscar se já existe
            question = self.db.query(MLQuestion).filter(
                MLQuestion.ml_question_id == ml_question_id,
                MLQuestion.company_id == company_id
            ).first()
            
            # Status da pergunta
            status_str = question_data.get("status", "UNANSWERED")
            try:
                status = MLQuestionStatus[status_str]
            except KeyError:
                status = MLQuestionStatus.UNANSWERED
            
            # Dados da resposta
            answer_data = question_data.get("answer", {})
            answer_text = answer_data.get("text") if answer_data else None
            answer_status = answer_data.get("status") if answer_data else None
            
            answer_date = None
            if answer_data and answer_data.get("date_created"):
                try:
                    date_str = answer_data["date_created"]
                    if date_str.endswith("Z"):
                        date_str = date_str.replace("Z", "+00:00")
                    answer_date = datetime.fromisoformat(date_str)
                except Exception as e:
                    logger.warning(f"Erro ao parsear data de resposta: {e}")
            
            # Dados do comprador
            from_data = question_data.get("from", {})
            
            # Dados do item
            item_data = question_data.get("item", {})
            
            # Parsear data da pergunta
            question_date = datetime.now()
            if question_data.get("date_created"):
                try:
                    date_str = question_data["date_created"]
                    if date_str.endswith("Z"):
                        date_str = date_str.replace("Z", "+00:00")
                    question_date = datetime.fromisoformat(date_str)
                except Exception as e:
                    logger.warning(f"Erro ao parsear data da pergunta: {e}")
            
            if question:
                # Atualizar existente
                question.question_text = question_data.get("text", "")
                question.status = status
                question.answer_text = answer_text
                question.answer_status = answer_status
                question.answered_at = answer_date
                question.answer_date = answer_date
                question.buyer_nickname = from_data.get("nickname") if from_data else None
                question.buyer_answered_questions = from_data.get("answered_questions") if from_data else None
                question.item_title = item_data.get("title") if item_data else question.item_title
                question.item_thumbnail = item_data.get("thumbnail") if item_data else question.item_thumbnail
                question.question_data = question_data
                question.updated_at = datetime.now()
                question.last_sync = datetime.now()
                question.deleted_from_list = question_data.get("deleted_from_list", False)
                question.hold = question_data.get("hold", False)
                
                # Atualizar ml_item_id e ml_seller_id se necessário
                if item_data and item_data.get("id") and not question.ml_item_id:
                    question.ml_item_id = str(item_data.get("id"))
                if question_data.get("seller_id") and not question.ml_seller_id:
                    question.ml_seller_id = str(question_data.get("seller_id"))
            else:
                # Extrair item_id do objeto item
                item_id = None
                if item_data and item_data.get("id"):
                    item_id = str(item_data.get("id"))
                elif question_data.get("item_id"):
                    item_id = str(question_data.get("item_id"))
                
                # Validar que temos item_id (campo obrigatório)
                if not item_id:
                    logger.warning(f"Item ID não encontrado na pergunta {ml_question_id}")
                    # Tentar usar um valor padrão ou buscar de outra fonte
                    # Por enquanto, vamos usar "UNKNOWN" para não quebrar o banco
                    item_id = "UNKNOWN"
                
                # Obter seller_id da conta ML (ml_user_id)
                # Se não estiver disponível na resposta da API, usar o ml_user_id da conta
                seller_id = ""
                if question_data.get("seller_id"):
                    seller_id = str(question_data.get("seller_id"))
                else:
                    # Buscar ml_account para obter ml_user_id
                    ml_account = self.db.query(MLAccount).filter(MLAccount.id == ml_account_id).first()
                    if ml_account:
                        seller_id = str(ml_account.ml_user_id)
                
                # Validar que temos seller_id (campo obrigatório)
                if not seller_id:
                    logger.warning(f"Seller ID não encontrado para pergunta {ml_question_id}")
                    seller_id = "UNKNOWN"
                
                # Criar novo
                question = MLQuestion(
                    company_id=company_id,
                    ml_account_id=ml_account_id,
                    ml_question_id=ml_question_id,
                    ml_item_id=item_id,
                    ml_seller_id=seller_id,
                    ml_buyer_id=str(from_data.get("id", "")) if from_data and from_data.get("id") else None,
                    question_text=question_data.get("text", ""),
                    status=status,
                    answer_text=answer_text,
                    answer_status=answer_status,
                    answered_at=answer_date,
                    answer_date=answer_date,
                    item_title=item_data.get("title") if item_data else None,
                    item_thumbnail=item_data.get("thumbnail") if item_data else None,
                    buyer_nickname=from_data.get("nickname") if from_data else None,
                    buyer_answered_questions=from_data.get("answered_questions") if from_data else None,
                    deleted_from_list=question_data.get("deleted_from_list", False),
                    hold=question_data.get("hold", False),
                    question_date=question_date,
                    question_data=question_data,
                    last_sync=datetime.now()
                )
                self.db.add(question)
            
            self.db.commit()
            self.db.refresh(question)
            
            logger.info(f"✅ Pergunta {ml_question_id} salva/atualizada no banco")
            return question
            
        except Exception as e:
            logger.error(f"Erro ao salvar pergunta no banco: {e}", exc_info=True)
            self.db.rollback()
            return None
    
    def sync_questions(self, company_id: int, user_id: int, ml_account_id: int = None, status: str = None) -> Dict:
        """Sincroniza todas as perguntas do vendedor (todas as contas ou uma conta específica)"""
        try:
            # Obter token
            token_manager = TokenManager(self.db)
            
            # Buscar contas ML ativas da empresa
            query = self.db.query(MLAccount).filter(
                MLAccount.company_id == company_id,
                MLAccount.status == MLAccountStatus.ACTIVE
            )
            
            if ml_account_id:
                # Validar que a conta ML pertence à empresa do usuário logado
                query = query.filter(MLAccount.id == ml_account_id)
            
            ml_accounts = query.all()
            
            if not ml_accounts:
                if ml_account_id:
                    return {
                        "success": False,
                        "error": f"Conta ML {ml_account_id} não encontrada ou não pertence à sua empresa"
                    }
                else:
                    return {
                        "success": False,
                        "error": "Nenhuma conta ML ativa encontrada para esta empresa"
                    }
            
            total_questions = 0
            total_saved = 0
            total_errors = 0
            accounts_synced = []
            accounts_failed = []
            
            # Sincronizar cada conta
            for ml_account in ml_accounts:
                try:
                    token_record = token_manager.get_token_record_for_account(ml_account.id, company_id)
                    if not token_record or not token_record.access_token:
                        logger.warning(
                            "Token válido não encontrado para conta ML %s (%s)",
                            ml_account.id,
                            ml_account.nickname,
                        )
                        accounts_failed.append({
                            "account_id": ml_account.id,
                            "nickname": ml_account.nickname,
                            "error": "Token de acesso não encontrado ou inválido"
                        })
                        continue
                    
                    access_token = token_record.access_token
                    
                    # Buscar todas as perguntas desta conta
                    questions = self.get_all_questions(str(ml_account.ml_user_id), access_token, status)
                    
                    if not questions:
                        logger.info(
                            "Nenhuma pergunta retornada para conta %s (%s) com status=%s",
                            ml_account.id,
                            ml_account.nickname,
                            status or "ALL",
                        )
                    
                    saved_count = 0
                    error_count = 0
                    
                    for question_data in questions:
                        result = self.save_question_to_db(question_data, company_id, ml_account.id)
                        if result:
                            saved_count += 1
                        else:
                            error_count += 1
                    
                    total_questions += len(questions)
                    total_saved += saved_count
                    total_errors += error_count
                    
                    accounts_synced.append({
                        "account_id": ml_account.id,
                        "nickname": ml_account.nickname,
                        "questions": len(questions),
                        "saved": saved_count,
                        "errors": error_count
                    })
                    
                except Exception as e:
                    logger.error(f"Erro ao sincronizar conta ML {ml_account.id}: {e}", exc_info=True)
                    accounts_failed.append({
                        "account_id": ml_account.id,
                        "nickname": ml_account.nickname,
                        "error": str(e)
                    })
                    total_errors += 1
            
            return {
                "success": True,
                "total": total_questions,
                "saved": total_saved,
                "errors": total_errors,
                "accounts_synced": accounts_synced,
                "accounts_failed": accounts_failed,
                "total_accounts": len(ml_accounts)
            }
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar perguntas: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

