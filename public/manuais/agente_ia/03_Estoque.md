# Ferramentas: Estoque

## Visão Geral

Ferramentas para gestão e consulta de estoque de produtos. Permitem ao agente de IA consultar estoque, movimentações e sincronizar com Mercado Livre.

---

## Ferramentas a Serem Criadas

As seguintes ferramentas são necessárias para gestão completa de estoque, mas ainda não estão implementadas:

---

## get_stock_by_product

### Objetivo
Consulta o estoque atual de um produto, incluindo quantidade disponível, reservada e em diferentes depósitos.

### Tabelas Associadas
- **product_stocks** - Tabela de estoque de produtos
- **warehouses** - Tabela de depósitos
- **internal_products** - Tabela de produtos internos
- **sku_management** - Tabela de associação SKU

### Parâmetros (Propostos)
- **product_id** (integer, opcional) - ID interno do produto
- **internal_product_id** (integer, opcional) - ID do produto interno
- **ml_item_id** (string, opcional) - ID do item no Mercado Livre
- **warehouse_id** (integer, opcional) - ID do depósito (se não informado, retorna todos)

### Retorno (Proposto)
```json
{
  "product_id": 123,
  "internal_product_id": 456,
  "warehouses": [
    {
      "warehouse_id": 1,
      "warehouse_name": "Depósito Principal",
      "available_quantity": 50,
      "reserved_quantity": 5
    }
  ],
  "total_available": 50,
  "total_reserved": 5
}
```

### Status
❌ **Não implementada** - Precisa ser criada

---

## get_stock_movements

### Objetivo
Lista movimentações de estoque de um produto, permitindo rastrear histórico de entradas e saídas.

### Tabelas Associadas
- **stock_movements** - Tabela de movimentações de estoque
- **product_stocks** - Tabela de estoque de produtos
- **internal_products** - Tabela de produtos internos

### Parâmetros (Propostos)
- **product_id** (integer, opcional) - ID interno do produto
- **internal_product_id** (integer, opcional) - ID do produto interno
- **start_date** (string, opcional) - Data inicial no formato YYYY-MM-DD
- **end_date** (string, opcional) - Data final no formato YYYY-MM-DD
- **movement_type** (string, opcional) - Tipo de movimentação (entrada, saida, ajuste)
- **limit** (integer, opcional, padrão: 50) - Limite de resultados
- **offset** (integer, opcional, padrão: 0) - Offset para paginação

### Retorno (Proposto)
```json
{
  "movements": [
    {
      "id": 789,
      "date": "2025-11-23T10:30:00",
      "type": "saida",
      "quantity": -2,
      "notes": "Venda - Pedido 123456789",
      "warehouse_id": 1,
      "warehouse_name": "Depósito Principal"
    }
  ],
  "total": 1
}
```

### Status
❌ **Não implementada** - Precisa ser criada

---

## update_stock_quantity

### Objetivo
Atualiza a quantidade de estoque de um produto, permitindo ajustes manuais ou automáticos.

### Tabelas Associadas
- **product_stocks** - Tabela de estoque de produtos
- **stock_movements** - Tabela de movimentações de estoque
- **internal_products** - Tabela de produtos internos

### Parâmetros (Propostos)
- **internal_product_id** (integer, obrigatório) - ID do produto interno
- **warehouse_id** (integer, opcional) - ID do depósito (se não informado, atualiza depósito padrão)
- **quantity** (integer, obrigatório) - Quantidade a adicionar/subtrair (pode ser negativo)
- **notes** (string, opcional) - Observações sobre a movimentação
- **movement_type** (string, opcional) - Tipo de movimentação (entrada, saida, ajuste)

### Retorno (Proposto)
```json
{
  "success": true,
  "product_id": 123,
  "internal_product_id": 456,
  "warehouse_id": 1,
  "previous_quantity": 50,
  "new_quantity": 52,
  "movement_id": 789
}
```

### Status
❌ **Não implementada** - Precisa ser criada

### Observações
- A quantidade pode ser positiva (entrada) ou negativa (saída)
- Cria automaticamente um registro em `stock_movements`
- Valida se há estoque suficiente antes de permitir saída

---

## sync_stock_to_ml

### Objetivo
Sincroniza o estoque interno com os anúncios do Mercado Livre, atualizando a quantidade disponível em todos os anúncios associados ao SKU.

### Tabelas Associadas
- **product_stocks** - Tabela de estoque de produtos
- **sku_management** - Tabela de associação SKU
- **ml_products** - Tabela de produtos ML
- **ml_accounts** - Tabela de contas ML

### Parâmetros (Propostos)
- **internal_product_id** (integer, obrigatório) - ID do produto interno
- **ml_account_id** (integer, opcional) - ID da conta ML (se não informado, sincroniza todas as contas ativas)

### Retorno (Proposto)
```json
{
  "success": true,
  "internal_product_id": 456,
  "synced_announcements": [
    {
      "ml_item_id": "MLB123456789",
      "ml_account_id": 1,
      "previous_quantity": 50,
      "new_quantity": 48,
      "status": "success"
    }
  ],
  "total_synced": 1,
  "errors": []
}
```

### Status
❌ **Não implementada** - Precisa ser criada

### Observações
- Sincroniza apenas produtos "normais" (não Full/fulfillment)
- Ignora anúncios com status CLOSED, PAUSED ou INACTIVE
- Atualiza todos os anúncios associados ao SKU em todas as contas ML ativas

---

## Resumo das Ferramentas

| Ferramenta | Objetivo | Status |
|------------|----------|--------|
| get_stock_by_product | Consulta estoque de produto | ❌ Não implementada |
| get_stock_movements | Lista movimentações | ❌ Não implementada |
| update_stock_quantity | Atualiza quantidade | ❌ Não implementada |
| sync_stock_to_ml | Sincroniza com ML | ❌ Não implementada |

---

## Notas de Implementação

Para implementar essas ferramentas, será necessário:

1. **Integração com serviços existentes**:
   - `StockService` - Para consultas e atualizações de estoque
   - `StockMovementService` - Para movimentações
   - `SKUManagementService` - Para associações SKU

2. **Validações necessárias**:
   - Verificar se o produto pertence à empresa do usuário
   - Validar se há estoque suficiente antes de permitir saída
   - Verificar status do anúncio antes de sincronizar

3. **Tratamento de erros**:
   - Produto não encontrado
   - Estoque insuficiente
   - Erro na sincronização com ML
   - Anúncio não encontrado

---

**Última atualização**: Novembro 2025

