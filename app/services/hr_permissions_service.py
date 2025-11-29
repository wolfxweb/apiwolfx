"""
Serviço para gerenciar permissões individuais de funcionários
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.hr_models import Employee, EmployeePermission

logger = logging.getLogger(__name__)


class HRPermissionsService:
    """Serviço para gerenciar permissões de funcionários"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def set_permissions(
        self,
        employee_id: int,
        company_id: int,
        permissions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Define permissões para um funcionário"""
        try:
            # Verificar se funcionário existe
            employee = self.db.query(Employee).filter(
                and_(
                    Employee.id == employee_id,
                    Employee.company_id == company_id
                )
            ).first()
            
            if not employee:
                return {"success": False, "error": "Funcionário não encontrado"}
            
            # Remover permissões existentes
            self.db.query(EmployeePermission).filter(
                EmployeePermission.employee_id == employee_id
            ).delete()
            
            # Criar novas permissões
            for perm in permissions:
                permission = EmployeePermission(
                    employee_id=employee_id,
                    company_id=company_id,
                    menu_name=perm.get("menu_name"),
                    submenu_name=perm.get("submenu_name"),
                    has_access=perm.get("has_access", True)
                )
                self.db.add(permission)
            
            self.db.commit()
            
            logger.info(f"✅ Permissões atualizadas: Employee={employee_id}")
            
            return {"success": True}
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao definir permissões: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_permissions(
        self,
        employee_id: int,
        company_id: int
    ) -> Dict[str, Any]:
        """Obtém permissões de um funcionário"""
        try:
            permissions = self.db.query(EmployeePermission).filter(
                and_(
                    EmployeePermission.employee_id == employee_id,
                    EmployeePermission.company_id == company_id
                )
            ).all()
            
            return {
                "success": True,
                "permissions": [
                    {
                        "menu_name": p.menu_name,
                        "submenu_name": p.submenu_name,
                        "has_access": p.has_access
                    }
                    for p in permissions
                ]
            }
        except Exception as e:
            logger.error(f"Erro ao obter permissões: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def check_permission(
        self,
        employee_id: int,
        company_id: int,
        menu_name: str,
        submenu_name: Optional[str] = None
    ) -> bool:
        """Verifica se funcionário tem permissão para acessar um menu"""
        try:
            # Se funcionário não está vinculado a um user, não tem permissões
            employee = self.db.query(Employee).filter(
                and_(
                    Employee.id == employee_id,
                    Employee.company_id == company_id
                )
            ).first()
            
            if not employee or not employee.user_id:
                return False
            
            # Buscar permissão específica
            query = self.db.query(EmployeePermission).filter(
                and_(
                    EmployeePermission.employee_id == employee_id,
                    EmployeePermission.company_id == company_id,
                    EmployeePermission.menu_name == menu_name,
                    EmployeePermission.has_access == True
                )
            )
            
            if submenu_name:
                query = query.filter(
                    EmployeePermission.submenu_name == submenu_name
                )
            else:
                query = query.filter(
                    EmployeePermission.submenu_name.is_(None)
                )
            
            permission = query.first()
            
            return permission is not None
        except Exception as e:
            logger.error(f"Erro ao verificar permissão: {e}", exc_info=True)
            return False
    
    def get_user_permissions_from_employee(
        self,
        user_id: int,
        company_id: int
    ) -> Dict[str, List[str]]:
        """Obtém permissões de menus baseado no funcionário vinculado ao usuário"""
        try:
            # Buscar funcionário vinculado ao usuário
            employee = self.db.query(Employee).filter(
                and_(
                    Employee.user_id == user_id,
                    Employee.company_id == company_id,
                    Employee.status == "active"
                )
            ).first()
            
            if not employee:
                return {}
            
            # Buscar permissões do funcionário
            permissions = self.db.query(EmployeePermission).filter(
                and_(
                    EmployeePermission.employee_id == employee.id,
                    EmployeePermission.company_id == company_id,
                    EmployeePermission.has_access == True
                )
            ).all()
            
            # Organizar por menu
            result = {}
            for perm in permissions:
                menu = perm.menu_name
                if menu not in result:
                    result[menu] = []
                
                if perm.submenu_name:
                    result[menu].append(perm.submenu_name)
            
            return result
        except Exception as e:
            logger.error(f"Erro ao obter permissões do usuário: {e}", exc_info=True)
            return {}

