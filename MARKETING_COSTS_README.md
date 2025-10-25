# 📊 Sistema de Custos de Marketing

Este sistema captura e distribui automaticamente os custos de marketing (Product Ads) do Mercado Livre através da Billing API.

## 🎯 Funcionalidades

### ✅ **Captura Automática**
- Sincronização via Billing API do Mercado Livre
- Custos consolidados mensais (tipo PADS)
- Distribuição proporcional entre pedidos do período

### ✅ **Armazenamento**
- Custos por pedido em `MLOrder.advertising_cost`
- Flag `is_advertising_sale` para identificar vendas com anúncio
- Métricas detalhadas em `advertising_metrics`

### ✅ **APIs Disponíveis**
- `POST /marketing/sync-costs` - Sincronizar custos
- `GET /marketing/summary` - Resumo de custos
- `GET /marketing/period` - Custos por período
- `GET /marketing/account/{id}` - Custos por conta
- `GET /marketing/metrics` - Métricas para dashboards

## 🚀 Como Usar

### 1. **Sincronização Manual**

```bash
# Testar sincronização
python test_marketing_sync.py

# Sincronizar via API
curl -X POST "http://localhost:8000/marketing/sync-costs?months=3" \
  -H "Cookie: session_token=SEU_TOKEN"
```

### 2. **Sincronização Automática**

```bash
# Instalar cron jobs
crontab crontab_marketing_sync.txt

# Verificar cron jobs
crontab -l

# Executar manualmente
python scripts/marketing_sync_cron.py daily
python scripts/marketing_sync_cron.py weekly
python scripts/marketing_sync_cron.py monthly
```

### 3. **Monitoramento**

```bash
# Ver logs
tail -f logs/marketing_sync_daily.log
tail -f logs/marketing_sync_weekly.log
tail -f logs/marketing_sync_monthly.log
```

## 📋 Estrutura dos Dados

### **Custo Consolidado Mensal**
```json
{
  "bill_includes": {
    "charges": [
      {
        "type": "PADS",           // Product Ads
        "amount": 1500.00,        // R$ 1.500,00 gastos no mês
        "label": "Product Ads"
      }
    ]
  }
}
```

### **Distribuição por Pedido**
```python
# Exemplo: Janeiro 2024
period_pads_cost = 1500.00  # R$ 1.500,00 gastos em Product Ads
orders_count = 100          # 100 pedidos no mês
cost_per_order = 15.00     # R$ 15,00 por pedido

# Cada pedido recebe:
order.advertising_cost = 15.00
order.is_advertising_sale = True
```

## 🔧 Configuração

### **Cron Jobs**
- **Diária**: 2h da manhã (último mês)
- **Semanal**: Domingo 3h (últimos 3 meses)
- **Mensal**: Dia 1, 4h (últimos 6 meses)

### **Logs**
- `logs/marketing_sync_daily.log` - Sincronização diária
- `logs/marketing_sync_weekly.log` - Sincronização semanal
- `logs/marketing_sync_monthly.log` - Sincronização mensal

## 📊 Dashboards

### **Métricas Disponíveis**
- Custo total de marketing
- Custo médio por pedido
- Breakdown mensal
- Tendências de custo
- Performance por conta ML

### **Integração com Dashboards**
- Dashboard Financeiro
- Análise de Produtos
- Relatórios de Vendas

## 🛠️ Desenvolvimento

### **Estrutura de Arquivos**
```
app/
├── services/
│   ├── marketing_costs_service.py      # Serviço principal
│   └── marketing_sync_job.py           # Job automático
├── controllers/
│   └── marketing_costs_controller.py   # Controller
├── routes/
│   └── marketing_costs_routes.py       # Rotas da API
└── models/
    └── saas_models.py                  # Modelos (MLOrder)

scripts/
└── marketing_sync_cron.py              # Script de cron

test_marketing_sync.py                  # Teste manual
crontab_marketing_sync.txt              # Configuração de cron
```

### **Testes**
```bash
# Teste completo
python test_marketing_sync.py

# Teste específico
python -c "
from app.services.marketing_costs_service import MarketingCostsService
from app.config.database import get_db
db = next(get_db())
service = MarketingCostsService(db)
result = service.sync_marketing_costs_for_company(1, 1)
print(result)
"
```

## 🔍 Troubleshooting

### **Problemas Comuns**

1. **Token Expirado**
   - Verificar tokens das contas ML
   - Renovar tokens automaticamente

2. **Sem Dados de Billing**
   - Verificar se a conta tem custos PADS
   - Aguardar processamento do ML (até 48h)

3. **Erro de Conexão**
   - Verificar conectividade com API do ML
   - Verificar rate limits

### **Logs de Debug**
```bash
# Ver logs detalhados
tail -f logs/marketing_sync_cron.log

# Ver logs da aplicação
tail -f logs/app.log
```

## 📈 Métricas de Performance

### **Indicadores**
- **ROAS**: Receita / Custo de Marketing
- **ACOS**: Custo de Marketing / Receita * 100
- **CPC**: Custo por Clique
- **CTR**: Taxa de Clique

### **Relatórios**
- Custo por período
- Eficiência por conta
- Tendências mensais
- Comparativo entre contas

## 🚨 Alertas

### **Configuração de Alertas**
- Custo acima do limite
- Falha na sincronização
- Contas sem dados
- Tokens expirados

### **Notificações**
- Email para administradores
- Logs de erro
- Dashboard de status

## 📚 Documentação da API

### **Endpoints Principais**

#### **Sincronizar Custos**
```http
POST /marketing/sync-costs?months=3
```

#### **Resumo de Custos**
```http
GET /marketing/summary?months=3
```

#### **Custos por Período**
```http
GET /marketing/period?date_from=2024-01-01&date_to=2024-01-31
```

#### **Custos por Conta**
```http
GET /marketing/account/123?months=3
```

#### **Métricas**
```http
GET /marketing/metrics?months=3
```

## 🎯 Próximos Passos

### **Melhorias Planejadas**
1. **Distribuição Inteligente**: Baseada em performance real dos produtos
2. **Alertas Automáticos**: Notificações por email/SMS
3. **Relatórios Avançados**: Exportação em PDF/Excel
4. **Integração com BI**: Dashboards em tempo real
5. **Machine Learning**: Previsão de custos e otimização

### **Roadmap**
- [ ] Distribuição baseada em performance
- [ ] Alertas automáticos
- [ ] Relatórios avançados
- [ ] Integração com BI
- [ ] Machine Learning para otimização

---

**Desenvolvido por**: Equipe GIVM  
**Versão**: 1.0.0  
**Última atualização**: 2024-01-XX
