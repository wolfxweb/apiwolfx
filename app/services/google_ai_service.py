"""
Serviço para integração com a API Google AI (Gemini, Imagen, VEO)
Suporta texto, imagem e vídeo
"""
import os
import logging
import requests
from typing import Dict, Optional, Any
from sqlalchemy.orm import Session

from app.services.ai_provider_base import BaseAIProvider

logger = logging.getLogger(__name__)


class GoogleAIService(BaseAIProvider):
    """
    Serviço para interagir com a API Google AI.
    
    Suporta:
    - Texto: Gemini (gemini-2.0-flash-exp, gemini-1.5-pro)
    - Imagem: Imagen 3.0
    - Vídeo: VEO 3
    """
    
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    
    def __init__(self, db: Session, api_key: Optional[str] = None):
        """
        Inicializa o serviço Google AI
        
        Args:
            db: Sessão do banco de dados
            api_key: Chave da API Google (se None, lê de VITE_GOOGLE_API_KEY)
        """
        super().__init__(db, api_key)
        
        # Se não foi passada, tentar ler do .env
        if not self.api_key:
            self.api_key = os.getenv("VITE_GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")
        
        if not self.api_key:
            logger.warning("⚠️ GOOGLE_API_KEY não configurada. Funcionalidades do Google AI estarão desabilitadas.")
    
    def get_provider_name(self) -> str:
        """Retorna o nome do provedor"""
        return "google"
    
    def generate_text(
        self,
        prompt: str,
        model: str = "gemini-2.0-flash-exp",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        instructions: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Gera texto usando Gemini
        
        Args:
            prompt: Prompt/texto de entrada
            model: Modelo Gemini (gemini-2.0-flash-exp, gemini-1.5-pro)
            temperature: Temperatura (0.0-2.0)
            max_tokens: Máximo de tokens na resposta
            instructions: Instruções do sistema (system instruction)
            context_data: Dados de contexto adicionais
        
        Returns:
            Dict com success, content, usage, error
        """
        if not self.validate_api_key():
            return {
                "success": False,
                "error": "Chave de API Google não configurada"
            }
        
        try:
            # Preparar conteúdo
            contents = []
            
            # Adicionar contexto se fornecido
            if context_data:
                context_text = f"\n\nContexto adicional:\n{self._format_context(context_data)}"
                prompt = prompt + context_text
            
            # Adicionar partes da mensagem
            parts = [{"text": prompt}]
            
            contents.append({
                "role": "user",
                "parts": parts
            })
            
            # Preparar payload
            payload = {
                "contents": contents
            }
            
            # Adicionar system instruction se fornecido
            if instructions:
                payload["systemInstruction"] = {
                    "parts": [{"text": instructions}]
                }
            
            # Configurações de geração
            generation_config = {}
            
            if temperature is not None:
                generation_config["temperature"] = max(0.0, min(2.0, temperature))
            
            if max_tokens is not None:
                generation_config["maxOutputTokens"] = max_tokens
            
            if generation_config:
                payload["generationConfig"] = generation_config
            
            # URL do endpoint
            url = f"{self.BASE_URL}/models/{model}:generateContent?key={self.api_key}"
            
            # Fazer requisição
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extrair conteúdo
                content = ""
                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        for part in candidate["content"]["parts"]:
                            if "text" in part:
                                content += part["text"]
                
                # Extrair uso de tokens
                usage = data.get("usageMetadata", {})
                
                return {
                    "success": True,
                    "content": content,
                    "usage": {
                        "prompt_tokens": usage.get("promptTokenCount", 0),
                        "completion_tokens": usage.get("candidatesTokenCount", 0),
                        "total_tokens": usage.get("totalTokenCount", 0)
                    },
                    "model": model
                }
            else:
                error_msg = f"Erro na API Google: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", error_msg)
                except:
                    error_msg = f"{error_msg} - {response.text}"
                
                logger.error(f"❌ Erro na API Google: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
        
        except requests.exceptions.Timeout:
            logger.error("❌ Timeout na requisição à API Google")
            return {
                "success": False,
                "error": "Timeout na requisição à API Google"
            }
        except Exception as e:
            logger.error(f"❌ Erro ao chamar API Google: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Erro ao chamar API Google: {str(e)}"
            }
    
    def generate_image(
        self,
        prompt: str,
        model: Optional[str] = "imagen-3.0-generate-001",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Gera imagem usando Imagen 3.0
        
        Args:
            prompt: Descrição da imagem desejada
            model: Modelo Imagen (imagen-3.0-generate-001)
            **kwargs: Parâmetros adicionais (aspect_ratio, safety_filter_level, etc.)
        
        Returns:
            Dict com success, image_url, image_data, usage, error
        """
        if not self.validate_api_key():
            return {
                "success": False,
                "error": "Chave de API Google não configurada"
            }
        
        try:
            # Preparar payload para Imagen
            payload = {
                "prompt": prompt
            }
            
            # Adicionar parâmetros opcionais
            if "aspect_ratio" in kwargs:
                payload["aspectRatio"] = kwargs["aspect_ratio"]
            
            if "safety_filter_level" in kwargs:
                payload["safetyFilterLevel"] = kwargs["safety_filter_level"]
            
            # URL do endpoint Imagen
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict?key={self.api_key}"
            
            # Fazer requisição
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extrair URL da imagem
                image_url = None
                if "generatedImages" in data and len(data["generatedImages"]) > 0:
                    image_url = data["generatedImages"][0].get("imageUrl")
                
                return {
                    "success": True,
                    "image_url": image_url,
                    "usage": {
                        "total_tokens": 0  # Imagen não usa tokens da mesma forma
                    },
                    "model": model
                }
            else:
                error_msg = f"Erro na API Google Imagen: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", error_msg)
                except:
                    error_msg = f"{error_msg} - {response.text}"
                
                logger.error(f"❌ Erro na API Google Imagen: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
        
        except Exception as e:
            logger.error(f"❌ Erro ao gerar imagem com Google Imagen: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Erro ao gerar imagem: {str(e)}"
            }
    
    def generate_video(
        self,
        prompt: str,
        model: Optional[str] = "veo-3",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Gera vídeo usando VEO 3
        
        Args:
            prompt: Descrição do vídeo desejado
            model: Modelo VEO (veo-3)
            **kwargs: Parâmetros adicionais (duration, resolution, etc.)
        
        Returns:
            Dict com success, video_url, video_data, usage, error
        """
        if not self.validate_api_key():
            return {
                "success": False,
                "error": "Chave de API Google não configurada"
            }
        
        try:
            # Preparar payload para VEO
            payload = {
                "prompt": prompt
            }
            
            # Adicionar parâmetros opcionais
            if "duration" in kwargs:
                payload["duration"] = kwargs["duration"]
            
            if "resolution" in kwargs:
                payload["resolution"] = kwargs["resolution"]
            
            # URL do endpoint VEO
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateVideo?key={self.api_key}"
            
            # Fazer requisição
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=300  # Vídeo pode demorar mais
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extrair URL do vídeo
                video_url = None
                if "generatedVideo" in data:
                    video_url = data["generatedVideo"].get("videoUrl")
                
                return {
                    "success": True,
                    "video_url": video_url,
                    "usage": {
                        "total_tokens": 0  # VEO não usa tokens da mesma forma
                    },
                    "model": model
                }
            else:
                error_msg = f"Erro na API Google VEO: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", error_msg)
                except:
                    error_msg = f"{error_msg} - {response.text}"
                
                logger.error(f"❌ Erro na API Google VEO: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
        
        except Exception as e:
            logger.error(f"❌ Erro ao gerar vídeo com Google VEO: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Erro ao gerar vídeo: {str(e)}"
            }
    
    def search_research(
        self,
        query: str,
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Realiza pesquisa usando Gemini (não é o foco, mas pode ser usado)
        
        Args:
            query: Query de pesquisa
            model: Modelo a ser usado
        
        Returns:
            Dict com success, content, usage, error
        """
        # Gemini não é especializado em pesquisa, mas pode responder perguntas
        return self.generate_text(
            prompt=f"Pesquise e responda: {query}",
            model=model or "gemini-2.0-flash-exp",
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

