# 📊 Comparação: API ML vs Modelo Atual

## ✅ Dados que a API Retorna:

### Métricas de Performance
- `clicks` - Cliques
- `prints` - Impressões
- `cost` - Investimento
- `cpc` - Custo por clique
- `ctr` - Taxa de cliques (%)

### Vendas por Publicidade
- `direct_items_quantity` - Vendas diretas (quantidade)
- `indirect_items_quantity` - Vendas indiretas (quantidade)
- `advertising_items_quantity` - Total vendas publicidade
- `direct_units_quantity` - Unidades vendidas diretas
- `indirect_units_quantity` - Unidades vendidas indiretas
- `units_quantity` - Total unidades vendidas

### Receitas
- `direct_amount` - Receita de vendas diretas (R$)
- `indirect_amount` - Receita de vendas indiretas (R$)
- `total_amount` - Receita total (R$)

### Vendas Orgânicas (sem publicidade)
- `organic_items_quantity` - Vendas orgânicas (quantidade)
- `organic_units_quantity` - Unidades vendidas orgânicas
- `organic_units_amount` - Receita orgânica (R$)

### Métricas Avançadas
- `acos` - Custo de publicidade de vendas (%)
- `cvr` - Taxa de conversão (%)
- `roas` - Retorno sobre investimento (x)
- `sov` - Share of Voice (%)

---

## ❌ Modelo Atual (ml_campaign_metrics):

```python
impressions = Column(Integer, default=0)     # ✅ prints
clicks = Column(Integer, default=0)          # ✅ clicks
conversions = Column(Integer, default=0)     # ❓ qual campo?
spent = Column(Float, default=0)             # ✅ cost
revenue = Column(Float, default=0)           # ✅ total_amount
ctr = Column(Float, default=0)               # ✅ ctr
cpc = Column(Float, default=0)               # ✅ cpc
roas = Column(Float, default=0)              # ✅ roas
```

---

## 🚨 CAMPOS FALTANDO (IMPORTANTES):

### Vendas Diretas vs Indiretas
- ❌ `direct_items_quantity`
- ❌ `indirect_items_quantity`
- ❌ `advertising_items_quantity`
- ❌ `direct_amount`
- ❌ `indirect_amount`

### Unidades Vendidas
- ❌ `direct_units_quantity`
- ❌ `indirect_units_quantity`
- ❌ `units_quantity`

### Vendas Orgânicas
- ❌ `organic_items_quantity`
- ❌ `organic_units_quantity`
- ❌ `organic_units_amount`

### Métricas Avançadas
- ❌ `acos`
- ❌ `cvr`
- ❌ `sov`

---

## 💡 RECOMENDAÇÃO:

**Adicionar TODOS os campos à tabela `ml_campaign_metrics`** para ter histórico completo:

```sql
ALTER TABLE ml_campaign_metrics ADD COLUMN:
- direct_items_quantity INTEGER DEFAULT 0
- indirect_items_quantity INTEGER DEFAULT 0
- advertising_items_quantity INTEGER DEFAULT 0
- direct_units_quantity INTEGER DEFAULT 0
- indirect_units_quantity INTEGER DEFAULT 0
- units_quantity INTEGER DEFAULT 0
- direct_amount FLOAT DEFAULT 0
- indirect_amount FLOAT DEFAULT 0
- organic_items_quantity INTEGER DEFAULT 0
- organic_units_quantity INTEGER DEFAULT 0
- organic_units_amount FLOAT DEFAULT 0
- acos FLOAT DEFAULT 0
- cvr FLOAT DEFAULT 0
- sov FLOAT DEFAULT 0
```

Isso permitirá:
✅ Análises detalhadas de vendas diretas vs indiretas
✅ Comparação vendas orgânicas vs pagas
✅ Métricas avançadas (ACOS, CVR, SOV)
✅ Histórico completo de 90 dias

