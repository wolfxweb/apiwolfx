# Fluxo de Exclusão de Empresa por Company ID

## Ordem de Exclusão

### 1. Financial Goals (PRIMEIRO - antes de qualquer acesso ao relacionamento)
- `financial_goals` - Deletado primeiro para evitar problemas com cascade

### 2. Tabelas Financeiras (Transações primeiro)
- `financial_transactions` - Referencia customers, suppliers, accounts
- `accounts_receivable` - Contas a receber
- `accounts_payable` - Contas a pagar
- `financial_customers` - Clientes financeiros
- `financial_suppliers` - Fornecedores financeiros
- `financial_accounts` - Contas financeiras
- `financial_categories` - Categorias
- `cost_centers` - Centros de custo
- `financial_planning` → `monthly_planning` - Planejamento (delete monthly primeiro)

### 3. Tabelas de Marketing e Campanhas
- `ml_campaign_products` → `ml_campaigns` - Produtos de campanha primeiro
- `ml_campaign_metrics` → `ml_campaigns` - Métricas de campanha

### 4. Catálogo ML
- `ml_catalog_history` → `ml_catalog_monitoring` - Histórico primeiro
- `ml_catalog_monitoring` - Monitoramento
- `catalog_participants` - Participantes

### 5. Produtos e Pedidos ML
- `ml_product_sync` → `ml_products` - Sincronizações primeiro
- `ml_products` - Produtos ML
- `ml_orders` - Pedidos ML

### 6. Billing ML
- `ml_billing_charges` → `ml_billing_periods` - Charges primeiro
- `ml_billing_periods` - Períodos de billing

### 7. Contas ML e Assinaturas
- `ml_accounts` - Contas Mercado Livre
- `subscriptions` - Assinaturas

### 8. Produtos e Fornecedores
- `internal_products` - Produtos internos
- `products` - Produtos
- `fornecedores` - Fornecedores

### 9. Ordens de Compra
- `ordem_compra_item` → `ordem_compra` - Itens primeiro
- `ordem_compra_link` - Links
- `ordem_compra` - Ordens

### 10. Payments
- `payment_transactions` → `payments` - Transações primeiro
- `payments` - Pagamentos
- `payment_methods` - Métodos de pagamento

### 11. Outras Tabelas Financeiras
- `reconciliation_items` → `bank_reconciliation` - Itens primeiro
- `bank_reconciliation` - Reconciliação bancária
- `chart_of_accounts` - Plano de contas
- `financial_alerts` - Alertas financeiros

### 12. Outras Tabelas
- `ai_product_analysis` - Análise de produtos IA
- `sku_management` - Gestão de SKU
- `api_logs` - Logs da API

### 13. Tabelas de Usuários (ANTES de deletar users)
- `user_sessions` → `users` - Sessões primeiro
- `user_ml_accounts` → `users` - Contas ML de usuários primeiro
- `tokens` → `users` - Tokens primeiro

### 14. Usuários
- `users` - Usuários da empresa

### 15. Empresa (FINAL)
- `companies` - A empresa em si

## Total de Tabelas: 35+ tabelas deletadas

## Observações

- Todas as operações são protegidas com try-except
- Tabelas opcionais que não existem são ignoradas
- Ordem respeita foreign keys (filhos antes dos pais)
- Operações críticas têm tratamento de erro específico
- Commit único no final para garantir consistência

