"""
Controller para Planejamento Financeiro
"""
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from datetime import datetime, date
from decimal import Decimal

from app.models.financial_planning_models import (
    FinancialPlanning, MonthlyPlanning, CostCenterPlanning, CategoryPlanning
)
from app.models.financial_models import CostCenter, FinancialCategory

logger = logging.getLogger(__name__)

class FinancialPlanningController:
    """Controller para planejamento financeiro"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_annual_planning(self, company_id: int, year: int, months_data: List[Dict] = None) -> Dict:
        """Cria planejamento anual"""
        try:
            # Verificar se já existe planejamento para o ano
            existing_planning = self.db.query(FinancialPlanning).filter(
                FinancialPlanning.company_id == company_id,
                FinancialPlanning.year == year
            ).first()
            
            if existing_planning:
                return {
                    "success": False,
                    "error": f"Já existe planejamento para o ano {year}"
                }
            
            # Criar planejamento anual
            planning = FinancialPlanning(
                company_id=company_id,
                year=year
            )
            self.db.add(planning)
            self.db.flush()  # Para obter o ID
            
            # Criar planejamento mensal para cada mês
            monthly_plans = []
            for month in range(1, 13):
                # Buscar dados do mês se fornecidos
                month_data = None
                if months_data:
                    month_data = next((m for m in months_data if m.get('month') == month), None)
                
                monthly_plan = MonthlyPlanning(
                    planning_id=planning.id,
                    month=month,
                    year=year,
                    expected_revenue=Decimal(str(month_data.get('expected_revenue', 0.00))) if month_data else Decimal('0.00'),
                    expected_margin_percent=Decimal(str(month_data.get('expected_margin_percent', 0.00))) if month_data else Decimal('0.00'),
                    expected_margin_value=Decimal(str(month_data.get('expected_margin_value', 0.00))) if month_data else Decimal('0.00')
                )
                self.db.add(monthly_plan)
                monthly_plans.append(monthly_plan)
            
            self.db.commit()
            
            return {
                "success": True,
                "planning_id": planning.id,
                "message": f"Planejamento para {year} criado com sucesso"
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar planejamento anual: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_annual_planning(self, company_id: int, year: int) -> Dict:
        """Busca planejamento anual"""
        try:
            planning = self.db.query(FinancialPlanning).filter(
                FinancialPlanning.company_id == company_id,
                FinancialPlanning.year == year
            ).first()
            
            if not planning:
                return {
                    "success": False,
                    "error": f"Nenhum planejamento encontrado para {year}"
                }
            
            # Buscar planejamentos mensais
            monthly_plans = self.db.query(MonthlyPlanning).filter(
                MonthlyPlanning.planning_id == planning.id
            ).order_by(MonthlyPlanning.month).all()
            
            # Buscar centros de custo da empresa
            cost_centers = self.db.query(CostCenter).filter(
                CostCenter.company_id == company_id
            ).all()
            
            # Buscar categorias da empresa
            categories = self.db.query(FinancialCategory).filter(
                FinancialCategory.company_id == company_id
            ).all()
            
            # Montar dados dos meses
            months_data = []
            for monthly_plan in monthly_plans:
                # Buscar planejamentos por centro de custo
                cost_center_plans = self.db.query(CostCenterPlanning).filter(
                    CostCenterPlanning.monthly_planning_id == monthly_plan.id
                ).all()
                
                month_data = {
                    "month": monthly_plan.month,
                    "year": monthly_plan.year,
                    "expected_revenue": float(monthly_plan.expected_revenue or 0),
                    "expected_margin_percent": float(monthly_plan.expected_margin_percent or 0),
                    "expected_margin_value": float(monthly_plan.expected_margin_value or 0),
                    "cost_centers": []
                }
                
                # Montar dados dos centros de custo (apenas os que têm planejamento)
                for cost_center_plan in cost_center_plans:
                    # Buscar planejamentos por categoria
                    category_plans = self.db.query(CategoryPlanning).filter(
                        CategoryPlanning.cost_center_planning_id == cost_center_plan.id
                    ).all()
                    
                    cost_center_data = {
                        "id": cost_center_plan.id,
                        "cost_center_id": cost_center_plan.cost_center_id,
                        "name": cost_center_plan.cost_center.name if cost_center_plan.cost_center else "N/A",
                        "max_spending": float(cost_center_plan.max_spending or 0),
                        "notes": cost_center_plan.notes or "",
                        "categories": []
                    }
                    
                    # Montar dados das categorias (apenas as que têm planejamento)
                    for category_plan in category_plans:
                        category_data = {
                            "id": category_plan.id,
                            "category_id": category_plan.category_id,
                            "name": category_plan.category.name if category_plan.category else "N/A",
                            "type": category_plan.category.type.value if category_plan.category and category_plan.category.type else "expense",
                            "max_spending": float(category_plan.max_spending or 0),
                            "notes": category_plan.notes or ""
                        }
                        
                        cost_center_data["categories"].append(category_data)
                    
                    month_data["cost_centers"].append(cost_center_data)
                
                months_data.append(month_data)
            
            return {
                "success": True,
                "planning": {
                    "id": planning.id,
                    "year": planning.year,
                    "months": months_data
                },
                "cost_centers": [{"id": cc.id, "name": cc.name} for cc in cost_centers],
                "categories": [{"id": cat.id, "name": cat.name} for cat in categories]
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar planejamento anual: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_monthly_planning(self, monthly_planning_id: int, data: Dict) -> Dict:
        """Atualiza planejamento mensal"""
        try:
            monthly_plan = self.db.query(MonthlyPlanning).filter(
                MonthlyPlanning.id == monthly_planning_id
            ).first()
            
            if not monthly_plan:
                return {
                    "success": False,
                    "error": "Planejamento mensal não encontrado"
                }
            
            # Atualizar dados do mês
            if "expected_revenue" in data:
                monthly_plan.expected_revenue = Decimal(str(data["expected_revenue"]))
            
            if "expected_margin_percent" in data:
                monthly_plan.expected_margin_percent = Decimal(str(data["expected_margin_percent"]))
            
            if "expected_margin_value" in data:
                monthly_plan.expected_margin_value = Decimal(str(data["expected_margin_value"]))
            
            self.db.commit()
            
            return {
                "success": True,
                "message": "Planejamento mensal atualizado com sucesso"
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar planejamento mensal: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_cost_center_planning(self, monthly_planning_id: int, cost_center_id: int, data: Dict) -> Dict:
        """Atualiza planejamento por centro de custo"""
        try:
            # Buscar ou criar planejamento do centro de custo
            cost_center_plan = self.db.query(CostCenterPlanning).filter(
                CostCenterPlanning.monthly_planning_id == monthly_planning_id,
                CostCenterPlanning.cost_center_id == cost_center_id
            ).first()
            
            if not cost_center_plan:
                cost_center_plan = CostCenterPlanning(
                    monthly_planning_id=monthly_planning_id,
                    cost_center_id=cost_center_id,
                    max_spending=Decimal(str(data.get("max_spending", 0))),
                    notes=data.get("notes", "")
                )
                self.db.add(cost_center_plan)
            else:
                cost_center_plan.max_spending = Decimal(str(data.get("max_spending", 0)))
                cost_center_plan.notes = data.get("notes", "")
            
            self.db.commit()
            
            return {
                "success": True,
                "message": "Planejamento do centro de custo atualizado com sucesso"
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar planejamento do centro de custo: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_category_planning(self, cost_center_planning_id: int, category_id: int, data: Dict) -> Dict:
        """Atualiza planejamento por categoria"""
        try:
            # Buscar ou criar planejamento da categoria
            category_plan = self.db.query(CategoryPlanning).filter(
                CategoryPlanning.cost_center_planning_id == cost_center_planning_id,
                CategoryPlanning.category_id == category_id
            ).first()
            
            if not category_plan:
                category_plan = CategoryPlanning(
                    cost_center_planning_id=cost_center_planning_id,
                    category_id=category_id,
                    max_spending=Decimal(str(data.get("max_spending", 0))),
                    notes=data.get("notes", "")
                )
                self.db.add(category_plan)
            else:
                category_plan.max_spending = Decimal(str(data.get("max_spending", 0)))
                category_plan.notes = data.get("notes", "")
            
            self.db.commit()
            
            return {
                "success": True,
                "message": "Planejamento da categoria atualizado com sucesso"
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar planejamento da categoria: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def clear_annual_planning(self, company_id: int, year: int) -> Dict:
        """Remove todos os planejamentos de um ano"""
        try:
            # Buscar planejamento anual
            planning = self.db.query(FinancialPlanning).filter(
                FinancialPlanning.company_id == company_id,
                FinancialPlanning.year == year
            ).first()
            
            if not planning:
                return {
                    "success": False,
                    "error": f"Nenhum planejamento encontrado para {year}"
                }
            
            # Remover planejamento (cascade remove todos os relacionados)
            self.db.delete(planning)
            self.db.commit()
            
            return {
                "success": True,
                "message": f"Planejamento de {year} removido com sucesso"
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao limpar planejamento anual: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def update_annual_planning(self, company_id: int, year: int, months_data: List[Dict]) -> Dict:
        """Atualiza planejamento financeiro anual"""
        try:
            # Buscar planejamento existente
            planning = self.db.query(FinancialPlanning).filter(
                FinancialPlanning.company_id == company_id,
                FinancialPlanning.year == year
            ).first()
            
            if not planning:
                return {
                    "success": False,
                    "error": f"Nenhum planejamento encontrado para o ano {year}"
                }
            
            # Atualizar dados dos meses
            for month_data in months_data:
                month = month_data.get('month')
                if not month:
                    continue
                
                # Buscar planejamento mensal
                monthly_plan = self.db.query(MonthlyPlanning).filter(
                    MonthlyPlanning.planning_id == planning.id,
                    MonthlyPlanning.month == month
                ).first()
                
                if monthly_plan:
                    # Atualizar dados básicos
                    monthly_plan.expected_revenue = Decimal(str(month_data.get('expected_revenue', 0.00)))
                    monthly_plan.expected_margin_percent = Decimal(str(month_data.get('expected_margin_percent', 0.00)))
                    monthly_plan.expected_margin_value = Decimal(str(month_data.get('expected_margin_value', 0.00)))
                    
                    # Processar centros de custo
                    cost_centers_data = month_data.get('cost_centers', [])
                    
                    # Remover centros de custo existentes
                    existing_cost_centers = self.db.query(CostCenterPlanning).filter(
                        CostCenterPlanning.monthly_planning_id == monthly_plan.id
                    ).all()
                    
                    for existing_cc in existing_cost_centers:
                        self.db.delete(existing_cc)
                    
                    # Adicionar novos centros de custo
                    for cost_center_data in cost_centers_data:
                        cost_center_plan = CostCenterPlanning(
                            monthly_planning_id=monthly_plan.id,
                            cost_center_id=cost_center_data.get('cost_center_id'),
                            max_spending=Decimal(str(cost_center_data.get('max_spending', 0.00))),
                            notes=cost_center_data.get('notes', '')
                        )
                        self.db.add(cost_center_plan)
                        self.db.flush()  # Para obter o ID
                        
                        # Processar categorias
                        categories_data = cost_center_data.get('categories', [])
                        for category_data in categories_data:
                            category_plan = CategoryPlanning(
                                cost_center_planning_id=cost_center_plan.id,
                                category_id=category_data.get('category_id'),
                                max_spending=Decimal(str(category_data.get('max_spending', 0.00))),
                                notes=category_data.get('notes', '')
                            )
                            self.db.add(category_plan)
            
            self.db.commit()
            
            return {
                "success": True,
                "message": f"Planejamento de {year} atualizado com sucesso"
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar planejamento anual: {e}")
            return {
                "success": False,
                "error": str(e)
            }
