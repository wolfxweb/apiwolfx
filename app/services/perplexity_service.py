"""
Serviço para integração com a API Perplexity
Focado em pesquisa e busca de informações em tempo real
"""
import os
import logging
import requests
from typing import Dict, Optional, Any
from sqlalchemy.orm import Session

from app.services.ai_provider_base import BaseAIProvider

logger = logging.getLogger(__name__)


class PerplexityService(BaseAIProvider):
    """
    Serviço para interagir com a API Perplexity.
    
    Perplexity é especializado em pesquisa e busca de informações em tempo real,
    acessando a web para fornecer respostas atualizadas.
    """
    
    BASE_URL = "https://api.perplexity.ai"
    
    def __init__(self, db: Session, api_key: Optional[str] = None):
        """
        Inicializa o serviço Perplexity
        
        Args:
            db: Sessão do banco de dados
            api_key: Chave da API Perplexity (se None, lê de VITE_PERPLEXITY_API_KEY)
        """
        super().__init__(db, api_key)
        
        # Se não foi passada, tentar ler do .env
        if not self.api_key:
            self.api_key = os.getenv("VITE_PERPLEXITY_API_KEY") or os.getenv("PERPLEXITY_API_KEY")
        
        if not self.api_key:
            logger.warning("⚠️ PERPLEXITY_API_KEY não configurada. Funcionalidades de pesquisa estarão desabilitadas.")
    
    def get_provider_name(self) -> str:
        """Retorna o nome do provedor"""
        return "perplexity"
    
    def generate_text(
        self,
        prompt: str,
        model: str = "sonar-pro",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        instructions: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Gera texto usando Perplexity (pesquisa + geração)
        
        Args:
            prompt: Prompt/pesquisa
            model: Modelo Perplexity (sonar-pro, sonar, sonar-reasoning)
            temperature: Temperatura (0.0-2.0)
            max_tokens: Máximo de tokens
            instructions: Instruções do sistema (opcional)
            context_data: Dados de contexto adicionais
        
        Returns:
            Dict com success, content, usage, error
        """
        if not self.validate_api_key():
            return {
                "success": False,
                "error": "Chave de API Perplexity não configurada"
            }
        
        try:
            # Preparar mensagens
            messages = []
            
            # Adicionar instruções do sistema se fornecidas
            if instructions:
                messages.append({
                    "role": "system",
                    "content": instructions
                })
            
            # Adicionar contexto se fornecido
            if context_data:
                context_text = f"\n\nContexto adicional:\n{self._format_context(context_data)}"
                prompt = prompt + context_text
            
            # Adicionar mensagem do usuário
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # Preparar payload
            payload = {
                "model": model,
                "messages": messages
            }
            
            # Adicionar parâmetros opcionais
            if temperature is not None:
                payload["temperature"] = max(0.0, min(2.0, temperature))
            
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens
            
            # Headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Fazer requisição
            response = requests.post(
                f"{self.BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extrair conteúdo
                content = ""
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0].get("message", {}).get("content", "")
                
                # Extrair uso de tokens
                usage = data.get("usage", {})
                
                # Extrair citações/fontes se disponível
                citations = []
                if "citations" in data:
                    citations = data["citations"]
                
                return {
                    "success": True,
                    "content": content,
                    "usage": {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0)
                    },
                    "citations": citations,
                    "model": model
                }
            else:
                error_msg = f"Erro na API Perplexity: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", error_msg)
                except:
                    error_msg = f"{error_msg} - {response.text}"
                
                logger.error(f"❌ Erro na API Perplexity: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
        
        except requests.exceptions.Timeout:
            logger.error("❌ Timeout na requisição à API Perplexity")
            return {
                "success": False,
                "error": "Timeout na requisição à API Perplexity"
            }
        except Exception as e:
            logger.error(f"❌ Erro ao chamar API Perplexity: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Erro ao chamar API Perplexity: {str(e)}"
            }
    
    def search_research(
        self,
        query: str,
        model: Optional[str] = "sonar-pro",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Realiza pesquisa usando Perplexity (método principal)
        
        Args:
            query: Query de pesquisa
            model: Modelo a ser usado (sonar-pro, sonar, sonar-reasoning)
        
        Returns:
            Dict com success, content, sources, usage, error
        """
        # Para Perplexity, pesquisa e geração de texto são a mesma coisa
        result = self.generate_text(
            prompt=query,
            model=model or "sonar-pro",
            **kwargs
        )
        
        # Adicionar informações de fontes se disponível
        if result.get("success") and "citations" in result:
            result["sources"] = result.get("citations", [])
        
        return result
    
    def _format_context(self, context_data: Dict[str, Any]) -> str:
        """
        Formata dados de contexto em texto
        
        Args:
            context_data: Dicionário com dados de contexto
        
        Returns:
            String formatada
        """
        import json
        return json.dumps(context_data, indent=2, ensure_ascii=False)

