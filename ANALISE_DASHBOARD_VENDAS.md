# 📊 Análise de Consultas do Dashboard de Vendas

## 🔍 **Resumo Executivo**

O Dashboard de Vendas atualmente realiza **8 consultas SQL** ao banco de dados e **2N chamadas HTTP** à API do Mercado Livre a cada carregamento, onde N é o número de contas ML ativas da empresa.

## 📋 **Lista Completa de Consultas**

### **🔍 CONSULTAS SQL AO BANCO DE DADOS (8 consultas)**

#### **1. Query Principal de Pedidos Confirmados**
```sql
SELECT 
    ml_order_id, total_amount, sale_fees, shipping_cost, 
    advertising_cost, coupon_amount, order_items, date_closed, status
FROM ml_orders
WHERE company_id = :company_id
  AND date_closed >= :date_from
  AND date_closed IS NOT NULL
ORDER BY date_closed DESC
```
**Propósito**: Buscar todos os pedidos confirmados no período
**Frequência**: A cada carregamento do dashboard

#### **2. Query de Pedidos Cancelados**
```sql
SELECT 
    COUNT(*) as count,
    COALESCE(SUM(total_amount), 0) as total_value
FROM ml_orders
WHERE company_id = :company_id
  AND date_closed >= :date_from
  AND status = 'CANCELLED'
  AND tags::jsonb @> '["delivered"]'::jsonb
  AND NOT (tags::jsonb @> '["test_order"]'::jsonb)
```
**Propósito**: Calcular vendas canceladas no período
**Frequência**: A cada carregamento do dashboard

#### **3. Query de Pedidos Devolvidos**
```sql
SELECT 
    COUNT(*) as count,
    COALESCE(SUM(total_amount), 0) as total_value
FROM ml_orders
WHERE company_id = :company_id
  AND date_closed >= :date_from
  AND status = 'REFUNDED'
```
**Propósito**: Calcular vendas devolvidas no período
**Frequência**: A cada carregamento do dashboard

#### **4. Query de Contas ML**
```sql
SELECT id, ml_user_id, nickname
FROM ml_accounts
WHERE company_id = :company_id
```
**Propósito**: Buscar contas ML da empresa
**Frequência**: A cada carregamento do dashboard

#### **5. Query de Usuário Ativo**
```sql
SELECT id, company_id, email, first_name, last_name
FROM users
WHERE company_id = :company_id AND is_active = true
LIMIT 1
```
**Propósito**: Buscar usuário ativo para obter token
**Frequência**: A cada carregamento do dashboard

#### **6. Query de Agregações (Totais)**
```sql
SELECT 
    COUNT(*) as total_orders,
    COALESCE(SUM(total_amount), 0) as total_revenue,
    COALESCE(SUM(sale_fees), 0) as ml_fees_total,
    COALESCE(SUM(shipping_cost), 0) as shipping_fees_total,
    COALESCE(SUM(advertising_cost), 0) as marketing_cost_total,
    COALESCE(SUM(coupon_amount), 0) as discounts_total
FROM ml_orders
WHERE company_id = :company_id
  AND date_closed >= :date_from
  AND date_closed IS NOT NULL
```
**Propósito**: Calcular totais de receita, taxas e custos
**Frequência**: A cada carregamento do dashboard

#### **7. Query de Produtos Vendidos**
```sql
SELECT id, ml_item_id, title, status, permalink, available_quantity, seller_sku
FROM ml_products
WHERE company_id = :company_id
  AND ml_item_id IN (:item_0, :item_1, :item_2, ...)
```
**Propósito**: Buscar dados dos produtos que foram vendidos
**Frequência**: A cada carregamento do dashboard

#### **8. Query de Produtos Ativos**
```sql
SELECT COUNT(*)
FROM ml_products
WHERE company_id = :company_id
  AND status IN ('ACTIVE', 'PAUSED')
```
**Propósito**: Contar total de produtos ativos da empresa
**Frequência**: A cada carregamento do dashboard

### **🌐 CHAMADAS HTTP À API DO MERCADO LIVRE (2N consultas)**

