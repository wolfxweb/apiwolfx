"""
Factory para criar instâncias de serviços de IA baseado no provider
"""
import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.services.ai_provider_base import BaseAIProvider
from app.services.perplexity_service import PerplexityService
from app.services.anthropic_service import AnthropicService
from app.services.google_ai_service import GoogleAIService
from app.services.openai_assistant_service import OpenAIAssistantService

logger = logging.getLogger(__name__)


class AIProviderFactory:
    """
    Factory para criar instâncias de serviços de IA.
    
    Detecta o provider e retorna a instância apropriada do serviço.
    """
    
    @staticmethod
    def get_service(provider: str, db: Session, api_key: Optional[str] = None):
        """
        Retorna instância do serviço apropriado baseado no provider
        
        Args:
            provider: Nome do provider ("openai", "perplexity", "anthropic", "google")
            db: Sessão do banco de dados
            api_key: Chave da API (opcional, será lida do .env se não fornecida)
        
        Returns:
            Instância do serviço apropriado (BaseAIProvider para novos providers, OpenAIAssistantService para OpenAI)
        
        Raises:
            ValueError: Se o provider não for suportado
        """
        provider_lower = provider.lower().strip()
        
        if provider_lower == "openai":
            # OpenAI usa o serviço existente (não herda de BaseAIProvider)
            return OpenAIAssistantService(db)
        elif provider_lower == "perplexity":
            return PerplexityService(db, api_key)
        elif provider_lower == "anthropic":
            return AnthropicService(db, api_key)
        elif provider_lower == "google":
            return GoogleAIService(db, api_key)
        else:
            raise ValueError(f"Provider não suportado: {provider}. Use: openai, perplexity, anthropic, google")
    
    @staticmethod
    def get_service_from_agent(agent, db: Session):
        """
        Retorna instância do serviço baseado no agente
        
        Args:
            agent: Instância de OpenAIAssistant
            db: Sessão do banco de dados
        
        Returns:
            Instância do serviço apropriado
        """
        # Obter provider do agente (default: openai)
        provider = getattr(agent, 'provider', 'openai')
        if not provider:
            provider = 'openai'
        
        return AIProviderFactory.get_service(provider, db)

