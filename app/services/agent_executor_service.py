"""
Serviço centralizado para execução de agentes IA
Permite executar qualquer agente cadastrado no banco de dados em qualquer ponto do sistema
Suporta múltiplos providers: OpenAI, Perplexity, Anthropic, Google
"""
import logging
from typing import Dict, Optional, Any, Tuple
from sqlalchemy.orm import Session

from app.controllers.openai_assistant_controller import OpenAIAssistantController
from app.models.saas_models import OpenAIAssistant, InteractionMode
from app.services.ai_provider_factory import AIProviderFactory

logger = logging.getLogger(__name__)


class AgentExecutorService:
    """
    Serviço centralizado para execução de agentes IA.
    
    Detecta automaticamente se o agente é do tipo CHAT ou REPORT baseado no campo
    interaction_mode do banco de dados e executa o método apropriado.
    
    Uso básico:
        executor = AgentExecutorService(db)
        result = executor.execute(
            agent_id=2,
            user=user,
            message="Pesquise sobre marketing digital"
        )
    """
    
    def __init__(self, db: Session):
        """
        Inicializa o executor de agentes
        
        Args:
            db: Sessão do banco de dados
        """
        self.db = db
        self.controller = OpenAIAssistantController(db)
        self._agent_cache = {}  # Cache de agentes por ID
    
    def _get_agent(self, agent_id: int) -> Optional[OpenAIAssistant]:
        """
        Busca agente no banco e valida se está ativo
        
        Args:
            agent_id: ID do agente
        
        Returns:
            Objeto OpenAIAssistant ou None se não encontrado/inativo
        """
        # Verificar cache primeiro
        if agent_id in self._agent_cache:
            cached_agent = self._agent_cache[agent_id]
            # Verificar se ainda está ativo (cache pode estar desatualizado)
            if cached_agent.is_active:
                return cached_agent
            else:
                # Remover do cache se inativo
                del self._agent_cache[agent_id]
        
        # Buscar no banco
        agent = self.db.query(OpenAIAssistant).filter(
            OpenAIAssistant.id == agent_id,
            OpenAIAssistant.is_active == True
        ).first()
        
        if agent:
            # Adicionar ao cache
            self._agent_cache[agent_id] = agent
            return agent
        else:
            logger.warning(f"⚠️ Agente ID {agent_id} não encontrado ou inativo")
            return None
    
    def _extract_company_and_user_id(self, user: dict) -> Tuple[Optional[int], Optional[int]]:
        """
        Extrai company_id e user_id do objeto user
        
        Args:
            user: Objeto user do contexto (retornado por get_current_user)
        
        Returns:
            Tuple (company_id, user_id)
        """
        user_id = None
        company_id = None
        
        if isinstance(user, dict):
            # Extrair user_id
            user_id = user.get("id")
            
            # Extrair company_id (tentar diferentes formatos)
            if "company_id" in user:
                company_id = user.get("company_id")
            elif "company" in user:
                company = user.get("company")
                if isinstance(company, dict):
                    company_id = company.get("id")
                elif hasattr(company, "id"):
                    company_id = company.id
        
        return company_id, user_id
    
    def execute(
        self,
        agent_id: int,
        user: dict,
        message: str,
        thread_id: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
        use_case: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executa um agente detectando automaticamente se é CHAT ou REPORT
        
        Args:
            agent_id: ID do agente no banco de dados
            user: Objeto user do contexto (retornado por get_current_user)
            message: Mensagem/prompt para o agente
            thread_id: ID da thread (apenas para modo chat, opcional)
            context_data: Dados adicionais de contexto (opcional)
            use_case: Caso de uso (opcional)
        
        Returns:
            Dict com:
                - success: bool
                - content: str (resposta do agente, se success=True)
                - thread_id: str (ID da thread, apenas para chat)
                - error: str (mensagem de erro, se success=False)
                - usage: dict (informações de uso de tokens)
                - requires_login: bool (se erro de autenticação)
                - tokens_balance: dict (saldo de tokens, se erro de saldo)
        """
        try:
            # Validar message/prompt
            if not message or not message.strip():
                return {
                    'success': False,
                    'error': 'Mensagem não pode estar vazia'
                }
            
            # Buscar e validar agente
            agent = self._get_agent(agent_id)
            if not agent:
                return {
                    'success': False,
                    'error': f'Agente ID {agent_id} não encontrado ou inativo'
                }
            
            # Extrair company_id e user_id
            company_id, user_id = self._extract_company_and_user_id(user)
            
            if not company_id:
                return {
                    'success': False,
                    'error': 'Company ID não encontrado no contexto do usuário'
                }
            
            if not user_id:
                return {
                    'success': False,
                    'error': 'User ID não encontrado no contexto do usuário'
                }
            
            # Preparar contexto
            if context_data is None:
                context_data = {}
            
            # Detectar modo e executar
            interaction_mode = agent.interaction_mode
            
            # Se for enum, pegar o valor
            if hasattr(interaction_mode, 'value'):
                mode_value = interaction_mode.value
            else:
                mode_value = str(interaction_mode)
            
            logger.info(f"🤖 Executando agente ID {agent_id} ({agent.name}) em modo {mode_value}")
            
            if mode_value == "chat":
                return self._execute_chat(
                    agent_id=agent_id,
                    company_id=company_id,
                    user_id=user_id,
                    message=message,
                    thread_id=thread_id,
                    context_data=context_data,
                    use_case=use_case
                )
            elif mode_value == "report":
                return self._execute_report(
                    agent_id=agent_id,
                    company_id=company_id,
                    user_id=user_id,
                    prompt=message,
                    context_data=context_data,
                    use_case=use_case
                )
            else:
                return {
                    'success': False,
                    'error': f'Modo de interação inválido: {mode_value}'
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao executar agente: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Erro ao executar agente: {str(e)}'
            }
    
    def _get_provider_service(self, agent: OpenAIAssistant):
        """
        Obtém o serviço apropriado baseado no provider do agente
        
        Args:
            agent: Instância de OpenAIAssistant
        
        Returns:
            Instância do serviço apropriado
        """
        return AIProviderFactory.get_service_from_agent(agent, self.db)
    
    def _execute_chat(
        self,
        agent_id: int,
        company_id: int,
        user_id: int,
        message: str,
        thread_id: Optional[str],
        context_data: Dict[str, Any],
        use_case: Optional[str]
    ) -> Dict[str, Any]:
        """Executa agente em modo chat"""
        try:
            # Buscar agente novamente para ter acesso ao provider
            agent = self._get_agent(agent_id)
            if not agent:
                return {
                    'success': False,
                    'error': f'Agente ID {agent_id} não encontrado ou inativo'
                }
            
            # Verificar provider
            provider = getattr(agent, 'provider', 'openai') or 'openai'
            
            # Se for OpenAI, usar o controller existente
            if provider == 'openai':
                result = self.controller.use_assistant_chat(
                    assistant_id=agent_id,
                    company_id=company_id,
                    user_id=user_id,
                    message=message,
                    thread_id=thread_id,
                    context_data=context_data,
                    use_case=use_case
                )
            else:
                # Para outros providers, usar o serviço diretamente
                provider_service = self._get_provider_service(agent)
                
                # Preparar prompt com initial_prompt se disponível
                final_prompt = message
                if agent.initial_prompt:
                    initial_prompt_clean = agent.initial_prompt
                    # Substituir tags dinâmicas
                    if '[[USUARIO]]' in initial_prompt_clean:
                        # Tentar obter nome do usuário do contexto
                        user_name = context_data.get('user_name', 'Usuário') if context_data else 'Usuário'
                        initial_prompt_clean = initial_prompt_clean.replace('[[USUARIO]]', user_name)
                    final_prompt = f"{initial_prompt_clean}\n\n{message}"
                
                # Chamar o serviço do provider
                result = provider_service.generate_text(
                    prompt=final_prompt,
                    model=agent.model,
                    temperature=float(agent.temperature) if agent.temperature else None,
                    max_tokens=agent.max_tokens,
                    instructions=agent.instructions,
                    context_data=context_data
                )
                
                # Registrar uso (para novos providers)
                from app.models.saas_models import OpenAIAssistantUsage, UsageStatus
                from datetime import datetime
                
                usage_record = OpenAIAssistantUsage(
                    assistant_id=agent_id,
                    company_id=company_id,
                    user_id=user_id,
                    thread_id=thread_id,
                    interaction_mode="chat",
                    use_case=use_case,
                    provider=provider,
                    status=UsageStatus.COMPLETED if result.get('success') else UsageStatus.FAILED,
                    prompt_tokens=result.get('usage', {}).get('prompt_tokens', 0),
                    completion_tokens=result.get('usage', {}).get('completion_tokens', 0),
                    total_tokens=result.get('usage', {}).get('total_tokens', 0),
                    error_message=result.get('error') if not result.get('success') else None,
                    created_at=datetime.utcnow(),
                    completed_at=datetime.utcnow()
                )
                self.db.add(usage_record)
                self.db.commit()
                
                # Formatar resultado no formato esperado
                if result.get('success'):
                    result = {
                        'success': True,
                        'response': result.get('content', ''),
                        'usage': result.get('usage', {}),
                        'thread_id': thread_id  # Manter thread_id se fornecido
                    }
                else:
                    result = {
                        'success': False,
                        'error': result.get('error', 'Erro desconhecido')
                    }
            
            if result.get('success'):
                # O 'response' pode ser uma string diretamente ou um dict
                response_data = result.get('response', '')
                
                # Log completo da resposta do controller
                logger.info(f"📥 Resposta completa do controller:")
                logger.info(f"   Tipo: {type(response_data)}")
                logger.info(f"   Conteúdo completo: {response_data}")
                print(f"\n{'='*80}")
                print(f"📥 RESPOSTA COMPLETA DO CONTROLLER")
                print(f"{'='*80}")
                print(f"Tipo: {type(response_data)}")
                print(f"Conteúdo completo:")
                print(response_data)
                print(f"{'='*80}\n")
                
                # Se for string, usar diretamente; se for dict, extrair 'content'
                if isinstance(response_data, str):
                    content = response_data
                elif isinstance(response_data, dict):
                    content = response_data.get('content', '')
                else:
                    content = str(response_data) if response_data else ''
                
                logger.info(f"📝 Conteúdo extraído (tamanho: {len(content)}):")
                logger.info(f"   {content}")
                print(f"\n{'='*80}")
                print(f"📝 CONTEÚDO EXTRAÍDO DO MODELO")
                print(f"{'='*80}")
                print(f"Tamanho: {len(content)} caracteres")
                print(f"Conteúdo completo:")
                print(content)
                print(f"{'='*80}\n")
                
                if not content:
                    logger.warning("⚠️ Conteúdo vazio retornado pelo agente!")
                    print("⚠️ ATENÇÃO: Conteúdo vazio retornado pelo agente!")
                
                return {
                    'success': True,
                    'content': content,
                    'thread_id': result.get('thread_id'),
                    'raw_response': response_data,
                    'usage': result.get('usage', {})
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Erro desconhecido ao executar agente'),
                    'requires_login': result.get('requires_login', False),
                    'tokens_balance': result.get('tokens_balance')
                }
        except Exception as e:
            logger.error(f"❌ Erro ao executar agente em modo chat: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Erro ao executar agente: {str(e)}'
            }
    
    def _execute_report(
        self,
        agent_id: int,
        company_id: int,
        user_id: int,
        prompt: str,
        context_data: Dict[str, Any],
        use_case: Optional[str]
    ) -> Dict[str, Any]:
        """Executa agente em modo report"""
        try:
            # Buscar agente novamente para ter acesso ao provider
            agent = self._get_agent(agent_id)
            if not agent:
                return {
                    'success': False,
                    'error': f'Agente ID {agent_id} não encontrado ou inativo'
                }
            
            # Verificar provider
            provider = getattr(agent, 'provider', 'openai') or 'openai'
            
            # Se for OpenAI, usar o controller existente
            if provider == 'openai':
                result = self.controller.use_assistant_report(
                    assistant_id=agent_id,
                    company_id=company_id,
                    user_id=user_id,
                    prompt=prompt,
                    context_data=context_data,
                    use_case=use_case
                )
            else:
                # Para outros providers, usar o serviço diretamente
                provider_service = self._get_provider_service(agent)
                
                # Preparar prompt com initial_prompt se disponível
                final_prompt = prompt
                if agent.initial_prompt:
                    initial_prompt_clean = agent.initial_prompt
                    # Substituir tags dinâmicas
                    if '[[USUARIO]]' in initial_prompt_clean:
                        # Tentar obter nome do usuário do contexto
                        user_name = context_data.get('user_name', 'Usuário') if context_data else 'Usuário'
                        initial_prompt_clean = initial_prompt_clean.replace('[[USUARIO]]', user_name)
                    final_prompt = f"{initial_prompt_clean}\n\n{prompt}"
                
                # Verificar se é pesquisa (Perplexity) ou geração de texto
                if provider == 'perplexity':
                    # Perplexity é especializado em pesquisa
                    result = provider_service.search_research(
                        query=final_prompt,
                        model=agent.model
                    )
                else:
                    # Outros providers usam generate_text
                    result = provider_service.generate_text(
                        prompt=final_prompt,
                        model=agent.model,
                        temperature=float(agent.temperature) if agent.temperature else None,
                        max_tokens=agent.max_tokens,
                        instructions=agent.instructions,
                        context_data=context_data
                    )
                
                # Registrar uso (para novos providers)
                from app.models.saas_models import OpenAIAssistantUsage, UsageStatus
                from datetime import datetime
                
                usage_record = OpenAIAssistantUsage(
                    assistant_id=agent_id,
                    company_id=company_id,
                    user_id=user_id,
                    thread_id=None,
                    interaction_mode="report",
                    use_case=use_case,
                    provider=provider,
                    status=UsageStatus.COMPLETED if result.get('success') else UsageStatus.FAILED,
                    prompt_tokens=result.get('usage', {}).get('prompt_tokens', 0),
                    completion_tokens=result.get('usage', {}).get('completion_tokens', 0),
                    total_tokens=result.get('usage', {}).get('total_tokens', 0),
                    error_message=result.get('error') if not result.get('success') else None,
                    created_at=datetime.utcnow(),
                    completed_at=datetime.utcnow()
                )
                self.db.add(usage_record)
                self.db.commit()
                
                # Formatar resultado no formato esperado
                if result.get('success'):
                    result = {
                        'success': True,
                        'response': result.get('content', ''),
                        'usage': result.get('usage', {})
                    }
                else:
                    result = {
                        'success': False,
                        'error': result.get('error', 'Erro desconhecido')
                    }
            
            if result.get('success'):
                response_data = result.get('response', '')
                
                # Em modo report, response pode ser string ou dict
                if isinstance(response_data, str):
                    content = response_data
                    raw_response = {'content': response_data}
                elif isinstance(response_data, dict):
                    content = response_data.get('content', '') or str(response_data)
                    raw_response = response_data
                else:
                    content = str(response_data) if response_data else ''
                    raw_response = {'content': content}
                
                # Registrar uso se disponível
                usage = result.get('usage', {})
                
                return {
                    'success': True,
                    'content': content,
                    'raw_response': raw_response,
                    'usage': usage
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Erro desconhecido ao executar agente')
                }
        except Exception as e:
            logger.error(f"❌ Erro ao executar agente em modo report: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Erro ao executar agente: {str(e)}'
            }
    
    def clear_cache(self):
        """Limpa o cache de agentes"""
        self._agent_cache.clear()

