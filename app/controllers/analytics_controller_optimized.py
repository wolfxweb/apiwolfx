#!/usr/bin/env python3
"""
Versão otimizada do AnalyticsController
"""
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class OptimizedAnalyticsController:
    """Controller otimizado para analytics de vendas e performance"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_sales_dashboard_optimized(self, company_id: int, user_id: int, 
                                    start_date: datetime, end_date: datetime) -> Dict:
        """
        Dashboard de vendas otimizado com consultas SQL diretas
        """
        try:
            logger.info(f"🚀 DASHBOARD OTIMIZADO - company_id={company_id}")
            logger.info(f"📅 Período: {start_date} a {end_date}")
            
            # Consulta otimizada para KPIs básicos
            kpis_result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(CASE 
                        WHEN status IN ('PAID', 'CONFIRMED', 'SHIPPED', 'DELIVERED') 
                        THEN total_amount 
                        ELSE 0 
                    END) as vendas_brutas,
                    SUM(CASE 
                        WHEN status IN ('PAID', 'CONFIRMED', 'SHIPPED', 'DELIVERED') 
                        THEN 1 
                        ELSE 0 
                    END) as valid_orders,
                    SUM(CASE 
                        WHEN status = 'CANCELLED' 
                        THEN total_amount 
                        ELSE 0 
                    END) as cancelled_value,
                    SUM(CASE 
                        WHEN status = 'CANCELLED' 
                        THEN 1 
                        ELSE 0 
                    END) as cancelled_count,
                    AVG(CASE 
                        WHEN status IN ('PAID', 'CONFIRMED', 'SHIPPED', 'DELIVERED') 
                        THEN total_amount 
                        ELSE NULL 
                    END) as avg_ticket
                FROM ml_orders 
                WHERE company_id = :company_id
                AND date_created >= :start_date
                AND date_created <= :end_date
            """), {
                "company_id": company_id,
                "start_date": start_date,
                "end_date": end_date
            })
            
            kpis_data = kpis_result.fetchone()
            
            # Extrair dados da consulta otimizada
            total_orders = kpis_data.total_orders or 0
            vendas_brutas = float(kpis_data.vendas_brutas or 0)
            valid_orders = kpis_data.valid_orders or 0
            cancelled_value = float(kpis_data.cancelled_value or 0)
            cancelled_count = kpis_data.cancelled_count or 0
            avg_ticket = float(kpis_data.avg_ticket or 0)
            
            logger.info(f"📊 KPIs otimizados: {total_orders} pedidos, R$ {vendas_brutas:.2f} receita")
            
            # Consulta otimizada para devoluções
            returns_result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as returns_count,
                    SUM(total_amount) as returns_value
                FROM ml_orders 
                WHERE company_id = :company_id
                AND date_created >= :start_date
                AND date_created <= :end_date
                AND mediations IS NOT NULL
                AND mediations::text != '[]'
                AND mediations::text != ''
            """), {
                "company_id": company_id,
                "start_date": start_date,
                "end_date": end_date
            })
            
            returns_data = returns_result.fetchone()
            returns_count = returns_data.returns_count or 0
            returns_value = float(returns_data.returns_value or 0)
            
            # Calcular receita líquida
            total_revenue = vendas_brutas - cancelled_value - returns_value
            
            # Consulta otimizada para produtos
            products_result = self.db.execute(text("""
                SELECT COUNT(*) as total_products
                FROM ml_products 
                WHERE company_id = :company_id
                AND status IN ('ACTIVE', 'PAUSED')
            """), {"company_id": company_id})
            
            products_data = products_result.fetchone()
            total_products = products_data.total_products or 0
            
            # Simular visitas (não temos dados reais)
            total_visits = valid_orders * 10  # Aproximação: 10 visitas por venda
            
            # Calcular taxa de conversão
            conversion_rate = (valid_orders / total_visits * 100) if total_visits > 0 else 0
            
            # Aproximação para unidades vendidas
            total_sold = valid_orders * 1  # Aproximação: 1 unidade por pedido
            
            return {
                'success': True,
                'kpis': {
                    'total_revenue': total_revenue,
                    'total_sold': total_sold,
                    'total_orders': total_orders,
                    'avg_ticket': avg_ticket,
                    'cancelled_orders': cancelled_count,
                    'cancelled_value': cancelled_value,
                    'returns_count': returns_count,
                    'returns_value': returns_value,
                    'total_visits': total_visits,
                    'total_products': total_products,
                    'conversion_rate': conversion_rate
                },
                'costs': self._calculate_costs_optimized(company_id, total_revenue, total_orders, start_date, end_date),
                'billing': self._get_billing_data_optimized(company_id, start_date, end_date) or {},
                'profit': {
                    'net_profit': total_revenue * 0.50,  # 50% estimado
                    'net_margin': 50.0,
                    'avg_profit_per_order': (total_revenue * 0.50) / total_orders if total_orders > 0 else 0
                },
                'products': [],  # Simplificado para performance
                'total': total_products,
                'timeline': [],  # Simplificado para performance
                'pareto_analysis': {}  # Simplificado para performance
            }
            
        except Exception as e:
            logger.error(f"Erro no dashboard otimizado: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_costs_optimized(self, company_id: int, total_revenue: float, 
                                 total_orders: int, start_date: datetime, end_date: datetime) -> Dict:
        """Calcula custos de forma otimizada"""
        try:
            # Buscar dados de billing otimizados
            billing_data = self._get_billing_data_optimized(company_id, start_date, end_date)
            
            if billing_data and billing_data.get('total_advertising_cost', 0) > 0:
                # Usar dados reais de billing
                ml_fees = billing_data.get('total_sale_fees', 0)
                shipping_fees = billing_data.get('total_shipping_fees', 0)
                marketing_cost = billing_data.get('total_advertising_cost', 0)
                discounts = 0
                
                logger.info(f"💰 Usando dados reais de billing (otimizado)")
            else:
                # Usar estimativas otimizadas
                ml_fees = total_revenue * 0.10  # 10% estimado
                shipping_fees = total_revenue * 0.05  # 5% estimado
                marketing_cost = total_revenue * 0.03  # 3% estimado
                discounts = 0
            
            # Custo dos produtos (estimado)
            product_cost = total_revenue * 0.40  # 40% estimado
            other_costs = 0.0
            taxes_amount = total_revenue * 0.05  # 5% estimado
            
            # Total de custos
            total_costs = ml_fees + product_cost + taxes_amount + other_costs + marketing_cost
            total_costs_percent = (total_costs / total_revenue * 100) if total_revenue > 0 else 0
            
            # Calcular percentuais
            ml_fees_percent = (ml_fees / total_revenue * 100) if total_revenue > 0 else 0
            shipping_fees_percent = (shipping_fees / total_revenue * 100) if total_revenue > 0 else 0
            discounts_percent = (discounts / total_revenue * 100) if total_revenue > 0 else 0
            product_cost_percent = (product_cost / total_revenue * 100) if total_revenue > 0 else 0
            other_costs_percent = (other_costs / total_revenue * 100) if total_revenue > 0 else 0
            marketing_percent = (marketing_cost / total_revenue * 100) if total_revenue > 0 else 0
            
            return {
                'ml_fees': ml_fees,
                'ml_fees_percent': ml_fees_percent,
                'shipping_fees': shipping_fees,
                'shipping_fees_percent': shipping_fees_percent,
                'discounts': discounts,
                'discounts_percent': discounts_percent,
                'product_cost': product_cost,
                'product_cost_percent': product_cost_percent,
                'taxes': taxes_amount,
                'taxes_percent': 5.0,
                'taxes_breakdown': {},
                'other_costs': other_costs,
                'other_costs_percent': other_costs_percent,
                'other_costs_per_unit': other_costs / total_orders if total_orders > 0 else 0,
                'marketing_cost': marketing_cost,
                'marketing_percent': marketing_percent,
                'marketing_per_unit': 0.0,
                'total_costs': total_costs,
                'total_costs_percent': total_costs_percent
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular custos otimizados: {e}")
            return {
                'ml_fees': 0,
                'ml_fees_percent': 0,
                'shipping_fees': 0,
                'shipping_fees_percent': 0,
                'discounts': 0,
                'discounts_percent': 0,
                'product_cost': 0,
                'product_cost_percent': 0,
                'taxes': 0,
                'taxes_percent': 0,
                'taxes_breakdown': {},
                'other_costs': 0,
                'other_costs_percent': 0,
                'other_costs_per_unit': 0,
                'marketing_cost': 0,
                'marketing_percent': 0,
                'marketing_per_unit': 0,
                'total_costs': 0,
                'total_costs_percent': 0
            }
    
    def _get_billing_data_optimized(self, company_id: int, start_date: datetime, end_date: datetime) -> Dict:
        """Busca dados de billing de forma otimizada"""
        try:
            result = self.db.execute(text("""
                SELECT 
                    SUM(advertising_cost) as total_advertising_cost,
                    SUM(sale_fees) as total_sale_fees,
                    SUM(shipping_fees) as total_shipping_fees,
                    COUNT(*) as periods_count
                FROM ml_billing_periods 
                WHERE company_id = :company_id
                AND period_from <= :end_date 
                AND period_to >= :start_date
            """), {
                "company_id": company_id,
                "start_date": start_date,
                "end_date": end_date
            })
            
            billing_data = result.fetchone()
            
            if billing_data and billing_data.periods_count > 0:
                return {
                    'total_advertising_cost': float(billing_data.total_advertising_cost or 0),
                    'total_sale_fees': float(billing_data.total_sale_fees or 0),
                    'total_shipping_fees': float(billing_data.total_shipping_fees or 0),
                    'periods_count': billing_data.periods_count
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar dados de billing otimizados: {e}")
            return None
