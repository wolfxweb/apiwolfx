"""
Controller para o módulo financeiro SaaS
Gerencia a lógica de negócio das operações financeiras
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging

from app.services.financial_service import FinancialService

logger = logging.getLogger(__name__)

class FinancialController:
    """Controller para operações financeiras"""
    
    def __init__(self):
        pass
    
    # =====================================================
    # CONTAS BANCÁRIAS E CAIXAS
    # =====================================================
    
    def create_financial_account(self, company_id: int, account_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Cria uma nova conta bancária/caixa"""
        try:
            service = FinancialService(db)
            result = service.create_financial_account(company_id, account_data)
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erro no controller ao criar conta: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def get_financial_accounts(self, company_id: int, active_only: bool = True, db: Session = None) -> List[Dict[str, Any]]:
        """Lista contas financeiras da empresa"""
        try:
            service = FinancialService(db)
            return service.get_financial_accounts(company_id, active_only)
            
        except Exception as e:
            logger.error(f"❌ Erro no controller ao listar contas: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def update_account_balance(self, account_id: int, company_id: int, new_balance: float, db: Session) -> Dict[str, Any]:
        """Atualiza saldo de uma conta"""
        try:
            service = FinancialService(db)
            result = service.update_account_balance(account_id, company_id, new_balance)
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erro no controller ao atualizar saldo: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    # =====================================================
    # CENTROS DE CUSTO
    # =====================================================
    
    def create_cost_center(self, company_id: int, cost_center_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Cria um novo centro de custo"""
        try:
            service = FinancialService(db)
            result = service.create_cost_center(company_id, cost_center_data)
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erro no controller ao criar centro de custo: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def get_cost_centers(self, company_id: int, active_only: bool = True, db: Session = None) -> List[Dict[str, Any]]:
        """Lista centros de custo da empresa"""
        try:
            service = FinancialService(db)
            return service.get_cost_centers(company_id, active_only)
            
        except Exception as e:
            logger.error(f"❌ Erro no controller ao listar centros de custo: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    # =====================================================
    # CATEGORIAS FINANCEIRAS
    # =====================================================
    
    def create_financial_category(self, company_id: int, category_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Cria uma nova categoria financeira"""
        try:
            service = FinancialService(db)
            result = service.create_financial_category(company_id, category_data)
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erro no controller ao criar categoria: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def get_financial_categories(self, company_id: int, category_type: Optional[str] = None, active_only: bool = True, db: Session = None) -> List[Dict[str, Any]]:
        """Lista categorias financeiras da empresa"""
        try:
            service = FinancialService(db)
            return service.get_financial_categories(company_id, category_type, active_only)
            
        except Exception as e:
            logger.error(f"❌ Erro no controller ao listar categorias: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def update_financial_category(self, company_id: int, category_id: int, category_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Atualiza uma categoria financeira"""
        try:
            service = FinancialService(db)
            result = service.update_financial_category(company_id, category_id, category_data)
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erro no controller ao atualizar categoria: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def delete_financial_category(self, company_id: int, category_id: int, db: Session) -> Dict[str, Any]:
        """Exclui uma categoria financeira"""
        try:
            service = FinancialService(db)
            result = service.delete_financial_category(company_id, category_id)
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erro no controller ao excluir categoria: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    # =====================================================
    # CENTROS DE CUSTO
    # =====================================================
    
    def create_cost_center(self, company_id: int, cost_center_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Cria um novo centro de custo"""
        try:
            service = FinancialService(db)
            result = service.create_cost_center(company_id, cost_center_data)
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erro no controller ao criar centro de custo: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def update_cost_center(self, company_id: int, cost_center_id: int, cost_center_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Atualiza um centro de custo"""
        try:
            service = FinancialService(db)
            result = service.update_cost_center(company_id, cost_center_id, cost_center_data)
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erro no controller ao atualizar centro de custo: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def delete_cost_center(self, company_id: int, cost_center_id: int, db: Session) -> Dict[str, Any]:
        """Exclui um centro de custo"""
        try:
            service = FinancialService(db)
            result = service.delete_cost_center(company_id, cost_center_id)
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erro no controller ao excluir centro de custo: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    # =====================================================
    # FORMAS DE PAGAMENTO
    # =====================================================
    
    def create_payment_method(self, company_id: int, payment_method_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Cria uma nova forma de pagamento"""
        try:
            service = FinancialService(db)
            result = service.create_payment_method(company_id, payment_method_data)
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erro no controller ao criar forma de pagamento: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def get_payment_methods(self, company_id: int, active_only: bool = True, db: Session = None) -> List[Dict[str, Any]]:
        """Lista formas de pagamento da empresa"""
        try:
            service = FinancialService(db)
            return service.get_payment_methods(company_id, active_only)
            
        except Exception as e:
            logger.error(f"❌ Erro no controller ao listar formas de pagamento: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    # =====================================================
    # CLIENTES E FORNECEDORES
    # =====================================================
    
    def create_financial_customer(self, company_id: int, customer_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Cria um novo cliente financeiro"""
        try:
            service = FinancialService(db)
            result = service.create_financial_customer(company_id, customer_data)
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erro no controller ao criar cliente: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def create_financial_supplier(self, company_id: int, supplier_data: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Cria um novo fornecedor financeiro"""
        try:
            service = FinancialService(db)
            result = service.create_financial_supplier(company_id, supplier_data)
            
            if not result["success"]:
                raise HTTPException(status_code=400, detail=result["message"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Erro no controller ao criar fornecedor: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def get_financial_customers(self, company_id: int, active_only: bool = True, db: Session = None) -> List[Dict[str, Any]]:
        """Lista clientes financeiros da empresa"""
        try:
            service = FinancialService(db)
            return service.get_financial_customers(company_id, active_only)
            
        except Exception as e:
            logger.error(f"❌ Erro no controller ao listar clientes: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    def get_financial_suppliers(self, company_id: int, active_only: bool = True, db: Session = None) -> List[Dict[str, Any]]:
        """Lista fornecedores financeiros da empresa"""
        try:
            service = FinancialService(db)
            return service.get_financial_suppliers(company_id, active_only)
            
        except Exception as e:
            logger.error(f"❌ Erro no controller ao listar fornecedores: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    # =====================================================
    # DASHBOARD FINANCEIRO
    # =====================================================
    
    def get_financial_dashboard_data(self, company_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None, db: Session = None) -> Dict[str, Any]:
        """Obtém dados para o dashboard financeiro"""
        try:
            from datetime import datetime
            
            # Converter strings de data se fornecidas
            start_date_obj = None
            end_date_obj = None
            
            if start_date:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            if end_date:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
            
            service = FinancialService(db)
            return service.get_financial_dashboard_data(company_id, start_date_obj, end_date_obj)
            
        except Exception as e:
            logger.error(f"❌ Erro no controller ao obter dashboard: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    # =====================================================
    # CONFIGURAÇÃO INICIAL
    # =====================================================
    
    def create_default_financial_setup(self, company_id: int, db: Session) -> Dict[str, Any]:
        """Cria configuração financeira padrão para uma nova empresa"""
        try:
            service = FinancialService(db)
            return service.create_default_financial_setup(company_id)
            
        except Exception as e:
            logger.error(f"❌ Erro no controller ao criar configuração padrão: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
