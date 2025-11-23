# Ferramentas: Produtos Mercado Livre

## Visão Geral

Ferramentas para consulta e análise de produtos do Mercado Livre. Permitem ao agente de IA acessar informações sobre produtos, seus atributos, variações e configurações.

---

## get_product_core

### Objetivo
Obtém os dados básicos (core) de um produto do Mercado Livre, incluindo ID, preço, estoque, categoria e SKU.

### Tabelas Associadas
- **ml_products** - Tabela principal de produtos ML

### Parâmetros
- **product_id** (integer, obrigatório) - ID interno do produto no sistema

### Retorno
```json
{
  "id": 123,
  "ml_item_id": "MLB123456789",
  "price": 99.90,
  "available_quantity": 50,
  "category_id": "MLB1234",
  "listing_type_id": "gold_special",
  "seller_sku": "PROD-001",
  "title": "Nome do Produto"
}
```

### Exemplo de Uso
```
get_product_core({
  "product_id": 123
})
```

### Observações
- Retorna erro se o produto não for encontrado ou não pertencer à empresa do usuário
- O `ml_item_id` é o identificador único do produto no Mercado Livre

---

## get_product_attributes

### Objetivo
Obtém atributos detalhados do produto, incluindo variações, configurações de envio, tags e status de saúde.

### Tabelas Associadas
- **ml_products** - Tabela principal de produtos ML

### Parâmetros
- **product_id** (integer, obrigatório) - ID interno do produto no sistema

### Retorno
```json
{
  "attributes": {...},
  "variations": [...],
  "shipping": {...},
  "tags": [...],
  "health": {...}
}
```

### Exemplo de Uso
```
get_product_attributes({
  "product_id": 123
})
```

### Observações
- Retorna todos os atributos do produto em formato JSON
- Inclui variações (tamanho, cor, etc.) se o produto tiver
- O campo `health` contém informações sobre a saúde do anúncio

---

## search_products_by_name

### Objetivo
Busca produtos por nome ou SKU, permitindo encontrar produtos de forma flexível.

### Tabelas Associadas
- **ml_products** - Tabela principal de produtos ML

### Parâmetros
- **query** (string, obrigatório) - Termo de busca (nome ou SKU)
- **limit** (integer, opcional, padrão: 10) - Número máximo de resultados
- **include_sku** (boolean, opcional, padrão: true) - Se deve buscar também por SKU

### Retorno
```json
{
  "results": [
    {
      "id": 123,
      "title": "Nome do Produto",
      "seller_sku": "PROD-001",
      "ml_item_id": "MLB123456789",
      "price": 99.90
    }
  ]
}
```

### Exemplo de Uso
```
search_products_by_name({
  "query": "notebook",
  "limit": 20,
  "include_sku": true
})
```

### Observações
- A busca é case-insensitive e usa LIKE (busca parcial)
- Se `include_sku` for true, busca tanto no título quanto no SKU
- Resultados ordenados por data de atualização (mais recentes primeiro)

---

## resolve_product_by_code

### Objetivo
Resolve um produto a partir de diferentes tipos de código (ID interno, SKU, ml_item_id), com detecção automática do tipo.

### Tabelas Associadas
- **ml_products** - Tabela principal de produtos ML

### Parâmetros
- **code** (string, obrigatório) - Código do produto (ID, SKU ou ml_item_id)
- **code_type** (string, opcional) - Tipo do código: "id", "seller_sku", "ml_item_id" ou null (auto-detecção)

### Retorno
```json
{
  "found": true,
  "product": {
    "id": 123,
    "title": "Nome do Produto",
    "seller_sku": "PROD-001",
    "ml_item_id": "MLB123456789",
    "price": 99.90
  }
}
```

ou

```json
{
  "found": false
}
```

### Exemplo de Uso
```
resolve_product_by_code({
  "code": "MLB123456789",
  "code_type": "ml_item_id"
})
```

ou com auto-detecção:

```
resolve_product_by_code({
  "code": "123"
})
```

### Observações
- Se `code_type` não for informado, tenta auto-detectar:
  1. Se for numérico, tenta como ID interno
  2. Se começar com "ML", tenta como ml_item_id
  3. Caso contrário, tenta como SKU
- Retorna `found: false` se o produto não for encontrado

---

## check_title_description_db

### Objetivo
Valida o título e descrição do produto, verificando se atendem aos critérios de qualidade (ex: tamanho máximo do título).

### Tabelas Associadas
- **ml_products** - Tabela principal de produtos ML

### Parâmetros
- **product_id** (integer, obrigatório) - ID interno do produto no sistema
- **max_title_length** (integer, opcional, padrão: 60) - Tamanho máximo permitido para o título

### Retorno
```json
{
  "title": "Nome do Produto",
  "issues": [
    "Título acima de 60 caracteres"
  ]
}
```

### Exemplo de Uso
```
check_title_description_db({
  "product_id": 123,
  "max_title_length": 60
})
```

### Observações
- Atualmente verifica apenas o tamanho do título
- O campo `issues` contém uma lista de problemas encontrados
- Pode ser expandido para validar descrição, palavras-chave, etc.

---

## Resumo das Ferramentas

| Ferramenta | Objetivo | Status |
|------------|----------|--------|
| get_product_core | Dados básicos do produto | ✅ Implementada |
| get_product_attributes | Atributos detalhados | ✅ Implementada |
| search_products_by_name | Busca por nome/SKU | ✅ Implementada |
| resolve_product_by_code | Resolve por código | ✅ Implementada |
| check_title_description_db | Valida título/descrição | ✅ Implementada |

---

**Última atualização**: Novembro 2025

