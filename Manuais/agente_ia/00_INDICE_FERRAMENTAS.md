# Índice de Ferramentas do Agente IA

## Sobre este Documento

Este documento lista todas as ferramentas (tools) disponíveis para o agente de IA do sistema SELVEZ. As ferramentas permitem que o agente de IA interaja com o sistema, consultando dados, realizando análises e executando operações.

## Estrutura

As ferramentas estão organizadas por categorias funcionais. Cada categoria possui um documento detalhado explicando todas as ferramentas daquela categoria.

---

## 📦 Categoria: Produtos Mercado Livre

**Arquivo**: `01_Produtos_ML.md`

Ferramentas relacionadas a produtos do Mercado Livre:

- **get_product_core** - Obtém dados básicos de um produto ML
- **get_product_attributes** - Obtém atributos, variações e configurações do produto
- **search_products_by_name** - Busca produtos por nome ou SKU
- **resolve_product_by_code** - Resolve produto por ID, SKU ou ml_item_id
- **check_title_description_db** - Valida título e descrição do produto

---

## 🛒 Categoria: Pedidos e Vendas

**Arquivo**: `02_Pedidos_Vendas.md`

Ferramentas para consulta de pedidos e análise de vendas:

- **get_orders** - Seleciona pedidos com múltiplos filtros (data, status, produto, comprador)
- **get_product_sales** - Lista vendas de um produto específico
- **get_orders_by_item** - Busca pedidos contendo um item específico
- **get_sales_aggregates** - Agregações de vendas (receita, quantidade, ticket médio)
- **get_billing_breakdown** - Breakdown detalhado de faturamento (receita, comissões, frete, descontos)
- **get_order_details** - Detalhes completos de um pedido (incluindo todos os itens, comprador, envio, pagamentos)

---

## 📊 Categoria: Estoque

**Arquivo**: `03_Estoque.md`

Ferramentas para gestão e consulta de estoque:

*Ferramentas a serem criadas:*
- **get_stock_by_product** - Consulta estoque de um produto
- **get_stock_movements** - Lista movimentações de estoque
- **update_stock_quantity** - Atualiza quantidade de estoque
- **sync_stock_to_ml** - Sincroniza estoque com Mercado Livre

---

## 💰 Categoria: Financeiro

**Arquivo**: `04_Financeiro.md`

Ferramentas para consulta e análise financeira:

*Ferramentas a serem criadas:*
- **get_accounts_receivable** - Consulta contas a receber
- **get_accounts_payable** - Consulta contas a pagar
- **get_cashflow** - Consulta fluxo de caixa
- **get_financial_summary** - Resumo financeiro

---

## 📢 Categoria: Publicidade e Marketing

**Arquivo**: `05_Publicidade.md`

Ferramentas para análise de publicidade e campanhas:

- **get_ads_metrics_by_item** - Métricas de publicidade por item ML
- **get_campaign_performance** - Performance de campanhas (a ser criada)
- **get_advertising_costs** - Custos de publicidade (a ser criada)

---

## 🔍 Categoria: Análises e Relatórios

**Arquivo**: `06_Analises.md`

Ferramentas para análises, cálculos e simulações:

- **compute_margin_db** - Calcula margem de lucro
- **simulate_price_candidates** - Simula candidatos de preço com diferentes margens
- **get_product_cost_config** - Obtém configuração de custos do produto (placeholder)
- **get_fee_preview_db** - Preview de taxas do Mercado Livre (placeholder)
- **get_required_attributes_db** - Atributos obrigatórios da categoria (placeholder)

---

## 🏪 Categoria: Catálogo e Concorrência

**Arquivo**: `07_Catalogo.md`

Ferramentas para monitoramento de catálogo e análise de concorrência:

- **get_catalog_competitors_db** - Lista concorrentes do catálogo compartilhado
- **get_catalog_monitoring_status** - Status e informações do monitoramento de catálogo (a ser criada)

---

## 🏭 Categoria: Fornecedores e Ordens de Compra

**Arquivo**: `08_Fornecedores_Ordens.md`

Ferramentas para gestão de fornecedores e ordens de compra:

- **get_suppliers** - Lista fornecedores (a ser criada)
- **get_supplier_details** - Detalhes de um fornecedor (a ser criada)
- **get_purchase_orders** - Lista ordens de compra (a ser criada)
- **get_purchase_order_details** - Detalhes de uma ordem de compra (a ser criada)
- **get_supplier_purchase_orders** - Ordens de compra de um fornecedor (a ser criada)

---

## 🔧 Ferramentas em Desenvolvimento

As seguintes ferramentas estão marcadas como "placeholder" ou "TODO" no código e precisam ser implementadas:

1. **get_product_cost_config** - Atualmente retorna valores padrão, precisa ler tabela de custos
2. **get_fee_preview_db** - Precisa calcular taxas reais baseadas em listing/categoria
3. **get_required_attributes_db** - Precisa retornar atributos reais da categoria ML
4. **get_ml_order_status** - Implementação pendente (mantida para compatibilidade)

---

## 📋 Como Usar as Ferramentas

As ferramentas são automaticamente disponibilizadas para o agente de IA quando:

1. A ferramenta está cadastrada na tabela `openai_tools`
2. A ferramenta está associada ao agente na tabela `openai_agent_tools`
3. A ferramenta está ativa (`is_active = TRUE`)
4. O handler da ferramenta está implementado em `OpenAIAssistantService._execute_tool_function`

---

## 🔗 Tabelas do Banco de Dados Relacionadas

### Tabelas de Ferramentas:
- **openai_tools** - Definição das ferramentas (nome, descrição, schema JSON)
- **openai_tool_handlers** - Handlers das ferramentas (resolução de nomes)
- **openai_agent_tools** - Associação entre agentes e ferramentas (N:N)

### Tabelas de Dados Principais:
- **ml_products** - Produtos do Mercado Livre
- **ml_orders** - Pedidos do Mercado Livre
- **product_stocks** - Estoque de produtos
- **stock_movements** - Movimentações de estoque
- **accounts_receivable** - Contas a receber
- **accounts_payable** - Contas a pagar
- **ml_campaigns** - Campanhas de publicidade
- **ml_campaign_metrics** - Métricas de campanhas

---

## 📚 Documentação Detalhada

Para detalhes completos de cada ferramenta, consulte os arquivos por categoria:

1. [Produtos ML](01_Produtos_ML.md)
2. [Pedidos e Vendas](02_Pedidos_Vendas.md)
3. [Estoque](03_Estoque.md)
4. [Financeiro](04_Financeiro.md)
5. [Publicidade](05_Publicidade.md)
6. [Análises](06_Analises.md)
7. [Catálogo](07_Catalogo.md)

---

**Última atualização**: Novembro 2025