#### **9. API de Claims/Devoluções (por conta ML)**
```
GET https://api.mercadolibre.com/post-purchase/v1/claims/search
Authorization: Bearer {access_token}
```
**Propósito**: Buscar devoluções via API do ML
**Frequência**: A cada carregamento do dashboard (N vezes)
**Problema**: ❌ Dados não são salvos no banco

#### **10. API de Visitas (por conta ML)**
```
GET https://api.mercadolibre.com/users/{user_id}/items_visits/time_window
Authorization: Bearer {access_token}
```
**Propósito**: Buscar total de visitas dos produtos
**Frequência**: A cada carregamento do dashboard (N vezes)
**Problema**: ❌ Dados não são salvos no banco

## 📊 **Resumo por Cenário**

### **Para 1 empresa com 1 conta ML:**
- ✅ **8 consultas SQL** ao banco de dados
- ❌ **2 chamadas HTTP** à API do ML (não salvas)

### **Para 1 empresa com N contas ML:**
- ✅ **8 consultas SQL** ao banco de dados  
- ❌ **2N chamadas HTTP** à API do ML (não salvas)

## ⚠️ **Problemas Identificados**

### **1. Performance**
- Dashboard carrega lentamente devido às chamadas HTTP
- Dependência da velocidade da API do Mercado Livre
- Sem cache de dados que mudam pouco

### **2. Rate Limiting**
- Pode esgotar limites da API do ML
- Múltiplas chamadas simultâneas por empresa

### **3. Confiabilidade**
- Dashboard falha se API do ML estiver lenta/fora
- Dados de claims e visitas são perdidos

### **4. Dados Não Persistidos**
- Claims/Devoluções não ficam salvos
- Visitas não ficam salvas
- Sem histórico para análises

## 🎯 **Soluções Recomendadas**

### **1. Implementar Sincronização Periódica**
```python
# Background job para sincronizar dados
def sync_ml_data():
    # Salvar claims/devoluções
    # Salvar visitas
    # Atualizar métricas
```

### **2. Criar Tabelas de Cache**
```sql
-- Tabela para visitas
CREATE TABLE ml_visits (
    id SERIAL PRIMARY KEY,
    company_id INTEGER,
    ml_account_id INTEGER,
    ml_item_id VARCHAR(50),
    visits_count INTEGER,
    date_visited DATE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Adicionar campos na tabela ml_orders para claims
ALTER TABLE ml_orders ADD COLUMN claims_count INTEGER DEFAULT 0;
ALTER TABLE ml_orders ADD COLUMN claims_value DECIMAL(10,2) DEFAULT 0;
```

### **3. Dashboard Otimizado**
- Usar apenas dados salvos no banco
- Carregamento instantâneo
- Sincronização em background

## 📈 **Benefícios da Refatoração**

✅ **Performance**: Dashboard carrega instantaneamente
✅ **Confiabilidade**: Não depende da API do ML
✅ **Histórico**: Dados ficam salvos para análises
✅ **Rate Limiting**: Evita limites da API
✅ **Offline**: Funciona mesmo se API do ML estiver fora
✅ **Escalabilidade**: Suporta múltiplas empresas

## 🔄 **Próximos Passos**

1. **Criar documento de análise** ✅
2. **Remover consultas atuais** ✅
3. **Simplificar dashboard** ✅
4. **Manter HTML atual** ✅
5. **Implementar dados reais gradualmente**

## ✅ **Refatoração Concluída**

### **O que foi feito:**
- ✅ **Backup criado** em `backup_dashboard_20251023_120204/`
- ✅ **Consultas pesadas removidas** do `analytics_controller.py`
- ✅ **Chamadas HTTP removidas** (Claims e Visitas)
- ✅ **Dashboard simplificado** com dados mock
- ✅ **HTML mantido** funcionando

### **Resultado:**
- 🚀 **Performance máxima** - sem consultas pesadas
- 🎯 **HTML funcionando** - interface preservada
- 📊 **Dados mock** - estrutura mantida
- 🔧 **Base limpa** - pronto para implementação gradual

---

**Data da Análise**: 23/10/2025
**Versão**: 2.0
**Status**: Refatoração Concluída - Dashboard Simplificado
