# Ajustes Necessários nas Ferramentas do Agente IA

## Objetivo

Este documento lista todos os ajustes necessários nas ferramentas implementadas para melhorar a qualidade das respostas do agente de IA e garantir que os dados retornados sejam adequados para apresentação ao usuário.

---

## Regra Principal: Tradução de Nomes de Colunas

**IMPORTANTE**: As ferramentas NÃO podem retornar nomes de colunas do banco de dados para o prompt de respostas. Todos os nomes devem ser traduzidos para português e usar nomenclatura amigável.

### Exemplos de Tradução:
- `ml_item_id` → `id_anuncio_ml` ou `codigo_anuncio`
- `seller_sku` → `sku` ou `codigo_produto`
- `available_quantity` → `estoque_disponivel` ou `quantidade_disponivel`
- `category_id` → `categoria` ou `id_categoria`
- `listing_type_id` → `tipo_anuncio` ou `tipo_listagem`
- `date_created` → `data_criacao` ou `data`
- `total_amount` → `valor_total` ou `total`
- `sale_fees` → `comissoes` ou `taxas_venda`
- `shipping_cost` → `frete` ou `custo_envio`
- `coupon_amount` → `desconto` ou `valor_desconto`
- `buyer_nickname` → `comprador` ou `nome_comprador`
- `order_items` → `itens` ou `produtos`
- `ml_order_id` → `id_pedido` ou `numero_pedido`

---

## Análise por Ferramenta

### 1. get_product_core

#### Problemas Identificados:
- ✅ Retorna `ml_item_id` (deveria ser `codigo_anuncio` ou `id_anuncio_ml`)
- ✅ Retorna `available_quantity` (deveria ser `estoque_disponivel`)
- ✅ Retorna `category_id` (deveria ser `categoria` ou `id_categoria`)
- ✅ Retorna `listing_type_id` (deveria ser `tipo_anuncio`)
- ✅ Retorna `seller_sku` (deveria ser `sku` ou `codigo_produto`)

#### Ajustes Necessários:
```python
return {
    "id": p.id,
    "codigo_anuncio": p.ml_item_id,  # era ml_item_id
    "preco": float(p.price) if p.price else None,  # era price
    "estoque_disponivel": p.available_quantity,  # era available_quantity
    "categoria": p.category_id,  # era category_id
    "tipo_anuncio": p.listing_type_id,  # era listing_type_id
    "sku": p.seller_sku,  # era seller_sku
    "titulo": p.title,  # era title
}
```

---

### 2. get_product_attributes

#### Problemas Identificados:
- ✅ Retorna nomes em inglês: `attributes`, `variations`, `shipping`, `tags`, `health`
- ⚠️ Retorna objetos JSON complexos que podem conter nomes de colunas internos

#### Ajustes Necessários:
```python
return {
    "atributos": p.attributes,  # era attributes
    "variacoes": p.variations,  # era variations
    "envio": p.shipping,  # era shipping
    "tags": p.tags,  # era tags (pode manter)
    "saude_anuncio": p.health,  # era health
}
```

**Nota**: Se os objetos JSON internos (`attributes`, `variations`, etc.) contiverem nomes de colunas, será necessário processar recursivamente para traduzir.

---

### 3. get_orders_by_item

#### Problemas Identificados:
- ✅ Retorna `ml_item_id` no parâmetro (OK, é entrada)
- ✅ Retorna `id` (deveria ser `id_pedido` ou `numero_pedido`)
- ✅ Retorna `date` (deveria ser `data` ou `data_criacao`)
- ✅ Retorna `total_amount` (deveria ser `valor_total`)
- ✅ Retorna `status` (OK, pode manter)
- ✅ Retorna `sale_fees` (deveria ser `comissoes`)
- ✅ Retorna `shipping_cost` (deveria ser `frete`)
- ✅ Retorna `coupon_amount` (deveria ser `desconto`)

#### Ajustes Necessários:
```python
result.append({
    "id_pedido": str(o.ml_order_id),  # era "id"
    "data": o.date_created.isoformat() if o.date_created else None,  # era "date"
    "valor_total": float(o.total_amount) if o.total_amount else 0,  # era "total_amount"
    "status": status_str,  # OK manter
    "comissoes": float(o.sale_fees) if o.sale_fees else 0,  # era "sale_fees"
    "frete": float(o.shipping_cost) if o.shipping_cost else 0,  # era "shipping_cost"
    "desconto": float(o.coupon_amount) if o.coupon_amount else 0,  # era "coupon_amount"
})
```

---

### 4. get_sales_aggregates

