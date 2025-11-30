"""
Serviço para gerenciar Recursos Humanos (RH)
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc, func
from app.models.hr_models import (
    Employee, Payroll, PayrollItem, EmployeeVacation, EmployeeBenefit,
    EmployeeStatus, PayrollStatus, VacationStatus
)
from app.models.saas_models import User, UserRole, Subscription
from app.models.financial_models import FinancialCategory, CostCenter
from app.controllers.auth_controller import AuthController

logger = logging.getLogger(__name__)


class HRService:
    """Serviço para gerenciar RH"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========== VALIDAÇÕES DE LIMITE ==========
    
    def _get_active_subscription(self, company_id: int) -> Optional[Subscription]:
        """Obtém a assinatura ativa da empresa"""
        try:
            subscription = self.db.query(Subscription).filter(
                Subscription.company_id == company_id,
                (Subscription.status == "active") | (Subscription.is_trial == True)
            ).order_by(Subscription.created_at.desc()).first()
            return subscription
        except Exception as e:
            logger.error(f"Erro ao buscar assinatura ativa: {e}", exc_info=True)
            return None
    
    def _count_active_users(self, company_id: int) -> int:
        """Conta usuários ativos da empresa"""
        try:
            count = self.db.query(User).filter(
                User.company_id == company_id,
                User.is_active == True
            ).count()
            return count
        except Exception as e:
            logger.error(f"Erro ao contar usuários ativos: {e}", exc_info=True)
            return 0
    
    def _check_user_limit(self, company_id: int) -> Dict[str, Any]:
        """Verifica se a empresa pode criar mais usuários"""
        try:
            subscription = self._get_active_subscription(company_id)
            
            # Se não houver assinatura, permitir criação (comportamento atual)
            if not subscription:
                return {
                    "allowed": True,
                    "max_users": None,
                    "current_users": 0,
                    "message": None
                }
            
            # Se não houver limite definido, permitir
            if not subscription.max_users or subscription.max_users <= 0:
                return {
                    "allowed": True,
                    "max_users": None,
                    "current_users": 0,
                    "message": None
                }
            
            # Contar usuários ativos
            current_users = self._count_active_users(company_id)
            max_users = subscription.max_users
            
            # Verificar se atingiu o limite
            if current_users >= max_users:
                return {
                    "allowed": False,
                    "max_users": max_users,
                    "current_users": current_users,
                    "message": f"Limite máximo de usuários atingido. O plano permite {max_users} usuários e você já possui {current_users} usuários ativos. Entre em contato para atualizar seu plano."
                }
            
            return {
                "allowed": True,
                "max_users": max_users,
                "current_users": current_users,
                "message": None
            }
        except Exception as e:
            logger.error(f"Erro ao verificar limite de usuários: {e}", exc_info=True)
            # Em caso de erro, permitir criação (fail-safe)
            return {
                "allowed": True,
                "max_users": None,
                "current_users": 0,
                "message": None
            }
    
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
        try:
            # Verificar se CPF já existe na empresa
            existing = self.db.query(Employee).filter(
                and_(
                    Employee.company_id == company_id,
                    Employee.cpf == cpf
                )
            ).first()
            
            if existing:
                return {
                    "success": False,
                    "error": "CPF já cadastrado para esta empresa"
                }
            
            user_id = None
            user = None
            # Se email e senha foram fornecidos, criar usuário
            if user_email and user_password:
                # Verificar limite de usuários antes de criar
                limit_check = self._check_user_limit(company_id)
                if not limit_check["allowed"]:
                    return {
                        "success": False,
                        "error": limit_check["message"]
                    }
                
                # Verificar se email já existe
                existing_user = self.db.query(User).filter(User.email == user_email).first()
                if existing_user:
                    return {
                        "success": False,
                        "error": "E-mail já cadastrado no sistema"
                    }
                
                # Criar usuário
                auth_controller = AuthController()
                password_hash = auth_controller.get_password_hash(user_password)
                
                # Definir role padrão se não fornecido - usar enum diretamente
                if user_role:
                    try:
                        role_enum = UserRole(user_role)
                    except ValueError:
                        role_enum = UserRole.VIEWER
                else:
                    role_enum = UserRole.VIEWER
                
                # Separar nome completo em first_name e last_name
                nome_parts = nome_completo.split() if nome_completo else []
                
                user = User(
                    company_id=company_id,
                    email=user_email,
                    first_name=nome_parts[0] if nome_parts else None,
                    last_name=' '.join(nome_parts[1:]) if len(nome_parts) > 1 else None,
                    password_hash=password_hash,
                    is_active=True,
                    role=role_enum
                )
                self.db.add(user)
                self.db.flush()  # Para obter o ID sem fazer commit ainda
                user_id = user.id
                logger.info(f"✅ Usuário criado na tabela users: Email={user_email}, Role={role_enum.value}, User ID={user_id}, Company ID={company_id}")
            
            employee = Employee(
                company_id=company_id,
                cpf=cpf,
                nome_completo=nome_completo,
                data_admissao=data_admissao,
                salario_base=salario_base,
                user_id=user_id,
                **kwargs
            )
            
            self.db.add(employee)
            self.db.commit()  # Commit de funcionário e usuário juntos
            self.db.refresh(employee)
            if user:
                self.db.refresh(user)
            
            logger.info(f"✅ Funcionário criado: ID={employee.id}, Company={company_id}, Nome={nome_completo}")
            
            return {
                "success": True,
                "employee": self._employee_to_dict(employee)
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar funcionário: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def list_employees(
        self,
        company_id: int,
        status: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lista funcionários da empresa"""
        try:
            query = self.db.query(Employee).filter(
                Employee.company_id == company_id
            )
            
            if status:
                query = query.filter(Employee.status == status)
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    (Employee.nome_completo.ilike(search_term)) |
                    (Employee.cpf.ilike(search_term)) |
                    (Employee.email.ilike(search_term)) |
                    (Employee.cargo.ilike(search_term))
                )
            
            employees = query.order_by(desc(Employee.created_at)).all()
            
            return {
                "success": True,
                "employees": [self._employee_to_dict(emp) for emp in employees],
                "total": len(employees)
            }
        except Exception as e:
            logger.error(f"Erro ao listar funcionários: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_employee(self, employee_id: int, company_id: int) -> Dict[str, Any]:
        """Obtém um funcionário específico"""
        try:
            employee = self.db.query(Employee).options(
                joinedload(Employee.financial_category),
                joinedload(Employee.cost_center)
            ).filter(
                and_(
                    Employee.id == employee_id,
                    Employee.company_id == company_id
                )
            ).first()
            
            if not employee:
                return {"success": False, "error": "Funcionário não encontrado"}
            
            return {
                "success": True,
                "employee": self._employee_to_dict(employee)
            }
        except Exception as e:
            logger.error(f"Erro ao obter funcionário: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def update_employee(
        self,
        employee_id: int,
        company_id: int,
        user_email: Optional[str] = None,
        user_password: Optional[str] = None,
        user_role: Optional[str] = None,
        status: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Atualiza um funcionário"""
        try:
            employee = self.db.query(Employee).filter(
                and_(
                    Employee.id == employee_id,
                    Employee.company_id == company_id
                )
            ).first()
            
            if not employee:
                return {"success": False, "error": "Funcionário não encontrado"}
            
            # Atualizar campos do funcionário (exceto user_email, user_password, user_role, status)
            employee_kwargs = {k: v for k, v in kwargs.items() if k not in ['user_email', 'user_password', 'user_role', 'status']}
            for key, value in employee_kwargs.items():
                if hasattr(employee, key) and value is not None:
                    setattr(employee, key, value)
            
            # Atualizar status do funcionário
            if status is not None:
                employee.status = status
                # Sincronizar status com usuário - IMPORTANTE: inativar usuário na tabela users
                if employee.user_id:
                    user = self.db.query(User).filter(User.id == employee.user_id).first()
                    if user:
                        # Se funcionário inativo ou demitido, inativar usuário também (perde acesso ao sistema)
                        if status in ['inactive', 'terminated']:
                            user.is_active = False
                            logger.info(f"✅ Usuário inativado na tabela users (sem acesso ao sistema): User ID={user.id}, Email={user.email}")
                        # Se funcionário ativo, reativar usuário também
                        elif status == 'active':
                            user.is_active = True
                            logger.info(f"✅ Usuário reativado na tabela users (com acesso ao sistema): User ID={user.id}, Email={user.email}")
                else:
                    logger.warning(f"⚠️ Funcionário ID={employee_id} não possui user_id vinculado, não é possível inativar usuário")
            
            # Gerenciar conta de usuário
            if user_email:
                # Se já tem usuário vinculado, atualizar
                if employee.user_id:
                    user = self.db.query(User).filter(User.id == employee.user_id).first()
                    if user:
                        # Verificar se email mudou e se já existe outro usuário com esse email
                        if user.email != user_email:
                            existing_user = self.db.query(User).filter(
                                and_(
                                    User.email == user_email,
                                    User.id != user.id
                                )
                            ).first()
                            if existing_user:
                                return {
                                    "success": False,
                                    "error": "E-mail já cadastrado no sistema"
                                }
                            user.email = user_email
                        
                        # Atualizar senha se fornecida
                        if user_password:
                            auth_controller = AuthController()
                            user.password_hash = auth_controller.get_password_hash(user_password)
                        
                        # Atualizar role se fornecido - usar enum diretamente
                        if user_role:
                            try:
                                user.role = UserRole(user_role)
                            except ValueError:
                                logger.warning(f"Role inválido: {user_role}, mantendo role atual")
                        
                        # Atualizar nome do usuário com nome do funcionário
                        if employee.nome_completo:
                            nome_parts = employee.nome_completo.split()
                            user.first_name = nome_parts[0] if nome_parts else None
                            user.last_name = ' '.join(nome_parts[1:]) if len(nome_parts) > 1 else None
                        
                        logger.info(f"✅ Usuário atualizado na tabela users: Email={user.email}, Role={user.role}, User ID={user.id}")
                    else:
                        # Usuário não encontrado, criar novo
                        employee.user_id = None
                else:
                    # Não tem usuário, criar novo - VERIFICAR LIMITE ANTES
                    # Verificar limite de usuários antes de criar
                    limit_check = self._check_user_limit(company_id)
                    if not limit_check["allowed"]:
                        return {
                            "success": False,
                            "error": limit_check["message"]
                        }
                    
                    existing_user = self.db.query(User).filter(User.email == user_email).first()
                    if existing_user:
                        return {
                            "success": False,
                            "error": "E-mail já cadastrado no sistema"
                        }
                    
                    auth_controller = AuthController()
                    password_hash = auth_controller.get_password_hash(user_password) if user_password else None
                    if not password_hash:
                        return {
                            "success": False,
                            "error": "Senha é obrigatória ao criar nova conta de usuário"
                        }
                    
                    # Definir role - usar enum diretamente
                    if user_role:
                        try:
                            role_enum = UserRole(user_role)
                        except ValueError:
                            role_enum = UserRole.VIEWER
                    else:
                        role_enum = UserRole.VIEWER
                    
                    # Separar nome completo em first_name e last_name
                    nome_parts = employee.nome_completo.split() if employee.nome_completo else []
                    
                    user = User(
                        company_id=company_id,
                        email=user_email,
                        first_name=nome_parts[0] if nome_parts else None,
                        last_name=' '.join(nome_parts[1:]) if len(nome_parts) > 1 else None,
                        password_hash=password_hash,
                        is_active=employee.status == 'active',  # Sincronizar status inicial
                        role=role_enum
                    )
                    self.db.add(user)
                    self.db.flush()
                    employee.user_id = user.id
                    logger.info(f"✅ Usuário criado na tabela users: Email={user_email}, Role={role_enum.value}, User ID={user.id}, Company ID={company_id}")
            
            # Sincronizar nome do usuário se funcionário foi atualizado
            if employee.user_id and employee.nome_completo:
                user = self.db.query(User).filter(User.id == employee.user_id).first()
                if user:
                    nome_parts = employee.nome_completo.split()
                    user.first_name = nome_parts[0] if nome_parts else None
                    user.last_name = ' '.join(nome_parts[1:]) if len(nome_parts) > 1 else None
            
            self.db.commit()
            self.db.refresh(employee)
            
            logger.info(f"✅ Funcionário atualizado: ID={employee_id}")
            
            return {
                "success": True,
                "employee": self._employee_to_dict(employee)
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar funcionário: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def delete_employee(self, employee_id: int, company_id: int) -> Dict[str, Any]:
        """Desativa um funcionário (soft delete)"""
        try:
            employee = self.db.query(Employee).filter(
                and_(
                    Employee.id == employee_id,
                    Employee.company_id == company_id
                )
            ).first()
            
            if not employee:
                return {"success": False, "error": "Funcionário não encontrado"}
            
            employee.status = EmployeeStatus.INACTIVE.value
            employee.data_demissao = date.today()
            
            # Inativar usuário também se existir
            if employee.user_id:
                user = self.db.query(User).filter(User.id == employee.user_id).first()
                if user:
                    user.is_active = False
                    logger.info(f"✅ Usuário inativado junto com funcionário: User ID={user.id}")
            
            self.db.commit()
            
            logger.info(f"✅ Funcionário desativado: ID={employee_id}")
            
            return {"success": True}
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao desativar funcionário: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    # ========== CÁLCULOS DE FOLHA ==========
    
    def calculate_inss(self, salario_bruto: Decimal) -> Decimal:
        """Calcula INSS baseado nas faixas de 2024/2025"""
        # Tabela INSS 2024/2025
        faixas = [
            (Decimal('0'), Decimal('1412.00'), Decimal('0.075')),  # 7.5%
            (Decimal('1412.01'), Decimal('2666.68'), Decimal('0.09')),  # 9%
            (Decimal('2666.69'), Decimal('4000.03'), Decimal('0.12')),  # 12%
            (Decimal('4000.04'), Decimal('7786.02'), Decimal('0.14')),  # 14%
        ]
        teto = Decimal('7786.02')
        
        if salario_bruto > teto:
            salario_bruto = teto
        
        inss = Decimal('0')
        for min_val, max_val, aliquota in faixas:
            if salario_bruto > min_val:
                base_calculo = min(salario_bruto, max_val) - min_val
                inss += base_calculo * aliquota
        
        return inss.quantize(Decimal('0.01'))
    
    def calculate_irrf(self, salario_bruto: Decimal, inss: Decimal, dependentes: int = 0) -> Decimal:
        """Calcula IRRF baseado na tabela progressiva"""
        # Dedução por dependente (2024/2025)
        deducao_dependente = Decimal('189.59')
        deducao_padrao = Decimal('528.00')  # Dedução padrão
        
        base_calculo = salario_bruto - inss - (dependentes * deducao_dependente) - deducao_padrao
        
        if base_calculo <= 0:
            return Decimal('0')
        
        # Tabela IRRF 2024/2025
        faixas = [
            (Decimal('0'), Decimal('22847.76'), Decimal('0'), Decimal('0')),  # Isento
            (Decimal('22847.77'), Decimal('33919.80'), Decimal('0.075'), Decimal('1713.58')),  # 7.5%
            (Decimal('33919.81'), Decimal('45012.60'), Decimal('0.15'), Decimal('4257.57')),  # 15%
            (Decimal('45012.61'), Decimal('55976.16'), Decimal('0.225'), Decimal('7633.51')),  # 22.5%
            (Decimal('55976.17'), Decimal('999999999'), Decimal('0.275'), Decimal('10432.32')),  # 27.5%
        ]
        
        for min_val, max_val, aliquota, deducao in faixas:
            if min_val <= base_calculo <= max_val:
                irrf = (base_calculo * aliquota) - deducao
                return max(Decimal('0'), irrf.quantize(Decimal('0.01')))
        
        return Decimal('0')
    
    def calculate_fgts(self, salario_bruto: Decimal) -> Decimal:
        """Calcula FGTS (8% sobre salário bruto)"""
        return (salario_bruto * Decimal('0.08')).quantize(Decimal('0.01'))
    
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
        """Calcula folha de pagamento para um funcionário"""
        try:
            employee = self.db.query(Employee).filter(
                and_(
                    Employee.id == employee_id,
                    Employee.company_id == company_id
                )
            ).first()
            
            if not employee:
                return {"success": False, "error": "Funcionário não encontrado"}
            
            # Usar salário base do funcionário se não fornecido
            if salario_bruto is None:
                salario_bruto = employee.salario_base
            
            # Calcular descontos legais
            inss = self.calculate_inss(salario_bruto)
            irrf = self.calculate_irrf(salario_bruto, inss, dependentes)
            fgts = self.calculate_fgts(salario_bruto)
            
            # Calcular total líquido
            total_descontos = descontos + inss + irrf
            salario_liquido = salario_bruto + adicionais - total_descontos
            
            return {
                "success": True,
                "payroll": {
                    "salario_bruto": float(salario_bruto),
                    "descontos": float(descontos),
                    "adicionais": float(adicionais),
                    "inss": float(inss),
                    "irrf": float(irrf),
                    "fgts": float(fgts),
                    "total_descontos": float(total_descontos),
                    "salario_liquido": float(salario_liquido)
                }
            }
        except Exception as e:
            logger.error(f"Erro ao calcular folha: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def create_payroll(
        self,
        employee_id: int,
        company_id: int,
        mes_referencia: int,
        ano_referencia: int,
        items: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Cria uma folha de pagamento"""
        try:
            # Verificar se já existe folha para o período
            existing = self.db.query(Payroll).filter(
                and_(
                    Payroll.employee_id == employee_id,
                    Payroll.mes_referencia == mes_referencia,
                    Payroll.ano_referencia == ano_referencia
                )
            ).first()
            
            if existing:
                return {"success": False, "error": "Folha já existe para este período"}
            
            # Calcular folha
            calc_result = self.calculate_payroll(
                employee_id, company_id, mes_referencia, ano_referencia
            )
            
            if not calc_result.get("success"):
                return calc_result
            
            payroll_data = calc_result["payroll"]
            
            # Criar folha
            payroll = Payroll(
                employee_id=employee_id,
                company_id=company_id,
                mes_referencia=mes_referencia,
                ano_referencia=ano_referencia,
                salario_bruto=Decimal(str(payroll_data["salario_bruto"])),
                descontos=Decimal(str(payroll_data["descontos"])),
                adicionais=Decimal(str(payroll_data["adicionais"])),
                inss=Decimal(str(payroll_data["inss"])),
                irrf=Decimal(str(payroll_data["irrf"])),
                fgts=Decimal(str(payroll_data["fgts"])),
                salario_liquido=Decimal(str(payroll_data["salario_liquido"])),
                status=PayrollStatus.DRAFT.value
            )
            
            self.db.add(payroll)
            self.db.flush()
            
            # Adicionar itens se fornecidos
            if items:
                for item in items:
                    payroll_item = PayrollItem(
                        payroll_id=payroll.id,
                        tipo=item.get("tipo", "desconto"),
                        descricao=item.get("descricao", ""),
                        valor=Decimal(str(item.get("valor", 0))),
                        codigo_referencia=item.get("codigo_referencia")
                    )
                    self.db.add(payroll_item)
            
            self.db.commit()
            self.db.refresh(payroll)
            
            logger.info(f"✅ Folha criada: ID={payroll.id}, Employee={employee_id}")
            
            return {
                "success": True,
                "payroll": self._payroll_to_dict(payroll)
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar folha: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
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
        try:
            vacation = EmployeeVacation(
                employee_id=employee_id,
                periodo_aquisitivo_inicio=periodo_aquisitivo_inicio,
                periodo_aquisitivo_fim=periodo_aquisitivo_fim,
                data_inicio=data_inicio,
                data_fim=data_fim,
                dias=dias,
                status=VacationStatus.SCHEDULED.value,
                observacoes=observacoes
            )
            
            self.db.add(vacation)
            self.db.commit()
            self.db.refresh(vacation)
            
            logger.info(f"✅ Férias criada: ID={vacation.id}, Employee={employee_id}")
            
            return {
                "success": True,
                "vacation": self._vacation_to_dict(vacation)
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar férias: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
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
        """Cria um benefício para funcionário"""
        try:
            benefit = EmployeeBenefit(
                employee_id=employee_id,
                tipo_beneficio=tipo_beneficio,
                descricao=descricao,
                valor=valor,
                data_inicio=data_inicio,
                data_fim=data_fim,
                status="active"
            )
            
            self.db.add(benefit)
            self.db.commit()
            self.db.refresh(benefit)
            
            logger.info(f"✅ Benefício criado: ID={benefit.id}, Employee={employee_id}")
            
            return {
                "success": True,
                "benefit": self._benefit_to_dict(benefit)
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar benefício: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    # ========== HELPERS ==========
    
    def _employee_to_dict(self, employee: Employee) -> Dict[str, Any]:
        """Converte Employee para dict"""
        # Buscar dados do usuário se existir
        user_email = None
        user_role = None
        if employee.user_id:
            user = self.db.query(User).filter(User.id == employee.user_id).first()
            if user:
                user_email = user.email
                user_role = user.role.value if hasattr(user.role, 'value') else str(user.role)
        
        return {
            "id": employee.id,
            "company_id": employee.company_id,
            "user_id": employee.user_id,
            "cpf": employee.cpf,
            "rg": employee.rg,
            "nome_completo": employee.nome_completo,
            "data_nascimento": employee.data_nascimento.isoformat() if employee.data_nascimento else None,
            "telefone": employee.telefone,
            "email": employee.email,
            "endereco": employee.endereco,
            "cidade": employee.cidade,
            "estado": employee.estado,
            "cep": employee.cep,
            "cargo": employee.cargo,
            "departamento": employee.departamento,
            "data_admissao": employee.data_admissao.isoformat() if employee.data_admissao else None,
            "data_demissao": employee.data_demissao.isoformat() if employee.data_demissao else None,
            "status": employee.status,
            "salario_base": float(employee.salario_base) if employee.salario_base else None,
            "tipo_contrato": employee.tipo_contrato,
            "carga_horaria": employee.carga_horaria,
            "financial_category_id": employee.financial_category_id,
            "cost_center_id": employee.cost_center_id,
            "financial_category_name": employee.financial_category.name if hasattr(employee, 'financial_category') and employee.financial_category else None,
            "cost_center_name": employee.cost_center.name if hasattr(employee, 'cost_center') and employee.cost_center else None,
            "user_email": user_email,
            "user_role": user_role,
            "created_at": employee.created_at.isoformat() if employee.created_at else None,
            "updated_at": employee.updated_at.isoformat() if employee.updated_at else None
        }
    
    def _payroll_to_dict(self, payroll: Payroll) -> Dict[str, Any]:
        """Converte Payroll para dict"""
        return {
            "id": payroll.id,
            "employee_id": payroll.employee_id,
            "company_id": payroll.company_id,
            "mes_referencia": payroll.mes_referencia,
            "ano_referencia": payroll.ano_referencia,
            "salario_bruto": float(payroll.salario_bruto) if payroll.salario_bruto else None,
            "descontos": float(payroll.descontos) if payroll.descontos else None,
            "adicionais": float(payroll.adicionais) if payroll.adicionais else None,
            "inss": float(payroll.inss) if payroll.inss else None,
            "irrf": float(payroll.irrf) if payroll.irrf else None,
            "fgts": float(payroll.fgts) if payroll.fgts else None,
            "salario_liquido": float(payroll.salario_liquido) if payroll.salario_liquido else None,
            "status": payroll.status,
            "observacoes": payroll.observacoes,
            "created_at": payroll.created_at.isoformat() if payroll.created_at else None,
            "updated_at": payroll.updated_at.isoformat() if payroll.updated_at else None
        }
    
    def _vacation_to_dict(self, vacation: EmployeeVacation) -> Dict[str, Any]:
        """Converte EmployeeVacation para dict"""
        return {
            "id": vacation.id,
            "employee_id": vacation.employee_id,
            "periodo_aquisitivo_inicio": vacation.periodo_aquisitivo_inicio.isoformat() if vacation.periodo_aquisitivo_inicio else None,
            "periodo_aquisitivo_fim": vacation.periodo_aquisitivo_fim.isoformat() if vacation.periodo_aquisitivo_fim else None,
            "data_inicio": vacation.data_inicio.isoformat() if vacation.data_inicio else None,
            "data_fim": vacation.data_fim.isoformat() if vacation.data_fim else None,
            "dias": vacation.dias,
            "status": vacation.status,
            "observacoes": vacation.observacoes,
            "created_at": vacation.created_at.isoformat() if vacation.created_at else None
        }
    
    def _benefit_to_dict(self, benefit: EmployeeBenefit) -> Dict[str, Any]:
        """Converte EmployeeBenefit para dict"""
        return {
            "id": benefit.id,
            "employee_id": benefit.employee_id,
            "tipo_beneficio": benefit.tipo_beneficio,
            "descricao": benefit.descricao,
            "valor": float(benefit.valor) if benefit.valor else None,
            "data_inicio": benefit.data_inicio.isoformat() if benefit.data_inicio else None,
            "data_fim": benefit.data_fim.isoformat() if benefit.data_fim else None,
            "status": benefit.status,
            "created_at": benefit.created_at.isoformat() if benefit.created_at else None
        }

