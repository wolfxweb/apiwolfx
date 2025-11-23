# Ferramentas: Pedidos e Vendas

## Visão Geral

Ferramentas para consulta de pedidos do Mercado Livre e análise de vendas. Permitem ao agente de IA acessar informações sobre pedidos, vendas, receitas e faturamento.

---

## get_orders

### Objetivo
Seleciona pedidos do Mercado Livre com múltiplos filtros opcionais, permitindo consultas flexíveis e complexas.

### Tabelas Associadas
- **ml_orders** - Tabela principal de pedidos ML
- **ml_products** - Tabela de produtos (para filtros por produto)

### Parâmetros
- **start_date** (string, opcional) - Data inicial no formato YYYY-MM-DD
- **end_date** (string, opcional) - Data final no formato YYYY-MM-DD
- **status** (string ou array, opcional) - Status do pedido (ex: "paid", "delivered", "cancelled")
- **ml_item_id** (string, opcional) - ID do item no Mercado Livre
- **product_name** (string, opcional) - Nome do produto (busca parcial)
- **seller_sku** (string, opcional) - SKU do produto
- **is_catalog** (boolean, opcional) - Se true, apenas produtos de catálogo; se false, apenas não-catálogo
- **buyer_nickname** (string, opcional) - Nome do comprador (busca parcial)
- **limit** (integer, opcional) - Limite de resultados (se não informado e houver filtros, retorna todos)
- **offset** (integer, opcional, padrão: 0) - Offset para paginação

### Retorno
```json
{
  "orders": [
    {
      "id": "123456789",
      "date": "2025-11-23T10:30:00",
      "total_amount": 199.90,
      "status": "paid",
      "sale_fees": 19.99,
      "shipping_cost": 15.00,
      "coupon_amount": 0.00,
      "buyer_nickname": "comprador123"
    }
  ],
  "total": 1
}
```

### Exemplo de Uso
```
get_orders({
  "start_date": "2025-11-01",
  "end_date": "2025-11-30",
  "status": "paid",
  "limit": 50
})
```

### Observações
- Se houver filtros além do company_id, o limite é ignorado (retorna todos os resultados)
- Status pode ser uma string única ou array de strings
- Filtros por produto (ml_item_id, product_name, seller_sku) são combinados com OR
- Resultados ordenados por data de criação (mais recentes primeiro)

---

## get_product_sales

### Objetivo
Lista vendas de um produto específico, incluindo quantidade vendida em cada pedido.

### Tabelas Associadas
- **ml_orders** - Tabela principal de pedidos ML
- **ml_products** - Tabela de produtos (para resolução de product_id)

### Parâmetros
- **product_id** (integer, opcional) - ID interno do produto
- **ml_item_id** (string, opcional) - ID do item no Mercado Livre
- **start_date** (string, opcional) - Data inicial no formato YYYY-MM-DD
- **end_date** (string, opcional) - Data final no formato YYYY-MM-DD
- **status** (string ou array, opcional) - Status do pedido
- **limit** (integer, opcional, padrão: 50) - Limite de resultados
- **offset** (integer, opcional, padrão: 0) - Offset para paginação

**Nota**: É obrigatório informar `product_id` OU `ml_item_id` (um dos dois).

### Retorno
```json
{
  "sales": [
    {
      "order_id": "123456789",
      "date": "2025-11-23T10:30:00",
      "status": "paid",
      "total_amount": 199.90,
      "quantity": 2
    }
  ]
}
```

### Exemplo de Uso
```
get_product_sales({
  "product_id": 123,
  "start_date": "2025-11-01",
  "end_date": "2025-11-30",
  "status": ["paid", "delivered"]
})
```

### Observações
- A quantidade (`quantity`) é a soma de todas as unidades do produto naquele pedido
- Se o produto não aparecer no pedido, o pedido não é incluído nos resultados
- Resultados ordenados por data de criação (mais recentes primeiro)

---

## get_orders_by_item

### Objetivo
Busca pedidos que contêm um item específico do Mercado Livre, retornando informações resumidas dos pedidos.

### Tabelas Associadas
- **ml_orders** - Tabela principal de pedidos ML

### Parâmetros
- **ml_item_id** (string, obrigatório) - ID do item no Mercado Livre
- **days** (integer, opcional, padrão: 30) - Número de dias para trás a partir de hoje

### Retorno
```json
{
  "orders": [
    {
      "id": "123456789",
      "date": "2025-11-23T10:30:00",
      "total_amount": 199.90,
      "status": "paid",
      "sale_fees": 19.99,
      "shipping_cost": 15.00,
      "coupon_amount": 0.00
    }
  ]
}
```

### Exemplo de Uso
```
get_orders_by_item({
  "ml_item_id": "MLB123456789",
  "days": 60
})
```

### Observações
- Busca apenas pedidos dos últimos N dias (padrão: 30)
- Retorna apenas pedidos que contêm o item especificado
- Ignora pedidos malformados (sem order_items)

---

## get_sales_aggregates

### Objetivo
Calcula agregações de vendas de um produto, incluindo receita total, quantidade vendida, ticket médio por pedido e preço médio por unidade.

### Tabelas Associadas
- **ml_orders** - Tabela principal de pedidos ML