#### Problemas Identificados:
- ✅ Retorna nomes em português (bom!), mas pode melhorar:
  - `receita_total` → OK
  - `pedidos_pagos` → OK
  - `quantidade_vendida` → OK
  - `ticket_medio_pedido` → OK
  - `preco_medio_unidade` → OK

#### Ajustes Necessários:
- ✅ Esta ferramenta já está bem traduzida, apenas garantir formatação de valores monetários

---

### 5. get_billing_breakdown

#### Problemas Identificados:
- ✅ Retorna nomes em português (bom!)
  - `receita_total` → OK
  - `comissoes_ml_total` → OK (pode simplificar para `comissoes`)
  - `frete_total` → OK (pode simplificar para `frete`)
  - `descontos_total` → OK (pode simplificar para `descontos`)
  - `faturamento_liquido` → OK

#### Ajustes Necessários:
- ✅ Já está bem traduzida, apenas considerar simplificar nomes se necessário

---

### 6. get_orders

#### Problemas Identificados:
- ✅ Retorna `orders` (deveria ser `pedidos`)
- ✅ Retorna `id` (deveria ser `id_pedido`)
- ✅ Retorna `date` (deveria ser `data`)
- ✅ Retorna `total_amount` (deveria ser `valor_total`)
- ✅ Retorna `status` (OK)
- ✅ Retorna `sale_fees` (deveria ser `comissoes`)
- ✅ Retorna `shipping_cost` (deveria ser `frete`)
- ✅ Retorna `coupon_amount` (deveria ser `desconto`)
- ✅ Retorna `buyer_nickname` (deveria ser `comprador`)
- ✅ Retorna `total` (OK, pode manter ou usar `total_pedidos`)

#### Ajustes Necessários:
```python
return {
    "pedidos": result,  # era "orders"
    "total_pedidos": len(result)  # era "total"
}

# E dentro de cada pedido:
result.append({
    "id_pedido": str(getattr(o, "ml_order_id", getattr(o, "id", None))),  # era "id"
    "data": o.date_created.isoformat() if getattr(o, "date_created", None) else None,  # era "date"
    "valor_total": float(o.total_amount) if getattr(o, "total_amount", None) else 0.0,  # era "total_amount"
    "status": status_str,  # OK
    "comissoes": float(o.sale_fees) if getattr(o, "sale_fees", None) else 0.0,  # era "sale_fees"
    "frete": float(o.shipping_cost) if getattr(o, "shipping_cost", None) else 0.0,  # era "shipping_cost"
    "desconto": float(o.coupon_amount) if getattr(o, "coupon_amount", None) else 0.0,  # era "coupon_amount"
    "comprador": getattr(o, "buyer_nickname", None)  # era "buyer_nickname"
})
```

---

### 7. get_product_sales

#### Problemas Identificados:
- ✅ Retorna `sales` (deveria ser `vendas`)
- ✅ Retorna `order_id` (deveria ser `id_pedido`)
- ✅ Retorna `date` (deveria ser `data`)
- ✅ Retorna `status` (OK)
- ✅ Retorna `total_amount` (deveria ser `valor_total`)
- ✅ Retorna `quantity` (deveria ser `quantidade`)

#### Ajustes Necessários:
```python
return {
    "vendas": results  # era "sales"
}

# E dentro de cada venda:
results.append({
    "id_pedido": str(getattr(o, "ml_order_id", getattr(o, "id", None))),  # era "order_id"
    "data": o.date_created.isoformat() if getattr(o, "date_created", None) else None,  # era "date"
    "status": status_str,  # OK
    "valor_total": float(o.total_amount) if getattr(o, "total_amount", None) else 0.0,  # era "total_amount"
    "quantidade": qty  # era "quantity"
})
```

---

### 8. get_catalog_competitors_db

#### Problemas Identificados:
- ✅ Retorna `competitors` (deveria ser `concorrentes`)
- ⚠️ Retorna dados do serviço `MLCatalogService` que podem conter nomes de colunas em inglês

#### Ajustes Necessários:
```python
return {
    "concorrentes": items[offset: offset + limit]  # era "competitors"
}
```

**Nota**: Verificar o retorno de `MLCatalogService.get_product_catalog_competitors()` e garantir que os dados internos também estejam traduzidos.

---

### 9. get_ads_metrics_by_item

#### Problemas Identificados:
- ⚠️ Retorna dados do serviço `MLProductAdsService` que podem conter nomes de colunas em inglês
- ⚠️ Precisa verificar o formato do retorno do serviço

