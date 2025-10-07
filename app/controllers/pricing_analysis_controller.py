"""
Controller para análise de preços e taxas
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.services.internal_product_service import InternalProductService
from app.services.ml_product_service import MLProductService
from app.models.saas_models import Company

logger = logging.getLogger(__name__)

class PricingAnalysisController:
    """Controller para análise de preços e taxas"""
    
    def __init__(self, db: Session):
        self.db = db
        self.internal_product_service = InternalProductService(db)
        self.ml_product_service = MLProductService(db)
    
    def get_pricing_analysis_by_sku(self, internal_sku: str, company_id: int) -> Dict[str, Any]:
        """Obtém análise de preços para um SKU específico"""
        try:
            # Buscar dados do produto interno
            result = self.internal_product_service.get_pricing_data_by_sku(internal_sku, company_id)
            
            if result.get("error"):
                return result
            
            pricing_data = result["pricing_data"]
            
            # Buscar produto ML associado se existir
            ml_product_data = None
            if pricing_data["base_product_id"]:
                ml_product = self.ml_product_service.get_ml_product_by_id(
                    pricing_data["base_product_id"], 
                    company_id
                )
                if ml_product.get("success"):
                    ml_product_data = ml_product["product"]
            
            # Calcular análise comparativa
            analysis = self._calculate_pricing_analysis(pricing_data, ml_product_data)
            
            return {
                "success": True,
                "analysis": {
                    "internal_product": pricing_data,
                    "ml_product": ml_product_data,
                    "comparative_analysis": analysis,
                    "recommendations": self._generate_recommendations(pricing_data, analysis)
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter análise de preços: {str(e)}")
            return {"error": f"Erro interno: {str(e)}"}
    
    def get_pricing_analysis_by_skus(self, internal_skus: List[str], company_id: int) -> Dict[str, Any]:
        """Obtém análise de preços para múltiplos SKUs"""
        try:
            # Buscar dados dos produtos internos
            result = self.internal_product_service.get_pricing_data_by_skus(internal_skus, company_id)
            
            if result.get("error"):
                return result
            
            pricing_data_list = result["pricing_data"]
            analyses = []
            
            for pricing_data in pricing_data_list:
                # Buscar produto ML associado se existir
                ml_product_data = None
                if pricing_data["base_product_id"]:
                    ml_product = self.ml_product_service.get_ml_product_by_id(
                        pricing_data["base_product_id"], 
                        company_id
                    )
                    if ml_product.get("success"):
                        ml_product_data = ml_product["product"]
                
                # Calcular análise comparativa
                analysis = self._calculate_pricing_analysis(pricing_data, ml_product_data)
                
                analyses.append({
                    "internal_product": pricing_data,
                    "ml_product": ml_product_data,
                    "comparative_analysis": analysis,
                    "recommendations": self._generate_recommendations(pricing_data, analysis)
                })
            
            # Calcular estatísticas gerais
            general_stats = self._calculate_general_statistics(analyses)
            
            return {
                "success": True,
                "analyses": analyses,
                "general_statistics": general_stats,
                "total_analyzed": len(analyses),
                "missing_skus": result.get("missing_skus", []),
                "found_skus": result.get("found_skus", [])
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter análise de preços em lote: {str(e)}")
            return {"error": f"Erro interno: {str(e)}"}
    
    def _calculate_pricing_analysis(self, internal_data: Dict, ml_data: Optional[Dict]) -> Dict[str, Any]:
        """Calcula análise comparativa entre produto interno e ML"""
        analysis = {
            "cost_analysis": {},
            "pricing_analysis": {},
            "margin_analysis": {},
            "competitiveness": {}
        }
        
        # Análise de custos
        cost_price = internal_data.get("cost_price", 0)
        marketing_cost = internal_data.get("marketing_cost", 0)
        other_costs = internal_data.get("other_costs", 0)
        tax_amount = internal_data.get("tax_amount", 0)
        total_costs = internal_data.get("total_costs_with_tax", 0)
        
        analysis["cost_analysis"] = {
            "cost_breakdown": {
                "cost_price": cost_price,
                "marketing_cost": marketing_cost,
                "other_costs": other_costs,
                "tax_amount": tax_amount,
                "total_costs": total_costs
            },
            "cost_percentage": {
                "cost_price_pct": (cost_price / total_costs * 100) if total_costs > 0 else 0,
                "marketing_pct": (marketing_cost / total_costs * 100) if total_costs > 0 else 0,
                "other_costs_pct": (other_costs / total_costs * 100) if total_costs > 0 else 0,
                "tax_pct": (tax_amount / total_costs * 100) if total_costs > 0 else 0
            }
        }
        
        # Análise de preços
        selling_price = internal_data.get("selling_price", 0)
        profit_margin = internal_data.get("profit_margin", 0)
        expected_margin = internal_data.get("expected_profit_margin", 0)
        
        analysis["pricing_analysis"] = {
            "selling_price": selling_price,
            "profit_margin": profit_margin,
            "expected_margin": expected_margin,
            "margin_difference": profit_margin - expected_margin,
            "is_meeting_expectations": profit_margin >= expected_margin
        }
        
        # Análise de margem
        if selling_price > 0:
            cost_percentage = (total_costs / selling_price) * 100
            profit_percentage = profit_margin
        else:
            cost_percentage = 0
            profit_percentage = 0
        
        analysis["margin_analysis"] = {
            "cost_percentage": cost_percentage,
            "profit_percentage": profit_percentage,
            "break_even_price": total_costs,
            "recommended_minimum_price": total_costs * 1.1,  # 10% de margem mínima
            "optimal_price": total_costs * 1.2  # 20% de margem ótima
        }
        
        # Análise de competitividade (se houver dados do ML)
        if ml_data:
            ml_price = float(ml_data.get("price", 0)) if ml_data.get("price") else 0
            if ml_price > 0:
                price_difference = selling_price - ml_price
                price_difference_pct = (price_difference / ml_price) * 100
                
                analysis["competitiveness"] = {
                    "ml_price": ml_price,
                    "price_difference": price_difference,
                    "price_difference_pct": price_difference_pct,
                    "is_competitive": price_difference <= 0,
                    "competitiveness_level": self._get_competitiveness_level(price_difference_pct)
                }
            else:
                analysis["competitiveness"] = {
                    "ml_price": 0,
                    "price_difference": 0,
                    "price_difference_pct": 0,
                    "is_competitive": True,
                    "competitiveness_level": "unknown"
                }
        else:
            analysis["competitiveness"] = {
                "ml_price": 0,
                "price_difference": 0,
                "price_difference_pct": 0,
                "is_competitive": True,
                "competitiveness_level": "no_ml_data"
            }
        
        return analysis
    
    def _generate_recommendations(self, internal_data: Dict, analysis: Dict) -> List[str]:
        """Gera recomendações baseadas na análise"""
        recommendations = []
        
        # Verificar margem de lucro
        profit_margin = analysis["pricing_analysis"]["profit_margin"]
        expected_margin = analysis["pricing_analysis"]["expected_margin"]
        
        if profit_margin < expected_margin:
            recommendations.append(f"⚠️ Margem de lucro atual ({profit_margin:.1f}%) está abaixo da esperada ({expected_margin:.1f}%)")
        
        if profit_margin < 10:
            recommendations.append("🔴 Margem de lucro muito baixa (< 10%). Considere aumentar o preço de venda")
        elif profit_margin < 20:
            recommendations.append("🟡 Margem de lucro baixa (< 20%). Avalie se é sustentável")
        else:
            recommendations.append("🟢 Margem de lucro adequada")
        
        # Verificar competitividade
        if analysis["competitiveness"]["ml_price"] > 0:
            price_diff_pct = analysis["competitiveness"]["price_difference_pct"]
            if price_diff_pct > 20:
                recommendations.append("🔴 Preço muito acima do mercado (+20%). Risco de perder vendas")
            elif price_diff_pct > 10:
                recommendations.append("🟡 Preço acima do mercado (+10%). Monitore a competitividade")
            elif price_diff_pct < -10:
                recommendations.append("🟢 Preço competitivo. Boa posição no mercado")
        
        # Verificar custos
        cost_breakdown = analysis["cost_analysis"]["cost_percentage"]
        if cost_breakdown["marketing_pct"] > 30:
            recommendations.append("📊 Custo de marketing alto (>30%). Avalie a eficiência das campanhas")
        
        if cost_breakdown["other_costs_pct"] > 20:
            recommendations.append("💰 Outros custos altos (>20%). Revise despesas operacionais")
        
        # Verificar preço de custo
        if internal_data.get("cost_price", 0) == 0:
            recommendations.append("❌ Preço de custo não informado. Essencial para análise precisa")
        
        return recommendations
    
    def _get_competitiveness_level(self, price_difference_pct: float) -> str:
        """Determina o nível de competitividade baseado na diferença de preço"""
        if price_difference_pct <= -20:
            return "very_competitive"
        elif price_difference_pct <= -10:
            return "competitive"
        elif price_difference_pct <= 0:
            return "neutral"
        elif price_difference_pct <= 10:
            return "slightly_expensive"
        elif price_difference_pct <= 20:
            return "expensive"
        else:
            return "very_expensive"
    
    def _calculate_general_statistics(self, analyses: List[Dict]) -> Dict[str, Any]:
        """Calcula estatísticas gerais para múltiplas análises"""
        if not analyses:
            return {}
        
        total_products = len(analyses)
        profit_margins = [a["comparative_analysis"]["pricing_analysis"]["profit_margin"] for a in analyses]
        cost_percentages = [a["comparative_analysis"]["margin_analysis"]["cost_percentage"] for a in analyses]
        
        # Filtrar valores válidos
        valid_margins = [m for m in profit_margins if m is not None and m >= 0]
        valid_costs = [c for c in cost_percentages if c is not None and c >= 0]
        
        stats = {
            "total_products": total_products,
            "average_profit_margin": sum(valid_margins) / len(valid_margins) if valid_margins else 0,
            "min_profit_margin": min(valid_margins) if valid_margins else 0,
            "max_profit_margin": max(valid_margins) if valid_margins else 0,
            "average_cost_percentage": sum(valid_costs) / len(valid_costs) if valid_costs else 0,
            "products_with_low_margin": len([m for m in valid_margins if m < 10]),
            "products_with_good_margin": len([m for m in valid_margins if m >= 20]),
            "competitive_products": len([a for a in analyses if a["comparative_analysis"]["competitiveness"]["is_competitive"]])
        }
        
        return stats