### Parâmetros
- **ml_item_id** (string, obrigatório) - ID do item no Mercado Livre
- **days** (integer, opcional, padrão: 30) - Número de dias para trás a partir de hoje

### Retorno
```json
{
  "receita_total": 1999.00,
  "pedidos_pagos": 10,
  "quantidade_vendida": 20,
  "ticket_medio_pedido": 199.90,
  "preco_medio_unidade": 99.95
}
```

### Exemplo de Uso
```
get_sales_aggregates({
  "ml_item_id": "MLB123456789",
  "days": 30
})
```

### Observações
- Considera apenas pedidos com status "paid" ou "delivered" para contar pedidos pagos
- `ticket_medio_pedido` = receita_total / pedidos_pagos
- `preco_medio_unidade` = receita_total / quantidade_vendida
- A quantidade vendida é a soma de todas as unidades do produto em todos os pedidos

---

## get_billing_breakdown

### Objetivo
Calcula breakdown detalhado de faturamento de um produto, incluindo receita, comissões, frete e descontos.

### Tabelas Associadas
- **ml_orders** - Tabela principal de pedidos ML

### Parâmetros
- **ml_item_id** (string, obrigatório) - ID do item no Mercado Livre
- **days** (integer, opcional, padrão: 30) - Número de dias para trás a partir de hoje

### Retorno
```json
{
  "receita_total": 1999.00,
  "comissoes_ml_total": 199.90,
  "frete_total": 150.00,
  "descontos_total": 50.00,
  "faturamento_liquido": 1599.10
}
```

### Exemplo de Uso
```
get_billing_breakdown({
  "ml_item_id": "MLB123456789",
  "days": 30
})
```

### Observações
- `faturamento_liquido` = receita_total - comissoes_ml_total - frete_total - descontos_total
- Considera todos os pedidos que contêm o item, independente do status
- Valores em reais (R$)

---

## get_order_details

### Objetivo
Obtém os detalhes completos de um pedido específico do Mercado Livre, incluindo todos os itens do pedido, dados do comprador, envio, pagamentos, taxas e demais informações.

### Tabelas Associadas
- **ml_orders** - Tabela principal de pedidos ML

### Parâmetros
- **order_id** (string ou integer, obrigatório) - ID do pedido (pode ser `ml_order_id` ou `order_id`)
- **include_items** (boolean, opcional, padrão: true) - Se deve incluir detalhes completos dos itens
- **include_shipping** (boolean, opcional, padrão: true) - Se deve incluir detalhes de envio
- **include_payments** (boolean, opcional, padrão: true) - Se deve incluir detalhes de pagamentos
- **include_billing** (boolean, opcional, padrão: true) - Se deve incluir breakdown de billing

### Retorno
```json
{
  "pedido": {
    "id_pedido": "123456789",
    "numero_pedido": "123456789-001",
    "status": "paid",
    "status_detalhe": "Pagamento aprovado",
    "data_criacao": "2025-11-23T10:30:00",
    "data_fechamento": "2025-11-23T11:00:00",
    "valor_total": 199.90,
    "valor_pago": 199.90
  },
  "comprador": {
    "apelido": "comprador123",
    "email": "comprador@email.com",
    "nome": "João",
    "sobrenome": "Silva"
  },
  "itens": [
    {
      "id_anuncio": "MLB123456789",
      "titulo": "Produto ABC",
      "quantidade": 2,
      "preco_unitario": 99.95,
      "preco_total": 199.90,
      "sku": "PROD-001"
    }
  ],
  "envio": {
    "custo": 15.00,
    "metodo": "me2",
    "status": "ready_to_ship",
    "data_envio": "2025-11-24T08:00:00"
  },
  "pagamentos": [
    {
      "metodo": "credit_card",
      "status": "approved",
      "valor": 199.90
    }
  ],
  "taxas": {
    "total": 19.99,
    "venda": 19.99
  },
  "resumo": {
    "total_itens": 2,
    "subtotal": 199.90,
    "frete": 15.00,
    "taxas": 19.99,
    "total": 214.89
  }
}
```

### Exemplo de Uso
```
get_order_details({
  "order_id": "123456789",
  "include_items": true,
  "include_shipping": true
})
```

### Observações
- O `order_id` pode ser o `ml_order_id` (BigInteger) ou o `order_id` (String)
- Retorna todos os itens do pedido com detalhes completos
- Inclui dados do comprador, envio, pagamentos e taxas
- Todos os campos estão traduzidos para português
- Valores monetários são números (float)

### Status
❌ **Não implementada** - Precisa ser criada

---

## Resumo das Ferramentas

| Ferramenta | Objetivo | Status |
|------------|----------|--------|
| get_orders | Seleciona pedidos com filtros | ✅ Implementada |
| get_product_sales | Lista vendas de um produto | ✅ Implementada |
| get_orders_by_item | Busca pedidos por item | ✅ Implementada |
| get_sales_aggregates | Agregações de vendas | ✅ Implementada |
| get_billing_breakdown | Breakdown de faturamento | ✅ Implementada |
| get_order_details | Detalhes completos de um pedido | ❌ Não implementada |

---

**Última atualização**: Novembro 2025

