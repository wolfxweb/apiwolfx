# Ferramentas: Análises e Relatórios

## Visão Geral

Ferramentas para análises, cálculos e simulações. Permitem ao agente de IA realizar cálculos de margem, simular preços e obter configurações de custos.

---

## compute_margin_db

### Objetivo
Calcula a margem de lucro de um produto com base no preço de venda, custos e percentuais de impostos e marketing.

### Tabelas Associadas
- Nenhuma (cálculo puro)

### Parâmetros
- **sale_price** (float, obrigatório) - Preço de venda do produto
- **product_cost** (float, obrigatório) - Custo do produto
- **taxes_percent** (float, opcional, padrão: 0) - Percentual de impostos sobre o preço de venda
- **other_costs** (float, opcional, padrão: 0) - Outros custos fixos
- **marketing_percent** (float, opcional, padrão: 0) - Percentual de marketing sobre o preço de venda
- **use_period_averages** (boolean, opcional, padrão: true) - Se deve usar médias do período (placeholder)

### Retorno
```json
{
  "profit": 50.00,
  "margin_percent": 50.0
}
```

### Exemplo de Uso
```
compute_margin_db({
  "sale_price": 100.00,
  "product_cost": 30.00,
  "taxes_percent": 10.0,
  "other_costs": 5.00,
  "marketing_percent": 5.0
})
```

### Observações
- Cálculo: `total_costs = product_cost + other_costs + (sale_price * taxes_percent / 100) + (sale_price * marketing_percent / 100)`
- `profit = sale_price - total_costs`
- `margin_percent = (profit / sale_price) * 100`
- O parâmetro `use_period_averages` é um placeholder e não está implementado ainda

---

## simulate_price_candidates

### Objetivo
Simula diferentes preços candidatos e calcula a margem de lucro para cada um, permitindo análise de estratégia de preços.

### Tabelas Associadas
- Nenhuma (cálculo puro)

### Parâmetros
- **candidates** (array, obrigatório) - Lista de preços candidatos para simular
- **product_cost** (float, obrigatório) - Custo do produto
- **taxes_percent** (float, opcional, padrão: 0) - Percentual de impostos
- **other_costs** (float, opcional, padrão: 0) - Outros custos fixos
- **marketing_percent** (float, opcional, padrão: 0) - Percentual de marketing

### Retorno
```json
{
  "candidates": [
    {
      "price": 90.00,
      "profit": 40.00,
      "margin_percent": 44.44
    },
    {
      "price": 100.00,
      "profit": 50.00,
      "margin_percent": 50.0
    },
    {
      "price": 110.00,
      "profit": 60.00,
      "margin_percent": 54.55
    }
  ]
}
```

### Exemplo de Uso
```
simulate_price_candidates({
  "candidates": [90.00, 100.00, 110.00],
  "product_cost": 30.00,
  "taxes_percent": 10.0,
  "marketing_percent": 5.0
})
```

### Observações
- Calcula margem para cada preço candidato
- Ignora valores inválidos na lista de candidatos
- Útil para análise de estratégia de preços

---

## get_product_cost_config

### Objetivo
Obtém configuração de custos de um produto, incluindo custo do produto, impostos e percentual de marketing.

### Tabelas Associadas
- **internal_products** - Tabela de produtos internos (a ser implementado)
- **companies** - Tabela de empresas (para percentuais padrão)

### Parâmetros
- **product_id** (integer, opcional) - ID do produto (a ser implementado)
- **internal_product_id** (integer, opcional) - ID do produto interno (a ser implementado)

### Retorno (Atual - Placeholder)
```json
{
  "custo_produto": 0.0,
  "impostos_percent": 0.0,
  "marketing_percent": 0.0
}
```

### Status
⚠️ **Placeholder** - Retorna valores padrão, precisa ler tabela de custos

### Observações
- Atualmente retorna valores padrão (0.0)
- Precisa ser implementado para ler custos reais do produto
- Deve considerar custos do produto interno e percentuais da empresa

---

## get_fee_preview_db

### Objetivo
Obtém preview de taxas do Mercado Livre para um preço específico, estimando comissões e taxas.

### Tabelas Associadas
- **ml_products** - Tabela de produtos ML (para obter categoria e listing type)
- Tabela de taxas ML (a ser implementado)

### Parâmetros
- **price** (float, obrigatório) - Preço do produto
- **category_id** (string, opcional) - ID da categoria ML (para cálculo mais preciso)
- **listing_type_id** (string, opcional) - Tipo de listing (gold_special, gold, etc.)

### Retorno (Atual - Placeholder)
```json
{
  "estimated_fee": 0.0,
  "price": 100.00
}
```

### Status
⚠️ **Placeholder** - Retorna taxa zero, precisa calcular taxas reais

### Observações
- Atualmente retorna taxa zero
- Precisa ser implementado para calcular taxas reais baseadas em:
  - Categoria do produto
  - Tipo de listing (gold_special, gold, etc.)
  - Preço do produto
- Pode usar a API do Mercado Livre ou tabela de taxas

---

## get_required_attributes_db

### Objetivo
Obtém lista de atributos obrigatórios e recomendados para uma categoria do Mercado Livre.

### Tabelas Associadas
- Tabela de atributos de categoria ML (a ser implementado)
- Cache de atributos ML (a ser implementado)

### Parâmetros
- **category_id** (string, obrigatório) - ID da categoria ML

### Retorno (Atual - Placeholder)
```json
{
  "required": [],
  "recommended": []
}
```

### Status
⚠️ **Placeholder** - Retorna listas vazias, precisa buscar atributos reais

### Observações
- Atualmente retorna listas vazias
- Precisa ser implementado para buscar atributos reais da categoria
- Pode usar a API do Mercado Livre: `/categories/{category_id}/attributes`
- Deve diferenciar atributos obrigatórios (`required`) de recomendados (`recommended`)

---

## Resumo das Ferramentas

| Ferramenta | Objetivo | Status |
|------------|----------|--------|
| compute_margin_db | Calcula margem de lucro | ✅ Implementada |
| simulate_price_candidates | Simula preços candidatos | ✅ Implementada |
| get_product_cost_config | Obtém configuração de custos | ⚠️ Placeholder |
| get_fee_preview_db | Preview de taxas ML | ⚠️ Placeholder |
| get_required_attributes_db | Atributos obrigatórios | ⚠️ Placeholder |

---

## Notas de Implementação

Para implementar as ferramentas placeholder, será necessário:

1. **get_product_cost_config**:
   - Ler custo do produto da tabela `internal_products`
   - Ler percentuais de impostos e marketing da tabela `companies`
   - Considerar custos específicos do produto se existirem

2. **get_fee_preview_db**:
   - Integrar com API do Mercado Livre ou tabela de taxas
   - Calcular taxas baseadas em categoria e listing type
   - Considerar diferentes tipos de listing (gold_special, gold, etc.)

3. **get_required_attributes_db**:
   - Integrar com API do Mercado Livre: `/categories/{category_id}/attributes`
   - Filtrar atributos por `required` e `recommended`
   - Cachear resultados para melhor performance

---

**Última atualização**: Novembro 2025

