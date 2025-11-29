"""
Controller para gerenciar suporte
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.support_service import SupportService

logger = logging.getLogger(__name__)


class SupportController:
    """Controller para gerenciar suporte"""
    
    def __init__(self, db: Session):
        self.db = db
        self.support_service = SupportService(db)
    
    def get_support_page(self, user: Dict) -> Dict[str, Any]:
        """Prepara dados para a página de suporte"""
        try:
            company_id = user.get("company", {}).get("id")
            user_id = user.get("id")
            
            # Listar manuais
            manuals = self.support_service.list_manuals()
            
            # Listar chamados do usuário
            tickets_result = self.support_service.list_tickets(
                company_id=company_id,
                user_id=user_id
            )
            tickets = tickets_result.get("tickets", []) if tickets_result.get("success") else []
            
            return {
                "success": True,
                "manuals": manuals,
                "tickets": tickets
            }
        except Exception as e:
            logger.error(f"Erro ao preparar página de suporte: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_manuals(self) -> Dict[str, Any]:
        """Lista todos os manuais"""
        try:
            manuals = self.support_service.list_manuals()
            return {
                "success": True,
                "manuals": manuals
            }
        except Exception as e:
            logger.error(f"Erro ao listar manuais: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_manual(self, filename: str) -> Dict[str, Any]:
        """Obtém conteúdo de um manual"""
        try:
            manual = self.support_service.get_manual_content(filename)
            if not manual:
                return {
                    "success": False,
                    "error": "Manual não encontrado"
                }
            
            return {
                "success": True,
                "manual": manual
            }
        except Exception as e:
            logger.error(f"Erro ao obter manual: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def search_manuals(self, query: str) -> Dict[str, Any]:
        """Busca nos manuais"""
        try:
            if not query or len(query.strip()) < 2:
                return {
                    "success": True,
                    "results": []
                }
            
            results = self.support_service.search_manuals(query.strip())
            return {
                "success": True,
                "results": results,
                "query": query
            }
        except Exception as e:
            logger.error(f"Erro ao buscar manuais: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_ticket(
        self,
        company_id: int,
        user_id: Optional[int],
        subject: str,
        description: str,
        category: Optional[str] = None,
        priority: str = "medium"
    ) -> Dict[str, Any]:
        """Cria um novo chamado"""
        return self.support_service.create_ticket(
            company_id=company_id,
            user_id=user_id,
            subject=subject,
            description=description,
            category=category,
            priority=priority
        )
    
    def list_tickets(
        self,
        company_id: int,
        user_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lista chamados"""
        return self.support_service.list_tickets(
            company_id=company_id,
            user_id=user_id,
            status=status
        )
    
    def get_ticket(self, ticket_id: int, company_id: int) -> Dict[str, Any]:
        """Obtém um chamado específico"""
        return self.support_service.get_ticket(ticket_id, company_id)
    
    def upload_attachment(
        self,
        ticket_id: int,
        company_id: int,
        user_id: Optional[int],
        filename: str,
        file_content: bytes,
        content_type: str,
        message_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Faz upload de um anexo"""
        return self.support_service.upload_attachment(
            ticket_id=ticket_id,
            company_id=company_id,
            user_id=user_id,
            filename=filename,
            file_content=file_content,
            content_type=content_type,
            message_id=message_id
        )
    
    def get_ticket_attachments(
        self,
        ticket_id: int,
        company_id: int
    ) -> Dict[str, Any]:
        """Lista anexos de um chamado"""
        return self.support_service.get_ticket_attachments(ticket_id, company_id)