#### Ajustes Necessários:
- Verificar o retorno de `MLProductAdsService.get_product_advertising_metrics()` e traduzir todos os campos:
  - `investment` → `investimento`
  - `clicks` → `cliques`
  - `impressions` → `impressoes`
  - `conversions` → `conversoes`
  - `revenue` → `receita`
  - `roas` → `roas` (pode manter sigla)
  - `acos` → `acos` (pode manter sigla)
  - `cpc` → `cpc` (pode manter sigla)
  - `ctr` → `ctr` (pode manter sigla)

---

### 10. compute_margin_db

#### Problemas Identificados:
- ✅ Retorna `profit` (deveria ser `lucro`)
- ✅ Retorna `margin_percent` (deveria ser `margem_percentual` ou `margem`)

#### Ajustes Necessários:
```python
return {
    "lucro": profit,  # era "profit"
    "margem_percentual": margin_percent  # era "margin_percent"
}
```

---

### 11. simulate_price_candidates

#### Problemas Identificados:
- ✅ Retorna `candidates` (deveria ser `candidatos`)
- ✅ Retorna `price` (deveria ser `preco`)
- ✅ Retorna `profit` (deveria ser `lucro`)
- ✅ Retorna `margin_percent` (deveria ser `margem_percentual`)

#### Ajustes Necessários:
```python
return {
    "candidatos": sims  # era "candidates"
}

# E dentro de cada candidato:
sims.append({
    "preco": price,  # era "price"
    "lucro": profit,  # era "profit"
    "margem_percentual": margin_percent  # era "margin_percent"
})
```

---

### 12. check_title_description_db

#### Problemas Identificados:
- ✅ Retorna `title` (deveria ser `titulo`)
- ✅ Retorna `issues` (deveria ser `problemas` ou `alertas`)

#### Ajustes Necessários:
```python
return {
    "titulo": title,  # era "title"
    "problemas": issues  # era "issues"
}
```

---

### 13. search_products_by_name

#### Problemas Identificados:
- ✅ Retorna `results` (deveria ser `resultados`)
- ✅ Retorna `id` (OK, pode manter)
- ✅ Retorna `title` (deveria ser `titulo`)
- ✅ Retorna `seller_sku` (deveria ser `sku`)
- ✅ Retorna `ml_item_id` (deveria ser `codigo_anuncio`)
- ✅ Retorna `price` (deveria ser `preco`)

#### Ajustes Necessários:
```python
return {
    "resultados": results  # era "results"
}

# E dentro de cada resultado:
results.append({
    "id": p.id,  # OK manter
    "titulo": p.title,  # era "title"
    "sku": p.seller_sku,  # era "seller_sku"
    "codigo_anuncio": p.ml_item_id,  # era "ml_item_id"
    "preco": float(p.price) if p.price else None  # era "price"
})
```

---

### 14. resolve_product_by_code

#### Problemas Identificados:
- ✅ Retorna `found` (deveria ser `encontrado`)
- ✅ Retorna `product` (deveria ser `produto`)
- ✅ Dentro de `product`, retorna `id` (OK)
- ✅ Dentro de `product`, retorna `title` (deveria ser `titulo`)
- ✅ Dentro de `product`, retorna `seller_sku` (deveria ser `sku`)
- ✅ Dentro de `product`, retorna `ml_item_id` (deveria ser `codigo_anuncio`)
- ✅ Dentro de `product`, retorna `price` (deveria ser `preco`)

#### Ajustes Necessários:
```python
if not product:
    return {"encontrado": False}  # era "found"

return {
    "encontrado": True,  # era "found"
    "produto": {  # era "product"
        "id": product.id,  # OK manter
        "titulo": product.title,  # era "title"
        "sku": product.seller_sku,  # era "seller_sku"
        "codigo_anuncio": product.ml_item_id,  # era "ml_item_id"
        "preco": float(product.price) if product.price else None  # era "price"
    }
}
```

---

## 15. NOVA FERRAMENTA: get_order_details

### Objetivo
Obtém os detalhes completos de um pedido específico do Mercado Livre, incluindo todos os itens do pedido, dados do comprador, envio, pagamentos, taxas e demais informações.

### Justificativa
A tabela `ml_orders` possui uma coluna `order_items` (JSON) que contém todos os itens do pedido, e muitos outros campos detalhados que não são retornados pelas ferramentas atuais. Uma ferramenta específica para obter detalhes completos de um pedido é essencial para análises detalhadas.

### Tabelas Associadas
- **ml_orders** - Tabela principal de pedidos ML

