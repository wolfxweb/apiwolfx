"""
Serviço para análise de produtos com ChatGPT
"""
import logging
import requests
import json
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.saas_models import MLProduct, MLOrder

logger = logging.getLogger(__name__)

class AIAnalysisService:
    """Serviço para análise de produtos com IA"""
    
    def __init__(self, db: Session):
        self.db = db
        self.api_key = "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"
        self.api_url = "https://api.openai.com/v1/chat/completions"
    
    def analyze_product(self, product_id: int, company_id: int, catalog_data: Optional[List] = None) -> Dict:
        """Analisa um produto usando ChatGPT"""
        try:
            logger.info(f"Iniciando análise IA para produto {product_id}")
            
            # 1. Buscar dados do produto
            product = self.db.query(MLProduct).filter(
                MLProduct.id == product_id,
                MLProduct.company_id == company_id
            ).first()
            
            if not product:
                return {"success": False, "error": "Produto não encontrado"}
            
            # 2. Buscar histórico de pedidos deste produto (últimos 100)
            # Como ml_item_id está dentro do JSON order_items, precisamos buscar todos
            # os pedidos da empresa e filtrar no Python
            all_orders = self.db.query(MLOrder).filter(
                MLOrder.company_id == company_id,
                MLOrder.order_items.isnot(None)
            ).order_by(desc(MLOrder.date_created)).limit(500).all()
            
            # Filtrar pedidos que contêm este produto
            orders = []
            for order in all_orders:
                if order.order_items:
                    # order_items é um JSON array
                    for item in order.order_items:
                        if item.get('item', {}).get('id') == product.ml_item_id:
                            orders.append(order)
                            break  # Já encontrou o produto neste pedido
                
                if len(orders) >= 100:  # Limitar a 100 pedidos
                    break
            
            logger.info(f"Encontrados {len(orders)} pedidos para o produto {product.ml_item_id}")
            
            # 3. Preparar dados estruturados
            analysis_data = self._prepare_analysis_data(product, orders, catalog_data)
            
            # 4. Criar prompt para ChatGPT
            prompt = self._create_analysis_prompt(analysis_data)
            
            # 5. Chamar API ChatGPT
            response = self._call_chatgpt(prompt)
            
            if response["success"]:
                return {
                    "success": True,
                    "analysis": response["analysis"],
                    "tokens_used": response.get("tokens_used", 0)
                }
            else:
                return {"success": False, "error": response.get("error")}
            
        except Exception as e:
            logger.error(f"Erro na análise com IA: {e}", exc_info=True)
            return {"success": False, "error": f"Erro ao processar análise: {str(e)}"}
    
    def _prepare_analysis_data(self, product: MLProduct, orders: List[MLOrder], 
                               catalog_data: Optional[List] = None) -> Dict:
        """Prepara dados estruturados para análise"""
        
        # Dados do produto
        product_data = {
            "id_ml": product.ml_item_id,
            "titulo": product.title,
            "sku": product.seller_sku,
            "preco_atual": float(product.price) if product.price else 0,
            "preco_base": float(product.base_price) if product.base_price else None,
            "preco_original": float(product.original_price) if product.original_price else None,
            "status": product.status.value if hasattr(product.status, 'value') else str(product.status),
            "categoria": product.category_name,
            "estoque_disponivel": product.available_quantity,
            "quantidade_vendida": product.sold_quantity,
            "condicao": product.condition,
            "tipo_envio": product.shipping
        }
        
        # Histórico de pedidos
        orders_data = []
        total_revenue = 0
        total_ml_fees = 0
        total_shipping = 0
        total_discounts = 0
        total_quantity = 0
        
        for order in orders:
            # Extrair quantidade e preço unitário do order_items
            quantity = 1
            unit_price = 0
            
            if order.order_items:
                for item in order.order_items:
                    if item.get('item', {}).get('id') == product.ml_item_id:
                        quantity = item.get('quantity', 1)
                        unit_price = item.get('unit_price', 0)
                        break
            
            # Converter valores de centavos para reais
            total_amount = float(order.total_amount / 100) if order.total_amount else 0
            sale_fees = float(order.sale_fees / 100) if order.sale_fees else 0
            shipping_cost = float(order.shipping_cost / 100) if order.shipping_cost else 0
            coupon_amount = float(order.coupon_amount / 100) if order.coupon_amount else 0
            
            order_data = {
                "id_pedido": str(order.ml_order_id),
                "data": order.date_created.isoformat() if order.date_created else None,
                "quantidade": quantity,
                "preco_unitario": float(unit_price),
                "total_pago": total_amount,
                "comissao_ml": sale_fees,
                "frete": shipping_cost,
                "desconto": coupon_amount,
                "status": order.status.value if hasattr(order.status, 'value') else str(order.status)
            }
            orders_data.append(order_data)
            
            # Acumular métricas (apenas pedidos pagos/entregues)
            status_str = order.status.value if hasattr(order.status, 'value') else str(order.status)
            if status_str in ['paid', 'delivered']:
                total_revenue += total_amount
                total_ml_fees += sale_fees
                total_shipping += shipping_cost
                total_discounts += coupon_amount
                total_quantity += quantity
        
        # Métricas agregadas de vendas
        paid_orders = []
        for o in orders:
            status_str = o.status.value if hasattr(o.status, 'value') else str(o.status)
            if status_str in ['paid', 'delivered']:
                paid_orders.append(o)
        
        avg_price = total_revenue / len(paid_orders) if paid_orders else 0
        
        sales_metrics = {
            "total_pedidos": len(orders),
            "pedidos_pagos": len(paid_orders),
            "receita_total": total_revenue,
            "comissoes_ml_total": total_ml_fees,
            "frete_total": total_shipping,
            "descontos_total": total_discounts,
            "ticket_medio": avg_price,
            "liquido_total": total_revenue - total_ml_fees
        }
        
        # Dados do catálogo (concorrentes)
        competitors_data = []
        if catalog_data:
            for comp in catalog_data[:50]:  # Limitar a 50 concorrentes principais
                competitors_data.append({
                    "vendedor": comp.get("seller_nickname", "N/A"),
                    "preco": comp.get("price", 0),
                    "envio": comp.get("shipping_type", "N/A"),
                    "envio_gratis": comp.get("free_shipping", False),
                    "mercado_lider": comp.get("mercado_lider_level", "none"),
                    "vendas": comp.get("sold_quantity", 0)
                })
        
        return {
            "produto": product_data,
            "historico_pedidos": orders_data,
            "metricas_vendas": sales_metrics,
            "concorrentes": competitors_data,
            "total_concorrentes": len(competitors_data)
        }
    
    def _create_analysis_prompt(self, data: Dict) -> str:
        """Cria prompt estruturado para ChatGPT"""
        
        produto = data["produto"]
        metricas = data["metricas_vendas"]
        total_pedidos = len(data["historico_pedidos"])
        total_concorrentes = data.get("total_concorrentes", 0)
        
        prompt = f"""Você é um especialista em análise de dados de e-commerce do Mercado Livre.

Analise os seguintes dados de um produto e forneça insights acionáveis:

📦 PRODUTO ANALISADO:
- Título: {produto['titulo']}
- SKU: {produto['sku']}
- Preço Atual: R$ {produto['preco_atual']:.2f}
- Status: {produto['status']}
- Categoria: {produto['categoria']}
- Estoque: {produto['estoque_disponivel']} unidades
- Vendidos (ML): {produto['quantidade_vendida']} unidades

📊 MÉTRICAS DE VENDAS ({total_pedidos} pedidos analisados):
- Total de Pedidos: {metricas['total_pedidos']}
- Pedidos Pagos: {metricas['pedidos_pagos']}
- Receita Total: R$ {metricas['receita_total']:.2f}
- Ticket Médio: R$ {metricas['ticket_medio']:.2f}
- Comissões ML: R$ {metricas['comissoes_ml_total']:.2f}
- Líquido Total: R$ {metricas['liquido_total']:.2f}

{f"🏆 CONCORRÊNCIA: {total_concorrentes} concorrentes no catálogo" if total_concorrentes > 0 else ""}

DADOS COMPLETOS (JSON):
{json.dumps(data, indent=2, ensure_ascii=False)}

Por favor, forneça uma análise estruturada em formato HTML contendo:

1. **RESUMO EXECUTIVO** (3-4 pontos principais)
2. **ANÁLISE DE PERFORMANCE** (vendas, conversão, tendências)
3. **ANÁLISE FINANCEIRA** (lucratividade, custos, oportunidades)
4. **RECOMENDAÇÕES ESTRATÉGICAS** (ações concretas prioritárias)
{f"5. **POSICIONAMENTO COMPETITIVO** (vs concorrentes)" if total_concorrentes > 0 else ""}

Use HTML para formatação: <strong>, <ul>, <li>, <em>, etc.
Seja específico, prático e focado em ações."""

        return prompt
    
    def _call_chatgpt(self, prompt: str) -> Dict:
        """Chama a API do ChatGPT"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-4o-mini",  # Modelo mais econômico
                "messages": [
                    {
                        "role": "system",
                        "content": "Você é um analista experiente de e-commerce e marketplace do Mercado Livre, especializado em pricing, estratégia competitiva e otimização de vendas. Forneça análises práticas e acionáveis em português do Brasil."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            logger.info("Chamando API ChatGPT...")
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis = result['choices'][0]['message']['content']
                tokens_used = result['usage']['total_tokens']
                
                logger.info(f"Análise concluída. Tokens usados: {tokens_used}")
                
                return {
                    "success": True,
                    "analysis": analysis,
                    "tokens_used": tokens_used
                }
            else:
                logger.error(f"Erro na API ChatGPT: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"Erro na API ChatGPT: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Erro ao chamar ChatGPT: {e}", exc_info=True)
            return {"success": False, "error": f"Erro de comunicação: {str(e)}"}

