"""
Serviço para gerenciar e usar assistentes OpenAI
"""
import os
import json
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from openai import OpenAI, APIError, RateLimitError, APITimeoutError
from app.models.saas_models import (
    OpenAIAssistant, OpenAIAssistantThread, OpenAIAssistantUsage,
    InteractionMode, UsageStatus
)

logger = logging.getLogger(__name__)


class OpenAIAssistantService:
    """Serviço para gerenciar e usar assistentes OpenAI"""
    
    def __init__(self, db: Session):
        self.db = db
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        
        if not self.api_key:
            logger.warning("⚠️ OPENAI_API_KEY não configurada. Funcionalidades de assistentes estarão desabilitadas.")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)
            logger.info("✅ Cliente OpenAI inicializado com sucesso")
    
    def _is_reasoning_model(self, model: str) -> bool:
        """Verifica se é um modelo de raciocínio (o1) que não usa temperature"""
        return model.startswith("o1") or model.startswith("o3") or model.startswith("o4")
    
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
        """Cria um novo assistente na OpenAI e salva no banco de dados"""
        if not self.client:
            return {"success": False, "error": "OpenAI API key não configurada."}
        
        try:
            # Preparar parâmetros para criação do assistente
            assistant_params = {
                "name": name,
                "instructions": instructions,
                "model": model,
            }
            
            # Adicionar temperature apenas se não for modelo de raciocínio
            if not self._is_reasoning_model(model):
                if temperature is not None:
                    assistant_params["temperature"] = temperature
            else:
                logger.info(f"ℹ️ Modelo {model} não suporta temperature, ignorando parâmetro")
            
            # Adicionar tools apenas se não for modelo de raciocínio
            if not self._is_reasoning_model(model):
                if tools:
                    assistant_params["tools"] = tools
            else:
                logger.info(f"ℹ️ Modelo {model} não suporta tools, ignorando parâmetro")
            
            # Criar assistente na OpenAI
            logger.info(f"🚀 Criando assistente '{name}' na OpenAI...")
            openai_assistant = self.client.beta.assistants.create(**assistant_params)
            
            # Salvar no banco de dados
            db_assistant = OpenAIAssistant(
                name=name,
                description=description,
                assistant_id=openai_assistant.id,
                model=model,
                instructions=instructions,
                temperature=temperature if not self._is_reasoning_model(model) else None,
                max_tokens=max_tokens,
                tools_config=tools if not self._is_reasoning_model(model) else None,
                interaction_mode=InteractionMode.CHAT if interaction_mode == "chat" else InteractionMode.REPORT,
                use_case=use_case,
                is_active=True
            )
            
            self.db.add(db_assistant)
            self.db.commit()
            self.db.refresh(db_assistant)
            
            logger.info(f"✅ Assistente criado com sucesso: {db_assistant.id} (OpenAI ID: {openai_assistant.id})")
            
            return {
                "success": True,
                "assistant": {
                    "id": db_assistant.id,
                    "name": db_assistant.name,
                    "assistant_id": db_assistant.assistant_id,
                    "model": db_assistant.model,
                    "interaction_mode": db_assistant.interaction_mode.value,
                    "created_at": db_assistant.created_at.isoformat() if db_assistant.created_at else None
                }
            }
            
        except APIError as e:
            logger.error(f"❌ Erro da API OpenAI ao criar assistente: {e}")
            self.db.rollback()
            return {"success": False, "error": f"Erro da API OpenAI: {e.message}"}
        except Exception as e:
            logger.error(f"❌ Erro ao criar assistente: {e}", exc_info=True)
            self.db.rollback()
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
        if not self.client:
            return {"success": False, "error": "OpenAI API key não configurada."}
        
        try:
            # Buscar assistente no banco
            db_assistant = self.db.query(OpenAIAssistant).filter(
                OpenAIAssistant.id == assistant_id
            ).first()
            
            if not db_assistant:
                return {"success": False, "error": "Assistente não encontrado."}
            
            # Preparar parâmetros para atualização na OpenAI
            update_params = {}
            
            if name is not None:
                update_params["name"] = name
            if instructions is not None:
                update_params["instructions"] = instructions
            if model is not None:
                update_params["model"] = model
            
            # Atualizar na OpenAI apenas se houver parâmetros para atualizar
            if update_params:
                # Verificar se precisa ajustar temperature/tools baseado no modelo
                final_model = model or db_assistant.model
                is_reasoning = self._is_reasoning_model(final_model)
                
                if not is_reasoning:
                    if temperature is not None:
                        update_params["temperature"] = temperature
                    if tools is not None:
                        update_params["tools"] = tools
                
                logger.info(f"🔄 Atualizando assistente {db_assistant.assistant_id} na OpenAI...")
                self.client.beta.assistants.update(
                    assistant_id=db_assistant.assistant_id,
                    **update_params
                )
            
            # Atualizar no banco de dados
            if name is not None:
                db_assistant.name = name
            if description is not None:
                db_assistant.description = description
            if instructions is not None:
                db_assistant.instructions = instructions
            if model is not None:
                db_assistant.model = model
            if temperature is not None and not self._is_reasoning_model(final_model):
                db_assistant.temperature = temperature
            elif self._is_reasoning_model(final_model):
                db_assistant.temperature = None
            if max_tokens is not None:
                db_assistant.max_tokens = max_tokens
            if tools is not None and not self._is_reasoning_model(final_model):
                db_assistant.tools_config = tools
            elif self._is_reasoning_model(final_model):
                db_assistant.tools_config = None
            if interaction_mode is not None:
                db_assistant.interaction_mode = InteractionMode.CHAT if interaction_mode == "chat" else InteractionMode.REPORT
            if use_case is not None:
                db_assistant.use_case = use_case
            if is_active is not None:
                db_assistant.is_active = is_active
            
            db_assistant.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(db_assistant)
            
            logger.info(f"✅ Assistente atualizado com sucesso: {db_assistant.id}")
            
            return {
                "success": True,
                "assistant": {
                    "id": db_assistant.id,
                    "name": db_assistant.name,
                    "assistant_id": db_assistant.assistant_id,
                    "model": db_assistant.model,
                    "interaction_mode": db_assistant.interaction_mode.value,
                    "updated_at": db_assistant.updated_at.isoformat() if db_assistant.updated_at else None
                }
            }
            
        except APIError as e:
            logger.error(f"❌ Erro da API OpenAI ao atualizar assistente: {e}")
            self.db.rollback()
            return {"success": False, "error": f"Erro da API OpenAI: {e.message}"}
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar assistente: {e}", exc_info=True)
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def delete_assistant(self, assistant_id: int) -> Dict:
        """Deleta um assistente (marca como inativo e deleta na OpenAI)"""
        if not self.client:
            return {"success": False, "error": "OpenAI API key não configurada."}
        
        try:
            # Buscar assistente no banco
            db_assistant = self.db.query(OpenAIAssistant).filter(
                OpenAIAssistant.id == assistant_id
            ).first()
            
            if not db_assistant:
                return {"success": False, "error": "Assistente não encontrado."}
            
            # Deletar na OpenAI
            logger.info(f"🗑️ Deletando assistente {db_assistant.assistant_id} na OpenAI...")
            self.client.beta.assistants.delete(assistant_id=db_assistant.assistant_id)
            
            # Marcar como inativo no banco
            db_assistant.is_active = False
            self.db.commit()
            
            logger.info(f"✅ Assistente deletado com sucesso: {db_assistant.id}")
            
            return {"success": True, "message": "Assistente deletado com sucesso."}
            
        except APIError as e:
            logger.error(f"❌ Erro da API OpenAI ao deletar assistente: {e}")
            self.db.rollback()
            return {"success": False, "error": f"Erro da API OpenAI: {e.message}"}
        except Exception as e:
            logger.error(f"❌ Erro ao deletar assistente: {e}", exc_info=True)
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def use_assistant_report_mode(
        self,
        assistant_id: int,
        company_id: int,
        user_id: Optional[int],
        prompt: str,
        context_data: Optional[Dict] = None,
        use_case: Optional[str] = None
    ) -> Dict:
        """Usa um assistente em modo relatório (gera análise única)"""
        if not self.client:
            return {"success": False, "error": "OpenAI API key não configurada."}
        
        # Criar registro de uso
        usage_record = OpenAIAssistantUsage(
            assistant_id=assistant_id,
            company_id=company_id,
            user_id=user_id,
            interaction_mode="report",
            use_case=use_case,
            status=UsageStatus.PENDING,
            created_at=datetime.utcnow()
        )
        self.db.add(usage_record)
        self.db.flush()
        
        start_time = time.time()
        request_data_size = len(json.dumps(context_data or {}).encode('utf-8')) if context_data else 0
        
        try:
            # Buscar assistente
            db_assistant = self.db.query(OpenAIAssistant).filter(
                OpenAIAssistant.id == assistant_id,
                OpenAIAssistant.is_active == True
            ).first()
            
            if not db_assistant:
                raise Exception("Assistente não encontrado ou inativo.")
            
            # Criar thread temporária
            thread = self.client.beta.threads.create()
            
            # Adicionar mensagem
            self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt
            )
            
            # Executar run
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=db_assistant.assistant_id
            )
            
            # Aguardar conclusão
            run = self._wait_for_run(thread.id, run.id)
            
            if run.status == 'completed':
                # Obter resposta
                messages = self.client.beta.threads.messages.list(
                    thread_id=thread.id,
                    order="desc",
                    limit=1
                )
                
                if messages.data and messages.data[0].role == 'assistant':
                    response_text = messages.data[0].content[0].text.value
                    response_data_size = len(response_text.encode('utf-8'))
                    
                    # Atualizar métricas do assistente
                    db_assistant.total_runs += 1
                    if run.usage:
                        db_assistant.total_tokens_used += run.usage.total_tokens
                    db_assistant.last_used_at = datetime.utcnow()
                    
                    # Atualizar registro de uso
                    duration = time.time() - start_time
                    usage_record.status = UsageStatus.COMPLETED
                    usage_record.completed_at = datetime.utcnow()
                    usage_record.duration_seconds = duration
                    usage_record.request_data_size = request_data_size
                    usage_record.response_data_size = response_data_size
                    
                    if run.usage:
                        usage_record.prompt_tokens = run.usage.prompt_tokens
                        usage_record.completion_tokens = run.usage.completion_tokens
                        usage_record.total_tokens = run.usage.total_tokens
                    
                    self.db.commit()
                    
                    return {
                        "success": True,
                        "response": response_text,
                        "usage": {
                            "prompt_tokens": run.usage.prompt_tokens if run.usage else 0,
                            "completion_tokens": run.usage.completion_tokens if run.usage else 0,
                            "total_tokens": run.usage.total_tokens if run.usage else 0
                        }
                    }
                else:
                    raise Exception("Resposta do assistente não encontrada.")
            else:
                error_msg = f"Run falhou com status: {run.status}"
                usage_record.status = UsageStatus.FAILED
                usage_record.error_message = error_msg
                usage_record.completed_at = datetime.utcnow()
                usage_record.duration_seconds = time.time() - start_time
                self.db.commit()
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"❌ Erro ao usar assistente em modo report: {e}", exc_info=True)
            usage_record.status = UsageStatus.FAILED
            usage_record.error_message = str(e)
            usage_record.completed_at = datetime.utcnow()
            usage_record.duration_seconds = time.time() - start_time
            self.db.commit()
            return {"success": False, "error": str(e)}
    
    def use_assistant_chat_mode(
        self,
        assistant_id: int,
        company_id: int,
        user_id: Optional[int],
        message: str,
        thread_id: Optional[str] = None,
        context_data: Optional[Dict] = None,
        use_case: Optional[str] = None
    ) -> Dict:
        """Usa um assistente em modo chat (conversa contínua)"""
        if not self.client:
            return {"success": False, "error": "OpenAI API key não configurada."}
        
        # Criar registro de uso
        usage_record = OpenAIAssistantUsage(
            assistant_id=assistant_id,
            company_id=company_id,
            user_id=user_id,
            thread_id=thread_id,
            interaction_mode="chat",
            use_case=use_case,
            status=UsageStatus.PENDING,
            created_at=datetime.utcnow()
        )
        self.db.add(usage_record)
        self.db.flush()
        
        start_time = time.time()
        request_data_size = len(json.dumps(context_data or {}).encode('utf-8')) if context_data else 0
        
        try:
            # Buscar assistente
            db_assistant = self.db.query(OpenAIAssistant).filter(
                OpenAIAssistant.id == assistant_id,
                OpenAIAssistant.is_active == True
            ).first()
            
            if not db_assistant:
                raise Exception("Assistente não encontrado ou inativo.")
            
            # Buscar ou criar thread
            if thread_id:
                # Buscar thread existente no banco
                db_thread = self.db.query(OpenAIAssistantThread).filter(
                    OpenAIAssistantThread.thread_id == thread_id,
                    OpenAIAssistantThread.company_id == company_id,
                    OpenAIAssistantThread.is_active == True
                ).first()
                
                if not db_thread:
                    raise Exception("Thread não encontrada.")
                
                openai_thread_id = thread_id
            else:
                # Criar nova thread
                thread = self.client.beta.threads.create()
                openai_thread_id = thread.id
                
                # Salvar thread no banco
                db_thread = OpenAIAssistantThread(
                    assistant_id=assistant_id,
                    company_id=company_id,
                    user_id=user_id,
                    thread_id=openai_thread_id,
                    context_data=context_data,
                    is_active=True
                )
                self.db.add(db_thread)
                self.db.flush()
            
            # Adicionar mensagem
            self.client.beta.threads.messages.create(
                thread_id=openai_thread_id,
                role="user",
                content=message
            )
            
            # Executar run
            run = self.client.beta.threads.runs.create(
                thread_id=openai_thread_id,
                assistant_id=db_assistant.assistant_id
            )
            
            # Aguardar conclusão
            run = self._wait_for_run(openai_thread_id, run.id)
            
            if run.status == 'completed':
                # Obter resposta
                messages = self.client.beta.threads.messages.list(
                    thread_id=openai_thread_id,
                    order="desc",
                    limit=1
                )
                
                if messages.data and messages.data[0].role == 'assistant':
                    response_text = messages.data[0].content[0].text.value
                    response_data_size = len(response_text.encode('utf-8'))
                    
                    # Atualizar thread
                    db_thread.last_message_at = datetime.utcnow()
                    db_thread.updated_at = datetime.utcnow()
                    
                    # Atualizar métricas do assistente
                    db_assistant.total_runs += 1
                    if run.usage:
                        db_assistant.total_tokens_used += run.usage.total_tokens
                    db_assistant.last_used_at = datetime.utcnow()
                    
                    # Atualizar registro de uso
                    duration = time.time() - start_time
                    usage_record.status = UsageStatus.COMPLETED
                    usage_record.completed_at = datetime.utcnow()
                    usage_record.duration_seconds = duration
                    usage_record.request_data_size = request_data_size
                    usage_record.response_data_size = response_data_size
                    usage_record.thread_id = openai_thread_id
                    
                    if run.usage:
                        usage_record.prompt_tokens = run.usage.prompt_tokens
                        usage_record.completion_tokens = run.usage.completion_tokens
                        usage_record.total_tokens = run.usage.total_tokens
                    
                    self.db.commit()
                    
                    return {
                        "success": True,
                        "response": response_text,
                        "thread_id": openai_thread_id,
                        "usage": {
                            "prompt_tokens": run.usage.prompt_tokens if run.usage else 0,
                            "completion_tokens": run.usage.completion_tokens if run.usage else 0,
                            "total_tokens": run.usage.total_tokens if run.usage else 0
                        }
                    }
                else:
                    raise Exception("Resposta do assistente não encontrada.")
            else:
                error_msg = f"Run falhou com status: {run.status}"
                usage_record.status = UsageStatus.FAILED
                usage_record.error_message = error_msg
                usage_record.completed_at = datetime.utcnow()
                usage_record.duration_seconds = time.time() - start_time
                self.db.commit()
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"❌ Erro ao usar assistente em modo chat: {e}", exc_info=True)
            usage_record.status = UsageStatus.FAILED
            usage_record.error_message = str(e)
            usage_record.completed_at = datetime.utcnow()
            usage_record.duration_seconds = time.time() - start_time
            self.db.commit()
            return {"success": False, "error": str(e)}
    
    def get_chat_history(self, thread_id: str, company_id: int, limit: int = 50) -> Dict:
        """Obtém histórico de mensagens de uma thread"""
        if not self.client:
            return {"success": False, "error": "OpenAI API key não configurada."}
        
        try:
            # Verificar se thread pertence à company
            db_thread = self.db.query(OpenAIAssistantThread).filter(
                OpenAIAssistantThread.thread_id == thread_id,
                OpenAIAssistantThread.company_id == company_id
            ).first()
            
            if not db_thread:
                return {"success": False, "error": "Thread não encontrada."}
            
            # Buscar mensagens na OpenAI
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id,
                limit=limit,
                order="asc"
            )
            
            history = []
            for msg in messages.data:
                history.append({
                    "role": msg.role,
                    "content": msg.content[0].text.value if msg.content else "",
                    "created_at": msg.created_at.isoformat() if hasattr(msg, 'created_at') else None
                })
            
            return {
                "success": True,
                "thread_id": thread_id,
                "messages": history
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter histórico: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _wait_for_run(self, thread_id: str, run_id: str, timeout: int = 300) -> Any:
        """Aguarda conclusão de um run com timeout"""
        start = time.time()
        while time.time() - start < timeout:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            if run.status in ['completed', 'failed', 'cancelled', 'expired']:
                return run
            time.sleep(1)
        raise TimeoutError("Run não completou a tempo")

