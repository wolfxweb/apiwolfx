# Ferramentas: Financeiro

## Visão Geral

Ferramentas para consulta e análise financeira. Permitem ao agente de IA acessar informações sobre contas a receber, contas a pagar, fluxo de caixa e resumos financeiros.

---

## Ferramentas a Serem Criadas

As seguintes ferramentas são necessárias para gestão financeira completa, mas ainda não estão implementadas:

---

## get_accounts_receivable

### Objetivo
Consulta contas a receber, permitindo filtrar por período, status, cliente e categoria.

### Tabelas Associadas
- **accounts_receivable** - Tabela de contas a receber
- **financial_customers** - Tabela de clientes
- **financial_categories** - Tabela de categorias financeiras

### Parâmetros (Propostos)
- **start_date** (string, opcional) - Data inicial no formato YYYY-MM-DD
- **end_date** (string, opcional) - Data final no formato YYYY-MM-DD
- **status** (string, opcional) - Status (pending, paid, overdue, cancelled)
- **customer_id** (integer, opcional) - ID do cliente
- **category_id** (integer, opcional) - ID da categoria
- **limit** (integer, opcional, padrão: 50) - Limite de resultados
- **offset** (integer, opcional, padrão: 0) - Offset para paginação

### Retorno (Proposto)
```json
{
  "accounts": [
    {
      "id": 123,
      "description": "Venda ML - Pedido 123456789",
      "amount": 199.90,
      "due_date": "2025-12-01",
      "status": "pending",
      "customer_name": "Cliente ABC",
      "category_name": "Vendas ML"
    }
  ],
  "total": 1,
  "total_amount": 199.90
}
```

### Status
❌ **Não implementada** - Precisa ser criada

---

## get_accounts_payable

### Objetivo
Consulta contas a pagar, permitindo filtrar por período, status, fornecedor e categoria.

### Tabelas Associadas
- **accounts_payable** - Tabela de contas a pagar
- **financial_suppliers** - Tabela de fornecedores
- **financial_categories** - Tabela de categorias financeiras

### Parâmetros (Propostos)
- **start_date** (string, opcional) - Data inicial no formato YYYY-MM-DD
- **end_date** (string, opcional) - Data final no formato YYYY-MM-DD
- **status** (string, opcional) - Status (pending, paid, overdue, cancelled)
- **supplier_id** (integer, opcional) - ID do fornecedor
- **category_id** (integer, opcional) - ID da categoria
- **limit** (integer, opcional, padrão: 50) - Limite de resultados
- **offset** (integer, opcional, padrão: 0) - Offset para paginação

### Retorno (Proposto)
```json
{
  "accounts": [
    {
      "id": 456,
      "description": "Compra de produtos - Fornecedor XYZ",
      "amount": 500.00,
      "due_date": "2025-12-15",
      "status": "pending",
      "supplier_name": "Fornecedor XYZ",
      "category_name": "Compras"
    }
  ],
  "total": 1,
  "total_amount": 500.00
}
```

### Status
❌ **Não implementada** - Precisa ser criada

---

## get_cashflow

### Objetivo
Consulta fluxo de caixa, mostrando entradas e saídas por período.

### Tabelas Associadas
- **accounts_receivable** - Tabela de contas a receber
- **accounts_payable** - Tabela de contas a pagar
- **financial_transactions** - Tabela de transações financeiras
- **financial_accounts** - Tabela de contas bancárias

### Parâmetros (Propostos)
- **start_date** (string, obrigatório) - Data inicial no formato YYYY-MM-DD
- **end_date** (string, obrigatório) - Data final no formato YYYY-MM-DD
- **account_id** (integer, opcional) - ID da conta bancária (se não informado, retorna todas)
- **group_by** (string, opcional) - Agrupamento: "day", "week", "month" (padrão: "day")

### Retorno (Proposto)
```json
{
  "period": {
    "start_date": "2025-11-01",
    "end_date": "2025-11-30"
  },
  "summary": {
    "total_inflows": 10000.00,
    "total_outflows": 5000.00,
    "net_flow": 5000.00
  },
  "daily_flows": [
    {
      "date": "2025-11-01",
      "inflows": 500.00,
      "outflows": 200.00,
      "net": 300.00
    }
  ]
}
```

### Status
❌ **Não implementada** - Precisa ser criada

---

## get_financial_summary

### Objetivo
Obtém resumo financeiro geral, incluindo saldo atual, contas a receber/pagar, fluxo previsto e indicadores.

### Tabelas Associadas
- **accounts_receivable** - Tabela de contas a receber
- **accounts_payable** - Tabela de contas a pagar
- **financial_accounts** - Tabela de contas bancárias
- **financial_transactions** - Tabela de transações financeiras

### Parâmetros (Propostos)
- **date** (string, opcional) - Data de referência no formato YYYY-MM-DD (padrão: hoje)
- **include_projected** (boolean, opcional, padrão: true) - Se deve incluir valores projetados

### Retorno (Proposto)
```json
{
  "date": "2025-11-23",
  "current_balance": 50000.00,
  "accounts_receivable": {
    "total": 10000.00,
    "pending": 8000.00,
    "overdue": 2000.00
  },
  "accounts_payable": {
    "total": 5000.00,
    "pending": 4000.00,
    "overdue": 1000.00
  },
  "projected_balance_30_days": 55000.00,
  "indicators": {
    "liquidity_ratio": 10.0,
    "days_receivable": 30,
    "days_payable": 15
  }
}
```

### Status
❌ **Não implementada** - Precisa ser criada

---

## Resumo das Ferramentas

| Ferramenta | Objetivo | Status |
|------------|----------|--------|
| get_accounts_receivable | Consulta contas a receber | ❌ Não implementada |
| get_accounts_payable | Consulta contas a pagar | ❌ Não implementada |
| get_cashflow | Consulta fluxo de caixa | ❌ Não implementada |
| get_financial_summary | Resumo financeiro | ❌ Não implementada |

---

## Notas de Implementação

Para implementar essas ferramentas, será necessário:

1. **Integração com serviços existentes**:
   - `FinancialService` - Para consultas financeiras
   - `AccountReceivableService` - Para contas a receber
   - `AccountPayableService` - Para contas a pagar

2. **Validações necessárias**:
   - Verificar se os registros pertencem à empresa do usuário
   - Validar períodos de datas
   - Calcular indicadores financeiros

3. **Tratamento de erros**:
   - Período inválido
   - Conta não encontrada
   - Erro ao calcular indicadores

---

**Última atualização**: Novembro 2025