### Parâmetros (Propostos)
- **order_id** (string ou integer, obrigatório) - ID do pedido (pode ser `ml_order_id` ou `order_id`)
- **include_items** (boolean, opcional, padrão: true) - Se deve incluir detalhes completos dos itens
- **include_shipping** (boolean, opcional, padrão: true) - Se deve incluir detalhes de envio
- **include_payments** (boolean, opcional, padrão: true) - Se deve incluir detalhes de pagamentos
- **include_billing** (boolean, opcional, padrão: true) - Se deve incluir breakdown de billing

### Retorno (Proposto)
```json
{
  "pedido": {
    "id_pedido": "123456789",
    "numero_pedido": "123456789-001",
    "status": "paid",
    "status_detalhe": "Pagamento aprovado",
    "data_criacao": "2025-11-23T10:30:00",
    "data_fechamento": "2025-11-23T11:00:00",
    "ultima_atualizacao": "2025-11-23T11:00:00",
    "valor_total": 199.90,
    "valor_pago": 199.90,
    "moeda": "BRL"
  },
  "comprador": {
    "id": "123456789",
    "apelido": "comprador123",
    "email": "comprador@email.com",
    "nome": "João",
    "sobrenome": "Silva",
    "telefone": {...}
  },
  "itens": [
    {
      "id_anuncio": "MLB123456789",
      "titulo": "Produto ABC",
      "quantidade": 2,
      "preco_unitario": 99.95,
      "preco_total": 199.90,
      "sku": "PROD-001",
      "variacao": {...},
      "condicao": "new"
    }
  ],
  "envio": {
    "id": "123456789",
    "custo": 15.00,
    "metodo": "me2",
    "status": "ready_to_ship",
    "endereco": {...},
    "detalhes": {...},
    "tipo": "me2",
    "data_envio": "2025-11-24T08:00:00",
    "data_entrega_estimada": "2025-11-28T18:00:00"
  },
  "pagamentos": [
    {
      "id": "123456789",
      "metodo": "credit_card",
      "tipo": "credit_card",
      "status": "approved",
      "valor": 199.90,
      "parcelas": 1
    }
  ],
  "taxas": {
    "total": 19.99,
    "publicacao": 0.00,
    "venda": 19.99,
    "envio": 0.00,
    "parcelamento": 0.00
  },
  "billing": {
    "detalhes": {...},
    "breakdown_venda": {...},
    "breakdown_marketplace": {...}
  },
  "descontos": {
    "cupom_id": "CUPOM123",
    "valor_cupom": 10.00,
    "descontos_aplicados": [...]
  },
  "publicidade": {
    "venda_por_anuncio": true,
    "campanha_id": "123456789",
    "custo": 5.00,
    "metricas": {...}
  },
  "resumo": {
    "total_itens": 2,
    "subtotal": 199.90,
    "frete": 15.00,
    "descontos": 10.00,
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
  "include_shipping": true,
  "include_payments": true,
  "include_billing": true
})
```

### Observações
- O `order_id` pode ser o `ml_order_id` (BigInteger) ou o `order_id` (String)
- Todos os campos devem estar traduzidos para português
- Objetos JSON aninhados (`order_items`, `shipping_details`, etc.) devem ser processados e traduzidos
- Se o pedido não for encontrado, retornar erro claro em português
- Valores monetários devem ser números (float), não strings

### Status
❌ **Não implementada** - Precisa ser criada

### Prioridade
🔴 **ALTA** - Ferramenta essencial para análises detalhadas de pedidos

---

## Resumo de Ajustes por Categoria

### Traduções Comuns Necessárias:

| Inglês | Português |
|--------|-----------|
| `id` | `id` (manter) ou `id_pedido`, `id_produto` conforme contexto |
| `ml_item_id` | `codigo_anuncio` ou `id_anuncio_ml` |
| `seller_sku` | `sku` ou `codigo_produto` |
| `available_quantity` | `estoque_disponivel` ou `quantidade_disponivel` |
| `category_id` | `categoria` ou `id_categoria` |
| `listing_type_id` | `tipo_anuncio` ou `tipo_listagem` |
| `date` / `date_created` | `data` ou `data_criacao` |
| `total_amount` | `valor_total` ou `total` |
| `sale_fees` | `comissoes` ou `taxas_venda` |
| `shipping_cost` | `frete` ou `custo_envio` |
| `coupon_amount` | `desconto` ou `valor_desconto` |
| `buyer_nickname` | `comprador` ou `nome_comprador` |
| `price` | `preco` |
| `title` | `titulo` |
| `quantity` | `quantidade` |
| `orders` | `pedidos` |
| `sales` | `vendas` |
| `results` | `resultados` |
| `competitors` | `concorrentes` |
| `candidates` | `candidatos` |
| `profit` | `lucro` |
| `margin_percent` | `margem_percentual` ou `margem` |
| `found` | `encontrado` |
| `product` | `produto` |
| `issues` | `problemas` ou `alertas` |

