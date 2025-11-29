"""
Controller para gerenciar tarefas
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import date
from app.services.task_service import TaskService
from app.models.saas_models import User

logger = logging.getLogger(__name__)


class TaskController:
    """Controller para gerenciar tarefas"""
    
    def __init__(self, db: Session):
        self.db = db
        self.task_service = TaskService(db)
    
    def create_task(
        self,
        company_id: int,
        user_id: int,
        title: str,
        due_date: date,
        assigned_to: Optional[int] = None,
        description: Optional[str] = None,
        status: str = "pending",
        priority: str = "medium",
        category: Optional[str] = None,
        product_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Cria uma nova tarefa"""
        return self.task_service.create_task(
            company_id=company_id,
            created_by=user_id,
            title=title,
            due_date=due_date,
            assigned_to=assigned_to,
            description=description,
            status=status,
            priority=priority,
            category=category,
            product_id=product_id
        )
    
    def list_tasks(
        self,
        company_id: int,
        status: Optional[str] = None,
        assigned_to: Optional[int] = None,
        created_by: Optional[int] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        due_date_from: Optional[date] = None,
        due_date_to: Optional[date] = None
    ) -> Dict[str, Any]:
        """Lista tarefas da empresa"""
        return self.task_service.list_tasks(
            company_id=company_id,
            status=status,
            assigned_to=assigned_to,
            created_by=created_by,
            category=category,
            search=search,
            due_date_from=due_date_from,
            due_date_to=due_date_to
        )
    
    def get_task(self, task_id: int, company_id: int) -> Dict[str, Any]:
        """Obtém uma tarefa específica"""
        return self.task_service.get_task(task_id, company_id)
    
    def update_task(
        self,
        task_id: int,
        company_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        assigned_to: Optional[int] = None,
        due_date: Optional[date] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        product_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Atualiza uma tarefa"""
        return self.task_service.update_task(
            task_id=task_id,
            company_id=company_id,
            title=title,
            description=description,
            assigned_to=assigned_to,
            due_date=due_date,
            priority=priority,
            category=category,
            product_id=product_id
        )
    
    def update_task_status(
        self,
        task_id: int,
        company_id: int,
        status: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Atualiza o status de uma tarefa"""
        return self.task_service.update_task_status(
            task_id=task_id,
            company_id=company_id,
            status=status,
            user_id=user_id
        )
    
    def delete_task(self, task_id: int, company_id: int, user_id: int) -> Dict[str, Any]:
        """Exclui uma tarefa"""
        return self.task_service.delete_task(
            task_id=task_id,
            company_id=company_id,
            user_id=user_id
        )
    
    def get_company_users(self, company_id: int) -> List[Dict[str, Any]]:
        """Obtém lista de usuários da empresa para atribuição"""
        try:
            users = self.db.query(User).filter(
                User.company_id == company_id,
                User.is_active == True
            ).order_by(User.first_name, User.last_name).all()
            
            return [
                {
                    "id": user.id,
                    "name": f"{user.first_name} {user.last_name}".strip() or user.email,
                    "email": user.email
                }
                for user in users
            ]
        except Exception as e:
            logger.error(f"Erro ao obter usuários da empresa: {e}", exc_info=True)
            return []

