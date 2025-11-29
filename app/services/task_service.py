"""
Serviço para gerenciar tarefas e atividades
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func as sql_func
from datetime import date, datetime, timezone
from app.models.task_models import Task
from app.models.saas_models import User

logger = logging.getLogger(__name__)


class TaskService:
    """Serviço para gerenciar tarefas"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_task(
        self,
        company_id: int,
        created_by: int,
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
        try:
            # Validar que o criador pertence à empresa
            creator = self.db.query(User).filter(
                and_(
                    User.id == created_by,
                    User.company_id == company_id
                )
            ).first()
            
            if not creator:
                return {"success": False, "error": "Usuário criador não encontrado"}
            
            # Validar usuário atribuído se fornecido
            if assigned_to:
                assignee = self.db.query(User).filter(
                    and_(
                        User.id == assigned_to,
                        User.company_id == company_id
                    )
                ).first()
                
                if not assignee:
                    return {"success": False, "error": "Usuário atribuído não encontrado"}
            
            task = Task(
                company_id=company_id,
                created_by=created_by,
                assigned_to=assigned_to,
                title=title,
                description=description,
                status=status,
                priority=priority,
                category=category,
                due_date=due_date,
                product_id=product_id
            )
            
            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)
            
            logger.info(f"✅ Tarefa criada: ID={task.id}, Title={title}, Company={company_id}")
            
            return {
                "success": True,
                "task": self._task_to_dict(task)
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar tarefa: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
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
        """Lista tarefas da empresa com filtros"""
        try:
            query = self.db.query(Task).filter(Task.company_id == company_id)
            
            # Aplicar filtros
            if status:
                query = query.filter(Task.status == status)
            
            if assigned_to:
                query = query.filter(Task.assigned_to == assigned_to)
            
            if created_by:
                query = query.filter(Task.created_by == created_by)
            
            if category:
                query = query.filter(Task.category == category)
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        Task.title.ilike(search_term),
                        Task.description.ilike(search_term)
                    )
                )
            
            if due_date_from:
                query = query.filter(Task.due_date >= due_date_from)
            
            if due_date_to:
                query = query.filter(Task.due_date <= due_date_to)
            
            # Ordenar por data de vencimento (mais próximas primeiro) e depois por prioridade
            tasks = query.order_by(
                Task.due_date.asc(),
                Task.priority.desc(),
                Task.created_at.desc()
            ).all()
            
            return {
                "success": True,
                "tasks": [self._task_to_dict(task) for task in tasks]
            }
        except Exception as e:
            logger.error(f"Erro ao listar tarefas: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_task(self, task_id: int, company_id: int) -> Dict[str, Any]:
        """Obtém uma tarefa específica"""
        try:
            task = self.db.query(Task).filter(
                and_(
                    Task.id == task_id,
                    Task.company_id == company_id
                )
            ).first()
            
            if not task:
                return {"success": False, "error": "Tarefa não encontrada"}
            
            return {
                "success": True,
                "task": self._task_to_dict(task)
            }
        except Exception as e:
            logger.error(f"Erro ao obter tarefa: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
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
        try:
            task = self.db.query(Task).filter(
                and_(
                    Task.id == task_id,
                    Task.company_id == company_id
                )
            ).first()
            
            if not task:
                return {"success": False, "error": "Tarefa não encontrada"}
            
            # Atualizar campos
            if title is not None:
                task.title = title
            if description is not None:
                task.description = description
            if assigned_to is not None:
                # Validar usuário atribuído
                if assigned_to:
                    assignee = self.db.query(User).filter(
                        and_(
                            User.id == assigned_to,
                            User.company_id == company_id
                        )
                    ).first()
                    if not assignee:
                        return {"success": False, "error": "Usuário atribuído não encontrado"}
                task.assigned_to = assigned_to
            if due_date is not None:
                task.due_date = due_date
            if priority is not None:
                task.priority = priority
            if category is not None:
                task.category = category
            if product_id is not None:
                task.product_id = product_id
            
            task.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            self.db.refresh(task)
            
            logger.info(f"✅ Tarefa atualizada: ID={task_id}")
            
            return {
                "success": True,
                "task": self._task_to_dict(task)
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar tarefa: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def update_task_status(
        self,
        task_id: int,
        company_id: int,
        status: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Atualiza o status de uma tarefa"""
        try:
            task = self.db.query(Task).filter(
                and_(
                    Task.id == task_id,
                    Task.company_id == company_id
                )
            ).first()
            
            if not task:
                return {"success": False, "error": "Tarefa não encontrada"}
            
            # Validar que o usuário pode atualizar (deve ser o atribuído ou admin)
            if user_id:
                user = self.db.query(User).filter(User.id == user_id).first()
                if user:
                    # Verificar se é admin ou se é o usuário atribuído
                    if user.role not in ["company_admin", "super_admin"]:
                        if task.assigned_to != user_id and task.created_by != user_id:
                            return {"success": False, "error": "Você não tem permissão para atualizar esta tarefa"}
            
            old_status = task.status
            task.status = status
            
            # Se status mudou para completed, definir completed_at
            if status == "completed" and old_status != "completed":
                task.completed_at = datetime.now(timezone.utc)
            elif status != "completed":
                task.completed_at = None
            
            # Se status mudou para cancelled, definir completed_at como None
            if status == "cancelled":
                task.completed_at = None
            
            task.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            self.db.refresh(task)
            
            logger.info(f"✅ Status da tarefa atualizado: ID={task_id}, Status={status}")
            
            return {
                "success": True,
                "task": self._task_to_dict(task)
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar status da tarefa: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def delete_task(self, task_id: int, company_id: int, user_id: int) -> Dict[str, Any]:
        """Exclui uma tarefa (apenas criador ou admin)"""
        try:
            task = self.db.query(Task).filter(
                and_(
                    Task.id == task_id,
                    Task.company_id == company_id
                )
            ).first()
            
            if not task:
                return {"success": False, "error": "Tarefa não encontrada"}
            
            # Verificar permissão (criador ou admin)
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                if user.role not in ["company_admin", "super_admin"]:
                    if task.created_by != user_id:
                        return {"success": False, "error": "Você não tem permissão para excluir esta tarefa"}
            
            self.db.delete(task)
            self.db.commit()
            
            logger.info(f"✅ Tarefa excluída: ID={task_id}")
            
            return {"success": True}
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao excluir tarefa: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Converte modelo Task para dicionário"""
        return {
            "id": task.id,
            "company_id": task.company_id,
            "created_by": task.created_by,
            "assigned_to": task.assigned_to,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "category": task.category,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "product_id": task.product_id,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            # Dados relacionados
            "creator_name": f"{task.creator.first_name} {task.creator.last_name}".strip() if task.creator else None,
            "assignee_name": f"{task.assignee.first_name} {task.assignee.last_name}".strip() if task.assignee else None,
            "product_name": task.product.name if task.product else None,
        }

