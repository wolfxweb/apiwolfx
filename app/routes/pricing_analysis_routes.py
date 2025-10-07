"""
Rotas para análise de preços e taxas
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from app.config.database import get_db
from app.controllers.pricing_analysis_controller import PricingAnalysisController
from app.controllers.auth_controller import AuthController
from fastapi import Cookie, Request

router = APIRouter()

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Obtém usuário atual da sessão (mesma função das rotas ML)"""
    session_token = request.cookies.get('session_token')
    if not session_token:
        raise HTTPException(status_code=401, detail="Sessão não encontrada")
    
    auth_controller = AuthController()
    result = auth_controller.get_user_by_session(session_token, db)
    if result.get("error"):
        raise HTTPException(status_code=401, detail=result["error"])
    
    return result["user"]

@router.get("/analysis/sku/{internal_sku}")
async def get_pricing_analysis_by_sku(
    internal_sku: str,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Obtém análise de preços e taxas para um SKU específico
    
    Args:
        internal_sku: SKU interno do produto
        db: Sessão do banco de dados
        user: Usuário logado (obtido da sessão)
    
    Returns:
        Análise completa de preços, custos, margens e competitividade
    """
    try:
        controller = PricingAnalysisController(db)
        result = controller.get_pricing_analysis_by_sku(internal_sku, user["company"]["id"])
        
        if result.get("error"):
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.post("/analysis/skus")
async def get_pricing_analysis_by_skus(
    internal_skus: List[str] = Body(..., description="Lista de SKUs internos para análise"),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Obtém análise de preços e taxas para múltiplos SKUs
    
    Args:
        internal_skus: Lista de SKUs internos
        db: Sessão do banco de dados
        user: Usuário logado (obtido da sessão)
    
    Returns:
        Análise completa para todos os SKUs + estatísticas gerais
    """
    try:
        if not internal_skus:
            raise HTTPException(status_code=400, detail="Lista de SKUs não pode estar vazia")
        
        if len(internal_skus) > 50:
            raise HTTPException(status_code=400, detail="Máximo de 50 SKUs por requisição")
        
        controller = PricingAnalysisController(db)
        result = controller.get_pricing_analysis_by_skus(internal_skus, user["company"]["id"])
        
        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/analysis/sku/{internal_sku}/summary")
async def get_pricing_summary_by_sku(
    internal_sku: str,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Obtém resumo da análise de preços para um SKU específico
    
    Args:
        internal_sku: SKU interno do produto
        db: Sessão do banco de dados
        user: Usuário logado (obtido da sessão)
    
    Returns:
        Resumo com dados essenciais para dashboard
    """
    try:
        controller = PricingAnalysisController(db)
        result = controller.get_pricing_analysis_by_sku(internal_sku, user["company"]["id"])
        
        if result.get("error"):
            raise HTTPException(status_code=404, detail=result["error"])
        
        analysis = result["analysis"]
        internal_product = analysis["internal_product"]
        comparative = analysis["comparative_analysis"]
        
        # Criar resumo
        summary = {
            "sku": internal_product["internal_sku"],
            "name": internal_product["name"],
            "cost_price": internal_product["cost_price"],
            "selling_price": internal_product["selling_price"],
            "profit_margin": comparative["pricing_analysis"]["profit_margin"],
            "total_costs": internal_product["total_costs_with_tax"],
            "is_competitive": comparative["competitiveness"]["is_competitive"],
            "competitiveness_level": comparative["competitiveness"]["competitiveness_level"],
            "recommendations_count": len(analysis["recommendations"]),
            "key_recommendations": analysis["recommendations"][:3],  # Top 3 recomendações
            "status": "healthy" if comparative["pricing_analysis"]["is_meeting_expectations"] else "needs_attention"
        }
        
        return {
            "success": True,
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/analysis/company/summary")
async def get_company_pricing_summary(
    category: Optional[str] = Query(None, description="Filtrar por categoria"),
    brand: Optional[str] = Query(None, description="Filtrar por marca"),
    limit: int = Query(20, description="Número máximo de produtos", le=100),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Obtém resumo geral da análise de preços da empresa
    
    Args:
        category: Filtrar por categoria (opcional)
        brand: Filtrar por marca (opcional)
        limit: Limite de produtos (máximo 100)
        db: Sessão do banco de dados
        user: Usuário logado (obtido da sessão)
    
    Returns:
        Resumo geral com estatísticas da empresa
    """
    try:
        from app.services.internal_product_service import InternalProductService
        
        # Buscar produtos internos com filtros
        service = InternalProductService(db)
        products_result = service.get_internal_products(
            company_id=user["company"]["id"],
            category=category,
            limit=limit
        )
        
        if products_result.get("error"):
            raise HTTPException(status_code=400, detail=products_result["error"])
        
        products = products_result["products"]
        
        if not products:
            return {
                "success": True,
                "summary": {
                    "total_products": 0,
                    "message": "Nenhum produto encontrado com os filtros aplicados"
                }
            }
        
        # Extrair SKUs para análise
        skus = [p["internal_sku"] for p in products]
        
        # Obter análises
        controller = PricingAnalysisController(db)
        analysis_result = controller.get_pricing_analysis_by_skus(skus, user["company"]["id"])
        
        if analysis_result.get("error"):
            raise HTTPException(status_code=400, detail=analysis_result["error"])
        
        # Criar resumo da empresa
        general_stats = analysis_result["general_statistics"]
        
        summary = {
            "total_products": general_stats["total_products"],
            "average_profit_margin": round(general_stats["average_profit_margin"], 2),
            "min_profit_margin": round(general_stats["min_profit_margin"], 2),
            "max_profit_margin": round(general_stats["max_profit_margin"], 2),
            "average_cost_percentage": round(general_stats["average_cost_percentage"], 2),
            "products_with_low_margin": general_stats["products_with_low_margin"],
            "products_with_good_margin": general_stats["products_with_good_margin"],
            "competitive_products": general_stats["competitive_products"],
            "low_margin_percentage": round((general_stats["products_with_low_margin"] / general_stats["total_products"]) * 100, 2) if general_stats["total_products"] > 0 else 0,
            "competitive_percentage": round((general_stats["competitive_products"] / general_stats["total_products"]) * 100, 2) if general_stats["total_products"] > 0 else 0
        }
        
        return {
            "success": True,
            "summary": summary,
            "filters_applied": {
                "category": category,
                "brand": brand,
                "limit": limit
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/analysis/health-check")
async def pricing_health_check(
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Verifica a saúde geral da análise de preços da empresa
    
    Returns:
        Status de saúde com alertas e recomendações
    """
    try:
        from app.services.internal_product_service import InternalProductService
        
        # Buscar todos os produtos ativos
        service = InternalProductService(db)
        products_result = service.get_internal_products(
            company_id=user["company"]["id"],
            status="active",
            limit=100
        )
        
        if products_result.get("error"):
            raise HTTPException(status_code=400, detail=products_result["error"])
        
        products = products_result["products"]
        
        if not products:
            return {
                "success": True,
                "health_status": "no_products",
                "message": "Nenhum produto ativo encontrado",
                "recommendations": ["Adicione produtos internos para análise de preços"]
            }
        
        # Analisar saúde dos dados
        health_issues = []
        recommendations = []
        
        # Verificar produtos sem preço de custo
        products_without_cost = [p for p in products if not p.get("cost_price") or p["cost_price"] == 0]
        if products_without_cost:
            health_issues.append(f"{len(products_without_cost)} produtos sem preço de custo")
            recommendations.append("Preencha o preço de custo de todos os produtos para análise precisa")
        
        # Verificar produtos sem preço de venda
        products_without_selling = [p for p in products if not p.get("selling_price") or p["selling_price"] == 0]
        if products_without_selling:
            health_issues.append(f"{len(products_without_selling)} produtos sem preço de venda")
            recommendations.append("Defina preços de venda para todos os produtos")
        
        # Verificar produtos com margem baixa
        low_margin_products = [p for p in products if p.get("profit_margin", 0) < 10]
        if low_margin_products:
            health_issues.append(f"{len(low_margin_products)} produtos com margem baixa (< 10%)")
            recommendations.append("Revise preços de produtos com margem baixa")
        
        # Determinar status geral
        if len(health_issues) == 0:
            health_status = "excellent"
            message = "Todos os produtos têm dados completos"
        elif len(health_issues) <= 2:
            health_status = "good"
            message = "Alguns produtos precisam de atenção"
        else:
            health_status = "needs_attention"
            message = "Múltiplos problemas encontrados"
        
        return {
            "success": True,
            "health_status": health_status,
            "message": message,
            "total_products": len(products),
            "health_issues": health_issues,
            "recommendations": recommendations,
            "issues_count": len(health_issues)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
