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
            # Configurar cliente OpenAI com header para Assistants API v2
            # Documentação oficial: https://platform.openai.com/docs/assistants/migration
            # A API v1 foi depreciada, precisamos usar v2 com o header OpenAI-Beta: assistants=v2
            self.client = OpenAI(
                api_key=self.api_key,
                default_headers={
                    "OpenAI-Beta": "assistants=v2"
                }
            )
            logger.info("✅ Cliente OpenAI inicializado com sucesso (Assistants API v2)")
    
    def _is_reasoning_model(self, model: str) -> bool:
        """Verifica se é um modelo de raciocínio (o1, o3, o4) que não usa temperature"""
        return model.startswith("o1") or model.startswith("o3") or model.startswith("o4")
    
    def _is_gpt5_model(self, model: str) -> bool:
        """Verifica se é um modelo GPT-5 que usa reasoning_effort e verbosity ao invés de temperature"""
        return model.startswith("gpt-5")
    
    def _needs_max_completion_tokens(self, model: str) -> bool:
        """Verifica se o modelo requer max_completion_tokens ao invés de max_tokens"""
        # Modelos que requerem max_completion_tokens
        # Baseado na documentação da OpenAI, modelos GPT-5 mais recentes podem usar max_completion_tokens
        if not model:
            return False
        # gpt-5-nano e outros modelos GPT-5 específicos podem requerer max_completion_tokens
        # Por enquanto, vamos verificar se é gpt-5-nano especificamente
        return model.startswith("gpt-5-nano")
    
    def _is_model_supported_by_assistants_api(self, model: str) -> bool:
        """Verifica se o modelo é suportado pela Assistants API"""
        if not model:
            return False
        
        # Modelos NÃO suportados (verificar primeiro para evitar falsos positivos)
        unsupported_models = [
            "gpt-5-nano",  # gpt-5-nano NÃO suporta Assistants API
        ]
        
        # Verificar se é um modelo não suportado
        for unsupported in unsupported_models:
            if model.startswith(unsupported):
                return False
        
        # Modelos suportados pela Assistants API v2
        # IMPORTANTE: Ordem importa! Modelos mais específicos primeiro
        supported_models = [
            "gpt-5.1", "gpt-5-pro", "gpt-5-mini",  # Modelos GPT-5 específicos (antes de gpt-5 genérico)
            "gpt-4o-mini", "gpt-4o", "gpt-4-turbo-preview", "gpt-4-turbo", "gpt-4",  # Modelos GPT-4
            "gpt-3.5-turbo-16k", "gpt-3.5-turbo",  # Modelos GPT-3.5
            "gpt-5",  # gpt-5 genérico (depois dos específicos)
        ]
        
        # Verificar se o modelo começa com algum dos modelos suportados
        for supported in supported_models:
            if model.startswith(supported):
                return True
        
        return False
    
    def _needs_assistants_api(self, tools: Optional[List[Dict]], model: str) -> bool:
        """Verifica se precisa usar Assistants API (Code Interpreter ou File Search)"""
        # Primeiro verificar se o modelo é suportado
        if not self._is_model_supported_by_assistants_api(model):
            return False
        
        # Depois verificar se tem ferramentas que requerem Assistants API
        if not tools:
            return False
        for tool in tools:
            if isinstance(tool, dict) and tool.get("type") in ["code_interpreter", "file_search"]:
                return True
        return False
    
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
        memory_data: Optional[Dict] = None,
        initial_prompt: Optional[str] = None
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
            
            # Log das ferramentas antes de salvar
            if tools:
                logger.info(f"🔧 Salvando {len(tools)} ferramenta(s) no banco de dados")
                for i, tool in enumerate(tools):
                    tool_name = tool.get("function", {}).get("name", "desconhecida") if isinstance(tool, dict) else "desconhecida"
                    logger.info(f"   - Ferramenta {i+1}: {tool_name}")
            else:
                logger.info("ℹ️ Nenhuma ferramenta configurada para este agente")
            
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
                initial_prompt=initial_prompt,
                is_active=True
            )
            
            self.db.add(db_assistant)
            self.db.commit()
            self.db.refresh(db_assistant)
            
            # Verificar se foi salvo corretamente
            if db_assistant.tools_config:
                logger.info(f"✅ Ferramentas salvas no banco: {json.dumps(db_assistant.tools_config, ensure_ascii=False)}")
            else:
                logger.info("ℹ️ Nenhuma ferramenta salva (tools_config é None)")
            
            logger.info(f"✅ Agente '{name}' criado com sucesso (ID: {db_assistant.id}, Assistant ID: {db_assistant.assistant_id})")
            
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
        memory_data: Optional[Dict] = None,
        initial_prompt: Optional[str] = None
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
            # Usar o modelo atualizado ou o modelo existente
            current_model = model if model is not None else db_assistant.model
            is_gpt5 = self._is_gpt5_model(current_model)
            is_reasoning = self._is_reasoning_model(current_model)
            
            if is_gpt5:
                # GPT-5: atualizar reasoning_effort e verbosity no tools_config
                current_config = db_assistant.tools_config or {}
                if not isinstance(current_config, dict):
                    current_config = {}
                
                if tools is not None:
                    current_config["tools"] = tools
                    logger.info(f"🔧 Atualizando {len(tools)} ferramenta(s) para agente GPT-5")
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
                    logger.info(f"🔧 Atualizando {len(tools)} ferramenta(s) para agente não-GPT-5")
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
            if initial_prompt is not None:
                db_assistant.initial_prompt = initial_prompt
            
            db_assistant.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(db_assistant)
            
            # Verificar se ferramentas foram salvas
            if db_assistant.tools_config:
                logger.info(f"✅ Ferramentas atualizadas no banco: {json.dumps(db_assistant.tools_config, ensure_ascii=False)}")
            else:
                logger.info("ℹ️ Nenhuma ferramenta configurada (tools_config é None)")
            
            logger.info(f"✅ Agente atualizado com sucesso: {db_assistant.id}")
            
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
            
            # Substituir [[INFO]] pelo JSON do context_data se existir
            if context_data:
                if "analysis_json" in context_data:
                    # Usar o JSON formatado do frontend
                    info_json = context_data.get("analysis_json", "")
                    if "[[INFO]]" in system_content:
                        system_content = system_content.replace("[[INFO]]", info_json)
                        logger.info("✅ Substituído [[INFO]] nas instruções pelo JSON de análise")
                else:
                    # Se não tiver analysis_json, formatar o context_data completo
                    info_json = json.dumps(context_data, ensure_ascii=False, indent=2)
                    if "[[INFO]]" in system_content:
                        system_content = system_content.replace("[[INFO]]", info_json)
                        logger.info("✅ Substituído [[INFO]] nas instruções pelo context_data completo")
            
            # Adicionar memórias ao contexto se habilitado
            if db_assistant.memory_enabled and db_assistant.memory_data:
                memory_text = json.dumps(db_assistant.memory_data, ensure_ascii=False)
                system_content += f"\n\n[CONTEXTO DE MEMÓRIA]\nMemórias compartilhadas: {memory_text}"
            
            messages_history.append({
                "role": "system",
                "content": system_content
            })
            
            # Adicionar contexto adicional se fornecido (apenas se não foi usado para substituir [[INFO]])
            if context_data and "[[INFO]]" not in db_assistant.instructions:
                context_text = json.dumps(context_data, ensure_ascii=False)
                messages_history.append({
                    "role": "system",
                    "content": f"[CONTEXTO ADICIONAL]\n{context_text}"
                })
            
            # Processar prompt do usuário: substituir [[USUARIO]] no prompt inicial se existir
            user_prompt_content = prompt
            if db_assistant.initial_prompt and "[[USUARIO]]" in db_assistant.initial_prompt:
                # Substituir a tag [[USUARIO]] pelo texto do usuário
                user_prompt_content = db_assistant.initial_prompt.replace("[[USUARIO]]", prompt)
            
            # Adicionar prompt do usuário
            messages_history.append({
                "role": "user",
                "content": user_prompt_content
            })
            
            # Preparar parâmetros para Chat Completions
            chat_params = {
                "model": db_assistant.model,
                "messages": messages_history,
            }
            
            # Adicionar limite de tokens (alguns modelos usam max_completion_tokens ao invés de max_tokens)
            if self._needs_max_completion_tokens(db_assistant.model):
                chat_params["max_completion_tokens"] = db_assistant.max_tokens
            else:
                chat_params["max_tokens"] = db_assistant.max_tokens
            
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
            
            # Adicionar ferramentas (tools) se configuradas
            tools = None
            if db_assistant.tools_config:
                if isinstance(db_assistant.tools_config, dict):
                    tools = db_assistant.tools_config.get("tools")
                elif isinstance(db_assistant.tools_config, list):
                    tools = db_assistant.tools_config
            
            # Criar thread temporária para processamento de ferramentas (se necessário)
            # Para modo report, não precisamos de thread persistente, mas precisamos para tool calls
            import uuid
            temp_thread_id = str(uuid.uuid4())
            temp_db_thread = OpenAIAssistantThread(
                assistant_id=assistant_id,
                company_id=company_id,
                user_id=user_id,
                thread_id=temp_thread_id,
                context_data=context_data,
                is_active=True
            )
            self.db.add(temp_db_thread)
            self.db.flush()
            
            # Verificar se precisa usar Assistants API (Code Interpreter ou File Search)
            # E se o modelo é suportado pela Assistants API
            has_code_interpreter_or_file_search = tools and any(
                t.get("type") in ["code_interpreter", "file_search"] 
                for t in tools if isinstance(t, dict)
            )
            is_supported = self._is_model_supported_by_assistants_api(db_assistant.model)
            
            if has_code_interpreter_or_file_search and is_supported:
                # Usar Assistants API se o modelo suporta E tem Code Interpreter/File Search
                logger.info("🔧 Detectado Code Interpreter ou File Search com modelo suportado - usando Assistants API")
                response = self._use_assistants_api_report_mode(
                    db_assistant, temp_db_thread, user_prompt_content, tools, usage_record, start_time, request_data_size
                )
            else:
                # Usar Chat Completions (GPT-5)
                # Se tem Code Interpreter/File Search mas modelo não suporta, remover essas ferramentas
                if has_code_interpreter_or_file_search and not is_supported:
                    logger.warning(f"⚠️ Modelo {db_assistant.model} não suporta Assistants API. Code Interpreter/File Search não estarão disponíveis. Usando Chat Completions.")
                    # Remover Code Interpreter e File Search, manter apenas Function Calling
                    tools = [t for t in tools if isinstance(t, dict) and t.get("type") not in ["code_interpreter", "file_search"]]
                
                # Usar Chat Completions (com ou sem Function Calling)
                if tools and not self._is_reasoning_model(db_assistant.model):
                    chat_params["tools"] = tools
                    logger.info(f"🔧 Adicionando {len(tools)} ferramenta(s) à chamada")
                
                # Fazer chamada ao Chat Completions e processar tool calls se necessário
                logger.info(f"💬 Gerando relatório via Chat Completions (GPT-5)...")
                response = self._process_chat_with_tools(chat_params, tools, temp_db_thread, max_iterations=5)
            
            if response and response.get("success"):
                response_text = response.get("response", "")
                response_data_size = len(response_text.encode('utf-8'))
                
                # Obter uso de tokens
                usage_info_dict = response.get("usage", {})
                # Criar objeto similar ao usage_info original para compatibilidade
                class UsageInfo:
                    def __init__(self, data):
                        self.prompt_tokens = data.get("prompt_tokens", 0)
                        self.completion_tokens = data.get("completion_tokens", 0)
                        self.total_tokens = data.get("total_tokens", 0)
                
                usage_info = UsageInfo(usage_info_dict) if usage_info_dict else None
                    
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
                # Buscar thread existente no banco (com isolamento por company_id e user_id)
                query = self.db.query(OpenAIAssistantThread).filter(
                    OpenAIAssistantThread.thread_id == thread_id,
                    OpenAIAssistantThread.company_id == company_id,
                    OpenAIAssistantThread.is_active == True
                )
                
                # Adicionar filtro por user_id se fornecido (isolamento por usuário)
                if user_id:
                    query = query.filter(OpenAIAssistantThread.user_id == user_id)
                
                db_thread = query.first()
                
                if not db_thread:
                    raise Exception("Thread não encontrada ou você não tem permissão para acessá-la.")
                
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
                
                # Substituir [[INFO]] pelo JSON do context_data se existir
                if context_data:
                    if "analysis_json" in context_data:
                        # Usar o JSON formatado do frontend
                        info_json = context_data.get("analysis_json", "")
                        if "[[INFO]]" in system_content:
                            system_content = system_content.replace("[[INFO]]", info_json)
                            logger.info("✅ Substituído [[INFO]] nas instruções pelo JSON de análise")
                    else:
                        # Se não tiver analysis_json, formatar o context_data completo
                        info_json = json.dumps(context_data, ensure_ascii=False, indent=2)
                        if "[[INFO]]" in system_content:
                            system_content = system_content.replace("[[INFO]]", info_json)
                            logger.info("✅ Substituído [[INFO]] nas instruções pelo context_data completo")
                
                # Adicionar contexto adicional se fornecido (apenas se não foi usado para substituir [[INFO]])
                if context_data and "[[INFO]]" not in db_assistant.instructions:
                    context_text = json.dumps(context_data, ensure_ascii=False)
                    system_content += f"\n\n[CONTEXTO ADICIONAL]\n{context_text}"
                
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
            
            # Processar mensagem do usuário: substituir [[USUARIO]] no prompt inicial se existir
            user_message_content = message
            if db_assistant.initial_prompt and "[[USUARIO]]" in db_assistant.initial_prompt:
                # Substituir a tag [[USUARIO]] pelo texto do usuário
                user_message_content = db_assistant.initial_prompt.replace("[[USUARIO]]", message)
            
            # Adicionar mensagem atual do usuário
            messages_history.append({
                "role": "user",
                "content": user_message_content
            })
            
            # Salvar mensagem do usuário no banco (salvar a mensagem original, não a processada)
            user_message = OpenAIAssistantMessage(
                thread_id=db_thread.id,
                role="user",
                content=message  # Salvar mensagem original
            )
            self.db.add(user_message)
            self.db.flush()
            
            # Preparar parâmetros para Chat Completions
            chat_params = {
                "model": db_assistant.model,
                "messages": messages_history,
            }
            
            # Adicionar limite de tokens (alguns modelos usam max_completion_tokens ao invés de max_tokens)
            if self._needs_max_completion_tokens(db_assistant.model):
                chat_params["max_completion_tokens"] = db_assistant.max_tokens
            else:
                chat_params["max_tokens"] = db_assistant.max_tokens
            
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
            
            # Adicionar ferramentas (tools) se configuradas
            tools = None
            if db_assistant.tools_config:
                if isinstance(db_assistant.tools_config, dict):
                    tools = db_assistant.tools_config.get("tools")
                elif isinstance(db_assistant.tools_config, list):
                    tools = db_assistant.tools_config
            
            # Verificar se precisa usar Assistants API (Code Interpreter ou File Search)
            # E se o modelo é suportado pela Assistants API
            has_code_interpreter_or_file_search = tools and any(
                t.get("type") in ["code_interpreter", "file_search"] 
                for t in tools if isinstance(t, dict)
            )
            is_supported = self._is_model_supported_by_assistants_api(db_assistant.model)
            
            if has_code_interpreter_or_file_search and is_supported:
                # Usar Assistants API se o modelo suporta E tem Code Interpreter/File Search
                logger.info("🔧 Detectado Code Interpreter ou File Search com modelo suportado - usando Assistants API")
                response = self._use_assistants_api_chat_mode(
                    db_assistant, db_thread, user_message_content, tools, usage_record, start_time, request_data_size
                )
            else:
                # Usar Chat Completions (GPT-5)
                # Se tem Code Interpreter/File Search mas modelo não suporta, remover essas ferramentas
                if has_code_interpreter_or_file_search and not is_supported:
                    logger.warning(f"⚠️ Modelo {db_assistant.model} não suporta Assistants API. Code Interpreter/File Search não estarão disponíveis. Usando Chat Completions.")
                    # Remover Code Interpreter e File Search, manter apenas Function Calling
                    tools = [t for t in tools if isinstance(t, dict) and t.get("type") not in ["code_interpreter", "file_search"]]
                
                # Usar Chat Completions (com ou sem Function Calling)
                if tools and not self._is_reasoning_model(db_assistant.model):
                    chat_params["tools"] = tools
                    logger.info(f"🔧 Adicionando {len(tools)} ferramenta(s) à chamada")
                
                # Fazer chamada ao Chat Completions e processar tool calls se necessário
                logger.info(f"💬 Enviando mensagem para agente via Chat Completions (GPT-5)...")
                response = self._process_chat_with_tools(chat_params, tools, db_thread, max_iterations=5)
            
            if response and response.get("success"):
                response_text = response.get("response", "")
                response_data_size = len(response_text.encode('utf-8'))
                
                # Salvar resposta do assistente no banco
                assistant_message = OpenAIAssistantMessage(
                    thread_id=db_thread.id,
                    role="assistant",
                    content=response_text
                )
                self.db.add(assistant_message)
                
                # Obter uso de tokens
                usage_info_dict = response.get("usage", {})
                # Criar objeto similar ao usage_info original para compatibilidade
                class UsageInfo:
                    def __init__(self, data):
                        self.prompt_tokens = data.get("prompt_tokens", 0)
                        self.completion_tokens = data.get("completion_tokens", 0)
                        self.total_tokens = data.get("total_tokens", 0)
                
                usage_info = UsageInfo(usage_info_dict) if usage_info_dict else None
                
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
    
    def _process_chat_with_tools(
        self, 
        chat_params: Dict, 
        tools: Optional[List[Dict]], 
        db_thread: OpenAIAssistantThread,
        max_iterations: int = 5
    ) -> Dict:
        """
        Processa chat com suporte a tool calls.
        Faz loop até que o modelo não queira mais chamar ferramentas.
        """
        messages = chat_params.get("messages", [])
        total_usage = None
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"🔄 Iteração {iteration}/{max_iterations} do chat com ferramentas...")
            
            # Fazer chamada ao Chat Completions
            response = self.client.chat.completions.create(**chat_params)
            
            if not response.choices or len(response.choices) == 0:
                return {"success": False, "error": "Resposta do agente não encontrada."}
            
            message = response.choices[0].message
            usage_info = response.usage if hasattr(response, 'usage') else None
            
            # Acumular uso de tokens
            if usage_info:
                if total_usage is None:
                    total_usage = {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0
                    }
                total_usage["prompt_tokens"] += usage_info.prompt_tokens
                total_usage["completion_tokens"] += usage_info.completion_tokens
                total_usage["total_tokens"] += usage_info.total_tokens
            
            # Verificar se o modelo quer chamar ferramentas
            if message.tool_calls and len(message.tool_calls) > 0:
                logger.info(f"🔧 Modelo quer chamar {len(message.tool_calls)} ferramenta(s)")
                
                # Adicionar mensagem do assistente com tool_calls ao histórico
                assistant_message_dict = {
                    "role": "assistant",
                    "content": message.content or None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                }
                messages.append(assistant_message_dict)
                
                # Salvar mensagem do assistente com tool_calls no banco
                assistant_message = OpenAIAssistantMessage(
                    thread_id=db_thread.id,
                    role="assistant",
                    content=json.dumps({
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in message.tool_calls
                        ]
                    }, ensure_ascii=False)
                )
                self.db.add(assistant_message)
                self.db.flush()
                
                # Processar cada tool call
                tool_outputs = []
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    try:
                        function_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        function_args = {}
                    
                    logger.info(f"⚙️ Processando ferramenta: {function_name} com args: {function_args}")
                    
                    # Executar função local (aqui você implementa suas funções)
                    result = self._execute_tool_function(function_name, function_args, db_thread)
                    
                    # Adicionar resultado ao histórico
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(result, ensure_ascii=False)
                    })
                    
                    # Salvar resultado no banco
                    tool_message = OpenAIAssistantMessage(
                        thread_id=db_thread.id,
                        role="tool",
                        content=json.dumps(result, ensure_ascii=False)
                    )
                    self.db.add(tool_message)
                    self.db.flush()
                
                # Adicionar resultados ao histórico de mensagens
                messages.extend(tool_outputs)
                
                # Atualizar chat_params para próxima iteração
                chat_params["messages"] = messages
                
                # Continuar loop para processar resposta final
                continue
            else:
                # Não há tool calls, retornar resposta final
                response_text = message.content or ""
                
                # Salvar resposta final do assistente no banco
                assistant_message = OpenAIAssistantMessage(
                    thread_id=db_thread.id,
                    role="assistant",
                    content=response_text
                )
                self.db.add(assistant_message)
                self.db.flush()
                
                return {
                    "success": True,
                    "response": response_text,
                    "usage": total_usage or {
                        "prompt_tokens": usage_info.prompt_tokens if usage_info else 0,
                        "completion_tokens": usage_info.completion_tokens if usage_info else 0,
                        "total_tokens": usage_info.total_tokens if usage_info else 0
                    }
                }
        
        # Se chegou aqui, excedeu o número máximo de iterações
        logger.warning(f"⚠️ Máximo de iterações ({max_iterations}) atingido")
        return {
            "success": False,
            "error": f"Máximo de iterações ({max_iterations}) atingido. O modelo pode estar em loop."
        }
    
    def _execute_tool_function(self, function_name: str, function_args: Dict, db_thread: OpenAIAssistantThread) -> Dict:
        """
        Executa uma função de ferramenta customizada.
        Aqui você implementa as funções que o agente pode chamar.
        """
        try:
            logger.info(f"🔨 Executando função: {function_name}")
            
            # Exemplo de implementação de funções
            # Você pode adicionar mais funções aqui conforme necessário
            
            if function_name == "get_ml_order_status":
                # Exemplo: buscar status de pedido
                order_id = function_args.get("order_id")
                if not order_id:
                    return {"error": "order_id é obrigatório"}
                
                # Aqui você implementaria a lógica real
                # Por enquanto, retornamos um exemplo
                return {
                    "order_id": order_id,
                    "status": "pending",
                    "message": "Função get_ml_order_status chamada com sucesso (implementação pendente)"
                }
            
            elif function_name == "get_product_info":
                # Exemplo: buscar informações de produto
                product_id = function_args.get("product_id")
                if not product_id:
                    return {"error": "product_id é obrigatório"}
                
                return {
                    "product_id": product_id,
                    "message": "Função get_product_info chamada com sucesso (implementação pendente)"
                }
            
            else:
                # Função não implementada
                logger.warning(f"⚠️ Função '{function_name}' não implementada")
                return {
                    "error": f"Função '{function_name}' não está implementada no sistema",
                    "available_functions": ["get_ml_order_status", "get_product_info"]
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao executar função {function_name}: {e}", exc_info=True)
            return {"error": f"Erro ao executar função: {str(e)}"}
    
    def _use_assistants_api_chat_mode(
        self,
        db_assistant: OpenAIAssistant,
        db_thread: OpenAIAssistantThread,
        user_message: str,
        tools: List[Dict],
        usage_record: OpenAIAssistantUsage,
        start_time: float,
        request_data_size: int
    ) -> Dict:
        """
        Usa Assistants API quando Code Interpreter ou File Search estão presentes.
        Cria ou atualiza assistente na OpenAI e usa threads/runs.
        """
        # Verificar se o modelo é suportado ANTES de tentar usar Assistants API
        if not self._is_model_supported_by_assistants_api(db_assistant.model):
            error_msg = f"Modelo {db_assistant.model} não é suportado pela Assistants API. Use Chat Completions."
            logger.warning(f"⚠️ {error_msg}")
            raise Exception(error_msg)
        
        try:
            logger.info("🤖 Usando Assistants API para Code Interpreter/File Search")
            
            # Verificar se já existe assistente na OpenAI
            openai_assistant_id = None
            if db_assistant.assistant_id and not db_assistant.assistant_id.startswith("local_"):
                # Verificar se o assistant_id é válido (deve começar com "asst")
                if db_assistant.assistant_id.startswith("asst_"):
                    # Tentar usar assistente existente
                    try:
                        existing_assistant = self.client.beta.assistants.retrieve(db_assistant.assistant_id)
                        openai_assistant_id = existing_assistant.id
                        logger.info(f"✅ Usando assistente OpenAI existente: {openai_assistant_id}")
                    except Exception as e:
                        logger.warning(f"⚠️ Assistente OpenAI não encontrado, criando novo: {e}")
                        # Limpar assistant_id inválido do banco (usar "local_" como prefixo para indicar que não é um ID da OpenAI)
                        db_assistant.assistant_id = f"local_{db_assistant.id}_{int(time.time())}"
                        self.db.commit()
                        openai_assistant_id = None
                else:
                    # assistant_id inválido (não começa com "asst_"), limpar e criar novo
                    logger.warning(f"⚠️ assistant_id inválido no banco ({db_assistant.assistant_id}), criando novo assistente")
                    db_assistant.assistant_id = f"local_{db_assistant.id}_{int(time.time())}"
                    self.db.commit()
                    openai_assistant_id = None
            
            # Criar ou atualizar assistente na OpenAI se necessário
            if not openai_assistant_id:
                assistant_params = {
                    "name": db_assistant.name,
                    "instructions": db_assistant.instructions,
                    "model": db_assistant.model,
                    "tools": tools
                }
                
                # Adicionar parâmetros específicos do modelo
                # NOTA: reasoning_effort e verbosity podem não ser suportados na criação do assistente
                # mas vamos tentar adicioná-los se for GPT-5 (podem ser suportados na API v2)
                if self._is_gpt5_model(db_assistant.model):
                    if db_assistant.tools_config and isinstance(db_assistant.tools_config, dict):
                        # Tentar adicionar reasoning_effort e verbosity (pode falhar, mas vamos tentar)
                        if db_assistant.tools_config.get("reasoning_effort"):
                            assistant_params["reasoning_effort"] = db_assistant.tools_config["reasoning_effort"]
                        if db_assistant.tools_config.get("verbosity"):
                            assistant_params["verbosity"] = db_assistant.tools_config["verbosity"]
                elif not self._is_reasoning_model(db_assistant.model):
                    if db_assistant.temperature is not None:
                        assistant_params["temperature"] = float(db_assistant.temperature)
                
                # Criar assistente (header v2 já está configurado no cliente via default_headers)
                try:
                    # Tentar criar com reasoning_effort/verbosity se for GPT-5
                    openai_assistant = self.client.beta.assistants.create(**assistant_params)
                except (TypeError, AttributeError) as e:
                    # Se reasoning_effort ou verbosity não forem suportados, remover e tentar novamente
                    if "reasoning_effort" in str(e) or "verbosity" in str(e):
                        logger.warning(f"⚠️ reasoning_effort/verbosity não suportados na criação do assistente, removendo: {e}")
                        assistant_params.pop("reasoning_effort", None)
                        assistant_params.pop("verbosity", None)
                        openai_assistant = self.client.beta.assistants.create(**assistant_params)
                    else:
                        raise
                except Exception as e:
                    # Se o erro for sobre API v1, o header pode não estar sendo aplicado
                    if "v1 Assistants API has been deprecated" in str(e) or "invalid_beta" in str(e):
                        logger.error(f"❌ Erro: Header v2 não está sendo aplicado. Verifique a versão do SDK: {e}")
                        raise Exception("Assistants API v2 não configurada corretamente. Atualize o SDK do OpenAI.")
                    else:
                        raise
                openai_assistant_id = openai_assistant.id
                
                # Atualizar assistant_id no banco
                db_assistant.assistant_id = openai_assistant_id
                self.db.commit()
                logger.info(f"✅ Assistente criado na OpenAI: {openai_assistant_id}")
            
            # Criar ou buscar thread na OpenAI
            openai_thread_id = db_thread.thread_id
            if not openai_thread_id or openai_thread_id.startswith("local_"):
                # Criar nova thread na OpenAI (header v2 já está configurado no cliente)
                openai_thread = self.client.beta.threads.create()
                openai_thread_id = openai_thread.id
                db_thread.thread_id = openai_thread_id
                self.db.commit()
                logger.info(f"✅ Thread criada na OpenAI: {openai_thread_id}")
            
            # Adicionar mensagem do usuário à thread (header v2 já está configurado no cliente)
            self.client.beta.threads.messages.create(
                thread_id=openai_thread_id,
                role="user",
                content=user_message
            )
            
            # Criar run com parâmetros adicionais se for GPT-5
            run_params = {
                "thread_id": openai_thread_id,
                "assistant_id": openai_assistant_id
            }
            
            # Tentar adicionar reasoning_effort e verbosity no run (podem ser suportados aqui)
            if self._is_gpt5_model(db_assistant.model):
                if db_assistant.tools_config and isinstance(db_assistant.tools_config, dict):
                    if db_assistant.tools_config.get("reasoning_effort"):
                        run_params["reasoning_effort"] = db_assistant.tools_config["reasoning_effort"]
                    if db_assistant.tools_config.get("verbosity"):
                        run_params["verbosity"] = db_assistant.tools_config["verbosity"]
            
            try:
                run = self.client.beta.threads.runs.create(**run_params)
            except TypeError as e:
                # Se não suportar no run, criar sem esses parâmetros
                if "reasoning_effort" in str(e) or "verbosity" in str(e):
                    logger.warning(f"⚠️ reasoning_effort/verbosity não suportados no run, removendo: {e}")
                    run_params.pop("reasoning_effort", None)
                    run_params.pop("verbosity", None)
                    run = self.client.beta.threads.runs.create(**run_params)
                else:
                    raise
            
            # Aguardar conclusão do run
            logger.info(f"⏳ Aguardando conclusão do run {run.id}...")
            while run.status in ["queued", "in_progress", "requires_action"]:
                time.sleep(1)
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=openai_thread_id,
                    run_id=run.id
                )
                
                # Processar tool calls se necessário
                if run.status == "requires_action":
                    tool_outputs = []
                    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                        if tool_call.type == "function":
                            function_name = tool_call.function.name
                            function_args = json.loads(tool_call.function.arguments)
                            result = self._execute_tool_function(function_name, function_args, db_thread)
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": json.dumps(result, ensure_ascii=False)
                            })
                    
                    if tool_outputs:
                        run = self.client.beta.threads.runs.submit_tool_outputs(
                            thread_id=openai_thread_id,
                            run_id=run.id,
                            tool_outputs=tool_outputs
                        )
            
            # Verificar resultado
            if run.status == "completed":
                # Buscar mensagens da thread
                messages = self.client.beta.threads.messages.list(thread_id=openai_thread_id)
                response_text = ""
                
                for msg in messages.data:
                    if msg.role == "assistant" and msg.content:
                        if isinstance(msg.content, list):
                            for content in msg.content:
                                if hasattr(content, 'text'):
                                    response_text = content.text.value
                                    break
                        break
                
                # Salvar resposta no banco
                assistant_message = OpenAIAssistantMessage(
                    thread_id=db_thread.id,
                    role="assistant",
                    content=response_text
                )
                self.db.add(assistant_message)
                
                # Obter uso de tokens
                usage_info = None
                if hasattr(run, 'usage') and run.usage:
                    usage_info = run.usage
                
                # Atualizar métricas
                db_assistant.total_runs += 1
                if usage_info:
                    db_assistant.total_tokens_used += usage_info.total_tokens
                db_assistant.last_used_at = datetime.utcnow()
                
                # Atualizar registro de uso
                duration = time.time() - start_time
                usage_record.status = UsageStatus.COMPLETED
                usage_record.completed_at = datetime.utcnow()
                usage_record.duration_seconds = duration
                usage_record.response_data_size = len(response_text.encode('utf-8'))
                usage_record.request_data_size = request_data_size
                
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
                error_msg = f"Run falhou com status: {run.status}"
                if hasattr(run, 'last_error') and run.last_error:
                    error_msg += f" - {run.last_error.message}"
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"❌ Erro ao usar Assistants API: {e}", exc_info=True)
            usage_record.status = UsageStatus.FAILED
            usage_record.error_message = str(e)
            usage_record.completed_at = datetime.utcnow()
            usage_record.duration_seconds = time.time() - start_time
            self.db.commit()
            return {"success": False, "error": str(e)}
    
    def _use_assistants_api_report_mode(
        self,
        db_assistant: OpenAIAssistant,
        db_thread: OpenAIAssistantThread,
        user_prompt: str,
        tools: List[Dict],
        usage_record: OpenAIAssistantUsage,
        start_time: float,
        request_data_size: int
    ) -> Dict:
        """
        Usa Assistants API para modo report quando Code Interpreter ou File Search estão presentes.
        Similar ao _use_assistants_api_chat_mode mas para modo report.
        """
        try:
            logger.info("🤖 Usando Assistants API para modo report (Code Interpreter/File Search)")
            
            # Verificar se já existe assistente na OpenAI
            openai_assistant_id = None
            if db_assistant.assistant_id and not db_assistant.assistant_id.startswith("local_"):
                try:
                    existing_assistant = self.client.beta.assistants.retrieve(db_assistant.assistant_id)
                    openai_assistant_id = existing_assistant.id
                    logger.info(f"✅ Usando assistente OpenAI existente: {openai_assistant_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Assistente OpenAI não encontrado, criando novo: {e}")
                    openai_assistant_id = None
            
            # Criar ou atualizar assistente na OpenAI se necessário
            if not openai_assistant_id:
                assistant_params = {
                    "name": db_assistant.name,
                    "instructions": db_assistant.instructions,
                    "model": db_assistant.model,
                    "tools": tools
                }
                
                # Adicionar parâmetros específicos do modelo
                # NOTA: reasoning_effort e verbosity podem não ser suportados na criação do assistente
                # mas vamos tentar adicioná-los se for GPT-5 (podem ser suportados na API v2)
                if self._is_gpt5_model(db_assistant.model):
                    if db_assistant.tools_config and isinstance(db_assistant.tools_config, dict):
                        # Tentar adicionar reasoning_effort e verbosity (pode falhar, mas vamos tentar)
                        if db_assistant.tools_config.get("reasoning_effort"):
                            assistant_params["reasoning_effort"] = db_assistant.tools_config["reasoning_effort"]
                        if db_assistant.tools_config.get("verbosity"):
                            assistant_params["verbosity"] = db_assistant.tools_config["verbosity"]
                elif not self._is_reasoning_model(db_assistant.model):
                    if db_assistant.temperature is not None:
                        assistant_params["temperature"] = float(db_assistant.temperature)
                
                # Criar assistente (header v2 já está configurado no cliente via default_headers)
                try:
                    # Tentar criar com reasoning_effort/verbosity se for GPT-5
                    openai_assistant = self.client.beta.assistants.create(**assistant_params)
                except (TypeError, AttributeError) as e:
                    # Se reasoning_effort ou verbosity não forem suportados, remover e tentar novamente
                    if "reasoning_effort" in str(e) or "verbosity" in str(e):
                        logger.warning(f"⚠️ reasoning_effort/verbosity não suportados na criação do assistente, removendo: {e}")
                        assistant_params.pop("reasoning_effort", None)
                        assistant_params.pop("verbosity", None)
                        openai_assistant = self.client.beta.assistants.create(**assistant_params)
                    else:
                        raise
                except Exception as e:
                    # Se o erro for sobre API v1, o header pode não estar sendo aplicado
                    if "v1 Assistants API has been deprecated" in str(e) or "invalid_beta" in str(e):
                        logger.error(f"❌ Erro: Header v2 não está sendo aplicado. Verifique a versão do SDK: {e}")
                        raise Exception("Assistants API v2 não configurada corretamente. Atualize o SDK do OpenAI.")
                    else:
                        raise
                openai_assistant_id = openai_assistant.id
                
                # Atualizar assistant_id no banco
                db_assistant.assistant_id = openai_assistant_id
                self.db.commit()
                logger.info(f"✅ Assistente criado na OpenAI: {openai_assistant_id}")
            
            # Criar thread temporária na OpenAI
            openai_thread = self.client.beta.threads.create()
            openai_thread_id = openai_thread.id
            logger.info(f"✅ Thread criada na OpenAI: {openai_thread_id}")
            
            # Adicionar mensagem do usuário à thread
            self.client.beta.threads.messages.create(
                thread_id=openai_thread_id,
                role="user",
                content=user_prompt
            )
            
            # Criar run com parâmetros adicionais se for GPT-5
            run_params = {
                "thread_id": openai_thread_id,
                "assistant_id": openai_assistant_id
            }
            
            # Tentar adicionar reasoning_effort e verbosity no run (podem ser suportados aqui)
            if self._is_gpt5_model(db_assistant.model):
                if db_assistant.tools_config and isinstance(db_assistant.tools_config, dict):
                    if db_assistant.tools_config.get("reasoning_effort"):
                        run_params["reasoning_effort"] = db_assistant.tools_config["reasoning_effort"]
                    if db_assistant.tools_config.get("verbosity"):
                        run_params["verbosity"] = db_assistant.tools_config["verbosity"]
            
            try:
                run = self.client.beta.threads.runs.create(**run_params)
            except TypeError as e:
                # Se não suportar no run, criar sem esses parâmetros
                if "reasoning_effort" in str(e) or "verbosity" in str(e):
                    logger.warning(f"⚠️ reasoning_effort/verbosity não suportados no run, removendo: {e}")
                    run_params.pop("reasoning_effort", None)
                    run_params.pop("verbosity", None)
                    run = self.client.beta.threads.runs.create(**run_params)
                else:
                    raise
            
            # Aguardar conclusão do run
            logger.info(f"⏳ Aguardando conclusão do run {run.id}...")
            while run.status in ["queued", "in_progress", "requires_action"]:
                time.sleep(1)
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=openai_thread_id,
                    run_id=run.id
                )
                
                # Processar tool calls se necessário
                if run.status == "requires_action":
                    tool_outputs = []
                    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                        if tool_call.type == "function":
                            function_name = tool_call.function.name
                            function_args = json.loads(tool_call.function.arguments)
                            result = self._execute_tool_function(function_name, function_args, db_thread)
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": json.dumps(result, ensure_ascii=False)
                            })
                    
                    if tool_outputs:
                        run = self.client.beta.threads.runs.submit_tool_outputs(
                            thread_id=openai_thread_id,
                            run_id=run.id,
                            tool_outputs=tool_outputs
                        )
            
            # Verificar resultado
            if run.status == "completed":
                # Buscar mensagens da thread
                messages = self.client.beta.threads.messages.list(thread_id=openai_thread_id)
                response_text = ""
                
                for msg in messages.data:
                    if msg.role == "assistant" and msg.content:
                        if isinstance(msg.content, list):
                            for content in msg.content:
                                if hasattr(content, 'text'):
                                    response_text = content.text.value
                                    break
                        break
                
                # Obter uso de tokens
                usage_info = None
                if hasattr(run, 'usage') and run.usage:
                    usage_info = run.usage
                
                # Atualizar métricas
                db_assistant.total_runs += 1
                if usage_info:
                    db_assistant.total_tokens_used += usage_info.total_tokens
                db_assistant.last_used_at = datetime.utcnow()
                
                # Atualizar registro de uso
                duration = time.time() - start_time
                usage_record.status = UsageStatus.COMPLETED
                usage_record.completed_at = datetime.utcnow()
                usage_record.duration_seconds = duration
                usage_record.response_data_size = len(response_text.encode('utf-8'))
                usage_record.request_data_size = request_data_size
                
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
                error_msg = f"Run falhou com status: {run.status}"
                if hasattr(run, 'last_error') and run.last_error:
                    error_msg += f" - {run.last_error.message}"
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"❌ Erro ao usar Assistants API (report mode): {e}", exc_info=True)
            usage_record.status = UsageStatus.FAILED
            usage_record.error_message = str(e)
            usage_record.completed_at = datetime.utcnow()
            usage_record.duration_seconds = time.time() - start_time
            self.db.commit()
            return {"success": False, "error": str(e)}
    
    def get_chat_history(self, thread_id: str, company_id: int, user_id: Optional[int] = None, limit: int = 50) -> Dict:
        """Obtém histórico de mensagens de uma thread"""
        if not self.client:
            return {"success": False, "error": "OpenAI API key não configurada."}
        
        try:
            # Verificar se thread pertence à company e ao user (isolamento)
            query = self.db.query(OpenAIAssistantThread).filter(
                OpenAIAssistantThread.thread_id == thread_id,
                OpenAIAssistantThread.company_id == company_id
            )
            
            # Adicionar filtro por user_id se fornecido (isolamento por usuário)
            if user_id:
                query = query.filter(OpenAIAssistantThread.user_id == user_id)
            
            db_thread = query.first()
            
            if not db_thread:
                return {"success": False, "error": "Thread não encontrada ou você não tem permissão para acessá-la."}
            
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

