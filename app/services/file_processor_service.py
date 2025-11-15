"""
Serviço para processar arquivos enviados para uso com agentes OpenAI
"""
import json
import csv
import io
import logging
from typing import Dict, Optional
from fastapi import UploadFile

logger = logging.getLogger(__name__)


class FileProcessorService:
    """Processa arquivos e extrai conteúdo para uso em context_data"""
    
    @staticmethod
    async def process_file(file: UploadFile) -> Dict:
        """
        Processa um arquivo e retorna seu conteúdo estruturado
        
        Args:
            file: Arquivo enviado pelo usuário
            
        Returns:
            Dict com 'success', 'content', 'type', 'error'
        """
        try:
            # Ler conteúdo do arquivo
            content = await file.read()
            filename = file.filename.lower()
            
            # Detectar tipo de arquivo
            if filename.endswith('.json'):
                return FileProcessorService._process_json(content)
            elif filename.endswith('.csv'):
                return FileProcessorService._process_csv(content)
            elif filename.endswith('.txt'):
                return FileProcessorService._process_txt(content)
            elif filename.endswith('.pdf'):
                return await FileProcessorService._process_pdf(content)
            else:
                return {
                    "success": False,
                    "error": f"Tipo de arquivo não suportado: {filename}. Tipos suportados: JSON, CSV, TXT, PDF"
                }
        
        except Exception as e:
            logger.error(f"❌ Erro ao processar arquivo {file.filename}: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Erro ao processar arquivo: {str(e)}"
            }
    
    @staticmethod
    def _process_json(content: bytes) -> Dict:
        """Processa arquivo JSON"""
        try:
            text = content.decode('utf-8')
            data = json.loads(text)
            return {
                "success": True,
                "content": data,
                "type": "json",
                "text": json.dumps(data, ensure_ascii=False, indent=2)
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON inválido: {str(e)}"
            }
        except UnicodeDecodeError as e:
            return {
                "success": False,
                "error": f"Erro de codificação: {str(e)}"
            }
    
    @staticmethod
    def _process_csv(content: bytes) -> Dict:
        """Processa arquivo CSV"""
        try:
            text = content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(text))
            rows = list(csv_reader)
            
            # Converter para formato mais legível
            result = {
                "headers": csv_reader.fieldnames or [],
                "rows": rows,
                "total_rows": len(rows)
            }
            
            return {
                "success": True,
                "content": result,
                "type": "csv",
                "text": json.dumps(result, ensure_ascii=False, indent=2)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Erro ao processar CSV: {str(e)}"
            }
    
    @staticmethod
    def _process_txt(content: bytes) -> Dict:
        """Processa arquivo TXT"""
        try:
            text = content.decode('utf-8')
            return {
                "success": True,
                "content": text,
                "type": "txt",
                "text": text
            }
        except UnicodeDecodeError:
            # Tentar outras codificações comuns
            for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    text = content.decode(encoding)
                    return {
                        "success": True,
                        "content": text,
                        "type": "txt",
                        "text": text
                    }
                except:
                    continue
            
            return {
                "success": False,
                "error": "Não foi possível decodificar o arquivo de texto"
            }
    
    @staticmethod
    async def _process_pdf(content: bytes) -> Dict:
        """Processa arquivo PDF"""
        try:
            # Tentar importar PyPDF2
            try:
                import PyPDF2
            except ImportError:
                # Tentar pdfplumber como alternativa
                try:
                    import pdfplumber
                    return FileProcessorService._process_pdf_with_pdfplumber(content)
                except ImportError:
                    return {
                        "success": False,
                        "error": "Biblioteca para processar PDF não instalada. Instale PyPDF2 ou pdfplumber."
                    }
            
            # Processar com PyPDF2
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_parts = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(f"--- Página {page_num + 1} ---\n{text}\n")
                except Exception as e:
                    logger.warning(f"Erro ao extrair texto da página {page_num + 1}: {e}")
                    continue
            
            full_text = "\n".join(text_parts)
            
            return {
                "success": True,
                "content": full_text,
                "type": "pdf",
                "text": full_text,
                "pages": len(pdf_reader.pages)
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Erro ao processar PDF: {str(e)}"
            }
    
    @staticmethod
    def _process_pdf_with_pdfplumber(content: bytes) -> Dict:
        """Processa PDF usando pdfplumber (alternativa)"""
        import pdfplumber
        
        pdf_file = io.BytesIO(content)
        text_parts = []
        
        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text()
                    if text:
                        text_parts.append(f"--- Página {page_num + 1} ---\n{text}\n")
                except Exception as e:
                    logger.warning(f"Erro ao extrair texto da página {page_num + 1}: {e}")
                    continue
        
        full_text = "\n".join(text_parts)
        
        return {
            "success": True,
            "content": full_text,
            "type": "pdf",
            "text": full_text,
            "pages": len(pdf.pages)
        }
    
    @staticmethod
    def format_for_context(files_data: list) -> Dict:
        """
        Formata dados de múltiplos arquivos para incluir no context_data
        
        Args:
            files_data: Lista de resultados de processamento de arquivos
            
        Returns:
            Dict formatado para context_data
        """
        if not files_data:
            return {}
        
        result = {
            "uploaded_files": []
        }
        
        for file_data in files_data:
            if file_data.get("success"):
                result["uploaded_files"].append({
                    "type": file_data.get("type"),
                    "content": file_data.get("content"),
                    "text": file_data.get("text"),
                    "pages": file_data.get("pages")
                })
        
        return result

