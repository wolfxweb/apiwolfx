"""
Controller para gerenciar assistentes OpenAI
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from app.services.openai_assistant_service import OpenAIAssistantService
from app.models.saas_models import (
    OpenAIAssistant, OpenAIAssistantThread, OpenAIAssistantUsage,
    InteractionMode, UsageStatus
)

logger = logging.getLogger(__name__)


class OpenAIAssistantController:
    """Controller para gerenciar assistentes OpenAI"""
    
    def __init__(self, db: Session):
        self.db = db
        self.service = OpenAIAssistantService(db)
    
    def list_assistants(self, active_only: bool = True) -> Dict:
        """Lista todos os assistentes"""
        try:
            query = self.db.query(OpenAIAssistant)
            
            if active_only:
                query = query.filter(OpenAIAssistant.is_active == True)
            
            assistants = query.order_by(desc(OpenAIAssistant.created_at)).all()
            
            return {
                "success": True,
                "assistants": [
                    {
                        "id": a.id,
                        "name": a.name,
                        "description": a.description,
                        "assistant_id": a.assistant_id,
                        "model": a.model,
                        "instructions": a.instructions[:200] + "..." if len(a.instructions) > 200 else a.instructions,
                        "temperature": float(a.temperature) if a.temperature else None,
                        "max_tokens": a.max_tokens,
                        "tools_config": a.tools_config,
                        "interaction_mode": a.interaction_mode.value,
                        "use_case": a.use_case,
                        "is_active": a.is_active,
                        "total_runs": a.total_runs,
                        "total_tokens_used": a.total_tokens_used,
                        "created_at": a.created_at.isoformat() if a.created_at else None,
                        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
                        "last_used_at": a.last_used_at.isoformat() if a.last_used_at else None,
                        "is_reasoning_model": a.is_reasoning_model()
                    }
                    for a in assistants
                ]
            }
        except Exception as e:
            logger.error(f"❌ Erro ao listar assistentes: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def create_assistant(
        self,
        name: str,
        description: Optional[str],
        instructions: str,
        model: str = "gpt-5.1",
        temperature: Optional[float] = None,
        max_tokens: int = 4000,
        tools: Optional[List[Dict]] = None,
        interaction_mode: str = "report",
        use_case: Optional[str] = None
    ) -> Dict:
        """Cria um novo assistente"""
        try:
            return self.service.create_assistant(
                name=name,
                description=description,
                instructions=instructions,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                interaction_mode=interaction_mode,
                use_case=use_case
            )
        except Exception as e:
            logger.error(f"❌ Erro ao criar assistente: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_assistant(self, assistant_id: int) -> Dict:
        """Obtém um assistente específico"""
        try:
            assistant = self.db.query(OpenAIAssistant).filter(
                OpenAIAssistant.id == assistant_id
            ).first()
            
            if not assistant:
                return {"success": False, "error": "Assistente não encontrado"}
            
            return {
                "success": True,
                "assistant": {
                    "id": assistant.id,
                    "name": assistant.name,
                    "description": assistant.description,
                    "assistant_id": assistant.assistant_id,
                    "model": assistant.model,
                    "instructions": assistant.instructions,
                    "temperature": float(assistant.temperature) if assistant.temperature else None,
                    "max_tokens": assistant.max_tokens,
                    "tools_config": assistant.tools_config,
                    "interaction_mode": assistant.interaction_mode.value,
                    "use_case": assistant.use_case,
                    "is_active": assistant.is_active,
                    "total_runs": assistant.total_runs,
                    "total_tokens_used": assistant.total_tokens_used,
                    "created_at": assistant.created_at.isoformat() if assistant.created_at else None,
                    "updated_at": assistant.updated_at.isoformat() if assistant.updated_at else None,
                    "last_used_at": assistant.last_used_at.isoformat() if assistant.last_used_at else None,
                    "is_reasoning_model": assistant.is_reasoning_model()
                }
            }
        except Exception as e:
            logger.error(f"❌ Erro ao obter assistente: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def update_assistant(
        self,
        assistant_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        interaction_mode: Optional[str] = None,
        use_case: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Dict:
        """Atualiza um assistente existente"""
        try:
            return self.service.update_assistant(
                assistant_id=assistant_id,
                name=name,
                description=description,
                instructions=instructions,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                interaction_mode=interaction_mode,
                use_case=use_case,
                is_active=is_active
            )
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar assistente: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def delete_assistant(self, assistant_id: int) -> Dict:
        """Deleta um assistente"""
        try:
            return self.service.delete_assistant(assistant_id=assistant_id)
        except Exception as e:
            logger.error(f"❌ Erro ao deletar assistente: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def use_assistant_report(
        self,
        assistant_id: int,
        company_id: int,
        user_id: Optional[int],
        prompt: str,
        context_data: Optional[Dict] = None,
        use_case: Optional[str] = None
    ) -> Dict:
        """Usa um assistente em modo relatório"""
        try:
            return self.service.use_assistant_report_mode(
                assistant_id=assistant_id,
                company_id=company_id,
                user_id=user_id,
                prompt=prompt,
                context_data=context_data,
                use_case=use_case
            )
        except Exception as e:
            logger.error(f"❌ Erro ao usar assistente em modo report: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def use_assistant_chat(
        self,
        assistant_id: int,
        company_id: int,
        user_id: Optional[int],
        message: str,
        thread_id: Optional[str] = None,
        context_data: Optional[Dict] = None,
        use_case: Optional[str] = None
    ) -> Dict:
        """Usa um assistente em modo chat"""
        try:
            return self.service.use_assistant_chat_mode(
                assistant_id=assistant_id,
                company_id=company_id,
                user_id=user_id,
                message=message,
                thread_id=thread_id,
                context_data=context_data,
                use_case=use_case
            )
        except Exception as e:
            logger.error(f"❌ Erro ao usar assistente em modo chat: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_chat_history(self, thread_id: str, company_id: int, limit: int = 50) -> Dict:
        """Obtém histórico de mensagens de uma thread"""
        try:
            return self.service.get_chat_history(
                thread_id=thread_id,
                company_id=company_id,
                limit=limit
            )
        except Exception as e:
            logger.error(f"❌ Erro ao obter histórico: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_usage_stats(self, company_id: Optional[int] = None, days: int = 30) -> Dict:
        """Obtém estatísticas gerais de uso de tokens"""
        try:
            query = self.db.query(
                func.sum(OpenAIAssistantUsage.prompt_tokens).label('total_prompt_tokens'),
                func.sum(OpenAIAssistantUsage.completion_tokens).label('total_completion_tokens'),
                func.sum(OpenAIAssistantUsage.total_tokens).label('total_tokens'),
                func.count(OpenAIAssistantUsage.id).label('total_requests')
            )
            
            # Filtrar por data
            date_from = datetime.utcnow() - timedelta(days=days)
            query = query.filter(OpenAIAssistantUsage.created_at >= date_from)
            
            # Filtrar por company_id se fornecido
            if company_id:
                query = query.filter(OpenAIAssistantUsage.company_id == company_id)
            
            # Filtrar apenas requisições completadas
            query = query.filter(OpenAIAssistantUsage.status == UsageStatus.COMPLETED)
            
            result = query.first()
            
            return {
                "success": True,
                "stats": {
                    "total_prompt_tokens": result.total_prompt_tokens or 0,
                    "total_completion_tokens": result.total_completion_tokens or 0,
                    "total_tokens": result.total_tokens or 0,
                    "total_requests": result.total_requests or 0,
                    "days": days
                }
            }
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas de uso: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_usage_by_assistant(
        self,
        company_id: Optional[int] = None,
        days: int = 30
    ) -> Dict:
        """Obtém uso de tokens agrupado por assistente"""
        try:
            query = self.db.query(
                OpenAIAssistant.id,
                OpenAIAssistant.name,
                func.sum(OpenAIAssistantUsage.prompt_tokens).label('total_prompt_tokens'),
                func.sum(OpenAIAssistantUsage.completion_tokens).label('total_completion_tokens'),
                func.sum(OpenAIAssistantUsage.total_tokens).label('total_tokens'),
                func.count(OpenAIAssistantUsage.id).label('total_requests')
            ).join(
                OpenAIAssistantUsage,
                OpenAIAssistantUsage.assistant_id == OpenAIAssistant.id
            )
            
            # Filtrar por data
            date_from = datetime.utcnow() - timedelta(days=days)
            query = query.filter(OpenAIAssistantUsage.created_at >= date_from)
            
            # Filtrar por company_id se fornecido
            if company_id:
                query = query.filter(OpenAIAssistantUsage.company_id == company_id)
            
            # Filtrar apenas requisições completadas
            query = query.filter(OpenAIAssistantUsage.status == UsageStatus.COMPLETED)
            
            query = query.group_by(
                OpenAIAssistant.id,
                OpenAIAssistant.name
            ).order_by(desc('total_tokens'))
            
            results = query.all()
            
            return {
                "success": True,
                "usage": [
                    {
                        "assistant_id": r.id,
                        "assistant_name": r.name,
                        "total_prompt_tokens": r.total_prompt_tokens or 0,
                        "total_completion_tokens": r.total_completion_tokens or 0,
                        "total_tokens": r.total_tokens or 0,
                        "total_requests": r.total_requests or 0
                    }
                    for r in results
                ],
                "days": days
            }
        except Exception as e:
            logger.error(f"❌ Erro ao obter uso por assistente: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_usage_daily(
        self,
        company_id: Optional[int] = None,
        days: int = 30
    ) -> Dict:
        """Obtém uso de tokens agrupado por dia"""
        try:
            query = self.db.query(
                func.date(OpenAIAssistantUsage.created_at).label('date'),
                func.sum(OpenAIAssistantUsage.prompt_tokens).label('total_prompt_tokens'),
                func.sum(OpenAIAssistantUsage.completion_tokens).label('total_completion_tokens'),
                func.sum(OpenAIAssistantUsage.total_tokens).label('total_tokens'),
                func.count(OpenAIAssistantUsage.id).label('total_requests')
            )
            
            # Filtrar por data
            date_from = datetime.utcnow() - timedelta(days=days)
            query = query.filter(OpenAIAssistantUsage.created_at >= date_from)
            
            # Filtrar por company_id se fornecido
            if company_id:
                query = query.filter(OpenAIAssistantUsage.company_id == company_id)
            
            # Filtrar apenas requisições completadas
            query = query.filter(OpenAIAssistantUsage.status == UsageStatus.COMPLETED)
            
            query = query.group_by(
                func.date(OpenAIAssistantUsage.created_at)
            ).order_by(desc('date'))
            
            results = query.all()
            
            return {
                "success": True,
                "usage": [
                    {
                        "date": r.date.isoformat() if r.date else None,
                        "total_prompt_tokens": r.total_prompt_tokens or 0,
                        "total_completion_tokens": r.total_completion_tokens or 0,
                        "total_tokens": r.total_tokens or 0,
                        "total_requests": r.total_requests or 0
                    }
                    for r in results
                ],
                "days": days
            }
        except Exception as e:
            logger.error(f"❌ Erro ao obter uso diário: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

