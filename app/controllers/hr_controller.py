"""
Controller para Recursos Humanos (RH)
"""
from typing import Dict, Any, Optional, List
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from app.services.hr_service import HRService
from app.services.hr_permissions_service import HRPermissionsService


class HRController:
    """Controller para gerenciar RH"""
    
    def __init__(self, db: Session):
        self.db = db
        self.hr_service = HRService(db)
        self.permissions_service = HRPermissionsService(db)
    
    # ========== FUNCIONÁRIOS ==========
    
    def create_employee(
        self,
        company_id: int,
        cpf: str,
        nome_completo: str,
        data_admissao: date,
        salario_base: Decimal,
        user_email: Optional[str] = None,
        user_password: Optional[str] = None,
        user_role: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Cria um novo funcionário"""
        return self.hr_service.create_employee(
            company_id=company_id,
            cpf=cpf,
            nome_completo=nome_completo,
            data_admissao=data_admissao,
            salario_base=salario_base,
            user_email=user_email,
            user_password=user_password,
            user_role=user_role,
            **kwargs
        )
    
    def list_employees(
        self,
        company_id: int,
        status: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lista funcionários"""
        return self.hr_service.list_employees(
            company_id=company_id,
            status=status,
            search=search
        )
    
    def get_employee(
        self,
        employee_id: int,
        company_id: int
    ) -> Dict[str, Any]:
        """Obtém um funcionário"""
        return self.hr_service.get_employee(employee_id, company_id)
    
    def update_employee(
        self,
        employee_id: int,
        company_id: int,
        user_email: Optional[str] = None,
        user_password: Optional[str] = None,
        user_role: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Atualiza um funcionário"""
        return self.hr_service.update_employee(
            employee_id, 
            company_id, 
            user_email=user_email,
            user_password=user_password,
            user_role=user_role,
            **kwargs
        )
    
    def delete_employee(
        self,
        employee_id: int,
        company_id: int
    ) -> Dict[str, Any]:
        """Desativa um funcionário"""
        return self.hr_service.delete_employee(employee_id, company_id)
    
    # ========== FOLHA DE PAGAMENTO ==========
    
    def calculate_payroll(
        self,
        employee_id: int,
        company_id: int,
        mes_referencia: int,
        ano_referencia: int,
        salario_bruto: Optional[Decimal] = None,
        descontos: Decimal = Decimal('0'),
        adicionais: Decimal = Decimal('0'),
        dependentes: int = 0
    ) -> Dict[str, Any]:
        """Calcula folha de pagamento"""
        return self.hr_service.calculate_payroll(
            employee_id=employee_id,
            company_id=company_id,
            mes_referencia=mes_referencia,
            ano_referencia=ano_referencia,
            salario_bruto=salario_bruto,
            descontos=descontos,
            adicionais=adicionais,
            dependentes=dependentes
        )
    
    def create_payroll(
        self,
        employee_id: int,
        company_id: int,
        mes_referencia: int,
        ano_referencia: int,
        items: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Cria uma folha de pagamento"""
        return self.hr_service.create_payroll(
            employee_id=employee_id,
            company_id=company_id,
            mes_referencia=mes_referencia,
            ano_referencia=ano_referencia,
            items=items
        )
    
    # ========== FÉRIAS ==========
    
    def create_vacation(
        self,
        employee_id: int,
        periodo_aquisitivo_inicio: date,
        periodo_aquisitivo_fim: date,
        data_inicio: date,
        data_fim: date,
        dias: int = 30,
        observacoes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cria um registro de férias"""
        return self.hr_service.create_vacation(
            employee_id=employee_id,
            periodo_aquisitivo_inicio=periodo_aquisitivo_inicio,
            periodo_aquisitivo_fim=periodo_aquisitivo_fim,
            data_inicio=data_inicio,
            data_fim=data_fim,
            dias=dias,
            observacoes=observacoes
        )
    
    # ========== BENEFÍCIOS ==========
    
    def create_benefit(
        self,
        employee_id: int,
        tipo_beneficio: str,
        descricao: str,
        valor: Decimal,
        data_inicio: date,
        data_fim: Optional[date] = None
    ) -> Dict[str, Any]:
        """Cria um benefício"""
        return self.hr_service.create_benefit(
            employee_id=employee_id,
            tipo_beneficio=tipo_beneficio,
            descricao=descricao,
            valor=valor,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
    
    # ========== PERMISSÕES ==========
    
    def set_permissions(
        self,
        employee_id: int,
        company_id: int,
        permissions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Define permissões para um funcionário"""
        return self.permissions_service.set_permissions(
            employee_id=employee_id,
            company_id=company_id,
            permissions=permissions
        )
    
    def get_permissions(
        self,
        employee_id: int,
        company_id: int
    ) -> Dict[str, Any]:
        """Obtém permissões de um funcionário"""
        return self.permissions_service.get_permissions(employee_id, company_id)
    
    def check_permission(
        self,
        employee_id: int,
        company_id: int,
        menu_name: str,
        submenu_name: Optional[str] = None
    ) -> bool:
        """Verifica permissão"""
        return self.permissions_service.check_permission(
            employee_id=employee_id,
            company_id=company_id,
            menu_name=menu_name,
            submenu_name=submenu_name
        )

