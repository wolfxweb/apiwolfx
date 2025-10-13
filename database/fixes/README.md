# Scripts de Correção do Banco de Dados

Este diretório contém scripts de correção e manutenção do banco de dados.

## Arquivos de Fix:

### fix_database.py
- Adiciona colunas à tabela ml_orders:
  - has_catalog_products (BOOLEAN)
  - catalog_products_count (INTEGER)
  - catalog_products (JSON)

### fix_products_table.py
- Correção inicial da tabela products

### fix_products_table_complete.py
- Adiciona colunas à tabela products:
  - cost_price (VARCHAR)
  - tax_rate (VARCHAR)
  - marketing_cost (VARCHAR)
  - other_costs (VARCHAR)
  - notes (TEXT)

### fix_sku_constraint.py
- Remove constraint única do SKU na tabela sku_management

### fix_sku_constraint_final.py
- Versão final da correção de constraint do SKU

## Status:
✅ Todas as correções foram aplicadas ao banco de dados

## Data de movimentação:
Mon Oct 13 08:23:03 -03 2025

## Nota:
Estes scripts foram utilizados para corrigir problemas específicos do banco de dados durante o desenvolvimento. Mantidos para referência futura.
