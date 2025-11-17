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
        initial_prompt: Optional[str] = None,
        welcome_enabled: Optional[bool] = False,
        welcome_use_model: Optional[bool] = False,
        welcome_message: Optional[str] = None
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
                welcome_enabled=bool(welcome_enabled),
                welcome_use_model=bool(welcome_use_model),
                welcome_message=welcome_message,
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
        initial_prompt: Optional[str] = None,
        welcome_enabled: Optional[bool] = None,
        welcome_use_model: Optional[bool] = None,
        welcome_message: Optional[str] = None
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
            if welcome_enabled is not None:
                db_assistant.welcome_enabled = bool(welcome_enabled)
            if welcome_use_model is not None:
                db_assistant.welcome_use_model = bool(welcome_use_model)
            if welcome_message is not None:
                db_assistant.welcome_message = welcome_message
            
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
            
            # Carregar ferramentas vinculadas no banco (estrutura reutilizável)
            db_tools = self._load_agent_tools_from_db(assistant_id)
            if db_tools:
                tools = db_tools
            
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
                response = self._process_chat_with_tools(chat_params, tools, temp_db_thread, max_iterations=10)
            
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
                
                # Regras específicas do agente devem ser configuradas nas instruções do próprio agente (DB), não aqui.
                
                messages_history.append({
                    "role": "system",
                    "content": system_content
                })
            
            # Adicionar mensagens anteriores do histórico
            # IMPORTANTE: Reconstruir estrutura correta para tool calls
            i = 0
            while i < len(previous_messages):
                prev_msg = previous_messages[i]
                msg_dict = {
                    "role": prev_msg.role,
                    "content": prev_msg.content
                }
                
                # Se for mensagem 'assistant', verificar se tem tool_calls no content (JSON)
                if prev_msg.role == "assistant" and prev_msg.content:
                    try:
                        content_json = json.loads(prev_msg.content)
                        if isinstance(content_json, dict) and "tool_calls" in content_json:
                            # Reconstruir estrutura com tool_calls
                            msg_dict["tool_calls"] = []
                            for tc in content_json["tool_calls"]:
                                msg_dict["tool_calls"].append({
                                    "id": tc.get("id", ""),
                                    "type": "function",
                                    "function": {
                                        "name": tc.get("function", {}).get("name", ""),
                                        "arguments": tc.get("function", {}).get("arguments", "{}")
                                    }
                                })
                            # Se tem tool_calls, content deve ser None
                            msg_dict["content"] = None
                            messages_history.append(msg_dict)
                            
                            # Próximas mensagens 'tool' devem ser associadas a esta mensagem 'assistant'
                            # Avançar e adicionar mensagens 'tool' seguintes com tool_call_id
                            i += 1
                            tool_call_index = 0
                            while i < len(previous_messages) and previous_messages[i].role == "tool":
                                tool_msg = previous_messages[i]
                                
                                # Tentar extrair tool_call_id e name do content (JSON estruturado)
                                tool_call_id = None
                                tool_name = None
                                tool_result = None
                                
                                try:
                                    tool_content = json.loads(tool_msg.content) if tool_msg.content else {}
                                    if isinstance(tool_content, dict):
                                        # Formato novo: {tool_call_id, name, result}
                                        if "tool_call_id" in tool_content:
                                            tool_call_id = tool_content.get("tool_call_id")
                                            tool_name = tool_content.get("name")
                                            tool_result = tool_content.get("result")
                                        else:
                                            # Formato antigo: apenas resultado direto
                                            tool_result = tool_content
                                except (json.JSONDecodeError, TypeError):
                                    # Content não é JSON, tratar como string direta
                                    tool_result = tool_msg.content
                                
                                # Se não encontrou tool_call_id no content, usar do tool_calls correspondente
                                if not tool_call_id and tool_call_index < len(msg_dict["tool_calls"]):
                                    tool_call_id = msg_dict["tool_calls"][tool_call_index].get("id")
                                
                                # Se não encontrou name, usar do tool_calls correspondente
                                if not tool_name and tool_call_index < len(msg_dict["tool_calls"]):
                                    tool_name = msg_dict["tool_calls"][tool_call_index].get("function", {}).get("name")
                                
                                # Serializar resultado para content
                                if tool_result is not None:
                                    content_str = json.dumps(tool_result, ensure_ascii=False) if isinstance(tool_result, (dict, list)) else str(tool_result)
                                else:
                                    content_str = tool_msg.content or ""
                                
                                # Adicionar mensagem tool com estrutura correta
                                tool_dict = {
                                    "role": "tool",
                                    "content": content_str,
                                    "tool_call_id": tool_call_id or f"call_{i}"  # Fallback se não tiver ID
                                }
                                if tool_name:
                                    tool_dict["name"] = tool_name
                                
                                messages_history.append(tool_dict)
                                i += 1
                                tool_call_index += 1
                            
                            # Continuar loop sem incrementar i novamente (já foi incrementado)
                            continue
                    except (json.JSONDecodeError, KeyError, TypeError):
                        # Não é JSON com tool_calls, tratar como mensagem normal
                        pass
                
                # Mensagem normal (user, assistant sem tool_calls)
                # Se for mensagem 'tool' isolada (sem assistant anterior com tool_calls), pular
                if prev_msg.role == "tool":
                    logger.warning(f"⚠️ Mensagem 'tool' isolada encontrada (índice {i}), pulando. Isso pode indicar dados inconsistentes.")
                    i += 1
                    continue
                
                messages_history.append(msg_dict)
                i += 1
            
            # Processar mensagem do usuário e mensagem de boas-vindas configurável
            kickoff_used = False
            user_message_content = message
            welcome_enabled = getattr(db_assistant, "welcome_enabled", False)
            welcome_use_model = getattr(db_assistant, "welcome_use_model", False)
            welcome_text_cfg = getattr(db_assistant, "welcome_message", None)
            if not previous_messages and welcome_enabled:
                welcome_text = (welcome_text_cfg or "").strip()
                if welcome_text and welcome_use_model and (not message or not message.strip()):
                    # Dinâmica: usar welcome_text como kickoff para o modelo (não salvar como role=user no banco)
                    user_message_content = welcome_text
                    kickoff_used = True
                elif welcome_text and not welcome_use_model:
                    # Fixa: registrar mensagem assistant imediatamente (sem custo)
                    assistant_welcome = OpenAIAssistantMessage(
                        thread_id=db_thread.id,
                        role="assistant",
                        content=welcome_text
                    )
                    self.db.add(assistant_welcome)
                    self.db.flush()
                    # Se usuário não enviou nada, podemos retornar apenas a mensagem de boas-vindas
                    if not message or not message.strip():
                        db_thread.last_message_at = datetime.utcnow()
                        db_thread.updated_at = datetime.utcnow()
                        self.db.commit()
                        return {
                            "success": True,
                            "response": welcome_text,
                            "thread_id": openai_thread_id,
                            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                        }
            # Substituir [[USUARIO]] no prompt inicial se existir
            if db_assistant.initial_prompt and "[[USUARIO]]" in db_assistant.initial_prompt:
                user_message_content = db_assistant.initial_prompt.replace("[[USUARIO]]", user_message_content)
            # Adicionar mensagem atual do usuário (apenas se não for kickoff sintético)
            messages_history.append({
                "role": "user",
                "content": user_message_content
            })
            if not kickoff_used:
                # Salvar mensagem do usuário no banco (original)
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

            # Carregar ferramentas vinculadas no banco (estrutura reutilizável)
            # Todas as ferramentas devem estar associadas ao agente via tabela openai_agent_tools
            db_tools = self._load_agent_tools_from_db(assistant_id)
            if db_tools:
                tools = db_tools
            
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
                response = self._process_chat_with_tools(chat_params, tools, db_thread, max_iterations=10)
            
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
                # Tratar erro de forma mais amigável
                error_msg = response.get("error", "Resposta do agente não encontrada.") if response else "Resposta do agente não encontrada."
                
                # Se foi limite de iterações, retornar mensagem amigável ao usuário
                if "Máximo de iterações" in error_msg:
                    friendly_msg = "Desculpe, o agente precisou fazer muitas consultas e atingiu o limite de processamento. Por favor, tente reformular sua pergunta de forma mais específica ou divida em partes menores."
                else:
                    friendly_msg = f"Desculpe, ocorreu um erro ao processar sua mensagem: {error_msg}"
                
                # Salvar mensagem de erro como resposta do assistente
                assistant_message = OpenAIAssistantMessage(
                    thread_id=db_thread.id,
                    role="assistant",
                    content=friendly_msg
                )
                self.db.add(assistant_message)
                db_thread.last_message_at = datetime.utcnow()
                db_thread.updated_at = datetime.utcnow()
                
                # Marcar uso como falha
                usage_record.status = UsageStatus.FAILED
                usage_record.error_message = error_msg
                usage_record.completed_at = datetime.utcnow()
                usage_record.duration_seconds = time.time() - start_time
                self.db.commit()
                
                return {
                    "success": True,
                    "response": friendly_msg,
                    "thread_id": openai_thread_id,
                    "usage": None
                }
                
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
                    # Incluir tool_call_id e name no content como metadados para reconstrução
                    tool_content = {
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "result": result
                    }
                    tool_message = OpenAIAssistantMessage(
                        thread_id=db_thread.id,
                        role="tool",
                        content=json.dumps(tool_content, ensure_ascii=False)
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
        
        # Tentar retornar última resposta parcial se houver
        if messages:
            # Buscar última mensagem do assistente que não seja tool_call
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("role") == "assistant":
                    content = msg.get("content")
                    if content and not msg.get("tool_calls"):
                        # Retornar resposta parcial
                        return {
                            "success": True,
                            "response": content + "\n\n[Nota: Resposta parcial devido ao limite de processamento. Por favor, reformule sua pergunta se necessário.]",
                            "usage": total_usage or {
                                "prompt_tokens": 0,
                                "completion_tokens": 0,
                                "total_tokens": 0
                            }
                        }
        
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
            company_id = db_thread.company_id
            user_id = db_thread.user_id
            
            # ========== Product Core ==========
            if function_name == "get_product_core":
                product_id = int(function_args.get("product_id"))
                if not product_id:
                    return {"error": "product_id é obrigatório"}
                from app.models.saas_models import MLProduct
                p = self.db.query(MLProduct).filter(MLProduct.id == product_id, MLProduct.company_id == company_id).first()
                if not p:
                    return {"error": "Produto não encontrado"}
                return {
                    "id": p.id,
                    "ml_item_id": p.ml_item_id,
                    "price": float(p.price) if p.price else None,
                    "available_quantity": p.available_quantity,
                    "category_id": p.category_id,
                    "listing_type_id": p.listing_type_id,
                    "seller_sku": p.seller_sku,
                    "title": p.title,
                }

            # ========== Product Attributes ==========
            if function_name == "get_product_attributes":
                product_id = int(function_args.get("product_id"))
                if not product_id:
                    return {"error": "product_id é obrigatório"}
                from app.models.saas_models import MLProduct
                p = self.db.query(MLProduct).filter(MLProduct.id == product_id, MLProduct.company_id == company_id).first()
                if not p:
                    return {"error": "Produto não encontrado"}
                return {
                    "attributes": p.attributes,
                    "variations": p.variations,
                    "shipping": p.shipping,
                    "tags": p.tags,
                    "health": p.health,
                }

            # ========== Orders by Item ==========
            if function_name == "get_orders_by_item":
                ml_item_id = str(function_args.get("ml_item_id"))
                if not ml_item_id:
                    return {"error": "ml_item_id é obrigatório"}
                from datetime import datetime, timedelta
                days = int(function_args.get("days", 30))
                since = datetime.utcnow() - timedelta(days=days)
                from app.models.saas_models import MLOrder
                orders = (self.db.query(MLOrder)
                          .filter(MLOrder.company_id == company_id,
                                  MLOrder.date_created >= since,
                                  MLOrder.order_items.isnot(None))
                          .all())
                result = []
                for o in orders:
                    try:
                        if any((it.get("item", {}).get("id") == ml_item_id) for it in (o.order_items or [])):
                            result.append({
                                "id": str(o.ml_order_id),
                                "date": o.date_created.isoformat() if o.date_created else None,
                                "total_amount": float(o.total_amount) if o.total_amount else 0,
                                "status": (o.status.value if hasattr(o.status, 'value') else str(o.status)),
                                "sale_fees": float(o.sale_fees) if o.sale_fees else 0,
                                "shipping_cost": float(o.shipping_cost) if o.shipping_cost else 0,
                                "coupon_amount": float(o.coupon_amount) if o.coupon_amount else 0,
                            })
                    except Exception:
                        # Ignorar pedidos malformados
                        continue
                return {"orders": result}

            # ========== Sales Aggregates ==========
            if function_name == "get_sales_aggregates":
                ml_item_id = str(function_args.get("ml_item_id"))
                if not ml_item_id:
                    return {"error": "ml_item_id é obrigatório"}
                from datetime import datetime, timedelta
                days = int(function_args.get("days", 30))
                since = datetime.utcnow() - timedelta(days=days)
                from app.models.saas_models import MLOrder
                orders = (self.db.query(MLOrder)
                          .filter(MLOrder.company_id == company_id,
                                  MLOrder.date_created >= since,
                                  MLOrder.order_items.isnot(None))
                          .all())
                total_revenue = 0.0
                total_qty = 0
                paid_orders_count = 0
                for o in orders:
                    has_item = False
                    qty_for_order = 0
                    if o.order_items:
                        for it in o.order_items:
                            if it.get("item", {}).get("id") == ml_item_id:
                                has_item = True
                                qty_for_order += int(it.get("quantity", 1))
                    if not has_item:
                        continue
                    amount = float(o.total_amount) if o.total_amount else 0.0
                    total_revenue += amount
                    total_qty += qty_for_order
                    status_str = (o.status.value if hasattr(o.status, 'value') else str(o.status))
                    if status_str in ["paid", "delivered"]:
                        paid_orders_count += 1
                ticket_medio_pedido = (total_revenue / paid_orders_count) if paid_orders_count > 0 else 0.0
                preco_medio_unidade = (total_revenue / total_qty) if total_qty > 0 else 0.0
                return {
                    "receita_total": total_revenue,
                    "pedidos_pagos": paid_orders_count,
                    "quantidade_vendida": total_qty,
                    "ticket_medio_pedido": ticket_medio_pedido,
                    "preco_medio_unidade": preco_medio_unidade,
                }

            # ========== Billing Breakdown ==========
            if function_name == "get_billing_breakdown":
                ml_item_id = str(function_args.get("ml_item_id"))
                if not ml_item_id:
                    return {"error": "ml_item_id é obrigatório"}
                from datetime import datetime, timedelta
                days = int(function_args.get("days", 30))
                since = datetime.utcnow() - timedelta(days=days)
                from app.models.saas_models import MLOrder
                orders = (self.db.query(MLOrder)
                          .filter(MLOrder.company_id == company_id,
                                  MLOrder.date_created >= since,
                                  MLOrder.order_items.isnot(None))
                          .all())
                total_revenue = total_fees = total_shipping = total_discounts = 0.0
                for o in orders:
                    if any((it.get("item", {}).get("id") == ml_item_id) for it in (o.order_items or [])):
                        total_revenue += float(o.total_amount) if o.total_amount else 0.0
                        total_fees += float(o.sale_fees) if o.sale_fees else 0.0
                        total_shipping += float(o.shipping_cost) if o.shipping_cost else 0.0
                        total_discounts += float(o.coupon_amount) if o.coupon_amount else 0.0
                faturamento_liquido = total_revenue - total_fees - total_shipping - total_discounts
                return {
                    "receita_total": total_revenue,
                    "comissoes_ml_total": total_fees,
                    "frete_total": total_shipping,
                    "descontos_total": total_discounts,
                    "faturamento_liquido": faturamento_liquido,
                }

            # ========== General Orders Selector (ml_ordens) ==========
            if function_name == "get_orders":
                """
                Seleciona pedidos com filtros opcionais.
                Parâmetros aceitos:
                  - start_date (YYYY-MM-DD) opcional
                  - end_date (YYYY-MM-DD) opcional
                  - status (array|string) opcional
                  - ml_item_id (string) opcional - ID do item no Mercado Livre
                  - product_name (string) opcional - Nome do produto (busca parcial)
                  - seller_sku (string) opcional - SKU do produto
                  - is_catalog (boolean) opcional - Se True, apenas produtos de catálogo; Se False, apenas não-catálogo
                  - buyer_nickname (string) opcional
                  - limit (int) opcional - Se não informado, retorna todos os resultados
                  - offset (int) padrão 0
                """
                from app.models.saas_models import MLOrder, MLProduct
                from sqlalchemy import and_, or_
                from datetime import datetime, timedelta
                q = self.db.query(MLOrder).filter(MLOrder.company_id == company_id)
                # Datas
                start_date = function_args.get("start_date")
                end_date = function_args.get("end_date")
                if start_date:
                    try:
                        dt_start = datetime.fromisoformat(str(start_date)[:10])
                        q = q.filter(MLOrder.date_created >= dt_start)
                    except Exception:
                        pass
                if end_date:
                    try:
                        dt_end = datetime.fromisoformat(str(end_date)[:10]) + timedelta(days=1)
                        q = q.filter(MLOrder.date_created < dt_end)
                    except Exception:
                        pass
                # Status (string único ou lista)
                status = function_args.get("status")
                if status:
                    if isinstance(status, str):
                        status_list = [s.strip() for s in status.split(",") if s.strip()]
                    else:
                        status_list = [str(s).strip() for s in (status or []) if str(s).strip()]
                    if status_list:
                        try:
                            q = q.filter(MLOrder.status.in_(status_list))
                        except Exception:
                            # fallback string compare
                            pass
                # Filtrar por item - suporta ml_item_id, product_name, seller_sku e is_catalog
                ml_item_id = function_args.get("ml_item_id")
                product_name = function_args.get("product_name")
                seller_sku = function_args.get("seller_sku")
                is_catalog = function_args.get("is_catalog")  # True = apenas catálogo, False = apenas não-catálogo, None = todos
                
                # Se forneceu nome, SKU ou filtro de catálogo, buscar produtos primeiro
                ml_item_ids_to_filter = []
                if product_name or seller_sku or is_catalog is not None:
                    product_query = self.db.query(MLProduct).filter(MLProduct.company_id == company_id)
                    
                    if seller_sku:
                        product_query = product_query.filter(MLProduct.seller_sku == seller_sku)
                    elif product_name:
                        # Busca parcial no título
                        like = f"%{product_name}%"
                        product_query = product_query.filter(MLProduct.title.ilike(like))
                    
                    # Filtro de catálogo
                    if is_catalog is True:
                        # Apenas produtos de catálogo
                        product_query = product_query.filter(
                            (MLProduct.catalog_listing == True) | (MLProduct.catalog_product_id.isnot(None))
                        )
                    elif is_catalog is False:
                        # Apenas produtos não-catálogo
                        product_query = product_query.filter(
                            (MLProduct.catalog_listing == False) & (MLProduct.catalog_product_id.is_(None))
                        )
                    
                    try:
                        products = product_query.all()
                        ml_item_ids_to_filter = [p.ml_item_id for p in products if p.ml_item_id]
                        
                        if (product_name or seller_sku) and not ml_item_ids_to_filter:
                            # Produto não encontrado
                            logger.info(f"ℹ️ Produto não encontrado: {'SKU' if seller_sku else 'nome'}='{seller_sku or product_name}', company_id={company_id}")
                            return {
                                "orders": [],
                                "message": f"Produto não encontrado com {'SKU' if seller_sku else 'nome'}: {seller_sku or product_name}"
                            }
                    except Exception as e:
                        logger.error(f"❌ Erro ao buscar produtos para filtro (product_name={product_name}, seller_sku={seller_sku}, is_catalog={is_catalog}): {e}", exc_info=True)
                        return {
                            "orders": [],
                            "error": f"Erro ao buscar produtos: {str(e)}"
                        }
                
                # Se forneceu ml_item_id diretamente, adicionar à lista
                if ml_item_id:
                    ml_item_ids_to_filter.append(ml_item_id)
                
                # Se há filtro por item, garantir que order_items não seja None
                if ml_item_ids_to_filter:
                    q = q.filter(MLOrder.order_items.isnot(None))
                
                # Comprador
                buyer_nickname = function_args.get("buyer_nickname")
                if buyer_nickname and hasattr(MLOrder, "buyer_nickname"):
                    like = f"%{buyer_nickname}%"
                    try:
                        q = q.filter(MLOrder.buyer_nickname.ilike(like))
                    except Exception:
                        pass
                # Ordenação recente
                if hasattr(MLOrder, "date_created"):
                    q = q.order_by(MLOrder.date_created.desc())
                
                # Limite opcional - se houver filtros além do company_id, não aplicar limite
                # Filtros considerados: start_date, end_date, status, ml_item_id, product_name, seller_sku, is_catalog, buyer_nickname
                has_filters = bool(
                    start_date or end_date or status or ml_item_id or 
                    product_name or seller_sku or is_catalog is not None or buyer_nickname
                )
                
                limit = function_args.get("limit")
                offset = int(function_args.get("offset", 0))
                
                # Se houver filtros além do company_id, ignorar limite (retornar todos)
                if has_filters:
                    rows = q.offset(offset).all()
                elif limit is not None:
                    limit = int(limit)
                    rows = q.offset(offset).limit(limit).all()
                else:
                    # Sem filtros e sem limite informado - aplicar limite padrão de segurança
                    rows = q.offset(offset).limit(1000).all()
                
                result = []
                for o in rows:
                    # Se há filtro por item(s), verificar se o pedido contém algum dos itens
                    if ml_item_ids_to_filter:
                        try:
                            items = o.order_items or []
                            has_item = any(
                                (it.get("item", {}).get("id") in [str(mid) for mid in ml_item_ids_to_filter])
                                for it in items
                            )
                            if not has_item:
                                continue
                        except Exception as e:
                            logger.warning(f"⚠️ Erro ao verificar item no pedido {getattr(o, 'ml_order_id', getattr(o, 'id', 'unknown'))}: {e}")
                            continue
                    status_str = (o.status.value if hasattr(o.status, "value") else str(o.status)) if getattr(o, "status", None) is not None else None
                    result.append({
                        "id": str(getattr(o, "ml_order_id", getattr(o, "id", None))),
                        "date": o.date_created.isoformat() if getattr(o, "date_created", None) else None,
                        "total_amount": float(o.total_amount) if getattr(o, "total_amount", None) else 0.0,
                        "status": status_str,
                        "sale_fees": float(o.sale_fees) if getattr(o, "sale_fees", None) else 0.0,
                        "shipping_cost": float(o.shipping_cost) if getattr(o, "shipping_cost", None) else 0.0,
                        "coupon_amount": float(o.coupon_amount) if getattr(o, "coupon_amount", None) else 0.0,
                        "buyer_nickname": getattr(o, "buyer_nickname", None)
                    })
                return {"orders": result, "total": len(result)}

            # ========== Product Sales (by product or ml_item_id) ==========
            if function_name == "get_product_sales":
                """
                Filtra vendas de um produto.
                Parâmetros:
                  - product_id (int) ou ml_item_id (string) [um dos dois é obrigatório]
                  - start_date (YYYY-MM-DD) opcional
                  - end_date (YYYY-MM-DD) opcional
                  - status (array|string) opcional (ex.: paid, delivered)
                  - limit (int) padrão 50
                  - offset (int) padrão 0
                Retorno: lista de pedidos contendo o item, com quantidade total do item naquele pedido.
                """
                from app.models.saas_models import MLOrder, MLProduct
                from datetime import datetime, timedelta
                ml_item_id = function_args.get("ml_item_id")
                product_id = function_args.get("product_id")
                # Resolver ml_item_id via product_id se necessário
                if not ml_item_id and product_id is not None:
                    try:
                        pid = int(product_id)
                        p = self.db.query(MLProduct).filter(MLProduct.id == pid, MLProduct.company_id == company_id).first()
                        if not p:
                            return {"error": "Produto não encontrado"}
                        ml_item_id = p.ml_item_id
                    except Exception:
                        return {"error": "product_id inválido"}
                if not ml_item_id:
                    return {"error": "É obrigatório informar product_id ou ml_item_id"}
                q = self.db.query(MLOrder).filter(MLOrder.company_id == company_id, MLOrder.order_items.isnot(None))
                # Datas
                start_date = function_args.get("start_date")
                end_date = function_args.get("end_date")
                if start_date:
                    try:
                        dt_start = datetime.fromisoformat(str(start_date)[:10])
                        q = q.filter(MLOrder.date_created >= dt_start)
                    except Exception:
                        pass
                if end_date:
                    try:
                        dt_end = datetime.fromisoformat(str(end_date)[:10]) + timedelta(days=1)
                        q = q.filter(MLOrder.date_created < dt_end)
                    except Exception:
                        pass
                # Status (string ou lista)
                status = function_args.get("status")
                if status:
                    if isinstance(status, str):
                        status_list = [s.strip() for s in status.split(",") if s.strip()]
                    else:
                        status_list = [str(s).strip() for s in (status or []) if str(s).strip()]
                    if status_list:
                        try:
                            q = q.filter(MLOrder.status.in_(status_list))
                        except Exception:
                            pass
                # Ordenação e paginação
                if hasattr(MLOrder, "date_created"):
                    q = q.order_by(MLOrder.date_created.desc())
                limit = int(function_args.get("limit", 50))
                offset = int(function_args.get("offset", 0))
                rows = q.offset(offset).limit(limit).all()
                results = []
                for o in rows:
                    try:
                        qty = 0
                        for it in (o.order_items or []):
                            if it.get("item", {}).get("id") == str(ml_item_id):
                                qty += int(it.get("quantity", 1))
                        if qty <= 0:
                            continue
                        status_str = (o.status.value if hasattr(o.status, "value") else str(o.status)) if getattr(o, "status", None) is not None else None
                        results.append({
                            "order_id": str(getattr(o, "ml_order_id", getattr(o, "id", None))),
                            "date": o.date_created.isoformat() if getattr(o, "date_created", None) else None,
                            "status": status_str,
                            "total_amount": float(o.total_amount) if getattr(o, "total_amount", None) else 0.0,
                            "quantity": qty
                        })
                    except Exception:
                        continue
                return {"sales": results}

            # ========== Catalog Competitors ==========
            if function_name == "get_catalog_competitors_db":
                product_id = int(function_args.get("product_id"))
                limit = int(function_args.get("limit", 50))
                offset = int(function_args.get("offset", 0))
                from app.services.ml_catalog_service import MLCatalogService
                svc = MLCatalogService(self.db)
                data = svc.get_product_catalog_competitors(product_id, company_id) or {}
                items = data.get("catalog_products", []) or []
                return {"competitors": items[offset: offset + limit]}

            # ========== Ads Metrics ==========
            if function_name == "get_ads_metrics_by_item":
                ml_item_id = str(function_args.get("ml_item_id"))
                ml_account_id = int(function_args.get("ml_account_id")) if function_args.get("ml_account_id") is not None else None
                days = int(function_args.get("days", 30))
                if not ml_item_id or ml_account_id is None:
                    return {"error": "ml_item_id e ml_account_id são obrigatórios"}
                from app.services.ml_product_ads_service import MLProductAdsService
                ads = MLProductAdsService(self.db)
                return ads.get_product_advertising_metrics(ml_item_id=ml_item_id, ml_account_id=ml_account_id, days=days) or {}

            # ========== Product Cost Config (placeholder) ==========
            if function_name == "get_product_cost_config":
                # TODO: substituir por leitura real de tabela de custos
                return {"custo_produto": 0.0, "impostos_percent": 0.0, "marketing_percent": 0.0}

            # ========== Compute Margin DB ==========
            if function_name == "compute_margin_db":
                sale_price = float(function_args.get("sale_price"))
                product_cost = float(function_args.get("product_cost"))
                taxes_percent = float(function_args.get("taxes_percent", 0))
                other_costs = float(function_args.get("other_costs", 0))
                marketing_percent = float(function_args.get("marketing_percent", 0))
                use_period_averages = bool(function_args.get("use_period_averages", True))
                # placeholder simples; se needed, incluir médias do período
                total_costs = product_cost + other_costs + sale_price * (taxes_percent / 100.0) + sale_price * (marketing_percent / 100.0)
                profit = sale_price - total_costs
                margin_percent = (profit / sale_price * 100.0) if sale_price > 0 else 0.0
                return {"profit": profit, "margin_percent": margin_percent}

            # ========== Fee Preview (placeholder) ==========
            if function_name == "get_fee_preview_db":
                price = float(function_args.get("price"))
                # TODO: estimar fee real a partir de listing/categoria
                return {"estimated_fee": 0.0, "price": price}

            # ========== Simulate Price Candidates (placeholder) ==========
            if function_name == "simulate_price_candidates":
                candidates = function_args.get("candidates", []) or []
                product_cost = float(function_args.get("product_cost", 0))
                taxes_percent = float(function_args.get("taxes_percent", 0))
                other_costs = float(function_args.get("other_costs", 0))
                marketing_percent = float(function_args.get("marketing_percent", 0))
                sims = []
                for price in candidates:
                    try:
                        price = float(price)
                        total_costs = product_cost + other_costs + price * (taxes_percent / 100.0) + price * (marketing_percent / 100.0)
                        profit = price - total_costs
                        margin_percent = (profit / price * 100.0) if price > 0 else 0.0
                        sims.append({"price": price, "profit": profit, "margin_percent": margin_percent})
                    except Exception:
                        continue
                return {"candidates": sims}

            # ========== Required Attributes (placeholder) ==========
            if function_name == "get_required_attributes_db":
                category_id = function_args.get("category_id")
                if not category_id:
                    return {"error": "category_id é obrigatório"}
                # TODO: retornar atributos reais da categoria; placeholder vazio
                return {"required": [], "recommended": []}

            # ========== Check Title/Description ==========
            if function_name == "check_title_description_db":
                product_id = int(function_args.get("product_id"))
                maxlen = int(function_args.get("max_title_length", 60))
                from app.models.saas_models import MLProduct
                p = self.db.query(MLProduct).filter(MLProduct.id == product_id, MLProduct.company_id == company_id).first()
                if not p:
                    return {"error": "Produto não encontrado"}
                title = (p.title or "")
                issues = []
                if len(title) > maxlen:
                    issues.append(f"Título acima de {maxlen} caracteres")
                return {"title": title, "issues": issues}
            
            # ========== Search products by name ==========
            if function_name == "search_products_by_name":
                query = str(function_args.get("query", "")).strip()
                if not query:
                    return {"error": "query é obrigatório"}
                limit = int(function_args.get("limit", 10))
                include_sku = bool(function_args.get("include_sku", True))
                from app.models.saas_models import MLProduct
                q = self.db.query(MLProduct).filter(MLProduct.company_id == company_id)
                # ILIKE para título; opcional para SKU
                from sqlalchemy import or_
                like = f"%{query}%"
                if include_sku:
                    q = q.filter(or_(MLProduct.title.ilike(like), MLProduct.seller_sku.ilike(like)))
                else:
                    q = q.filter(MLProduct.title.ilike(like))
                q = q.order_by(MLProduct.updated_at.desc()) if hasattr(MLProduct, 'updated_at') else q
                rows = q.limit(limit).all()
                results = []
                for p in rows:
                    results.append({
                        "id": p.id,
                        "title": p.title,
                        "seller_sku": p.seller_sku,
                        "ml_item_id": p.ml_item_id,
                        "price": float(p.price) if p.price else None
                    })
                return {"results": results}
            
            # ========== Resolve product by code ==========
            if function_name == "resolve_product_by_code":
                code = str(function_args.get("code", "")).strip()
                code_type = function_args.get("code_type")  # id | seller_sku | ml_item_id | None
                if not code:
                    return {"error": "code é obrigatório"}
                from app.models.saas_models import MLProduct
                product = None
                if code_type == "id":
                    try:
                        pid = int(code)
                        product = self.db.query(MLProduct).filter(MLProduct.id == pid, MLProduct.company_id == company_id).first()
                    except Exception:
                        product = None
                elif code_type == "seller_sku":
                    product = self.db.query(MLProduct).filter(MLProduct.seller_sku == code, MLProduct.company_id == company_id).first()
                elif code_type == "ml_item_id":
                    product = self.db.query(MLProduct).filter(MLProduct.ml_item_id == code, MLProduct.company_id == company_id).first()
                else:
                    # Auto-detecção
                    tried = False
                    if code.isdigit():
                        tried = True
                        try:
                            pid = int(code)
                            product = self.db.query(MLProduct).filter(MLProduct.id == pid, MLProduct.company_id == company_id).first()
                        except Exception:
                            product = None
                    if product is None and code.upper().startswith("ML"):
                        tried = True
                        product = self.db.query(MLProduct).filter(MLProduct.ml_item_id == code, MLProduct.company_id == company_id).first()
                    if product is None and not tried:
                        # tentar SKU como fallback
                        product = self.db.query(MLProduct).filter(MLProduct.seller_sku == code, MLProduct.company_id == company_id).first()
                if not product:
                    return {"found": False}
                return {
                    "found": True,
                    "product": {
                        "id": product.id,
                        "title": product.title,
                        "seller_sku": product.seller_sku,
                        "ml_item_id": product.ml_item_id,
                        "price": float(product.price) if product.price else None
                    }
                }
            
            # ======== Exemplos antigos (mantidos para compatibilidade) ========
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
                    "available_functions": [
                        "get_product_core","get_product_attributes","get_orders","get_product_sales","get_orders_by_item","get_sales_aggregates",
                        "get_billing_breakdown","get_catalog_competitors_db","get_ads_metrics_by_item",
                        "get_product_cost_config","compute_margin_db","get_fee_preview_db",
                        "simulate_price_candidates","get_required_attributes_db","check_title_description_db"
                    ]
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao executar função {function_name}: {e}", exc_info=True)
            return {"error": f"Erro ao executar função: {str(e)}"}

    def _load_agent_tools_from_db(self, assistant_id: int) -> List[Dict]:
        """Lê ferramentas associadas ao agente (tabelas openai_agent_tools/openai_tools) e monta lista para Chat Completions.
        Retorna lista no formato [{"type":"function","function":{name, description, parameters}}].
        """
        try:
            from sqlalchemy import text as sql_text
            query = sql_text(
                """
                SELECT t.name, t.description, t.json_schema
                FROM openai_agent_tools at
                JOIN openai_tools t ON t.id = at.tool_id
                WHERE at.agent_id = :agent_id AND t.is_active = TRUE
                ORDER BY t.name
                """
            )
            rows = self.db.execute(query, {"agent_id": assistant_id}).fetchall()
            tools = []
            for r in rows:
                name = r[0]
                description = r[1]
                schema = r[2]
                if not isinstance(schema, dict):
                    # Caso venha como string JSON
                    try:
                        import json as _json
                        schema = _json.loads(schema)
                    except Exception:
                        continue
                tools.append({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description or "",
                        "parameters": schema
                    }
                })
            return tools
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível carregar ferramentas do DB para o agente {assistant_id}: {e}")
            return []
    
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

