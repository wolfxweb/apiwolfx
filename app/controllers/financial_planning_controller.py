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

    def get_planning_analysis(self, company_id: int, year: int, month: Optional[str] = None, metric: str = "revenue") -> Dict:
        """Análise de evolução: Planejamento vs Real"""
        try:
            # Buscar planejamento do ano
            planning = self.db.query(FinancialPlanning).filter(
                FinancialPlanning.company_id == company_id,
                FinancialPlanning.year == year
            ).first()
            
            if not planning:
                return {
                    "success": False,
                    "error": f"Nenhum planejamento encontrado para {year}"
                }
            
            # Buscar dados reais do período
            real_data = self._get_real_financial_data(company_id, year, month, metric)
            
            # Buscar dados planejados
            planned_data = self._get_planned_financial_data(planning.id, month, metric)
            
            # Comparar e gerar análise
            analysis = self._compare_planning_vs_real(planned_data, real_data, metric)
            
            return {
                "success": True,
                "data": analysis
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar análise de planejamento: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_real_financial_data(self, company_id: int, year: int, month: Optional[str], metric: str) -> Dict:
        """Busca dados financeiros reais"""
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import and_, extract
            
            # Definir período
            if month:
                start_date = datetime(year, int(month), 1)
                if int(month) == 12:
                    end_date = datetime(year + 1, 1, 1)
                else:
                    end_date = datetime(year, int(month) + 1, 1)
            else:
                start_date = datetime(year, 1, 1)
                end_date = datetime(year + 1, 1, 1)
            
            real_data = {}
            
            if metric == "revenue":
                # Buscar receitas reais separadas: Mercado Livre e Contas a Receber
                from app.models.saas_models import MLOrder
                from app.models.financial_models import AccountReceivable
                
                logger.info(f"🔍 DEBUG - Buscando dados reais para company_id={company_id}, período={start_date} a {end_date}")
                logger.info(f"🔍 DEBUG - Tipo do company_id: {type(company_id)}, Valor: {company_id}")
                
                # 1. Mercado Livre - Pedidos pagos/confirmados
                from app.models.saas_models import OrderStatus
                orders = self.db.query(MLOrder).filter(
                    and_(
                        MLOrder.company_id == company_id,
                        MLOrder.date_created >= start_date,
                        MLOrder.date_created < end_date,
                        MLOrder.status.in_([OrderStatus.PAID, OrderStatus.PENDING])
                    )
                ).all()
                
                logger.info(f"🔍 DEBUG - Encontrados {len(orders)} pedidos ML")
                for order in orders[:3]:  # Log dos primeiros 3 pedidos
                    logger.info(f"🔍 DEBUG - Pedido ML: {order.id}, status={order.status}, amount={order.total_amount}, date={order.date_created}")
                
                # 2. Contas a Receber - Receivables
                receivables = self.db.query(AccountReceivable).filter(
                    and_(
                        AccountReceivable.company_id == company_id,
                        AccountReceivable.due_date >= start_date,
                        AccountReceivable.due_date < end_date,
                        AccountReceivable.status.in_(['pending', 'paid'])
                    )
                ).all()
                
                logger.info(f"🔍 DEBUG - Encontradas {len(receivables)} contas a receber")
                for receivable in receivables[:3]:  # Log das primeiras 3 contas
                    logger.info(f"🔍 DEBUG - Conta a receber: {receivable.id}, status={receivable.status}, amount={receivable.amount}, date={receivable.due_date}")
                
                # Agrupar por mês - Mercado Livre
                ml_data = {}
                for order in orders:
                    order_month = order.date_created.strftime('%m/%Y')
                    if order_month not in ml_data:
                        ml_data[order_month] = 0.0
                    ml_data[order_month] += float(order.total_amount or 0)
                
                # Agrupar por mês - Contas a Receber
                receivables_data = {}
                for receivable in receivables:
                    receivable_month = receivable.due_date.strftime('%m/%Y')
                    if receivable_month not in receivables_data:
                        receivables_data[receivable_month] = 0.0
                    receivables_data[receivable_month] += float(receivable.amount or 0)
                
                logger.info(f"🔍 DEBUG - ML data: {ml_data}")
                logger.info(f"🔍 DEBUG - Receivables data: {receivables_data}")
                
                # Retornar dados separados
                real_data = {
                    'ml': ml_data,
                    'receivables': receivables_data
                }
                
            elif metric == "expenses":
                # Buscar despesas reais
                from app.models.database_models import FinancialTransaction
                
                expenses = self.db.query(FinancialTransaction).filter(
                    and_(
                        FinancialTransaction.company_id == company_id,
                        FinancialTransaction.date >= start_date,
                        FinancialTransaction.date < end_date,
                        FinancialTransaction.type == 'expense'
                    )
                ).all()
                
                # Agrupar por mês
                monthly_data = {}
                for expense in expenses:
                    expense_month = expense.date.strftime('%m/%Y')
                    if expense_month not in monthly_data:
                        monthly_data[expense_month] = 0.0
                    monthly_data[expense_month] += float(expense.amount or 0)
                
                real_data = monthly_data
                
            elif metric == "profit":
                # Calcular resultado (receitas - despesas)
                revenue_data = self._get_real_financial_data(company_id, year, month, "revenue")
                expense_data = self._get_real_financial_data(company_id, year, month, "expenses")
                
                # Combinar dados
                all_months = set(revenue_data.keys()) | set(expense_data.keys())
                real_data = {}
                for month_key in all_months:
                    revenue = revenue_data.get(month_key, 0.0)
                    expense = expense_data.get(month_key, 0.0)
                    real_data[month_key] = revenue - expense
            
            return real_data
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados reais: {e}")
            return {}
    
    def _get_planned_financial_data(self, planning_id: int, month: Optional[str], metric: str) -> Dict:
        """Busca dados planejados"""
        try:
            from app.models.financial_planning_models import MonthlyPlanning, CostCenterPlanning, CategoryPlanning
            
            # Buscar planejamento mensal
            query = self.db.query(MonthlyPlanning).filter(
                MonthlyPlanning.planning_id == planning_id
            )
            
            if month:
                query = query.filter(MonthlyPlanning.month == int(month))
            
            monthly_plans = query.all()
            
            planned_data = {}
            
            for monthly_plan in monthly_plans:
                month_key = f"{monthly_plan.month:02d}/{monthly_plan.year}"
                
                if metric == "revenue":
                    planned_data[month_key] = float(monthly_plan.expected_revenue or 0)
                    
                elif metric == "expenses":
                    # Somar gastos planejados dos centros de custo
                    cost_centers = self.db.query(CostCenterPlanning).filter(
                        CostCenterPlanning.monthly_planning_id == monthly_plan.id
                    ).all()
                    
                    total_expenses = 0.0
                    for cost_center in cost_centers:
                        # Somar apenas categorias do tipo "expense"
                        categories = self.db.query(CategoryPlanning).filter(
                            CategoryPlanning.cost_center_planning_id == cost_center.id
                        ).all()
                        
                        for category in categories:
                            # Verificar se a categoria é do tipo "expense"
                            if category.category and category.category.type.value == 'expense':
                                total_expenses += float(category.max_spending or 0)
                    
                    planned_data[month_key] = total_expenses
                    
                elif metric == "profit":
                    # Resultado planejado = receita - despesas
                    revenue = float(monthly_plan.expected_revenue or 0)
                    expenses = 0.0
                    
                    # Calcular despesas planejadas
                    cost_centers = self.db.query(CostCenterPlanning).filter(
                        CostCenterPlanning.monthly_planning_id == monthly_plan.id
                    ).all()
                    
                    for cost_center in cost_centers:
                        categories = self.db.query(CategoryPlanning).filter(
                            CategoryPlanning.cost_center_planning_id == cost_center.id
                        ).all()
                        
                        for category in categories:
                            if category.category and category.category.type.value == 'expense':
                                expenses += float(category.max_spending or 0)
                    
                    planned_data[month_key] = revenue - expenses
            
            return planned_data
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados planejados: {e}")
            return {}
    
    def _compare_planning_vs_real(self, planned_data: Dict, real_data: Dict, metric: str) -> Dict:
        """Compara dados planejados vs reais"""
        try:
            if metric == "revenue" and isinstance(real_data, dict) and 'ml' in real_data:
                # Para receitas, temos dados separados (ML + Receivables)
                return self._compare_revenue_detailed(planned_data, real_data)
            else:
                # Para outras métricas, usar lógica original
                return self._compare_standard(planned_data, real_data)
            
        except Exception as e:
            logger.error(f"Erro ao comparar dados: {e}")
            return {
                "summary": {"total_planned": 0, "total_real": 0, "difference": 0, "percentage_achieved": 0},
                "chart": {"labels": [], "planned": [], "ml": [], "receivables": []},
                "table": []
            }
    
    def _compare_revenue_detailed(self, planned_data: Dict, real_data: Dict) -> Dict:
        """Compara receitas com dados detalhados (ML + Receivables)"""
        try:
            ml_data = real_data.get('ml', {})
            receivables_data = real_data.get('receivables', {})
            
            # Combinar todos os meses
            all_months = set(planned_data.keys()) | set(ml_data.keys()) | set(receivables_data.keys())
            all_months = sorted(all_months)
            
            # Preparar dados para comparação
            comparison_data = []
            chart_data = {
                "labels": [],
                "planned": [],
                "ml": [],
                "receivables": []
            }
            
            total_planned = 0.0
            total_ml = 0.0
            total_receivables = 0.0
            
            for month_key in all_months:
                planned_value = planned_data.get(month_key, 0.0)
                ml_value = ml_data.get(month_key, 0.0)
                receivables_value = receivables_data.get(month_key, 0.0)
                total_real = ml_value + receivables_value
                
                difference = total_real - planned_value
                percentage_achieved = (total_real / planned_value * 100) if planned_value > 0 else 0.0
                
                comparison_data.append({
                    "month": month_key,
                    "planned": planned_value,
                    "ml": ml_value,
                    "receivables": receivables_value,
                    "total_real": total_real,
                    "difference": difference,
                    "percentage_achieved": percentage_achieved
                })
                
                chart_data["labels"].append(month_key)
                chart_data["planned"].append(planned_value)
                chart_data["ml"].append(ml_value)
                chart_data["receivables"].append(receivables_value)
                
                total_planned += planned_value
                total_ml += ml_value
                total_receivables += receivables_value
            
            # Calcular resumo
            total_real = total_ml + total_receivables
            total_difference = total_real - total_planned
            total_percentage_achieved = (total_real / total_planned * 100) if total_planned > 0 else 0.0
            
            summary = {
                "total_planned": total_planned,
                "total_ml": total_ml,
                "total_receivables": total_receivables,
                "total_real": total_real,
                "difference": total_difference,
                "percentage_achieved": total_percentage_achieved
            }
            
            return {
                "summary": summary,
                "chart": chart_data,
                "table": comparison_data
            }
            
        except Exception as e:
            logger.error(f"Erro ao comparar receitas detalhadas: {e}")
            return {
                "summary": {"total_planned": 0, "total_ml": 0, "total_receivables": 0, "total_real": 0, "difference": 0, "percentage_achieved": 0},
                "chart": {"labels": [], "planned": [], "ml": [], "receivables": []},
                "table": []
            }
    
    def _compare_standard(self, planned_data: Dict, real_data: Dict) -> Dict:
        """Comparação padrão para outras métricas"""
        try:
            # Combinar todos os meses
            all_months = set(planned_data.keys()) | set(real_data.keys())
            all_months = sorted(all_months)
            
            # Preparar dados para comparação
            comparison_data = []
            chart_data = {
                "labels": [],
                "planned": [],
                "real": []
            }
            
            total_planned = 0.0
            total_real = 0.0
            
            for month_key in all_months:
                planned_value = planned_data.get(month_key, 0.0)
                real_value = real_data.get(month_key, 0.0)
                difference = real_value - planned_value
                percentage_achieved = (real_value / planned_value * 100) if planned_value > 0 else 0.0
                
                comparison_data.append({
                    "month": month_key,
                    "planned": planned_value,
                    "real": real_value,
                    "difference": difference,
                    "percentage_achieved": percentage_achieved
                })
                
                chart_data["labels"].append(month_key)
                chart_data["planned"].append(planned_value)
                chart_data["real"].append(real_value)
                
                total_planned += planned_value
                total_real += real_value
            
            # Calcular resumo
            total_difference = total_real - total_planned
            total_percentage_achieved = (total_real / total_planned * 100) if total_planned > 0 else 0.0
            
            summary = {
                "total_planned": total_planned,
                "total_real": total_real,
                "difference": total_difference,
                "percentage_achieved": total_percentage_achieved
            }
            
            return {
                "summary": summary,
                "chart": chart_data,
                "table": comparison_data
            }
            
        except Exception as e:
            logger.error(f"Erro ao comparar dados: {e}")
            return {
                "summary": {"total_planned": 0, "total_real": 0, "difference": 0, "percentage_achieved": 0},
                "chart": {"labels": [], "planned": [], "real": []},
                "table": []
            }
