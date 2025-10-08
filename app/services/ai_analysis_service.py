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
    
    def analyze_product(self, product_id: int, company_id: int, catalog_data: Optional[List] = None, 
                       pricing_analysis: Optional[Dict] = None) -> Dict:
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
            analysis_data = self._prepare_analysis_data(product, orders, catalog_data, pricing_analysis)
            
            # 4. Criar prompt para ChatGPT
            prompt = self._create_analysis_prompt(analysis_data)
            
            # 5. Chamar API ChatGPT
            response = self._call_chatgpt(prompt)
            
            if response["success"]:
                return {
                    "success": True,
                    "analysis": response["analysis"],
                    "tokens_used": response.get("tokens_used", 0),
                    "debug_info": {
                        "data_sent": analysis_data,
                        "prompt_sent": prompt
                    }
                }
            else:
                return {"success": False, "error": response.get("error")}
            
        except Exception as e:
            logger.error(f"Erro na análise com IA: {e}", exc_info=True)
            return {"success": False, "error": f"Erro ao processar análise: {str(e)}"}
    
    def _prepare_analysis_data(self, product: MLProduct, orders: List[MLOrder], 
                               catalog_data: Optional[List] = None, pricing_analysis: Optional[Dict] = None) -> Dict:
        """Prepara dados estruturados para análise"""
        
        # Dados do produto
        product_data = {
            "id_ml": product.ml_item_id,
            "titulo": product.title,
            "descricao": product.description if product.description else "Sem descrição disponível",
            "sku": product.seller_sku,
            "preco_atual": float(product.price) if product.price else 0,
            "preco_base": float(product.base_price) if product.base_price else None,
            "preco_original": float(product.original_price) if product.original_price else None,
            "status": product.status.value if hasattr(product.status, 'value') else str(product.status),
            "categoria": product.category_name,
            "domain_id": product.domain_id,
            "estoque_disponivel": product.available_quantity,
            "quantidade_vendida": product.sold_quantity,
            "condicao": product.condition,
            "tipo_envio": product.shipping,
            "tem_video": bool(product.video_id),
            "sale_terms": product.sale_terms,
            "warranty": product.warranty,
            "health": product.health,
            "attributes": product.attributes,
            "variations": product.variations,
            "tags": product.tags
        }
        
        # Adicionar análise de custos e preços se fornecida
        if pricing_analysis:
            product_data["analise_custos"] = pricing_analysis
        
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
        
        # Dados do catálogo (concorrentes) com posicionamento
        competitors_data = []
        your_position = None
        
        if catalog_data:
            for idx, comp in enumerate(catalog_data, 1):  # Enviar todos os concorrentes
                comp_data = {
                    "posicao": idx,
                    "vendedor": comp.get("seller_nickname", "N/A"),
                    "preco": comp.get("price", 0),
                    "envio": comp.get("shipping_type", "N/A"),
                    "envio_gratis": comp.get("free_shipping", False),
                    "mercado_lider": comp.get("mercado_lider_level", "none"),
                    "vendas": comp.get("sold_quantity", 0)
                }
                competitors_data.append(comp_data)
                
                # Identificar posição do produto atual
                if comp.get("ml_item_id") == product.ml_item_id:
                    your_position = idx
        
        return {
            "produto": product_data,
            "posicionamento": {
                "sua_posicao": your_position,
                "total_concorrentes": len(competitors_data)
            } if your_position else None,
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
        posicionamento = data.get("posicionamento")
        custos = produto.get("analise_custos", {})
        
        prompt = f"""Você é um especialista em análise de dados de e-commerce do Mercado Livre.

Analise os seguintes dados de um produto e forneça insights acionáveis:

📦 PRODUTO ANALISADO:
- Título: {produto['titulo']}
- Descrição Completa: {produto.get('descricao', 'N/A')}
- SKU: {produto['sku']}
- Preço Atual: R$ {produto['preco_atual']:.2f}
- Status: {produto['status']}
- Categoria: {produto['categoria']}
- Estoque: {produto['estoque_disponivel']} unidades
- Vendidos (ML): {produto['quantidade_vendida']} unidades

💰 ANÁLISE DETALHADA DE CUSTOS E LUCRO:
{json.dumps(custos, indent=2, ensure_ascii=False) if custos else 'Dados de custos não disponíveis'}

📊 MÉTRICAS DE VENDAS ({total_pedidos} pedidos analisados):
- Total de Pedidos: {metricas['total_pedidos']}
- Pedidos Pagos: {metricas['pedidos_pagos']}
- Receita Total: R$ {metricas['receita_total']:.2f}
- Ticket Médio: R$ {metricas['ticket_medio']:.2f}
- Comissões ML: R$ {metricas['comissoes_ml_total']:.2f}
- Líquido Total: R$ {metricas['liquido_total']:.2f}

{f"🏆 POSICIONAMENTO NO CATÁLOGO: {posicionamento['sua_posicao']}º de {posicionamento['total_concorrentes']} anunciantes" if posicionamento and posicionamento.get('sua_posicao') else ""}
{f"🏆 CONCORRÊNCIA: {total_concorrentes} concorrentes no catálogo" if total_concorrentes > 0 else ""}

DADOS COMPLETOS (JSON):
{json.dumps(data, indent=2, ensure_ascii=False)}

Por favor, forneça uma análise estruturada DIRETAMENTE EM HTML PURO (sem blocos de código markdown):

<h2>1. RESUMO EXECUTIVO</h2>
<ul>
  <li>Performance geral e situação atual</li>
  <li>Principais oportunidades</li>
  <li>Principais riscos/alertas</li>
</ul>

<h2>2. ANÁLISE DE PERFORMANCE DE VENDAS</h2>
<p>Análise detalhada de vendas, conversão e tendências...</p>

<h2>3. ANÁLISE FINANCEIRA</h2>
<p>Lucratividade, custos, margens e oportunidades de otimização...</p>

<h2>4. RECOMENDAÇÕES ESTRATÉGICAS</h2>
<ul>
  <li><strong>Ação 1:</strong> Descrição...</li>
  <li><strong>Ação 2:</strong> Descrição...</li>
</ul>

{f"<h2>5. POSICIONAMENTO COMPETITIVO</h2><p>Análise vs {total_concorrentes} concorrentes...</p>" if total_concorrentes > 0 else ""}

IMPORTANTE:
- Retorne APENAS HTML puro, sem blocos ```html ou ```
- Use <h2> para seções principais
- Use <ul> e <li> para listas
- Use <strong> para destaques
- Use <p> para parágrafos
- Seja específico e prático"""

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

