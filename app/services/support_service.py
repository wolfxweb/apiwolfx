"""
Serviço para gerenciar chamados de suporte e documentação
"""
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from app.models.saas_models import SupportTicket, SupportTicketStatus, SupportTicketMessage, SupportTicketAttachment, User
from app.config.settings import settings

logger = logging.getLogger(__name__)


class SupportService:
    """Serviço para gerenciar suporte"""
    
    def __init__(self, db: Session):
        self.db = db
        self.manuals_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Manuais")
    
    def list_manuals(self) -> List[Dict[str, Any]]:
        """Lista todos os manuais disponíveis"""
        try:
            manuals = []
            
            if not os.path.exists(self.manuals_path):
                logger.warning(f"⚠️ Diretório de manuais não encontrado: {self.manuals_path}")
                return manuals
            
            # Listar arquivos .md no diretório Manuais
            for filename in os.listdir(self.manuals_path):
                if filename.endswith('.md') and not filename.startswith('.'):
                    # Excluir o índice geral do sistema CELX
                    if filename == '00_INDICE_GERAL.md':
                        continue
                    
                    filepath = os.path.join(self.manuals_path, filename)
                    if os.path.isfile(filepath):
                        # Ler título do arquivo (primeira linha após #)
                        title = filename.replace('.md', '').replace('_', ' ').title()
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                first_line = f.readline().strip()
                                if first_line.startswith('#'):
                                    title = first_line.replace('#', '').strip()
                        except Exception as e:
                            logger.warning(f"Erro ao ler título do manual {filename}: {e}")
                        
                        manuals.append({
                            "filename": filename,
                            "title": title,
                            "path": filepath
                        })
            
            # Ordenar por nome do arquivo
            manuals.sort(key=lambda x: x['filename'])
            
            return manuals
        except Exception as e:
            logger.error(f"Erro ao listar manuais: {e}", exc_info=True)
            return []
    
    def get_manual_content(self, filename: str) -> Optional[Dict[str, Any]]:
        """Obtém o conteúdo de um manual específico"""
        try:
            filepath = os.path.join(self.manuals_path, filename)
            
            if not os.path.exists(filepath) or not filename.endswith('.md'):
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extrair título
            title = filename.replace('.md', '').replace('_', ' ').title()
            lines = content.split('\n')
            for line in lines[:5]:
                if line.strip().startswith('#'):
                    title = line.replace('#', '').strip()
                    break
            
            return {
                "filename": filename,
                "title": title,
                "content": content
            }
        except Exception as e:
            logger.error(f"Erro ao ler manual {filename}: {e}", exc_info=True)
            return None
    
    def search_manuals(self, query: str) -> List[Dict[str, Any]]:
        """Busca nos manuais por termo"""
        try:
            results = []
            query_lower = query.lower()
            
            if not os.path.exists(self.manuals_path):
                return results
            
            for filename in os.listdir(self.manuals_path):
                if filename.endswith('.md') and not filename.startswith('.'):
                    filepath = os.path.join(self.manuals_path, filename)
                    if os.path.isfile(filepath):
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                content = f.read()
                                content_lower = content.lower()
                                
                                # Verificar se o termo está no conteúdo
                                if query_lower in content_lower:
                                    # Extrair título
                                    title = filename.replace('.md', '').replace('_', ' ').title()
                                    lines = content.split('\n')
                                    for line in lines[:5]:
                                        if line.strip().startswith('#'):
                                            title = line.replace('#', '').strip()
                                            break
                                    
                                    # Encontrar contexto (linha onde aparece)
                                    lines_list = content.split('\n')
                                    matches = []
                                    for i, line in enumerate(lines_list):
                                        if query_lower in line.lower():
                                            # Pegar contexto (linha anterior e posterior)
                                            context_start = max(0, i - 1)
                                            context_end = min(len(lines_list), i + 2)
                                            context = '\n'.join(lines_list[context_start:context_end])
                                            matches.append({
                                                "line": i + 1,
                                                "context": context
                                            })
                                            if len(matches) >= 3:  # Limitar a 3 matches por arquivo
                                                break
                                    
                                    results.append({
                                        "filename": filename,
                                        "title": title,
                                        "matches": matches,
                                        "match_count": len(matches)
                                    })
                        except Exception as e:
                            logger.warning(f"Erro ao buscar no manual {filename}: {e}")
            
            # Ordenar por número de matches (mais relevantes primeiro)
            results.sort(key=lambda x: x['match_count'], reverse=True)
            
            return results
        except Exception as e:
            logger.error(f"Erro ao buscar manuais: {e}", exc_info=True)
            return []
    
    def create_ticket(
        self,
        company_id: int,
        user_id: Optional[int],
        subject: str,
        description: str,
        category: Optional[str] = None,
        priority: str = "medium"
    ) -> Dict[str, Any]:
        """Cria um novo chamado de suporte com a primeira mensagem"""
        try:
            # Criar o ticket
            ticket = SupportTicket(
                company_id=company_id,
                user_id=user_id,
                subject=subject,
                description=description,
                category=category,
                priority=priority,
                status="open"  # Usar string diretamente
            )
            
            self.db.add(ticket)
            self.db.flush()  # Para obter o ID do ticket
            
            # Criar a primeira mensagem (do usuário)
            first_message = SupportTicketMessage(
                ticket_id=ticket.id,
                user_id=user_id,
                message=description,
                is_from_support=False
            )
            
            self.db.add(first_message)
            self.db.commit()
            self.db.refresh(ticket)
            
            logger.info(f"✅ Chamado de suporte criado: ID={ticket.id}, Company={company_id}, User={user_id}, Subject={subject[:50]}")
            
            return {
                "success": True,
                "ticket": {
                    "id": ticket.id,
                    "subject": ticket.subject,
                    "status": ticket.status.value if hasattr(ticket.status, 'value') else ticket.status,
                    "created_at": ticket.created_at.isoformat() if ticket.created_at else None
                }
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar chamado de suporte: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def add_message_to_ticket(
        self,
        ticket_id: int,
        company_id: Optional[int],
        user_id: Optional[int],
        message_content: str,
        is_from_support: bool = False
    ) -> Dict[str, Any]:
        """Adiciona uma nova mensagem a um chamado de suporte existente (company_id opcional para superadmin)"""
        try:
            if company_id:
                ticket = self.db.query(SupportTicket).filter(
                    and_(
                        SupportTicket.id == ticket_id,
                        SupportTicket.company_id == company_id
                    )
                ).first()
            else:
                # Para superadmin, não filtrar por company_id
                ticket = self.db.query(SupportTicket).filter(
                    SupportTicket.id == ticket_id
                ).first()
            
            if not ticket:
                return {
                    "success": False,
                    "error": "Chamado não encontrado"
                }
            
            # Criar mensagem
            message = SupportTicketMessage(
                ticket_id=ticket_id,
                user_id=user_id,
                message=message_content,
                is_from_support=is_from_support
            )
            
            self.db.add(message)
            
            # Atualizar status do ticket se necessário
            current_status = ticket.status.value if hasattr(ticket.status, 'value') else ticket.status
            if is_from_support and current_status == "open":
                ticket.status = "in_progress"
            elif not is_from_support and current_status == "in_progress":
                ticket.status = "waiting_user"
            
            self.db.commit()
            self.db.refresh(message)
            
            logger.info(f"✅ Mensagem adicionada ao chamado {ticket_id} por User={user_id}, Suporte={is_from_support}")
            
            return {
                "success": True,
                "message": {
                    "id": message.id,
                    "message": message.message,
                    "is_from_support": message.is_from_support,
                    "created_at": message.created_at.isoformat() if message.created_at else None
                }
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao adicionar mensagem ao chamado {ticket_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def upload_attachment(
        self,
        ticket_id: int,
        company_id: Optional[int],
        user_id: Optional[int],
        filename: str,
        file_content: bytes,
        content_type: str,
        message_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Faz upload de um anexo para um chamado (company_id opcional para superadmin)"""
        try:
            from uuid import uuid4
            
            # Verificar se o ticket existe (e pertence à empresa se company_id fornecido)
            if company_id:
                ticket = self.db.query(SupportTicket).filter(
                    and_(
                        SupportTicket.id == ticket_id,
                        SupportTicket.company_id == company_id
                    )
                ).first()
            else:
                # Para superadmin, não filtrar por company_id
                ticket = self.db.query(SupportTicket).filter(
                    SupportTicket.id == ticket_id
                ).first()
            
            if not ticket:
                return {
                    "success": False,
                    "error": "Chamado não encontrado"
                }
            
            # Criar diretório de uploads se não existir
            upload_dir = Path("public/uploads/support_attachments")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Gerar nome único para o arquivo
            file_ext = Path(filename).suffix
            unique_filename = f"{uuid4().hex}{file_ext}"
            file_path = upload_dir / unique_filename
            
            # Salvar arquivo
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            # Criar registro no banco
            attachment = SupportTicketAttachment(
                ticket_id=ticket_id,
                message_id=message_id,
                filename=filename,
                file_path=str(file_path),
                file_size=len(file_content),
                content_type=content_type,
                uploaded_by=user_id
            )
            
            self.db.add(attachment)
            self.db.commit()
            self.db.refresh(attachment)
            
            # URL pública do arquivo
            base_url = getattr(settings, "base_url", "") if hasattr(settings, "base_url") else ""
            if base_url:
                file_url = f"{base_url}/static/uploads/support_attachments/{unique_filename}"
            else:
                file_url = f"/static/uploads/support_attachments/{unique_filename}"
            
            logger.info(f"✅ Anexo enviado: {filename} para ticket {ticket_id}")
            
            return {
                "success": True,
                "attachment": {
                    "id": attachment.id,
                    "filename": attachment.filename,
                    "file_url": file_url,
                    "file_size": attachment.file_size,
                    "content_type": attachment.content_type,
                    "created_at": attachment.created_at.isoformat() if attachment.created_at else None
                }
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao fazer upload de anexo: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_ticket_attachments(
        self,
        ticket_id: int,
        company_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Lista anexos de um chamado (company_id opcional para superadmin)"""
        try:
            # Verificar se o ticket existe (e pertence à empresa se company_id fornecido)
            if company_id:
                ticket = self.db.query(SupportTicket).filter(
                    and_(
                        SupportTicket.id == ticket_id,
                        SupportTicket.company_id == company_id
                    )
                ).first()
            else:
                # Para superadmin, não filtrar por company_id
                ticket = self.db.query(SupportTicket).filter(
                    SupportTicket.id == ticket_id
                ).first()
            
            if not ticket:
                return {
                    "success": False,
                    "error": "Chamado não encontrado"
                }
            
            attachments = self.db.query(SupportTicketAttachment).filter(
                SupportTicketAttachment.ticket_id == ticket_id
            ).order_by(SupportTicketAttachment.created_at).all()
            
            attachments_list = []
            base_url = getattr(settings, "base_url", "") if hasattr(settings, "base_url") else ""
            
            for att in attachments:
                # Construir URL
                file_path = Path(att.file_path)
                unique_filename = file_path.name
                if base_url:
                    file_url = f"{base_url}/static/uploads/support_attachments/{unique_filename}"
                else:
                    file_url = f"/static/uploads/support_attachments/{unique_filename}"
                
                attachments_list.append({
                    "id": att.id,
                    "filename": att.filename,
                    "file_url": file_url,
                    "file_size": att.file_size,
                    "content_type": att.content_type,
                    "message_id": att.message_id,
                    "created_at": att.created_at.isoformat() if att.created_at else None,
                    "uploaded_by": att.uploaded_by,
                    "user_name": f"{att.user.first_name} {att.user.last_name}" if att.user else "Sistema"
                })
            
            return {
                "success": True,
                "attachments": attachments_list
            }
        except Exception as e:
            logger.error(f"Erro ao listar anexos: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_tickets(
        self,
        company_id: int,
        user_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lista chamados de suporte"""
        try:
            query = self.db.query(SupportTicket).filter(
                SupportTicket.company_id == company_id
            )
            
            if user_id:
                query = query.filter(SupportTicket.user_id == user_id)
            
            if status:
                # Filtrar por string do status
                query = query.filter(SupportTicket.status == status)
            
            tickets = query.order_by(desc(SupportTicket.created_at)).all()
            
            tickets_list = []
            for ticket in tickets:
                # Contar mensagens
                message_count = len(ticket.messages) if ticket.messages else 0
                
                # Status pode ser string ou enum
                status_value = ticket.status.value if hasattr(ticket.status, 'value') else ticket.status
                
                tickets_list.append({
                    "id": ticket.id,
                    "subject": ticket.subject,
                    "description": ticket.description,
                    "category": ticket.category,
                    "priority": ticket.priority,
                    "status": status_value,
                    "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                    "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
                    "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
                    "message_count": message_count,
                    "user_name": f"{ticket.user.first_name} {ticket.user.last_name}" if ticket.user else "Usuário"
                })
            
            return {
                "success": True,
                "tickets": tickets_list,
                "total": len(tickets_list)
            }
        except Exception as e:
            logger.error(f"Erro ao listar chamados: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_all_tickets(
        self,
        company_id: Optional[int] = None,
        status: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Lista chamados de suporte de TODAS as empresas (para superadmin)"""
        try:
            from app.models.saas_models import Company
            
            query = self.db.query(SupportTicket)
            
            # Filtrar por empresa se fornecido
            if company_id:
                query = query.filter(SupportTicket.company_id == company_id)
            
            # Filtrar por usuário se fornecido
            if user_id:
                query = query.filter(SupportTicket.user_id == user_id)
            
            # Filtrar por status se fornecido
            if status:
                query = query.filter(SupportTicket.status == status)
            
            tickets = query.order_by(desc(SupportTicket.created_at)).all()
            
            tickets_list = []
            for ticket in tickets:
                # Contar mensagens
                message_count = len(ticket.messages) if ticket.messages else 0
                
                # Status pode ser string ou enum
                status_value = ticket.status.value if hasattr(ticket.status, 'value') else ticket.status
                
                # Obter informações da empresa
                company_name = "N/A"
                if ticket.company:
                    company_name = ticket.company.name or ticket.company.nome_fantasia or "Empresa"
                
                tickets_list.append({
                    "id": ticket.id,
                    "company_id": ticket.company_id,
                    "company_name": company_name,
                    "subject": ticket.subject,
                    "description": ticket.description,
                    "category": ticket.category,
                    "priority": ticket.priority,
                    "status": status_value,
                    "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                    "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
                    "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
                    "message_count": message_count,
                    "user_name": f"{ticket.user.first_name} {ticket.user.last_name}" if ticket.user else "Usuário",
                    "user_email": ticket.user.email if ticket.user else None
                })
            
            return {
                "success": True,
                "tickets": tickets_list,
                "total": len(tickets_list)
            }
        except Exception as e:
            logger.error(f"Erro ao listar todos os chamados: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_ticket(self, ticket_id: int, company_id: Optional[int] = None) -> Dict[str, Any]:
        """Obtém um chamado específico (company_id opcional para superadmin)"""
        try:
            if company_id:
                ticket = self.db.query(SupportTicket).filter(
                    and_(
                        SupportTicket.id == ticket_id,
                        SupportTicket.company_id == company_id
                    )
                ).first()
            else:
                # Para superadmin, não filtrar por company_id
                ticket = self.db.query(SupportTicket).filter(
                    SupportTicket.id == ticket_id
                ).first()
            
            if not ticket:
                return {
                    "success": False,
                    "error": "Chamado não encontrado"
                }
            
            # Carregar mensagens
            messages_list = []
            for msg in ticket.messages:
                messages_list.append({
                    "id": msg.id,
                    "message": msg.message,
                    "is_from_support": msg.is_from_support,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    "user_name": f"{msg.user.first_name} {msg.user.last_name}" if msg.user else "Sistema"
                })
            
            # Carregar anexos
            attachments_list = []
            attachments = self.db.query(SupportTicketAttachment).filter(
                SupportTicketAttachment.ticket_id == ticket_id
            ).all()
            
            base_url = getattr(settings, "base_url", "") if hasattr(settings, "base_url") else ""
            for att in attachments:
                file_path = Path(att.file_path)
                unique_filename = file_path.name
                if base_url:
                    file_url = f"{base_url}/static/uploads/support_attachments/{unique_filename}"
                else:
                    file_url = f"/static/uploads/support_attachments/{unique_filename}"
                
                attachments_list.append({
                    "id": att.id,
                    "filename": att.filename,
                    "file_url": file_url,
                    "file_size": att.file_size,
                    "content_type": att.content_type
                })
            
            return {
                "success": True,
                "ticket": {
                    "id": ticket.id,
                    "subject": ticket.subject,
                    "description": ticket.description,
                    "category": ticket.category,
                    "priority": ticket.priority,
                    "status": ticket.status.value if hasattr(ticket.status, 'value') else ticket.status,
                    "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                    "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
                    "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
                    "messages": messages_list,
                    "attachments": attachments_list,
                    "user_name": f"{ticket.user.first_name} {ticket.user.last_name}" if ticket.user else "Usuário"
                }
            }
        except Exception as e:
            logger.error(f"Erro ao obter chamado: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_ticket_status(self, ticket_id: int, company_id: Optional[int], status: str) -> Dict[str, Any]:
        """Atualiza o status de um chamado (company_id opcional para superadmin)"""
        try:
            if company_id:
                ticket = self.db.query(SupportTicket).filter(
                    and_(
                        SupportTicket.id == ticket_id,
                        SupportTicket.company_id == company_id
                    )
                ).first()
            else:
                # Para superadmin, não filtrar por company_id
                ticket = self.db.query(SupportTicket).filter(
                    SupportTicket.id == ticket_id
                ).first()
            
            if not ticket:
                return {
                    "success": False,
                    "error": "Chamado não encontrado"
                }
            
            # Validar o novo status
            valid_statuses = ["open", "in_progress", "waiting_user", "resolved", "closed"]
            if status not in valid_statuses:
                return {
                    "success": False,
                    "error": f"Status inválido: {status}. Status válidos: {', '.join(valid_statuses)}"
                }
            
            # Atualizar status
            ticket.status = status
            
            # Se fechado, definir closed_at; caso contrário, limpar
            from datetime import datetime, timezone
            if status == "closed":
                ticket.closed_at = datetime.now(timezone.utc)
            else:
                ticket.closed_at = None  # Limpar data de fechamento se reaberto/alterado
            
            # Atualizar updated_at (o onupdate já faz isso, mas vamos garantir)
            ticket.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            self.db.refresh(ticket)
            
            logger.info(f"✅ Status do chamado {ticket_id} atualizado para: {status}")
            
            return {
                "success": True,
                "ticket": {
                    "id": ticket.id,
                    "status": ticket.status,
                    "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
                    "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None
                }
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar status do chamado {ticket_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

