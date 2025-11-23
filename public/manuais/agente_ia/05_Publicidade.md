# Ferramentas: Publicidade e Marketing

## Visão Geral

Ferramentas para análise de publicidade e campanhas do Mercado Livre. Permitem ao agente de IA acessar métricas de publicidade, performance de campanhas e custos de marketing.

---

## get_ads_metrics_by_item

### Objetivo
Obtém métricas de publicidade (Product Ads) para um item específico do Mercado Livre, incluindo investimento, cliques, conversões e ROAS.

### Tabelas Associadas
- **ml_campaigns** - Tabela de campanhas de publicidade
- **ml_campaign_products** - Tabela de produtos em campanhas
- **ml_campaign_metrics** - Tabela de métricas de campanhas
- **ml_products** - Tabela de produtos ML

### Parâmetros
- **ml_item_id** (string, obrigatório) - ID do item no Mercado Livre
- **ml_account_id** (integer, obrigatório) - ID da conta ML
- **days** (integer, opcional, padrão: 30) - Número de dias para trás a partir de hoje

### Retorno
```json
{
  "ml_item_id": "MLB123456789",
  "ml_account_id": 1,
  "period_days": 30,
  "metrics": {
    "investment": 500.00,
    "clicks": 1000,
    "impressions": 50000,
    "conversions": 20,
    "revenue": 2000.00,
    "roas": 4.0,
    "acos": 25.0,
    "cpc": 0.50,
    "ctr": 2.0
  }
}
```

### Exemplo de Uso
```
get_ads_metrics_by_item({
  "ml_item_id": "MLB123456789",
  "ml_account_id": 1,
  "days": 30
})
```

### Observações
- Retorna métricas agregadas do período especificado
- ROAS (Return on Ad Spend) = receita / investimento
- ACOS (Advertising Cost of Sales) = (investimento / receita) * 100
- CPC (Custo por Clique) = investimento / cliques
- CTR (Taxa de Cliques) = (cliques / impressões) * 100

---

## get_campaign_performance

### Objetivo
Obtém performance detalhada de uma campanha ou de todas as campanhas ativas, incluindo métricas por produto.

### Tabelas Associadas
- **ml_campaigns** - Tabela de campanhas de publicidade
- **ml_campaign_products** - Tabela de produtos em campanhas
- **ml_campaign_metrics** - Tabela de métricas de campanhas

### Parâmetros (Propostos)
- **campaign_id** (integer, opcional) - ID da campanha (se não informado, retorna todas)
- **ml_account_id** (integer, opcional) - ID da conta ML (se não informado, retorna todas)
- **start_date** (string, opcional) - Data inicial no formato YYYY-MM-DD
- **end_date** (string, opcional) - Data final no formato YYYY-MM-DD
- **status** (string, opcional) - Status da campanha (active, paused, ended)

### Retorno (Proposto)
```json
{
  "campaigns": [
    {
      "id": 123,
      "name": "Campanha Black Friday",
      "ml_account_id": 1,
      "status": "active",
      "metrics": {
        "investment": 1000.00,
        "clicks": 2000,
        "conversions": 50,
        "revenue": 5000.00,
        "roas": 5.0
      },
      "products": [
        {
          "ml_item_id": "MLB123456789",
          "investment": 500.00,
          "revenue": 2500.00,
          "roas": 5.0
        }
      ]
    }
  ],
  "total_campaigns": 1
}
```

### Status
❌ **Não implementada** - Precisa ser criada

---

## get_advertising_costs

### Objetivo
Obtém custos de publicidade agregados por período, permitindo análise de investimento em marketing.

### Tabelas Associadas
- **ml_campaigns** - Tabela de campanhas de publicidade
- **ml_campaign_metrics** - Tabela de métricas de campanhas
- **ml_accounts** - Tabela de contas ML

### Parâmetros (Propostos)
- **start_date** (string, obrigatório) - Data inicial no formato YYYY-MM-DD
- **end_date** (string, obrigatório) - Data final no formato YYYY-MM-DD
- **ml_account_id** (integer, opcional) - ID da conta ML (se não informado, retorna todas)
- **group_by** (string, opcional) - Agrupamento: "day", "week", "month", "campaign" (padrão: "day")

### Retorno (Proposto)
```json
{
  "period": {
    "start_date": "2025-11-01",
    "end_date": "2025-11-30"
  },
  "summary": {
    "total_investment": 5000.00,
    "total_revenue": 20000.00,
    "total_roas": 4.0,
    "total_clicks": 10000,
    "total_conversions": 200
  },
  "daily_costs": [
    {
      "date": "2025-11-01",
      "investment": 200.00,
      "revenue": 800.00,
      "roas": 4.0
    }
  ]
}
```

### Status
❌ **Não implementada** - Precisa ser criada

---

## Resumo das Ferramentas

| Ferramenta | Objetivo | Status |
|------------|----------|--------|
| get_ads_metrics_by_item | Métricas de publicidade por item | ✅ Implementada |
| get_campaign_performance | Performance de campanhas | ❌ Não implementada |
| get_advertising_costs | Custos de publicidade | ❌ Não implementada |

---

## Notas de Implementação

Para implementar as ferramentas pendentes, será necessário:

1. **Integração com serviços existentes**:
   - `MLProductAdsService` - Para métricas de publicidade
   - `CampaignSyncService` - Para sincronização de campanhas
   - `MLCampaignService` - Para gestão de campanhas

2. **Validações necessárias**:
   - Verificar se a conta ML pertence à empresa do usuário
   - Validar períodos de datas
   - Calcular métricas agregadas

3. **Tratamento de erros**:
   - Item não encontrado
   - Conta ML não encontrada
   - Erro ao calcular métricas

---

**Última atualização**: Novembro 2025

