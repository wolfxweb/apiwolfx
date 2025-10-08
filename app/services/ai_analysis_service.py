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
        
        # Dados do produto - COMPLETO
        product_data = {
            # Identificação
            "id_ml": product.ml_item_id,
            "user_product_id": product.user_product_id,
            "family_id": product.family_id,
            "family_name": product.family_name,
            
            # Títulos e descrição
            "titulo": product.title,
            "subtitulo": product.subtitle,
            "descricao": product.description if product.description else "Sem descrição disponível",
            
            # SKUs
            "sku": product.seller_sku,
            "seller_custom_field": product.seller_custom_field,
            
            # Preços
            "preco_atual": float(product.price) if product.price else 0,
            "preco_base": float(product.base_price) if product.base_price else None,
            "preco_original": float(product.original_price) if product.original_price else None,
            "moeda": product.currency_id,
            
            # Status e tipo
            "status": product.status.value if hasattr(product.status, 'value') else str(product.status),
            "sub_status": product.sub_status,
            "tipo_anuncio": product.listing_type_id,
            "modo_compra": product.buying_mode,
            
            # Categoria e catálogo
            "categoria_id": product.category_id,
            "categoria": product.category_name,
            "domain_id": product.domain_id,
            "e_catalogo": bool(product.catalog_product_id),
            "catalog_product_id": product.catalog_product_id,
            "catalog_listing": product.catalog_listing,
            
            # Quantidades
            "estoque_disponivel": product.available_quantity,
            "quantidade_vendida": product.sold_quantity,
            "quantidade_inicial": product.initial_quantity,
            
            # Condição
            "condicao": product.condition,
            
            # Envio
            "configuracao_envio": product.shipping,
            "frete_gratis": product.free_shipping,
            
            # Mídia
            "tem_video": bool(product.video_id),
            "video_id": product.video_id,
            "total_imagens": len(product.pictures) if product.pictures else 0,
            "imagens": self._analyze_pictures(product.pictures) if product.pictures else [],
            
            # Links
            "permalink": product.permalink,
            
            # Garantia e termos
            "sale_terms": product.sale_terms,
            "warranty": product.warranty,
            
            # Qualidade do anúncio
            "health": product.health,
            
            # Atributos técnicos
            "attributes": product.attributes,
            "total_atributos": len(product.attributes) if product.attributes else 0,
            
            # Variações
            "variations": product.variations,
            "tem_variacoes": bool(product.variations and len(product.variations) > 0),
            "total_variacoes": len(product.variations) if product.variations else 0,
            
            # Tags e promoções
            "tags": product.tags,
            "differential_pricing": product.differential_pricing,
            "deal_ids": product.deal_ids,
            "esta_em_promocao": bool(product.deal_ids and len(product.deal_ids) > 0),
            
            # Datas importantes
            "data_inicio": product.start_time.isoformat() if product.start_time else None,
            "data_fim": product.stop_time.isoformat() if product.stop_time else None,
            "ultima_sincronizacao": product.last_sync.isoformat() if product.last_sync else None,
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

Analise os seguintes dados COMPLETOS de um produto e forneça insights acionáveis:

📦 INFORMAÇÕES DO ANÚNCIO:
- ID ML: {produto['id_ml']}
- Título: {produto['titulo']}
- Subtítulo: {produto.get('subtitulo', 'N/A')}
- Descrição: {produto.get('descricao', 'N/A')}
- SKU: {produto['sku']}
- Tipo de Anúncio: {produto.get('tipo_anuncio', 'N/A')} (investimento em exposição)
- Modo de Compra: {produto.get('modo_compra', 'N/A')}
- Status: {produto['status']}
{f"- Sub-status: {produto.get('sub_status')}" if produto.get('sub_status') else ""}

💰 PREÇOS E PROMOÇÕES:
- Preço Atual: R$ {produto['preco_atual']:.2f}
{f"- Preço Original: R$ {produto['preco_original']:.2f} (com desconto ativo)" if produto.get('preco_original') else ""}
{f"- Em Promoção: Sim (Deal IDs: {produto.get('deal_ids')})" if produto.get('esta_em_promocao') else "- Em Promoção: Não"}

📂 CATEGORIA E CLASSIFICAÇÃO:
- Categoria: {produto['categoria']} (ID: {produto.get('categoria_id')})
{f"- Produto de Catálogo: Sim (ID: {produto.get('catalog_product_id')})" if produto.get('e_catalogo') else "- Produto de Catálogo: Não"}
- Condição: {produto.get('condicao', 'N/A')}

📦 ESTOQUE E VENDAS:
- Estoque Atual: {produto['estoque_disponivel']} unidades
- Quantidade Inicial: {produto.get('quantidade_inicial', 0)} unidades
- Total Vendido (ML): {produto['quantidade_vendida']} unidades
- Taxa de Conversão de Estoque: {(produto['quantidade_vendida'] / produto.get('quantidade_inicial', 1) * 100) if produto.get('quantidade_inicial') and produto.get('quantidade_inicial') > 0 else 0:.1f}%

🚚 ENVIO E LOGÍSTICA:
- Frete Grátis: {"Sim" if produto.get('frete_gratis') else "Não"}
- Configuração de Envio: {json.dumps(produto.get('configuracao_envio', {}), ensure_ascii=False) if produto.get('configuracao_envio') else 'N/A'}

📸 QUALIDADE DAS IMAGENS ({produto.get('total_imagens', 0)} imagens):
{json.dumps(produto.get('imagens', []), indent=2, ensure_ascii=False) if produto.get('imagens') else "Sem imagens"}

🎥 MULTIMÍDIA:
{f"- Vídeo: Sim (YouTube ID: {produto.get('video_id')})" if produto.get('tem_video') else "- Vídeo: Não"}

🔧 ATRIBUTOS TÉCNICOS ({produto.get('total_atributos', 0)} atributos):
{json.dumps(produto.get('attributes', []), indent=2, ensure_ascii=False) if produto.get('attributes') else "Sem atributos"}

🎨 VARIAÇÕES ({produto.get('total_variacoes', 0)} variações):
{json.dumps(produto.get('variations', []), indent=2, ensure_ascii=False) if produto.get('tem_variacoes') and produto.get('variations') else "Sem variações"}

🛡️ GARANTIA E TERMOS:
{f"- Garantia: {produto.get('warranty')}" if produto.get('warranty') else ""}
{f"- Termos de Venda: {json.dumps(produto.get('sale_terms', []), ensure_ascii=False)}" if produto.get('sale_terms') else ""}

💚 SAÚDE DO ANÚNCIO:
{json.dumps(produto.get('health', {}), indent=2, ensure_ascii=False) if produto.get('health') else "Sem dados de saúde"}

🏷️ TAGS E CLASSIFICAÇÕES:
{json.dumps(produto.get('tags', []), ensure_ascii=False) if produto.get('tags') else "Sem tags"}

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
  <li>Performance geral e situação atual do anúncio</li>
  <li>Principais oportunidades identificadas</li>
  <li>Principais riscos e alertas críticos</li>
</ul>

<h2>2. ANÁLISE DO ANÚNCIO (Qualidade e Otimização)</h2>
<p>Avalie:</p>
<ul>
  <li><strong>Título e Descrição:</strong> Qualidade, keywords, apelo comercial</li>
  <li><strong>Imagens:</strong> Quantidade, qualidade (ideal: 1200x1200px), necessidade de melhorias</li>
  <li><strong>Vídeo:</strong> Presença ou ausência, impacto potencial</li>
  <li><strong>Atributos Técnicos:</strong> Completude, relevância</li>
  <li><strong>Tipo de Anúncio:</strong> Se o investimento em {produto.get('tipo_anuncio')} está trazendo retorno</li>
  <li><strong>Health/Saúde:</strong> Status de exposição e qualidade do anúncio</li>
</ul>

<h2>3. ANÁLISE DE PERFORMANCE DE VENDAS</h2>
<p>Análise detalhada considerando:</p>
<ul>
  <li>Taxa de conversão (vendidos vs estoque inicial)</li>
  <li>Tendências de vendas ao longo do tempo</li>
  <li>Impacto de promoções e descontos</li>
  <li>Variações mais vendidas (se houver)</li>
</ul>

<h2>4. ANÁLISE FINANCEIRA E RENTABILIDADE</h2>
<ul>
  <li>Lucratividade atual e margens</li>
  <li>Custos ML (comissões, tipo de anúncio)</li>
  <li>Impacto do frete grátis (se aplicável)</li>
  <li>Oportunidades de otimização de preço</li>
</ul>

<h2>5. ANÁLISE COMPETITIVA E POSICIONAMENTO</h2>
{f"<p>Comparativo com {total_concorrentes} concorrentes no catálogo:</p>" if total_concorrentes > 0 else "<p>Análise de posicionamento:</p>"}
<ul>
  <li>Posicionamento de preço</li>
  <li>Diferenciais competitivos</li>
  <li>Gaps e oportunidades vs concorrência</li>
</ul>

<h2>6. RECOMENDAÇÕES PRÁTICAS (Priorizadas)</h2>
<p><strong>AÇÕES IMEDIATAS (Impacto Alto):</strong></p>
<ul>
  <li><strong>Ação 1:</strong> Descrição específica e passo a passo</li>
  <li><strong>Ação 2:</strong> Descrição específica e passo a passo</li>
</ul>
<p><strong>AÇÕES DE MÉDIO PRAZO:</strong></p>
<ul>
  <li>...</li>
</ul>

<h2>7. ALERTAS E RISCOS</h2>
<ul>
  <li>Pontos críticos que precisam atenção urgente</li>
  <li>Riscos identificados (estoque, competição, custos)</li>
</ul>

IMPORTANTE:
- Retorne APENAS HTML puro, sem blocos ```html ou ```
- Use <h2> para seções principais
- Use <ul> e <li> para listas
- Use <strong> para destaques
- Use <p> para parágrafos
- Seja específico e prático"""

        return prompt
    
    def _analyze_pictures(self, pictures: List[Dict]) -> List[Dict]:
        """Analisa qualidade das imagens do produto"""
        analyzed_pictures = []
        
        for idx, picture in enumerate(pictures):
            max_size = picture.get('max_size', '')
            width, height = 0, 0
            
            if max_size and 'x' in max_size:
                try:
                    parts = max_size.split('x')
                    width = int(parts[0])
                    height = int(parts[1])
                except:
                    pass
            
            # Classificar qualidade conforme recomendações do ML
            if width >= 1200 and height >= 1200:
                quality = "ideal"
                quality_label = "Ideal (1200x1200+)"
            elif width >= 800 or height >= 800:
                quality = "ok"
                quality_label = "OK (800px+, ativa zoom)"
            else:
                quality = "pequena"
                quality_label = "Pequena (menos de 800px)"
            
            analyzed_pictures.append({
                "numero": idx + 1,
                "tamanho": max_size,
                "largura": width,
                "altura": height,
                "qualidade": quality,
                "qualidade_label": quality_label,
                "url": picture.get('secure_url', '')
            })
        
        return analyzed_pictures
    
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

