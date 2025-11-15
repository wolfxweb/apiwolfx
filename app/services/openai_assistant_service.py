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
    OpenAIAssistant, OpenAIAssistantThread, OpenAIAssistantUsage, OpenAIAssistantMessage,
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
        """Verifica se é um modelo de raciocínio (o1, o3, o4) que não usa temperature"""
        return model.startswith("o1") or model.startswith("o3") or model.startswith("o4")
    
    def _is_gpt5_model(self, model: str) -> bool:
        """Verifica se é um modelo GPT-5 que usa reasoning_effort e verbosity ao invés de temperature"""
        return model.startswith("gpt-5")
    
    def create_assistant(
        self,
        name: str,
        description: Optional[str],
        instructions: str,
        model: str = "gpt-5.1",
        temperature: Optional[float] = None,
        reasoning_effort: Optional[str] = None,
        verbosity: Optional[str] = None,
        max_tokens: int = 4000,
        tools: Optional[List[Dict]] = None,
        interaction_mode: str = "report",
        use_case: Optional[str] = None,
        memory_enabled: bool = True,
        memory_data: Optional[Dict] = None
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
            
            # GPT-5 usa reasoning_effort e verbosity ao invés de temperature
            if self._is_gpt5_model(model):
                if reasoning_effort:
                    assistant_params["reasoning_effort"] = reasoning_effort
                elif not reasoning_effort:
                    # Padrão para GPT-5 se não especificado
                    assistant_params["reasoning_effort"] = "medium"
                
                if verbosity:
                    assistant_params["verbosity"] = verbosity
                elif not verbosity:
                    # Padrão para GPT-5 se não especificado
                    assistant_params["verbosity"] = "medium"
                
                logger.info(f"ℹ️ Modelo GPT-5 usando reasoning_effort={assistant_params.get('reasoning_effort')} e verbosity={assistant_params.get('verbosity')}")
            elif not self._is_reasoning_model(model):
                # Modelos GPT-4 e anteriores usam temperature
                if temperature is not None:
                    assistant_params["temperature"] = temperature
            else:
                # Modelos o1, o3, o4 não suportam temperature
                logger.info(f"ℹ️ Modelo {model} não suporta temperature, ignorando parâmetro")
            
            # Adicionar tools apenas se não for modelo de raciocínio
            if not self._is_reasoning_model(model):
                if tools:
                    assistant_params["tools"] = tools
            else:
                logger.info(f"ℹ️ Modelo {model} não suporta tools, ignorando parâmetro")
            
            # Não criar assistente na OpenAI - usar agente diretamente via Chat Completions
            # Gerar um ID único para o assistente (não é o ID da OpenAI)
            import uuid
            assistant_uuid = str(uuid.uuid4())
            
            logger.info(f"🚀 Criando agente '{name}' (sem criar na OpenAI, usando Chat Completions)...")
            
            # Salvar no banco de dados
            # Para GPT-5, armazenar reasoning_effort e verbosity no tools_config
            final_temperature = None
            final_tools_config = None
            
            if self._is_gpt5_model(model):
                # GPT-5: armazenar reasoning_effort e verbosity no tools_config como JSON
                config_data = {}
                if tools:
                    config_data["tools"] = tools
                if reasoning_effort:
                    config_data["reasoning_effort"] = reasoning_effort
                if verbosity:
                    config_data["verbosity"] = verbosity
                final_tools_config = config_data if config_data else None
                final_temperature = None  # GPT-5 não usa temperature
            elif not self._is_reasoning_model(model):
                # GPT-4 e anteriores: usar temperature normalmente
                final_temperature = temperature
                final_tools_config = tools if tools else None
            else:
                # Modelos o1, o3, o4: sem temperature e sem tools
                final_temperature = None
                final_tools_config = None
            
            db_assistant = OpenAIAssistant(
                name=name,
                description=description,
                assistant_id=assistant_uuid,  # ID interno, não da OpenAI
                model=model,
                instructions=instructions,
                temperature=final_temperature,
                max_tokens=max_tokens,
                tools_config=final_tools_config,
                interaction_mode=InteractionMode.CHAT if interaction_mode == "chat" else InteractionMode.REPORT,
                use_case=use_case,
                memory_enabled=memory_enabled,
                memory_data=memory_data,
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
        reasoning_effort: Optional[str] = None,
        verbosity: Optional[str] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        interaction_mode: Optional[str] = None,
        use_case: Optional[str] = None,
        is_active: Optional[bool] = None,
        memory_enabled: Optional[bool] = None,
        memory_data: Optional[Dict] = None
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
                return {"success": False, "error": "Agente não encontrado."}
            
            # Preparar parâmetros para atualização na OpenAI
            update_params = {}
            
            if name is not None:
                update_params["name"] = name
            if instructions is not None:
                update_params["instructions"] = instructions
            if model is not None:
                update_params["model"] = model
            
            # Não atualizar na OpenAI - não estamos usando Assistants API
            # Apenas atualizar no banco de dados
            logger.info(f"🔄 Atualizando agente {db_assistant.assistant_id} (configurações locais)...")
            
            # Atualizar no banco de dados
            if name is not None:
                db_assistant.name = name
            if description is not None:
                db_assistant.description = description
            if instructions is not None:
                db_assistant.instructions = instructions
            if model is not None:
                db_assistant.model = model
            
            # Atualizar parâmetros baseado no modelo
            is_gpt5 = self._is_gpt5_model(final_model)
            is_reasoning = self._is_reasoning_model(final_model)
            
            if is_gpt5:
                # GPT-5: atualizar reasoning_effort e verbosity no tools_config
                current_config = db_assistant.tools_config or {}
                if not isinstance(current_config, dict):
                    current_config = {}
                
                if tools is not None:
                    current_config["tools"] = tools
                if reasoning_effort is not None:
                    current_config["reasoning_effort"] = reasoning_effort
                if verbosity is not None:
                    current_config["verbosity"] = verbosity
                
                db_assistant.tools_config = current_config if current_config else None
                db_assistant.temperature = None  # GPT-5 não usa temperature
            elif not is_reasoning:
                # GPT-4 e anteriores: usar temperature normalmente
                if temperature is not None:
                    db_assistant.temperature = temperature
                if tools is not None:
                    db_assistant.tools_config = tools
            else:
                # Modelos o1, o3, o4: sem temperature e sem tools
                db_assistant.temperature = None
                db_assistant.tools_config = None
            
            if max_tokens is not None:
                db_assistant.max_tokens = max_tokens
            if interaction_mode is not None:
                db_assistant.interaction_mode = InteractionMode.CHAT if interaction_mode == "chat" else InteractionMode.REPORT
            if use_case is not None:
                db_assistant.use_case = use_case
            if is_active is not None:
                db_assistant.is_active = is_active
            if memory_enabled is not None:
                db_assistant.memory_enabled = memory_enabled
            if memory_data is not None:
                db_assistant.memory_data = memory_data
            
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
                return {"success": False, "error": "Agente não encontrado."}
            
            # Não deletar na OpenAI - não estamos usando Assistants API
            # Apenas marcar como inativo no banco
            logger.info(f"🗑️ Desativando agente {db_assistant.assistant_id}...")
            db_assistant.is_active = False
            self.db.commit()
            
            logger.info(f"✅ Agente desativado com sucesso: {db_assistant.id}")
            
            return {"success": True, "message": "Agente desativado com sucesso."}
            
        except Exception as e:
            logger.error(f"❌ Erro ao desativar agente: {e}", exc_info=True)
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
                raise Exception("Agente não encontrado ou inativo.")
            
            # Usar Chat Completions diretamente (não Assistants API)
            messages_history = []
            
            # Adicionar instruções do assistente como mensagem do sistema
            system_content = db_assistant.instructions
            
            # Adicionar memórias ao contexto se habilitado
            if db_assistant.memory_enabled and db_assistant.memory_data:
                memory_text = json.dumps(db_assistant.memory_data, ensure_ascii=False)
                system_content += f"\n\n[CONTEXTO DE MEMÓRIA]\nMemórias compartilhadas: {memory_text}"
            
            messages_history.append({
                "role": "system",
                "content": system_content
            })
            
            # Adicionar contexto adicional se fornecido
            if context_data:
                context_text = json.dumps(context_data, ensure_ascii=False)
                messages_history.append({
                    "role": "system",
                    "content": f"[CONTEXTO ADICIONAL]\n{context_text}"
                })
            
            # Adicionar prompt do usuário
            messages_history.append({
                "role": "user",
                "content": prompt
            })
            
            # Preparar parâmetros para Chat Completions
            chat_params = {
                "model": db_assistant.model,
                "messages": messages_history,
                "max_tokens": db_assistant.max_tokens
            }
            
            # Adicionar parâmetros específicos do modelo
            if self._is_gpt5_model(db_assistant.model):
                # GPT-5 usa reasoning_effort e verbosity
                if db_assistant.tools_config:
                    if isinstance(db_assistant.tools_config, dict):
                        if db_assistant.tools_config.get("reasoning_effort"):
                            chat_params["reasoning_effort"] = db_assistant.tools_config["reasoning_effort"]
                        if db_assistant.tools_config.get("verbosity"):
                            chat_params["verbosity"] = db_assistant.tools_config["verbosity"]
            elif not self._is_reasoning_model(db_assistant.model):
                # GPT-4 e anteriores usam temperature
                if db_assistant.temperature is not None:
                    chat_params["temperature"] = float(db_assistant.temperature)
            
            # Fazer chamada ao Chat Completions
            logger.info(f"💬 Gerando relatório via Chat Completions...")
            response = self.client.chat.completions.create(**chat_params)
            
            if response.choices and len(response.choices) > 0:
                response_text = response.choices[0].message.content
                response_data_size = len(response_text.encode('utf-8'))
                
                # Obter uso de tokens
                usage_info = response.usage if hasattr(response, 'usage') else None
                    
                # Atualizar métricas do assistente
                db_assistant.total_runs += 1
                if usage_info:
                    db_assistant.total_tokens_used += usage_info.total_tokens
                db_assistant.last_used_at = datetime.utcnow()
                
                # Atualizar registro de uso
                duration = time.time() - start_time
                usage_record.status = UsageStatus.COMPLETED
                usage_record.completed_at = datetime.utcnow()
                usage_record.duration_seconds = duration
                usage_record.request_data_size = request_data_size
                usage_record.response_data_size = response_data_size
                
                if usage_info:
                    usage_record.prompt_tokens = usage_info.prompt_tokens
                    usage_record.completion_tokens = usage_info.completion_tokens
                    usage_record.total_tokens = usage_info.total_tokens
                
                self.db.commit()
                
                return {
                    "success": True,
                    "response": response_text,
                    "usage": {
                        "prompt_tokens": usage_info.prompt_tokens if usage_info else 0,
                        "completion_tokens": usage_info.completion_tokens if usage_info else 0,
                        "total_tokens": usage_info.total_tokens if usage_info else 0
                    } if usage_info else None
                }
            else:
                raise Exception("Resposta do agente não encontrada.")
                
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
                raise Exception("Agente não encontrado ou inativo.")
            
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
                # Criar nova thread (ID interno, não da OpenAI)
                import uuid
                thread_uuid = str(uuid.uuid4())
                openai_thread_id = thread_uuid
                
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
            
            # Usar Chat Completions diretamente (não Assistants API)
            # Buscar histórico de mensagens da thread do banco
            messages_history = []
            
            # Buscar mensagens anteriores da thread no banco
            previous_messages = self.db.query(OpenAIAssistantMessage).filter(
                OpenAIAssistantMessage.thread_id == db_thread.id
            ).order_by(OpenAIAssistantMessage.created_at.asc()).all()
            
            # Adicionar instruções do assistente como primeira mensagem do sistema (apenas se não houver histórico)
            if not previous_messages:
                system_content = db_assistant.instructions
                
                # Adicionar memórias ao contexto do sistema se habilitado
                if db_assistant.memory_enabled:
                    memory_context = []
                    if db_assistant.memory_data:
                        memory_context.append(f"Memórias compartilhadas: {json.dumps(db_assistant.memory_data, ensure_ascii=False)}")
                    if db_thread.memory_data:
                        memory_context.append(f"Memórias desta conversa: {json.dumps(db_thread.memory_data, ensure_ascii=False)}")
                    if memory_context:
                        memory_text = "\n\n".join(memory_context)
                        system_content += f"\n\n[CONTEXTO DE MEMÓRIA]\n{memory_text}"
                
                messages_history.append({
                    "role": "system",
                    "content": system_content
                })
            
            # Adicionar mensagens anteriores do histórico
            for prev_msg in previous_messages:
                messages_history.append({
                    "role": prev_msg.role,
                    "content": prev_msg.content
                })
            
            # Adicionar mensagem atual do usuário
            messages_history.append({
                "role": "user",
                "content": message
            })
            
            # Salvar mensagem do usuário no banco
            user_message = OpenAIAssistantMessage(
                thread_id=db_thread.id,
                role="user",
                content=message
            )
            self.db.add(user_message)
            self.db.flush()
            
            # Preparar parâmetros para Chat Completions
            chat_params = {
                "model": db_assistant.model,
                "messages": messages_history,
                "max_tokens": db_assistant.max_tokens
            }
            
            # Adicionar parâmetros específicos do modelo
            if self._is_gpt5_model(db_assistant.model):
                # GPT-5 usa reasoning_effort e verbosity
                if db_assistant.tools_config:
                    if isinstance(db_assistant.tools_config, dict):
                        if db_assistant.tools_config.get("reasoning_effort"):
                            chat_params["reasoning_effort"] = db_assistant.tools_config["reasoning_effort"]
                        if db_assistant.tools_config.get("verbosity"):
                            chat_params["verbosity"] = db_assistant.tools_config["verbosity"]
            elif not self._is_reasoning_model(db_assistant.model):
                # GPT-4 e anteriores usam temperature
                if db_assistant.temperature is not None:
                    chat_params["temperature"] = float(db_assistant.temperature)
            
            # Fazer chamada ao Chat Completions
            logger.info(f"💬 Enviando mensagem para agente via Chat Completions...")
            response = self.client.chat.completions.create(**chat_params)
            
            if response.choices and len(response.choices) > 0:
                response_text = response.choices[0].message.content
                response_data_size = len(response_text.encode('utf-8'))
                
                # Salvar resposta do assistente no banco
                assistant_message = OpenAIAssistantMessage(
                    thread_id=db_thread.id,
                    role="assistant",
                    content=response_text
                )
                self.db.add(assistant_message)
                
                # Obter uso de tokens
                usage_info = response.usage if hasattr(response, 'usage') else None
                
                # Atualizar thread
                db_thread.last_message_at = datetime.utcnow()
                db_thread.updated_at = datetime.utcnow()
                
                # Atualizar métricas do assistente
                db_assistant.total_runs += 1
                if usage_info:
                    db_assistant.total_tokens_used += usage_info.total_tokens
                db_assistant.last_used_at = datetime.utcnow()
                
                # Atualizar registro de uso
                duration = time.time() - start_time
                usage_record.status = UsageStatus.COMPLETED
                usage_record.completed_at = datetime.utcnow()
                usage_record.duration_seconds = duration
                usage_record.request_data_size = request_data_size
                usage_record.response_data_size = response_data_size
                usage_record.thread_id = openai_thread_id
                
                if usage_info:
                    usage_record.prompt_tokens = usage_info.prompt_tokens
                    usage_record.completion_tokens = usage_info.completion_tokens
                    usage_record.total_tokens = usage_info.total_tokens
                
                self.db.commit()
                
                return {
                    "success": True,
                    "response": response_text,
                    "thread_id": openai_thread_id,
                    "usage": {
                        "prompt_tokens": usage_info.prompt_tokens if usage_info else 0,
                        "completion_tokens": usage_info.completion_tokens if usage_info else 0,
                        "total_tokens": usage_info.total_tokens if usage_info else 0
                    } if usage_info else None
                }
            else:
                raise Exception("Resposta do agente não encontrada.")
                
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
            
            # Buscar mensagens no banco de dados
            db_messages = self.db.query(OpenAIAssistantMessage).filter(
                OpenAIAssistantMessage.thread_id == db_thread.id
            ).order_by(OpenAIAssistantMessage.created_at.asc()).limit(limit).all()
            
            history = []
            for msg in db_messages:
                history.append({
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None
                })
            
            return {
                "success": True,
                "thread_id": thread_id,
                "messages": history
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter histórico: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    # Método _wait_for_run removido - não é mais necessário com Chat Completions

