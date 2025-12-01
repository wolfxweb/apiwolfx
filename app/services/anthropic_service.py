"""
Serviço para integração com a API Anthropic (Claude)
Focado em criação de texto de alta qualidade
"""
import os
import logging
import requests
from typing import Dict, Optional, Any
from sqlalchemy.orm import Session

from app.services.ai_provider_base import BaseAIProvider

logger = logging.getLogger(__name__)


class AnthropicService(BaseAIProvider):
    """
    Serviço para interagir com a API Anthropic (Claude).
    
    Claude é especializado em criação de texto de alta qualidade,
    análise e raciocínio complexo.
    """
    
    BASE_URL = "https://api.anthropic.com/v1"
    
    def __init__(self, db: Session, api_key: Optional[str] = None):
        """
        Inicializa o serviço Anthropic
        
        Args:
            db: Sessão do banco de dados
            api_key: Chave da API Anthropic (se None, lê de VITE_ANTHROPIC_API_KEY)
        """
        super().__init__(db, api_key)
        
        # Se não foi passada, tentar ler do .env
        if not self.api_key:
            self.api_key = os.getenv("VITE_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            logger.warning("⚠️ ANTHROPIC_API_KEY não configurada. Funcionalidades de Claude estarão desabilitadas.")
    
    def get_provider_name(self) -> str:
        """Retorna o nome do provedor"""
        return "anthropic"
    
    def generate_text(
        self,
        prompt: str,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        instructions: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Gera texto usando Claude
        
        Args:
            prompt: Prompt/texto de entrada
            model: Modelo Claude (claude-3-5-sonnet-20241022, claude-3-opus-20240229, etc.)
            temperature: Temperatura (0.0-1.0)
            max_tokens: Máximo de tokens na resposta
            instructions: Instruções do sistema (system message)
            context_data: Dados de contexto adicionais
        
        Returns:
            Dict com success, content, usage, error
        """
        if not self.validate_api_key():
            return {
                "success": False,
                "error": "Chave de API Anthropic não configurada"
            }
        
        try:
            # Preparar mensagens
            messages = []
            
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
                "messages": messages,
                "max_tokens": max_tokens or 4096  # Default do Anthropic
            }
            
            # Adicionar system message se fornecido
            if instructions:
                payload["system"] = instructions
            
            # Adicionar temperatura se fornecida
            if temperature is not None:
                payload["temperature"] = max(0.0, min(1.0, temperature))
            
            # Headers específicos do Anthropic
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            
            # Fazer requisição
            response = requests.post(
                f"{self.BASE_URL}/messages",
                json=payload,
                headers=headers,
                timeout=120  # Claude pode demorar mais
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extrair conteúdo
                content = ""
                if "content" in data and len(data["content"]) > 0:
                    # Claude retorna lista de content blocks
                    for block in data["content"]:
                        if block.get("type") == "text":
                            content += block.get("text", "")
                
                # Extrair uso de tokens
                usage = data.get("usage", {})
                
                return {
                    "success": True,
                    "content": content,
                    "usage": {
                        "prompt_tokens": usage.get("input_tokens", 0),
                        "completion_tokens": usage.get("output_tokens", 0),
                        "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                    },
                    "model": model
                }
            else:
                error_msg = f"Erro na API Anthropic: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", error_msg)
                except:
                    error_msg = f"{error_msg} - {response.text}"
                
                logger.error(f"❌ Erro na API Anthropic: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
        
        except requests.exceptions.Timeout:
            logger.error("❌ Timeout na requisição à API Anthropic")
            return {
                "success": False,
                "error": "Timeout na requisição à API Anthropic"
            }
        except Exception as e:
            logger.error(f"❌ Erro ao chamar API Anthropic: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Erro ao chamar API Anthropic: {str(e)}"
            }
    
    def search_research(
        self,
        query: str,
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Realiza pesquisa usando Claude (não é o foco, mas pode ser usado)
        
        Args:
            query: Query de pesquisa
            model: Modelo a ser usado
        
        Returns:
            Dict com success, content, usage, error
        """
        # Claude não é especializado em pesquisa, mas pode responder perguntas
        return self.generate_text(
            prompt=f"Pesquise e responda: {query}",
            model=model or "claude-3-5-sonnet-20241022",
            **kwargs
        )
    
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

