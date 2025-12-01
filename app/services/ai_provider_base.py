"""
Classe base abstrata para provedores de IA
Define a interface comum para todos os provedores (OpenAI, Perplexity, Anthropic, Google)
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List
from sqlalchemy.orm import Session


class BaseAIProvider(ABC):
    """
    Classe base abstrata para todos os provedores de IA.
    
    Todos os provedores devem implementar os métodos definidos aqui.
    """
    
    def __init__(self, db: Session, api_key: Optional[str] = None):
        """
        Inicializa o provedor
        
        Args:
            db: Sessão do banco de dados
            api_key: Chave da API (opcional, pode ser lida do .env)
        """
        self.db = db
        self.api_key = api_key
    
    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        instructions: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Gera texto usando o provedor de IA
        
        Args:
            prompt: Prompt/texto de entrada
            model: Modelo a ser usado
            temperature: Temperatura (0.0-2.0)
            max_tokens: Máximo de tokens na resposta
            instructions: Instruções do sistema (opcional)
            context_data: Dados de contexto adicionais
            **kwargs: Parâmetros adicionais específicos do provedor
        
        Returns:
            Dict com:
                - success: bool
                - content: str (texto gerado)
                - usage: dict (tokens usados)
                - error: str (se houver erro)
        """
        pass
    
    @abstractmethod
    def search_research(
        self,
        query: str,
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Realiza pesquisa/busca de informações (especialmente para Perplexity)
        
        Args:
            query: Query de pesquisa
            model: Modelo a ser usado (opcional)
            **kwargs: Parâmetros adicionais
        
        Returns:
            Dict com:
                - success: bool
                - content: str (resultado da pesquisa)
                - sources: List[str] (fontes, se disponível)
                - usage: dict (tokens usados)
                - error: str (se houver erro)
        """
        pass
    
    def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Gera imagem a partir de um prompt (opcional - apenas Google Imagen)
        
        Args:
            prompt: Descrição da imagem desejada
            model: Modelo a ser usado (opcional)
            **kwargs: Parâmetros adicionais (dimensões, estilo, etc.)
        
        Returns:
            Dict com:
                - success: bool
                - image_url: str (URL da imagem gerada)
                - image_data: bytes (dados da imagem, opcional)
                - usage: dict (tokens/créditos usados)
                - error: str (se houver erro)
        """
        return {
            "success": False,
            "error": "Geração de imagem não suportada por este provedor"
        }
    
    def generate_video(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Gera vídeo a partir de um prompt (opcional - apenas Google VEO)
        
        Args:
            prompt: Descrição do vídeo desejado
            model: Modelo a ser usado (opcional, ex: veo-3)
            **kwargs: Parâmetros adicionais (duração, resolução, etc.)
        
        Returns:
            Dict com:
                - success: bool
                - video_url: str (URL do vídeo gerado)
                - video_data: bytes (dados do vídeo, opcional)
                - usage: dict (tokens/créditos usados)
                - error: str (se houver erro)
        """
        return {
            "success": False,
            "error": "Geração de vídeo não suportada por este provedor"
        }
    
    def validate_api_key(self) -> bool:
        """
        Valida se a chave da API está configurada
        
        Returns:
            True se a chave está configurada, False caso contrário
        """
        return self.api_key is not None and len(self.api_key.strip()) > 0
    
    def get_provider_name(self) -> str:
        """
        Retorna o nome do provedor
        
        Returns:
            Nome do provedor (ex: "openai", "perplexity", "anthropic", "google")
        """
        return self.__class__.__name__.replace("Service", "").lower()

