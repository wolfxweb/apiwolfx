"""
Serviço para calcular projeções de estoque e recomendações
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, cast, String
from sqlalchemy.sql import extract
from decimal import Decimal
from datetime import datetime, timedelta
from app.models.saas_models import (
    StockProjection, ProductStock, StockMovement, StockMovementType,
    InternalProduct, Warehouse
)

logger = logging.getLogger(__name__)


class StockProjectionService:
    """Serviço para calcular projeções de estoque"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_turnover(
        self,
        company_id: int,
        internal_product_id: int,
        warehouse_id: Optional[int] = None,
        period_days: int = 30
    ) -> float:
        """Calcula rotatividade de estoque (turnover rate)"""
        try:
            date_from = datetime.utcnow() - timedelta(days=period_days)
            
            # Buscar estoque atual
            query = self.db.query(ProductStock).filter(
                and_(
                    ProductStock.company_id == company_id,
                    ProductStock.internal_product_id == internal_product_id
                )
            )
            
            if warehouse_id:
                query = query.filter(ProductStock.warehouse_id == warehouse_id)
            
            stocks = query.all()
            
            if not stocks:
                return 0.0
            
            # Calcular estoque médio no período
            # Buscar movimentações para calcular estoque médio
            total_quantity = sum(float(s.quantity) for s in stocks)
            
            # Buscar vendas no período
            product_stock_ids = [s.id for s in stocks]
            
            sales_query = self.db.query(
                func.sum(func.abs(StockMovement.quantity))
            ).filter(
                and_(
                    StockMovement.company_id == company_id,
                    StockMovement.product_stock_id.in_(product_stock_ids),
                    cast(StockMovement.movement_type, String) == "sale",  # StockMovementType.SALE.value
                    StockMovement.created_at >= date_from
                )
            )
            
            total_sales = sales_query.scalar() or 0.0
            
            # Calcular estoque médio (simplificado: média entre início e fim do período)
            # Em produção, seria melhor calcular média diária
            average_stock = total_quantity / 2 if total_quantity > 0 else 1.0
            
            # Rotatividade = Vendas no período / Estoque médio
            turnover_rate = float(total_sales) / average_stock if average_stock > 0 else 0.0
            
            return turnover_rate
            
        except Exception as e:
            logger.error(f"❌ Erro ao calcular rotatividade: {str(e)}")
            return 0.0
    
    def calculate_average_daily_sales(
        self,
        company_id: int,
        internal_product_id: Optional[int] = None,
        ml_item_id: Optional[str] = None,
        warehouse_id: Optional[int] = None,
        period_days: int = 30
    ) -> float:
        """Calcula média de vendas diárias"""
        try:
            date_from = datetime.utcnow() - timedelta(days=period_days)
            
            # Buscar product_stocks
            query = self.db.query(ProductStock).filter(
                ProductStock.company_id == company_id
            )
            
            if internal_product_id:
                query = query.filter(ProductStock.internal_product_id == internal_product_id)
            if ml_item_id:
                query = query.filter(ProductStock.ml_item_id == ml_item_id)
            if warehouse_id:
                query = query.filter(ProductStock.warehouse_id == warehouse_id)
            
            product_stocks = query.all()
            
            if not product_stocks:
                return 0.0
            
            product_stock_ids = [ps.id for ps in product_stocks]
            
            # Buscar total de vendas no período
            sales_query = self.db.query(
                func.sum(func.abs(StockMovement.quantity))
            ).filter(
                and_(
                    StockMovement.company_id == company_id,
                    StockMovement.product_stock_id.in_(product_stock_ids),
                    cast(StockMovement.movement_type, String) == "sale",  # StockMovementType.SALE.value
                    StockMovement.created_at >= date_from
                )
            )
            
            total_sales = sales_query.scalar() or 0.0
            
            # Média diária
            average_daily = float(total_sales) / period_days if period_days > 0 else 0.0
            
            return average_daily
            
        except Exception as e:
            logger.error(f"❌ Erro ao calcular média de vendas diárias: {str(e)}")
            return 0.0
    
    def project_stockout(
        self,
        company_id: int,
        internal_product_id: int,
        warehouse_id: Optional[int] = None,
        period_days: int = 30
    ) -> Optional[datetime]:
        """Projeta data de esgotamento de estoque"""
        try:
            # Obter estoque atual
            query = self.db.query(ProductStock).filter(
                and_(
                    ProductStock.company_id == company_id,
                    ProductStock.internal_product_id == internal_product_id
                )
            )
            
            if warehouse_id:
                query = query.filter(ProductStock.warehouse_id == warehouse_id)
            
            stocks = query.all()
            
            if not stocks:
                return None
            
            total_stock = sum(float(s.quantity - s.reserved_quantity) for s in stocks)
            
            if total_stock <= 0:
                return datetime.utcnow()  # Já está esgotado
            
            # Calcular média diária de vendas
            avg_daily_sales = self.calculate_average_daily_sales(
                company_id=company_id,
                internal_product_id=internal_product_id,
                warehouse_id=warehouse_id,
                period_days=period_days
            )
            
            if avg_daily_sales <= 0:
                return None  # Sem vendas, não há projeção
            
            # Dias restantes = estoque atual / média diária
            days_remaining = total_stock / avg_daily_sales
            
            # Data de esgotamento
            stockout_date = datetime.utcnow() + timedelta(days=days_remaining)
            
            return stockout_date
            
        except Exception as e:
            logger.error(f"❌ Erro ao projetar esgotamento: {str(e)}")
            return None
    
    def calculate_reorder_point(
        self,
        company_id: int,
        internal_product_id: int,
        warehouse_id: Optional[int] = None,
        lead_time_days: int = 7,
        safety_stock: Optional[float] = None,
        period_days: int = 30
    ) -> float:
        """Calcula ponto de reposição"""
        try:
            # Média de vendas diárias
            avg_daily_sales = self.calculate_average_daily_sales(
                company_id=company_id,
                internal_product_id=internal_product_id,
                warehouse_id=warehouse_id,
                period_days=period_days
            )
            
            # Estoque de segurança (padrão: 3 dias de vendas)
            if safety_stock is None:
                safety_stock = avg_daily_sales * 3
            
            # Ponto de reposição = (Lead time * Média diária) + Estoque de segurança
            reorder_point = (lead_time_days * avg_daily_sales) + safety_stock
            
            return max(0.0, reorder_point)
            
        except Exception as e:
            logger.error(f"❌ Erro ao calcular ponto de reposição: {str(e)}")
            return 0.0
    
    def calculate_projection(
        self,
        company_id: int,
        internal_product_id: int,
        warehouse_id: Optional[int] = None,
        period_days: int = 30,
        lead_time_days: int = 7
    ) -> Dict[str, Any]:
        """Calcula projeção completa de estoque"""
        try:
            # Buscar estoque atual
            query = self.db.query(ProductStock).filter(
                and_(
                    ProductStock.company_id == company_id,
                    ProductStock.internal_product_id == internal_product_id
                )
            )
            
            if warehouse_id:
                query = query.filter(ProductStock.warehouse_id == warehouse_id)
            
            stocks = query.all()
            
            if not stocks:
                return {
                    "success": False,
                    "error": "Estoque não encontrado"
                }
            
            total_stock = sum(float(s.quantity - s.reserved_quantity) for s in stocks)
            
            # Calcular métricas
            turnover_rate = self.calculate_turnover(
                company_id=company_id,
                internal_product_id=internal_product_id,
                warehouse_id=warehouse_id,
                period_days=period_days
            )
            
            avg_daily_sales = self.calculate_average_daily_sales(
                company_id=company_id,
                internal_product_id=internal_product_id,
                warehouse_id=warehouse_id,
                period_days=period_days
            )
            
            projected_stockout = self.project_stockout(
                company_id=company_id,
                internal_product_id=internal_product_id,
                warehouse_id=warehouse_id,
                period_days=period_days
            )
            
            days_of_stock = None
            if avg_daily_sales > 0:
                days_of_stock = total_stock / avg_daily_sales
            
            reorder_point = self.calculate_reorder_point(
                company_id=company_id,
                internal_product_id=internal_product_id,
                warehouse_id=warehouse_id,
                lead_time_days=lead_time_days,
                period_days=period_days
            )
            
            # Calcular recomendação de compra
            recommended_quantity = 0.0
            recommended_reorder_date = None
            
            if avg_daily_sales > 0 and total_stock <= reorder_point:
                # Calcular quando recomendar compra (quando chegar no ponto de reposição)
                if total_stock > 0:
                    days_to_reorder = (total_stock - reorder_point) / avg_daily_sales
                    if days_to_reorder <= 0:
                        recommended_reorder_date = datetime.utcnow()
                    else:
                        recommended_reorder_date = datetime.utcnow() + timedelta(days=days_to_reorder)
                
                # Quantidade recomendada = (lead_time + segurança) * média diária
                safety_stock = avg_daily_sales * 3
                recommended_quantity = (lead_time_days * avg_daily_sales) + safety_stock
            
            return {
                "success": True,
                "projection": {
                    "current_stock": total_stock,
                    "average_daily_sales": avg_daily_sales,
                    "days_of_stock": days_of_stock,
                    "turnover_rate": turnover_rate,
                    "projected_stockout_date": projected_stockout.isoformat() if projected_stockout else None,
                    "reorder_point": reorder_point,
                    "recommended_reorder_date": recommended_reorder_date.isoformat() if recommended_reorder_date else None,
                    "recommended_quantity": recommended_quantity,
                    "calculation_period_days": period_days
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao calcular projeção: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao calcular projeção: {str(e)}"
            }
    
    def update_projection(
        self,
        company_id: int,
        internal_product_id: int,
        warehouse_id: Optional[int] = None,
        period_days: int = 30,
        lead_time_days: int = 7
    ) -> Dict[str, Any]:
        """Atualiza ou cria projeção de estoque"""
        try:
            # Calcular projeção
            projection_data = self.calculate_projection(
                company_id=company_id,
                internal_product_id=internal_product_id,
                warehouse_id=warehouse_id,
                period_days=period_days,
                lead_time_days=lead_time_days
            )
            
            if not projection_data.get("success"):
                return projection_data
            
            proj = projection_data["projection"]
            
            # Buscar ou criar registro de projeção
            query = self.db.query(StockProjection).filter(
                and_(
                    StockProjection.company_id == company_id,
                    StockProjection.internal_product_id == internal_product_id
                )
            )
            
            if warehouse_id:
                query = query.filter(StockProjection.warehouse_id == warehouse_id)
            else:
                # Se não especificou warehouse, usar o primeiro encontrado
                product_stock = self.db.query(ProductStock).filter(
                    and_(
                        ProductStock.company_id == company_id,
                        ProductStock.internal_product_id == internal_product_id
                    )
                ).first()
                
                if product_stock:
                    warehouse_id = product_stock.warehouse_id
            
            if not warehouse_id:
                return {
                    "success": False,
                    "error": "Depósito não encontrado"
                }
            
            projection = query.first()
            
            projected_stockout = None
            if proj.get("projected_stockout_date"):
                try:
                    projected_stockout = datetime.fromisoformat(proj["projected_stockout_date"].replace('Z', '+00:00'))
                except:
                    pass
            
            recommended_reorder = None
            if proj.get("recommended_reorder_date"):
                try:
                    recommended_reorder = datetime.fromisoformat(proj["recommended_reorder_date"].replace('Z', '+00:00'))
                except:
                    pass
            
            if projection:
                # Atualizar existente
                projection.current_stock = Decimal(str(proj["current_stock"]))
                projection.average_daily_sales = Decimal(str(proj["average_daily_sales"]))
                projection.days_of_stock = Decimal(str(proj["days_of_stock"])) if proj.get("days_of_stock") else None
                projection.projected_stockout_date = projected_stockout
                projection.recommended_reorder_date = recommended_reorder
                projection.recommended_quantity = Decimal(str(proj["recommended_quantity"]))
                projection.turnover_rate = Decimal(str(proj["turnover_rate"]))
                projection.calculation_period_days = period_days
                projection.last_calculated_at = datetime.utcnow()
            else:
                # Criar novo
                projection = StockProjection(
                    company_id=company_id,
                    internal_product_id=internal_product_id,
                    warehouse_id=warehouse_id,
                    current_stock=Decimal(str(proj["current_stock"])),
                    average_daily_sales=Decimal(str(proj["average_daily_sales"])),
                    days_of_stock=Decimal(str(proj["days_of_stock"])) if proj.get("days_of_stock") else None,
                    projected_stockout_date=projected_stockout,
                    recommended_reorder_date=recommended_reorder,
                    recommended_quantity=Decimal(str(proj["recommended_quantity"])),
                    turnover_rate=Decimal(str(proj["turnover_rate"])),
                    calculation_period_days=period_days,
                    last_calculated_at=datetime.utcnow()
                )
                self.db.add(projection)
            
            self.db.commit()
            self.db.refresh(projection)
            
            logger.info(f"✅ Projeção atualizada: Produto {internal_product_id} (Warehouse: {warehouse_id})")
            
            return {
                "success": True,
                "projection": {
                    "id": projection.id,
                    "current_stock": float(projection.current_stock),
                    "average_daily_sales": float(projection.average_daily_sales),
                    "days_of_stock": float(projection.days_of_stock) if projection.days_of_stock else None,
                    "turnover_rate": float(projection.turnover_rate) if projection.turnover_rate else None,
                    "projected_stockout_date": projection.projected_stockout_date.isoformat() if projection.projected_stockout_date else None,
                    "recommended_reorder_date": projection.recommended_reorder_date.isoformat() if projection.recommended_reorder_date else None,
                    "recommended_quantity": float(projection.recommended_quantity) if projection.recommended_quantity else None
                }
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao atualizar projeção: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao atualizar projeção: {str(e)}"
            }
    
    def get_reorder_recommendations(
        self,
        company_id: int,
        warehouse_id: Optional[int] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Obtém recomendações de compra (produtos que precisam ser recomprados)"""
        try:
            query = self.db.query(StockProjection).filter(
                and_(
                    StockProjection.company_id == company_id,
                    StockProjection.recommended_quantity > 0,
                    or_(
                        StockProjection.recommended_reorder_date <= datetime.utcnow(),
                        StockProjection.recommended_reorder_date.is_(None)
                    )
                )
            )
            
            if warehouse_id:
                query = query.filter(StockProjection.warehouse_id == warehouse_id)
            
            projections = query.order_by(StockProjection.recommended_reorder_date).limit(limit).all()
            
            recommendations = []
            for proj in projections:
                product = self.db.query(InternalProduct).filter(
                    InternalProduct.id == proj.internal_product_id
                ).first()
                
                if product:
                    recommendations.append({
                        "product_id": product.id,
                        "product_name": product.name,
                        "product_sku": product.internal_sku,
                        "warehouse_id": proj.warehouse_id,
                        "warehouse_name": proj.warehouse.name if proj.warehouse else None,
                        "current_stock": float(proj.current_stock),
                        "recommended_quantity": float(proj.recommended_quantity) if proj.recommended_quantity else 0,
                        "recommended_reorder_date": proj.recommended_reorder_date.isoformat() if proj.recommended_reorder_date else None,
                        "projected_stockout_date": proj.projected_stockout_date.isoformat() if proj.projected_stockout_date else None,
                        "turnover_rate": float(proj.turnover_rate) if proj.turnover_rate else None
                    })
            
            return {
                "success": True,
                "recommendations": recommendations,
                "count": len(recommendations)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar recomendações: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao buscar recomendações: {str(e)}"
            }

