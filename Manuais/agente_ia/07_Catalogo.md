# Ferramentas: Catálogo e Concorrência

## Visão Geral

Ferramentas para monitoramento de catálogo compartilhado do Mercado Livre e análise de concorrência. Permitem ao agente de IA acessar informações sobre concorrentes, preços e posição na Buy Box.

---

## get_catalog_competitors_db

### Objetivo
Lista concorrentes de um produto no catálogo compartilhado do Mercado Livre, incluindo informações sobre preços, vendedores e posição na Buy Box.

### Tabelas Associadas
- **ml_catalog_monitoring** - Tabela de monitoramento de catálogo
- **ml_catalog_history** - Tabela de histórico de catálogo
- **ml_products** - Tabela de produtos ML
- **catalog_participants** - Tabela de participantes do catálogo

### Parâmetros
- **product_id** (integer, obrigatório) - ID interno do produto no sistema
- **limit** (integer, opcional, padrão: 50) - Limite de resultados
- **offset** (integer, opcional, padrão: 0) - Offset para paginação

### Retorno
```json
{
  "competitors": [
    {
      "position": 1,
      "seller_id": 123456789,
      "seller_nickname": "vendedor_abc",
      "price": 99.90,
      "available_quantity": 100,
      "has_buy_box": true,
      "shipping": {
        "free_shipping": true,
        "mode": "me2"
      },
      "status": "active"
    },
    {
      "position": 2,
      "seller_id": 987654321,
      "seller_nickname": "vendedor_xyz",
      "price": 105.00,
      "available_quantity": 50,
      "has_buy_box": false,
      "shipping": {
        "free_shipping": false,
        "mode": "not_specified"
      },
      "status": "active"
    }
  ]
}
```

### Exemplo de Uso
```
get_catalog_competitors_db({
  "product_id": 123,
  "limit": 20,
  "offset": 0
})
```

### Observações
- Retorna concorrentes ordenados por posição no catálogo
- Inclui informações sobre Buy Box (caixa de compra destacada)
- Dados vêm do serviço `MLCatalogService`
- Requer que o produto tenha monitoramento de catálogo ativo

---

## Ferramentas a Serem Criadas

As seguintes ferramentas complementares são necessárias para análise completa de catálogo:

---

## get_catalog_history

### Objetivo
Obtém histórico de mudanças no catálogo, incluindo variações de preço, novos vendedores e mudanças na Buy Box.

### Tabelas Associadas
- **ml_catalog_history** - Tabela de histórico de catálogo
- **ml_catalog_monitoring** - Tabela de monitoramento de catálogo

### Parâmetros (Propostos)
- **product_id** (integer, obrigatório) - ID interno do produto
- **start_date** (string, opcional) - Data inicial no formato YYYY-MM-DD
- **end_date** (string, opcional) - Data final no formato YYYY-MM-DD
- **event_type** (string, opcional) - Tipo de evento (price_change, new_seller, buy_box_change)

### Retorno (Proposto)
```json
{
  "history": [
    {
      "date": "2025-11-23T10:30:00",
      "event_type": "price_change",
      "seller_nickname": "vendedor_abc",
      "previous_price": 100.00,
      "new_price": 99.90,
      "position": 1
    }
  ],
  "total": 1
}
```

### Status
❌ **Não implementada** - Precisa ser criada

---

## get_buy_box_status

### Objetivo
Verifica o status atual da Buy Box para um produto, indicando qual vendedor possui a Buy Box e há quanto tempo.

### Tabelas Associadas
- **ml_catalog_monitoring** - Tabela de monitoramento de catálogo
- **catalog_participants** - Tabela de participantes do catálogo

### Parâmetros (Propostos)
- **product_id** (integer, obrigatório) - ID interno do produto

