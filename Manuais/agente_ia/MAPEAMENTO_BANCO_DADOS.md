# Mapeamento do Banco de Dados - Ferramentas do Agente IA

Este documento mapeia todas as tabelas e colunas relevantes para as ferramentas do agente IA.

## Tabelas Relacionadas a Pedidos

### ml_orders
Tabela principal de pedidos do Mercado Livre.

**Colunas Principais:**
- `id` (Integer, PK) - ID interno do pedido
- `company_id` (Integer, FK) - ID da empresa
- `ml_account_id` (Integer, FK) - ID da conta ML
- `ml_order_id` (BigInteger, unique) - ID do pedido no Mercado Livre
- `order_id` (String) - Número do pedido
- `status` (Enum OrderStatus) - Status do pedido (PENDING, CONFIRMED, PAID, SHIPPED, DELIVERED, CANCELLED, REFUNDED, etc.)
- `date_created` (DateTime) - Data de criação do pedido
- `date_closed` (DateTime) - Data de fechamento
- `total_amount` (Numeric) - Valor total do pedido
- `paid_amount` (Numeric) - Valor pago
- `sale_fees` (Numeric) - Taxas de venda/comissões
- `shipping_cost` (Numeric) - Custo de frete
- `coupon_amount` (Numeric) - Valor de desconto/cupom
- `buyer_nickname` (String) - Apelido do comprador
- `order_items` (JSON) - Array de itens do pedido (contém item.id, quantity, unit_price)
- `is_advertising_sale` (Boolean) - Se a venda foi por anúncio
- `advertising_cost` (Numeric) - Custo publicitário do pedido
- `advertising_campaign_id` (String) - ID da campanha

**Índices:**
- `ix_ml_orders_company_ml_account` - (company_id, ml_account_id)
- `ix_ml_orders_date_created` - date_created
- `ix_ml_orders_status` - status
- `ix_ml_orders_advertising` - is_advertising_sale

### ml_order_processing_statuses
Status interno de processamento dos pedidos.

**Colunas Principais:**
- `id` (Integer, PK)
- `order_id` (Integer, FK) - Referência a ml_orders.id
- `internal_status` (String) - Status interno
- `notes` (Text) - Observações

## Tabelas Relacionadas a Produtos

### ml_products
Produtos/anúncios do Mercado Livre.

**Colunas Principais:**
- `id` (Integer, PK) - ID interno
- `company_id` (Integer, FK) - ID da empresa
- `ml_account_id` (Integer, FK) - ID da conta ML
- `ml_item_id` (String, unique) - ID do item no Mercado Livre
- `title` (String) - Título do anúncio
- `seller_sku` (String) - SKU do vendedor
- `price` (String) - Preço
- `available_quantity` (Integer) - Quantidade disponível
- `sold_quantity` (Integer) - Quantidade vendida
- `category_id` (String) - ID da categoria
- `status` (Enum MLProductStatus) - Status do produto (active, paused, closed, etc.)
- `catalog_product_id` (String) - ID do produto no catálogo compartilhado
- `catalog_listing` (Boolean) - Se é anúncio de catálogo
- `attributes` (JSON) - Atributos do produto
- `variations` (JSON) - Variações
- `shipping` (JSON) - Configurações de envio
- `health` (JSON) - Status de saúde do anúncio

**Índices:**
- `ix_ml_products_company_account` - (company_id, ml_account_id)
- `ix_ml_products_account_status` - (ml_account_id, status)

### ml_product_attributes
Atributos específicos de produtos.

**Colunas Principais:**
- `id` (Integer, PK)
- `ml_product_id` (Integer, FK) - Referência a ml_products.id
- `attribute_id` (String) - ID do atributo
- `attribute_name` (String) - Nome do atributo
- `value_id` (String) - ID do valor
- `value_name` (String) - Nome do valor

### internal_products
Produtos internos/customizados.

**Colunas Principais:**
- `id` (Integer, PK)
- `company_id` (Integer, FK)
- `name` (String) - Nome do produto
- `sku` (String) - SKU interno

### product_stocks
Estoque de produtos.

**Colunas Principais:**
- `id` (Integer, PK)
- `company_id` (Integer, FK)
- `internal_product_id` (Integer, FK) - Referência a internal_products.id
- `warehouse_id` (Integer, FK) - ID do depósito
- `quantity` (Numeric) - Quantidade disponível
- `reserved_quantity` (Numeric) - Quantidade reservada

## Tabelas Relacionadas a Publicidade

### ml_campaigns
Campanhas de publicidade (Product Ads).

**Colunas Principais:**
- `id` (Integer, PK)
- `company_id` (Integer, FK)
- `ml_account_id` (Integer, FK)
- `campaign_id` (String, unique) - ID da campanha no ML
- `name` (String) - Nome da campanha
- `status` (String) - Status (active, paused, deleted)
- `daily_budget` (Float) - Orçamento diário
- `total_budget` (Float) - Orçamento total
- `total_spent` (Float) - Total gasto
- `total_impressions` (Integer) - Total de impressões
- `total_clicks` (Integer) - Total de cliques
- `total_conversions` (Integer) - Total de conversões
- `total_revenue` (Float) - Receita total

