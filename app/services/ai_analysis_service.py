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

# System Prompt - Define o comportamento geral da IA
SYSTEM_PROMPT = """Você é um especialista em análise de produtos para marketplaces como Mercado Livre, capaz de avaliar anúncios de forma detalhada, identificando pontos fortes, fracos e oportunidades de melhoria.

A tarefa é analisar o JSON do produto fornecido e gerar um relatório completo com base nos seguintes critérios:

1️⃣ **Dados Gerais do Produto**
- Confirme o título, descrição, categoria, SKU, preço, condição, estoque, envio, garantia, status e se é Mercado Líder.
- Identifique a posição do produto no marketplace (se disponível).

2️⃣ **Análise Financeira e Margem**
- Calcule a margem de lucro real: `(preço de venda - custo total) / preço de venda * 100`.
- Compare com a margem esperada e destaque diferenças.
- Sugira ações para melhorar a margem, se necessário (ex: reduzir custos, ajustar preço, negociar fornecedor).

3️⃣ **Análise de Concorrência**
- Liste TODOS os concorrentes do mesmo produto (informados no JSON) em uma tabela com APENAS 3 colunas:
  - Posição no catálogo
  - Nome do vendedor (campo "vendedor")
  - Preço (formate em R$ XX,XX com vírgula para decimais)
- NÃO inclua colunas de Envio, Status ML ou Vendas na tabela (mantenha apenas Posição, Vendedor e Preço)
- Calcule a média de preços dos concorrentes e avalie se meu produto está competitivo/caro/barato.
- Gere sugestão de preço competitivo formatado em R$ XX,XX, se aplicável.

4️⃣ **SEO – Título e Descrição**
- Verifique se o título é claro, relevante e otimizado para SEO (marca, modelo, característica, tipo de produto, menos de 60 caracteres).
- Avalie se a descrição é completa, organizada, com palavras-chave relevantes, benefícios, diferenciais e coerente com título e atributos.
- Sugira melhorias de SEO para título e descrição.

5️⃣ **Atributos do Produto**
- Confira se todos os atributos obrigatórios e recomendados estão preenchidos.
- Liste atributos faltantes ou incoerentes.
- Sugira valores prováveis para preenchimento.
- Avalie a completude e pontue de 0 a 10.

6️⃣ **Mídia**
- Verifique quantidade e qualidade das imagens e vídeos.
- Avalie coerência das imagens com o produto.
- Sugira melhorias (ex: adicionar imagens, reorganizar ordem, incluir vídeo).

7️⃣ **Reputação e Feedback** (se disponível)
- Analise nota média, quantidade de avaliações, elogios e reclamações.
- Gere diagnóstico da reputação e sugestões de ações.

8️⃣ **Recomendações Estratégicas**
- Gere pelo menos 5 recomendações práticas para melhorar:
  1. Margem de lucro
  2. Competitividade de preço
  3. SEO e visibilidade
  4. Conversão de vendas
  5. Reputação e avaliação geral

9️⃣ **Conclusão Geral**
- Resuma diagnóstico final:
  - 💚 Forte/Bom: rentável e competitivo
  - 🟡 Médio: precisa melhorar
  - 🔴 Fraco: requer ação imediata
- Destaque pontos fortes, fracos e oportunidades
- Priorize ações (Alta / Média / Baixa)

🔟 **Score Geral do Anúncio**
- Gere pontuação de 0 a 100 considerando todos os critérios acima.
- Classifique nível (Excelente, Bom, Médio, Fraco, Péssimo) e explique o resultado em 2–3 frases.

⚠️ **IMPORTANTE - FORMATAÇÃO:**
- TODOS os valores monetários JÁ ESTÃO EM REAIS no JSON (não multiplique nem divida)
- Apenas formate para o padrão brasileiro: R$ XX,XX (com vírgula para decimais)
- Use tabelas HTML completas com todos os dados disponíveis no JSON
- Seja específico e use os dados reais fornecidos, não invente informações
- Na tabela de concorrentes, use APENAS 3 colunas: Posição, Vendedor, Preço
- A taxa de conversão é baseada em (vendidos / estoque inicial), que pode incluir cancelamentos"""

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
            
            # Valores já estão em reais (não dividir por 100)
            total_amount = float(order.total_amount) if order.total_amount else 0
            sale_fees = float(order.sale_fees) if order.sale_fees else 0
            shipping_cost = float(order.shipping_cost) if order.shipping_cost else 0
            coupon_amount = float(order.coupon_amount) if order.coupon_amount else 0
            unit_price_reais = float(unit_price) if unit_price else 0  # Já em reais
            
            order_data = {
                "id_pedido": str(order.ml_order_id),
                "data": order.date_created.isoformat() if order.date_created else None,
                "quantidade": quantity,
                "preco_unitario": unit_price_reais,  # Já em reais
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
        
        prompt = f"""Analise o seguinte produto do Mercado Livre e gere um relatório estruturado em HTML seguindo EXATAMENTE os critérios definidos.

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

Por favor, forneça uma análise estruturada DIRETAMENTE EM HTML PURO (sem blocos de código markdown) seguindo EXATAMENTE esta estrutura:

<h2>1️⃣ Dados Gerais do Produto</h2>
<table class="table table-sm">
  <tr><td><strong>Título:</strong></td><td>[título]</td></tr>
  <tr><td><strong>Descrição:</strong></td><td>[resumo breve da descrição]</td></tr>
  <tr><td><strong>Categoria:</strong></td><td>[categoria]</td></tr>
  <tr><td><strong>SKU:</strong></td><td>[SKU]</td></tr>
  <tr><td><strong>Preço:</strong></td><td>R$ [valor]</td></tr>
  <tr><td><strong>Condição:</strong></td><td>[nova/usada]</td></tr>
  <tr><td><strong>Estoque:</strong></td><td>[quantidade]</td></tr>
  <tr><td><strong>Envio:</strong></td><td>[tipo de envio]</td></tr>
  <tr><td><strong>Garantia:</strong></td><td>[sim/não + detalhes]</td></tr>
  <tr><td><strong>Status:</strong></td><td>[ativo/pausado]</td></tr>
  <tr><td><strong>Tipo de Anúncio:</strong></td><td>[gold_special/free/etc]</td></tr>
  {f"<tr><td><strong>Posição no Catálogo:</strong></td><td>{posicionamento['sua_posicao']}º de {posicionamento['total_concorrentes']}</td></tr>" if posicionamento and posicionamento.get('sua_posicao') else ""}
</table>

<h2>2️⃣ Análise Financeira e Margem</h2>
<div class="alert alert-info">
  <p><strong>Cálculo da Margem Real:</strong></p>
  <ul>
    <li>Preço de Venda: R$ {produto['preco_atual']:.2f}</li>
    <li>Custos Totais: R$ [calcular da analise_custos]</li>
    <li>Margem Real: [calcular] %</li>
    <li>Margem Esperada: [se disponível] %</li>
  </ul>
  <p><strong>Diagnóstico:</strong> [análise se margem está boa/média/ruim]</p>
  <p><strong>Ações para melhorar margem:</strong></p>
  <ul>
    <li>[sugestão 1]</li>
    <li>[sugestão 2]</li>
  </ul>
</div>

<h2>3️⃣ Análise de Concorrência</h2>
{f"<p>Comparando com <strong>{total_concorrentes} concorrentes</strong> no mesmo catálogo:</p>" if total_concorrentes > 0 else "<p>Sem dados de concorrência disponíveis.</p>"}
{f'''<table class="table table-sm table-striped">
  <thead class="table-light">
    <tr>
      <th>Posição</th>
      <th>Vendedor</th>
      <th>Preço</th>
    </tr>
  </thead>
  <tbody>
    [Liste TODOS os concorrentes do JSON "concorrentes" usando EXATAMENTE estes campos:
     - posicao: número da posição
     - vendedor: nome do vendedor (campo "vendedor")
     - preco: formate em reais brasileiros (R$ XX,XX) com vírgula para decimais
    
    Exemplo de linha:
    <tr>
      <td>1</td>
      <td>Nome do Vendedor</td>
      <td>R$ 58,00</td>
    </tr>
    
    Crie UMA linha para CADA concorrente do array "concorrentes".]
  </tbody>
</table>''' if total_concorrentes > 0 else ''}
<p><strong>Avaliação:</strong> Meu produto está [competitivo/caro/barato] em relação à média (R$ [média formatada em XX,XX]).</p>
<p><strong>Sugestão de Preço Competitivo:</strong> R$ [valor sugerido em XX,XX] (justificativa detalhada)</p>

<h2>4️⃣ SEO – Título e Descrição</h2>
<div class="mb-3">
  <h5>📝 Análise do Título:</h5>
  <p>Título atual: <em>"{produto['titulo']}"</em></p>
  <ul>
    <li>✅/❌ Claro e relevante</li>
    <li>✅/❌ Otimizado para SEO (marca, modelo, características)</li>
    <li>✅/❌ Tamanho adequado (ideal: menos de 60 caracteres, atual: [X] caracteres)</li>
  </ul>
  <p><strong>Sugestão de melhoria:</strong> [título otimizado]</p>
</div>
<div class="mb-3">
  <h5>📄 Análise da Descrição:</h5>
  <ul>
    <li>✅/❌ Completa e organizada</li>
    <li>✅/❌ Com palavras-chave relevantes</li>
    <li>✅/❌ Destaca benefícios e diferenciais</li>
    <li>✅/❌ Coerente com título e atributos</li>
  </ul>
  <p><strong>Sugestões de melhoria:</strong></p>
  <ul>
    <li>[sugestão 1]</li>
    <li>[sugestão 2]</li>
  </ul>
</div>

<h2>5️⃣ Atributos do Produto</h2>
<p>Total de atributos preenchidos: <strong>{produto.get('total_atributos', 0)}</strong></p>
<div class="alert alert-warning">
  <p><strong>Atributos faltantes ou incoerentes:</strong></p>
  <ul>
    <li>[listar atributos faltantes]</li>
  </ul>
  <p><strong>Sugestões de valores:</strong></p>
  <ul>
    <li>[sugestão de preenchimento]</li>
  </ul>
</div>
<p><strong>Pontuação de Completude:</strong> [X]/10</p>

<h2>6️⃣ Análise de Mídia</h2>
<div class="row">
  <div class="col-md-6">
    <h5>📸 Imagens ({produto.get('total_imagens', 0)} fotos)</h5>
    <ul>
      <li>Quantidade: {"✅ Adequada" if produto.get('total_imagens', 0) >= 5 else "⚠️ Adicionar mais imagens"}</li>
      <li>Qualidade: [analisar baseado nas imagens]</li>
      <li>Coerência: [avaliar se imagens correspondem ao produto]</li>
    </ul>
    <p><strong>Sugestões:</strong></p>
    <ul>
      <li>[sugestão de melhoria de imagens]</li>
    </ul>
  </div>
  <div class="col-md-6">
    <h5>🎥 Vídeo</h5>
    <p>{"✅ Tem vídeo" if produto.get('tem_video') else "❌ Sem vídeo"}</p>
    {f'<p>Vídeo pode aumentar conversão em até 80%. <strong>Recomendação: Adicionar vídeo demonstrativo.</strong></p>' if not produto.get('tem_video') else '<p>Excelente! Vídeo ajuda muito na conversão.</p>'}
  </div>
</div>

<h2>7️⃣ Reputação e Performance</h2>
<p><strong>Histórico de Vendas:</strong></p>
<ul>
  <li>Total de pedidos: {metricas['total_pedidos']} (baseado em pedidos sincronizados)</li>
  <li>Pedidos pagos/entregues: {metricas['pedidos_pagos']} (baseado em pedidos sincronizados)</li>
  <li>Quantidade vendida (ML): {produto['quantidade_vendida']} unidades</li>
  <li>Receita média estimada: R$ {(produto['quantidade_vendida'] * metricas['ticket_medio']):.2f} (quantidade vendida × ticket médio)</li>
  <li>Ticket médio: R$ {metricas['ticket_medio']:.2f}</li>
</ul>

<h2>8️⃣ Recomendações Estratégicas</h2>
<div class="alert alert-success">
  <p><strong>TOP 5 AÇÕES PRIORITÁRIAS:</strong></p>
  <ol>
    <li><strong>Margem de Lucro:</strong> [ação específica]</li>
    <li><strong>Competitividade de Preço:</strong> [ação específica]</li>
    <li><strong>SEO e Visibilidade:</strong> [ação específica]</li>
    <li><strong>Conversão de Vendas:</strong> [ação específica]</li>
    <li><strong>Reputação:</strong> [ação específica]</li>
  </ol>
</div>

<h2>9️⃣ Conclusão Geral</h2>
<div class="card border-[cor]">
  <div class="card-body">
    <h5>[💚 Forte/Bom | 🟡 Médio | 🔴 Fraco]</h5>
    <p><strong>Resumo:</strong> [2-3 frases sobre diagnóstico geral]</p>
    <p><strong>✅ Pontos Fortes:</strong></p>
    <ul><li>[ponto 1]</li><li>[ponto 2]</li></ul>
    <p><strong>⚠️ Pontos Fracos:</strong></p>
    <ul><li>[ponto 1]</li><li>[ponto 2]</li></ul>
    <p><strong>🎯 Oportunidades:</strong></p>
    <ul><li>[oportunidade 1]</li><li>[oportunidade 2]</li></ul>
    
    <p><strong>Priorização de Ações:</strong></p>
    <ul>
      <li>🔴 <strong>Alta Prioridade:</strong> [ação]</li>
      <li>🟡 <strong>Média Prioridade:</strong> [ação]</li>
      <li>🟢 <strong>Baixa Prioridade:</strong> [ação]</li>
    </ul>
  </div>
</div>

<h2>🔟 Score Geral do Anúncio</h2>
<div class="text-center p-4 bg-light rounded">
  <h1 class="display-4">[X]/100</h1>
  <h5>[Excelente/Bom/Médio/Fraco/Péssimo]</h5>
  <p class="lead">[Explicação do score em 2-3 frases, justificando a pontuação]</p>
</div>

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
                "model": "gpt-4.1-nano",  # Modelo que funcionava antes
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 4000,  # Parâmetro padrão para gpt-4.1-nano
                "stream": False  # Desabilitar streaming para evitar timeouts
            }
            
            logger.info("Chamando API ChatGPT com gpt-4.1-nano...")
            logger.info(f"Payload keys: {list(payload.keys())}")
            logger.info(f"Max tokens: {payload.get('max_tokens')}")
            logger.info(f"Temperature: {payload.get('temperature')}")
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=180  # Aumentado para 3 minutos devido ao volume de dados
            )
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Response JSON keys: {list(result.keys())}")
                
                analysis = result['choices'][0]['message']['content']
                tokens_used = result['usage']['total_tokens']
                
                logger.info(f"✅ Análise concluída. Tokens usados: {tokens_used}")
                logger.info(f"📝 Tamanho da análise: {len(analysis)} caracteres")
                logger.info(f"Preview: {analysis[:200]}...")
                
                return {
                    "success": True,
                    "analysis": analysis,
                    "tokens_used": tokens_used
                }
            else:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_message = error_json.get('error', {}).get('message', error_detail)
                except:
                    error_message = error_detail
                
                logger.error(f"Erro na API ChatGPT: {response.status_code} - {error_detail}")
                return {
                    "success": False,
                    "error": f"Erro na API ChatGPT ({response.status_code}): {error_message}"
                }
                
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout ao chamar ChatGPT (esperou 180s): {e}", exc_info=True)
            return {"success": False, "error": "A análise está demorando mais que o esperado. Tente novamente em alguns instantes ou reduza a quantidade de dados."}
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de conexão ao chamar ChatGPT: {e}", exc_info=True)
            return {"success": False, "error": f"Erro de comunicação com a API: {str(e)}"}
        except Exception as e:
            logger.error(f"Erro inesperado ao chamar ChatGPT: {e}", exc_info=True)
            return {"success": False, "error": f"Erro inesperado: {str(e)}"}