---

## Outras Melhorias Necessárias

### 1. Formatação de Valores Monetários
- Todos os valores monetários devem ser retornados como números (float), não como strings
- Considerar formatação adicional se necessário para apresentação

### 2. Formatação de Datas
- Datas devem ser retornadas em formato ISO (YYYY-MM-DDTHH:MM:SS) ou apenas data (YYYY-MM-DD)
- Considerar timezone se necessário

### 3. Tratamento de Valores Nulos
- Valores nulos devem ser retornados como `null` (JSON) ou `None` (Python)
- Não retornar strings vazias ou valores padrão confusos

### 4. Validação de Entrada
- Manter validações existentes
- Adicionar validações adicionais se necessário

### 5. Mensagens de Erro
- Todas as mensagens de erro devem estar em português
- Mensagens devem ser claras e objetivas

---

## Priorização dos Ajustes

### Alta Prioridade (Impacto Direto nas Respostas):
1. ✅ `get_product_core` - Traduzir todos os campos
2. ✅ `get_orders` - Traduzir todos os campos
3. ✅ `get_product_sales` - Traduzir todos os campos
4. ✅ `get_orders_by_item` - Traduzir todos os campos
5. ✅ `search_products_by_name` - Traduzir todos os campos
6. ✅ `resolve_product_by_code` - Traduzir todos os campos
7. 🆕 `get_order_details` - **NOVA FERRAMENTA** - Obter detalhes completos de um pedido
8. 🆕 `get_catalog_monitoring_status` - **NOVA FERRAMENTA** - Status e informações do monitoramento de catálogo

### Média Prioridade (Funcionalidades Importantes):
9. 🆕 `get_suppliers` - **NOVA FERRAMENTA** - Lista fornecedores
10. 🆕 `get_supplier_details` - **NOVA FERRAMENTA** - Detalhes de um fornecedor
11. 🆕 `get_purchase_orders` - **NOVA FERRAMENTA** - Lista ordens de compra
12. 🆕 `get_purchase_order_details` - **NOVA FERRAMENTA** - Detalhes de uma ordem de compra
13. 🆕 `get_supplier_purchase_orders` - **NOVA FERRAMENTA** - Ordens de compra de um fornecedor

### Média Prioridade (Melhorias Importantes):
7. ✅ `get_product_attributes` - Verificar objetos JSON internos
8. ✅ `get_catalog_competitors_db` - Verificar retorno do serviço
9. ✅ `get_ads_metrics_by_item` - Verificar retorno do serviço
10. ✅ `compute_margin_db` - Traduzir campos
11. ✅ `simulate_price_candidates` - Traduzir campos
12. ✅ `check_title_description_db` - Traduzir campos

### Baixa Prioridade (Já Estão Bem):
13. ✅ `get_sales_aggregates` - Já está bem traduzido
14. ✅ `get_billing_breakdown` - Já está bem traduzido

---

## Checklist de Implementação

Para cada ferramenta, verificar:

- [ ] Todos os nomes de campos estão em português
- [ ] Nenhum nome de coluna do banco aparece no retorno
- [ ] Valores monetários estão como números (float)
- [ ] Datas estão em formato ISO
- [ ] Valores nulos estão como `null`
- [ ] Mensagens de erro estão em português
- [ ] Objetos JSON aninhados também estão traduzidos (se aplicável)
- [ ] Retornos de serviços externos estão traduzidos (se aplicável)

### Checklist Específico para get_order_details:

- [ ] Todos os campos do pedido estão traduzidos
- [ ] Array de itens (`order_items`) está processado e traduzido
- [ ] Cada item do pedido tem campos traduzidos (id_anuncio, titulo, quantidade, preco_unitario, etc.)
- [ ] Dados do comprador estão traduzidos
- [ ] Dados de envio (`shipping_details`) estão traduzidos
- [ ] Array de pagamentos (`payments`) está processado e traduzido
- [ ] Dados de billing (`billing_details`) estão traduzidos
- [ ] Descontos (`discounts_applied`) estão traduzidos
- [ ] Métricas de publicidade (`advertising_metrics`) estão traduzidas
- [ ] Resumo calculado está presente e correto

---

**Última atualização**: Novembro 2025