**Índices:**
- `ix_ml_campaigns_company_status` - (company_id, status)
- `ix_ml_campaigns_account_status` - (ml_account_id, status)

### ml_campaign_products
Produtos associados a campanhas.

**Colunas Principais:**
- `id` (Integer, PK)
- `campaign_id` (Integer, FK) - Referência a ml_campaigns.id
- `ml_product_id` (Integer, FK) - Referência a ml_products.id
- `status` (String) - Status (active, paused, removed)
- `impressions` (Integer) - Impressões
- `clicks` (Integer) - Cliques
- `conversions` (Integer) - Conversões
- `spent` (Float) - Gasto
- `revenue` (Float) - Receita

**Índices:**
- `ix_campaign_products_campaign` - campaign_id
- `ix_campaign_products_product` - ml_product_id

### ml_campaign_metrics
Métricas diárias das campanhas.

**Colunas Principais:**
- `id` (Integer, PK)
- `campaign_id` (Integer, FK) - Referência a ml_campaigns.id
- `metric_date` (DateTime) - Data das métricas
- `impressions` (Integer) - Impressões
- `clicks` (Integer) - Cliques
- `spent` (Float) - Gasto (CUSTO PUBLICITÁRIO)
- `ctr` (Float) - Taxa de cliques
- `cpc` (Float) - Custo por clique
- `direct_amount` (Float) - Receita vendas diretas
- `indirect_amount` (Float) - Receita vendas indiretas
- `total_amount` (Float) - Receita total
- `organic_units_amount` (Float) - Receita orgânica
- `acos` (Float) - Custo de publicidade de vendas
- `roas` (Float) - Retorno sobre investimento

**Índices:**
- `ix_campaign_metrics_date` - (campaign_id, metric_date)

## Tabelas Relacionadas a Catálogo

### ml_catalog_monitoring
Monitoramento de catálogo compartilhado.

**Colunas Principais:**
- `id` (Integer, PK)
- `company_id` (Integer, FK)
- `ml_product_id` (Integer, FK) - Referência a ml_products.id
- `catalog_product_id` (String) - ID do produto no catálogo
- `is_active` (Boolean) - Se está ativo
- `activated_at` (DateTime) - Data de ativação
- `last_check_at` (DateTime) - Última verificação

### ml_catalog_history
Histórico de verificações de catálogo.

**Colunas Principais:**
- `id` (Integer, PK)
- `company_id` (Integer, FK)
- `catalog_product_id` (String) - ID do produto no catálogo
- `collected_at` (DateTime) - Data da coleta
- `catalog_data` (JSON) - Dados do catálogo (participants, preços, etc.)

## Relacionamentos Importantes

1. **Pedidos → Produtos**: Via `order_items` (JSON) contendo `item.id` que corresponde a `ml_products.ml_item_id`

2. **Produtos → Campanhas**: Via `ml_campaign_products` (N:N)

3. **Campanhas → Métricas**: Via `ml_campaign_metrics` (1:N)

4. **Pedidos → Publicidade**: Via `is_advertising_sale` e `advertising_cost` em `ml_orders`

5. **Produtos → Catálogo**: Via `catalog_product_id` em `ml_products`

## Campos Não Utilizados pelas Ferramentas (Oportunidades)

1. `ml_orders.advertising_metrics` (JSON) - Métricas detalhadas de publicidade por pedido
2. `ml_products.health` (JSON) - Status de saúde do anúncio
3. `ml_campaigns.bidding_strategy` - Estratégia de lances
4. `ml_campaigns.optimization_goal` - Objetivo de otimização

## Queries Otimizadas

### Contagem de Pedidos
```sql
SELECT COUNT(*) FROM ml_orders 
WHERE company_id = :company_id 
AND [filtros adicionais]
```

### Produtos com Anúncios
```sql
-- Via campanhas ativas
SELECT DISTINCT mp.* FROM ml_products mp
JOIN ml_campaign_products mcp ON mcp.ml_product_id = mp.id
JOIN ml_campaigns mc ON mc.id = mcp.campaign_id
WHERE mc.company_id = :company_id 
AND mc.status = 'active'
AND mcp.status = 'active'

-- Via pedidos com anúncio
SELECT DISTINCT mp.* FROM ml_products mp
WHERE mp.ml_item_id IN (
    SELECT DISTINCT (item->>'id')::text 
    FROM ml_orders, jsonb_array_elements(order_items) AS item
    WHERE company_id = :company_id 
    AND is_advertising_sale = true
)
```

### Despesas Totais de Anúncios
```sql
-- Via pedidos
SELECT SUM(advertising_cost) FROM ml_orders
WHERE company_id = :company_id
AND is_advertising_sale = true
AND advertising_cost > 0

-- Via campanhas
SELECT SUM(spent) FROM ml_campaign_metrics mcm
JOIN ml_campaigns mc ON mc.id = mcm.campaign_id
WHERE mc.company_id = :company_id
AND mcm.spent > 0
```