### Retorno (Proposto)
```json
{
  "has_buy_box": true,
  "seller_id": 123456789,
  "seller_nickname": "vendedor_abc",
  "price": 99.90,
  "since_date": "2025-11-20T08:00:00",
  "days_with_buy_box": 3
}
```

### Status
❌ **Não implementada** - Precisa ser criada

---

## get_catalog_monitoring_status

### Objetivo
Obtém informações sobre o status do monitoramento de catálogo de um produto, incluindo se está ativo, última verificação, histórico recente e estatísticas.

### Tabelas Associadas
- **ml_catalog_monitoring** - Tabela de monitoramento de catálogo
- **ml_catalog_history** - Tabela de histórico de catálogo
- **ml_products** - Tabela de produtos ML

### Parâmetros (Propostos)
- **product_id** (integer, obrigatório) - ID interno do produto
- **include_latest_history** (boolean, opcional, padrão: true) - Se deve incluir dados do histórico mais recente
- **include_statistics** (boolean, opcional, padrão: true) - Se deve incluir estatísticas do monitoramento

### Retorno (Proposto)
```json
{
  "monitoramento": {
    "ativo": true,
    "data_ativacao": "2025-11-01T10:00:00",
    "ultima_verificacao": "2025-11-23T08:00:00",
    "total_verificacoes": 45,
    "id_catalogo": "MLB123456789"
  },
  "historico_recente": {
    "data_coleta": "2025-11-23T08:00:00",
    "total_participantes": 15,
    "posicao_empresa": 3,
    "preco_empresa": 99.90,
    "tem_buy_box": false,
    "vencedor_buy_box": {
      "id_vendedor": "987654321",
      "apelido": "vendedor_xyz",
      "preco": 95.00
    },
    "estatisticas_precos": {
      "menor_preco": 89.90,
      "maior_preco": 120.00,
      "preco_medio": 102.50,
      "preco_mediano": 100.00
    },
    "estatisticas_quantidade": {
      "total_disponivel": 500,
      "total_vendido": 1200
    }
  },
  "estatisticas_gerais": {
    "dias_monitorando": 22,
    "melhor_posicao": 1,
    "pior_posicao": 8,
    "posicao_media": 3.5,
    "vezes_com_buy_box": 5,
    "percentual_tempo_buy_box": 11.1
  }
}
```

### Exemplo de Uso
```
get_catalog_monitoring_status({
  "product_id": 123,
  "include_latest_history": true,
  "include_statistics": true
})
```

### Observações
- Retorna informações sobre o status do monitoramento (ativo/inativo)
- Inclui dados do histórico mais recente se disponível
- Calcula estatísticas gerais baseadas em todo o histórico
- Todos os preços devem ser convertidos de centavos para reais
- Se o produto não tiver monitoramento, retornar erro claro

### Status
❌ **Não implementada** - Precisa ser criada

### Prioridade
🔴 **ALTA** - Ferramenta essencial para consultar status e histórico do monitoramento

---

## Resumo das Ferramentas

| Ferramenta | Objetivo | Status |
|------------|----------|--------|
| get_catalog_competitors_db | Lista concorrentes do catálogo | ✅ Implementada |
| get_catalog_history | Histórico de mudanças | ❌ Não implementada |
| get_buy_box_status | Status da Buy Box | ❌ Não implementada |
| get_catalog_monitoring_status | Status e informações do monitoramento | ❌ Não implementada |

---

## Notas de Implementação

Para implementar as ferramentas pendentes, será necessário:

1. **Integração com serviços existentes**:
   - `MLCatalogService` - Para dados de catálogo
   - `CatalogMonitoringService` - Para monitoramento

2. **Validações necessárias**:
   - Verificar se o produto pertence à empresa do usuário
   - Verificar se o produto tem monitoramento ativo
   - Validar períodos de datas

3. **Tratamento de erros**:
   - Produto não encontrado
   - Monitoramento não ativo
   - Erro ao buscar histórico

---

**Última atualização**: Novembro 2025

