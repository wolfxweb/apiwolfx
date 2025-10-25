"""
Controller para gerenciar custos de marketing (Product Ads)
do Mercado Livre.

Este controller fornece endpoints para:
1. Sincronizar custos de marketing da Billing API
2. Visualizar resumos de custos por período
3. Gerenciar distribuição de custos por pedidos
4. Gerar relatórios de marketing
"""
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.services.marketing_costs_service import MarketingCostsService

logger = logging.getLogger(__name__)

class MarketingCostsController:
    """Controller para gerenciar custos de marketing"""
    
    def __init__(self, db: Session):
        self.db = db
        self.marketing_service = MarketingCostsService(db)
    
    def sync_marketing_costs(self, company_id: int, months: int = 3) -> Dict:
        """
        Sincroniza custos de marketing para uma empresa
        
        Args:
            company_id: ID da empresa
            months: Número de meses para sincronizar (padrão: 3)
            
        Returns:
            Resultado da sincronização
        """
        try:
            logger.info(f"🔄 Iniciando sincronização de custos de marketing para empresa {company_id}")
            
            result = self.marketing_service.sync_marketing_costs_for_company(company_id, months)
            
            if result["success"]:
                logger.info(f"✅ Sincronização concluída: R$ {result['total_cost']:.2f} em {result['orders_updated']} pedidos")
            else:
                logger.error(f"❌ Erro na sincronização: {result.get('error', 'Erro desconhecido')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro no controller de marketing: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_cost": 0,
                "orders_updated": 0
            }
    
    def get_marketing_summary(self, company_id: int, months: int = 3) -> Dict:
        """
        Busca resumo de custos de marketing
        
        Args:
            company_id: ID da empresa
            months: Número de meses para analisar
            
        Returns:
            Resumo de custos de marketing
        """
        try:
            logger.info(f"📊 Buscando resumo de marketing para empresa {company_id} ({months} meses)")
            
            summary = self.marketing_service.get_marketing_summary(company_id, months)
            
            # Adicionar métricas calculadas
            summary["success"] = True
            summary["company_id"] = company_id
            
            # Calcular métricas adicionais
            if summary["total_orders"] > 0:
                summary["cost_per_order"] = summary["total_cost"] / summary["total_orders"]
            else:
                summary["cost_per_order"] = 0
            
            # Calcular tendência (comparar últimos 2 meses)
            monthly_breakdown = summary.get("monthly_breakdown", {})
            if len(monthly_breakdown) >= 2:
                months_list = sorted(monthly_breakdown.keys())
                last_month = monthly_breakdown[months_list[-1]]["cost"]
                prev_month = monthly_breakdown[months_list[-2]]["cost"]
                
                if prev_month > 0:
                    summary["trend_percentage"] = ((last_month - prev_month) / prev_month) * 100
                else:
                    summary["trend_percentage"] = 0
            else:
                summary["trend_percentage"] = 0
            
            logger.info(f"✅ Resumo encontrado: R$ {summary['total_cost']:.2f} em {summary['total_orders']} pedidos")
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar resumo de marketing: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_cost": 0,
                "total_orders": 0,
                "monthly_breakdown": {}
            }
    
    def get_marketing_by_period(self, company_id: int, date_from: str, date_to: str) -> Dict:
        """
        Busca custos de marketing de um período específico
        
        Args:
            company_id: ID da empresa
            date_from: Data inicial (YYYY-MM-DD)
            date_to: Data final (YYYY-MM-DD)
            
        Returns:
            Custos de marketing do período
        """
        try:
            from datetime import datetime
            from sqlalchemy import and_
            from app.models.saas_models import MLOrder, MLAccount
            
            logger.info(f"📅 Buscando custos de marketing para período {date_from} a {date_to}")
            
            # Converter datas
            start_date = datetime.strptime(date_from, "%Y-%m-%d")
            end_date = datetime.strptime(date_to, "%Y-%m-%d")
            
            # Buscar pedidos com custos de marketing no período
            orders = self.db.query(MLOrder).filter(
                and_(
                    MLOrder.ml_account_id.in_(
                        self.db.query(MLAccount.id).filter(
                            MLAccount.company_id == company_id
                        )
                    ),
                    MLOrder.date_created >= start_date,
                    MLOrder.date_created <= end_date,
                    MLOrder.is_advertising_sale == True
                )
            ).all()
            
            # Calcular totais
            total_cost = sum(float(order.advertising_cost or 0) for order in orders)
            total_orders = len(orders)
            
            # Agrupar por conta ML
            accounts_breakdown = {}
            for order in orders:
                account_id = order.ml_account_id
                if account_id not in accounts_breakdown:
                    accounts_breakdown[account_id] = {
                        "account_id": account_id,
                        "total_cost": 0,
                        "orders_count": 0
                    }
                accounts_breakdown[account_id]["total_cost"] += float(order.advertising_cost or 0)
                accounts_breakdown[account_id]["orders_count"] += 1
            
            # Agrupar por dia
            daily_breakdown = {}
            for order in orders:
                day_key = order.date_created.strftime("%Y-%m-%d")
                if day_key not in daily_breakdown:
                    daily_breakdown[day_key] = {"cost": 0, "orders": 0}
                daily_breakdown[day_key]["cost"] += float(order.advertising_cost or 0)
                daily_breakdown[day_key]["orders"] += 1
            
            return {
                "success": True,
                "period": {
                    "date_from": date_from,
                    "date_to": date_to
                },
                "total_cost": total_cost,
                "total_orders": total_orders,
                "average_cost_per_order": total_cost / total_orders if total_orders > 0 else 0,
                "accounts_breakdown": list(accounts_breakdown.values()),
                "daily_breakdown": daily_breakdown
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar custos por período: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_cost": 0,
                "total_orders": 0
            }
    
    def get_marketing_by_account(self, company_id: int, ml_account_id: int, months: int = 3) -> Dict:
        """
        Busca custos de marketing de uma conta ML específica
        
        Args:
            company_id: ID da empresa
            ml_account_id: ID da conta ML
            months: Número de meses para analisar
            
        Returns:
            Custos de marketing da conta
        """
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import and_
            from app.models.saas_models import MLOrder, MLAccount
            
            logger.info(f"🏪 Buscando custos de marketing para conta {ml_account_id}")
            
            # Verificar se a conta pertence à empresa
            account = self.db.query(MLAccount).filter(
                MLAccount.id == ml_account_id,
                MLAccount.company_id == company_id
            ).first()
            
            if not account:
                return {
                    "success": False,
                    "error": "Conta não encontrada ou não pertence à empresa"
                }
            
            # Buscar pedidos com custos de marketing
            from_date = datetime.now() - timedelta(days=months * 30)
            
            orders = self.db.query(MLOrder).filter(
                and_(
                    MLOrder.ml_account_id == ml_account_id,
                    MLOrder.date_created >= from_date,
                    MLOrder.is_advertising_sale == True
                )
            ).all()
            
            # Calcular totais
            total_cost = sum(float(order.advertising_cost or 0) for order in orders)
            total_orders = len(orders)
            
            # Agrupar por mês
            monthly_breakdown = {}
            for order in orders:
                month_key = order.date_created.strftime("%Y-%m")
                if month_key not in monthly_breakdown:
                    monthly_breakdown[month_key] = {"cost": 0, "orders": 0}
                monthly_breakdown[month_key]["cost"] += float(order.advertising_cost or 0)
                monthly_breakdown[month_key]["orders"] += 1
            
            return {
                "success": True,
                "account": {
                    "id": account.id,
                    "nickname": account.nickname,
                    "email": account.email
                },
                "total_cost": total_cost,
                "total_orders": total_orders,
                "average_cost_per_order": total_cost / total_orders if total_orders > 0 else 0,
                "monthly_breakdown": monthly_breakdown,
                "period_months": months
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar custos da conta: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_cost": 0,
                "total_orders": 0
            }
    
    def get_marketing_metrics(self, company_id: int, months: int = 3) -> Dict:
        """
        Busca métricas de marketing para dashboards
        
        Args:
            company_id: ID da empresa
            months: Número de meses para analisar
            
        Returns:
            Métricas de marketing
        """
        try:
            logger.info(f"📈 Buscando métricas de marketing para empresa {company_id}")
            
            # Buscar resumo geral
            summary = self.marketing_service.get_marketing_summary(company_id, months)
            
            if not summary or summary.get("total_cost", 0) == 0:
                return {
                    "success": True,
                    "metrics": {
                        "total_cost": 0,
                        "total_orders": 0,
                        "average_cost_per_order": 0,
                        "cost_trend": 0,
                        "top_performing_months": [],
                        "monthly_breakdown": {}
                    }
                }
            
            # Calcular métricas adicionais
            monthly_breakdown = summary.get("monthly_breakdown", {})
            
            # Encontrar meses com melhor performance (menor custo por pedido)
            monthly_efficiency = []
            for month, data in monthly_breakdown.items():
                if data["orders"] > 0:
                    efficiency = data["cost"] / data["orders"]
                    monthly_efficiency.append({
                        "month": month,
                        "cost": data["cost"],
                        "orders": data["orders"],
                        "efficiency": efficiency
                    })
            
            # Ordenar por eficiência (menor custo por pedido = melhor)
            monthly_efficiency.sort(key=lambda x: x["efficiency"])
            
            # Calcular tendência
            if len(monthly_efficiency) >= 2:
                latest = monthly_efficiency[-1]["efficiency"]
                previous = monthly_efficiency[-2]["efficiency"]
                cost_trend = ((latest - previous) / previous * 100) if previous > 0 else 0
            else:
                cost_trend = 0
            
            return {
                "success": True,
                "metrics": {
                    "total_cost": summary["total_cost"],
                    "total_orders": summary["total_orders"],
                    "average_cost_per_order": summary["average_cost_per_order"],
                    "cost_trend": cost_trend,
                    "top_performing_months": monthly_efficiency[:3],  # Top 3 meses
                    "monthly_breakdown": monthly_breakdown
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar métricas de marketing: {e}")
            return {
                "success": False,
                "error": str(e),
                "metrics": {}
            }
