# 📢 SISTEMA DE PUBLICIDADE - MERCADO LIVRE (Product Ads)

## 📋 Visão Geral

Sistema completo para gerenciar campanhas de publicidade do Mercado Livre (Product Ads/PADS), incluindo monitoramento de métricas, gestão de campanhas e análise de ROI.

---

## ✅ O QUE TEMOS IMPLEMENTADO

### 🎯 1. MÉTRICAS E MONITORAMENTO

#### **Métricas por Produto**
- ✅ Impressões (prints)
- ✅ Cliques (clicks)
- ✅ CTR - Taxa de cliques
- ✅ Custo total (cost)
- ✅ CPC - Custo por clique
- ✅ ACOS - Advertising Cost of Sales
- ✅ CVR - Taxa de conversão
- ✅ ROAS - Return on Ad Spend
- ✅ SOV - Share of Voice

#### **Vendas Atribuídas**
- ✅ Vendas Orgânicas (sem anúncio)
- ✅ Vendas Diretas (clique no anúncio → compra)
- ✅ Vendas Indiretas (visualizou anúncio → comprou depois)
- ✅ Total de Vendas

#### **Billing (Custos Reais)**
- ✅ Períodos de faturamento mensais
- ✅ Custo total de publicidade por período
- ✅ Faturas abertas e fechadas
- ✅ Detalhamento de investimento em PADS
- ✅ Sincronização automática (cron job diário)

---

### 📊 2. ENDPOINTS DA API UTILIZADOS

#### **A) Leitura de Dados**
```
GET /advertising/{SITE_ID}/product_ads/ads/{ITEM_ID}
GET /advertising/advertisers?product_id=PADS
GET /advertising/{SITE_ID}/advertisers/{ADVERTISER_ID}/product_ads/campaigns/search
GET /billing/{SITE_ID}/billing_periods
GET /billing/{SITE_ID}/billing_periods/{PERIOD_ID}/summary
```

#### **B) Gestão de Campanhas (NOVO)**
```
GET /advertising/{SITE_ID}/advertisers/{ADVERTISER_ID}/product_ads/campaigns/{CAMPAIGN_ID}
POST /advertising/{SITE_ID}/advertisers/{ADVERTISER_ID}/product_ads/campaigns
PUT /advertising/{SITE_ID}/advertisers/{ADVERTISER_ID}/product_ads/campaigns/{CAMPAIGN_ID}
DELETE /advertising/{SITE_ID}/advertisers/{ADVERTISER_ID}/product_ads/campaigns/{CAMPAIGN_ID}
PATCH /advertising/{SITE_ID}/advertisers/{ADVERTISER_ID}/product_ads/campaigns/{CAMPAIGN_ID}/status
```

#### **C) Gestão de Produtos em Campanhas (NOVO)**
```
GET /advertising/{SITE_ID}/product_ads/campaigns/{CAMPAIGN_ID}/ads
POST /advertising/{SITE_ID}/product_ads/campaigns/{CAMPAIGN_ID}/ads
DELETE /advertising/{SITE_ID}/product_ads/campaigns/{CAMPAIGN_ID}/ads/{AD_ID}
```

#### **D) Gestão de Lances (NOVO)**
```
GET /advertising/{SITE_ID}/product_ads/campaigns/{CAMPAIGN_ID}/bids
PUT /advertising/{SITE_ID}/product_ads/campaigns/{CAMPAIGN_ID}/bids/{BID_ID}
POST /advertising/{SITE_ID}/product_ads/campaigns/{CAMPAIGN_ID}/bids/suggestions
```

---

## 🎯 3. FUNCIONALIDADES IMPLEMENTADAS

### **Dashboard de Publicidade** (`/ml/advertising`)
- ✅ Visão geral de todas as campanhas
- ✅ Métricas consolidadas (impressões, cliques, custo, ROAS)
- ✅ Gráficos de performance
- ✅ Análise de ROI por produto
- ✅ Top produtos em publicidade
- ✅ Comparação orgânico vs. anúncios

### **Gestão de Campanhas** (NOVO)
- ✅ Listar todas as campanhas ativas/pausadas
- ✅ Criar nova campanha
- ✅ Editar campanha existente
- ✅ Pausar/reativar campanha
- ✅ Deletar campanha
- ✅ Adicionar/remover produtos da campanha
- ✅ Definir orçamento diário
- ✅ Configurar estratégia de lance

### **Análise de Performance**
- ✅ Métricas por período (7, 30, 60, 90 dias)
- ✅ Comparação mês a mês
- ✅ Análise de custo-benefício
- ✅ Produtos com melhor ROAS
- ✅ Produtos com pior performance
- ✅ Sugestões de otimização

---

## 📁 4. ARQUIVOS DO SISTEMA

### **Services**
- `app/services/ml_product_ads_service.py` - Métricas por produto
- `app/services/ml_campaign_service.py` - Gestão de campanhas (NOVO)
- `app/services/ml_billing_service.py` - Custos de billing

### **Controllers**
- `app/controllers/ml_advertising_controller.py` - Controller principal
- `app/controllers/advertising_controller.py` - Gestão completa (NOVO)

### **Routes**
- `app/routes/ml_advertising_routes.py` - Rotas da API

### **Views**
- `app/views/templates/ml_advertising.html` - Tela principal (NOVO)

### **Models**
- Tabelas: `ml_billing_periods`, `ml_billing_charges`
- Models: `MLAccount`, `MLProduct`, `MLOrder`

---

## 🔐 5. AUTENTICAÇÃO

### **Token Management**
- ✅ Access Token (validade: 6 horas)
- ✅ Refresh Token (renovação automática)
- ✅ Armazenado por `ml_account_id`
- ✅ Renovação automática antes da expiração

### **Permissões Necessárias**
- `offline_access` - Para refresh token
- `read` - Leitura de dados
- `write` - Gestão de campanhas

---

## 📊 6. MÉTRICAS DISPONÍVEIS

| Métrica | Descrição | Uso |
|---------|-----------|-----|
| **Impressões** | Quantas vezes o anúncio foi exibido | Alcance |
| **Cliques** | Quantas vezes clicaram no anúncio | Interesse |
| **CTR** | Taxa de cliques (clicks/prints × 100) | Relevância |
| **Custo** | Valor total investido | Orçamento |
| **CPC** | Custo por clique (cost/clicks) | Eficiência |
| **CVR** | Taxa de conversão (vendas/cliques) | Qualidade |
| **ACOS** | % do custo sobre vendas (cost/sales × 100) | Rentabilidade |
| **ROAS** | Retorno sobre investimento (sales/cost) | ROI |
| **SOV** | Share of Voice (visibilidade vs. concorrentes) | Posicionamento |

---

## 🚀 7. COMO USAR

### **A) Visualizar Métricas**
1. Acesse: **Mercado Livre → Publicidade**
2. Veja métricas consolidadas de todas as campanhas
3. Filtre por período (7, 30, 60, 90 dias)
4. Analise produtos com melhor/pior performance

### **B) Criar Campanha**
1. Clique em **"+ Nova Campanha"**
2. Defina nome e orçamento diário
3. Selecione produtos para anunciar
4. Escolha estratégia de lance (automático/manual)
5. Ative a campanha

### **C) Gerenciar Campanha**
1. Clique em uma campanha existente
2. Edite orçamento, status ou produtos
3. Ajuste lances por produto
4. Pause ou reative conforme necessário

### **D) Analisar Performance**
1. Veja gráficos de performance ao longo do tempo
2. Compare ROI de diferentes campanhas
3. Identifique produtos com melhor ROAS
4. Otimize lances com base em sugestões

---

## 📈 8. BOAS PRÁTICAS

### **Orçamento**
- ✅ Defina orçamento diário realista
- ✅ Monitore consumo diariamente
- ✅ Ajuste conforme performance

### **Lances**
- ✅ Comece com lances automáticos
- ✅ Ajuste manualmente produtos com bom ROAS
- ✅ Reduza lances em produtos com alto ACOS

### **Produtos**
- ✅ Anuncie produtos com boa margem
- ✅ Teste diferentes produtos
- ✅ Pause produtos com ROAS < 2.0

### **Análise**
- ✅ Revise métricas semanalmente
- ✅ Compare vendas orgânicas vs. anúncios
- ✅ Calcule ROI real (vendas - custos)

---

## 🔄 9. SINCRONIZAÇÃO AUTOMÁTICA

### **Cron Jobs Ativos**
```bash
# Sincronização diária de custos de billing
0 8 * * * python /app/scripts/billing_sync_cron_direct.py

# Atualização de métricas de campanhas
0 */6 * * * python /app/scripts/update_campaign_metrics.py
```

### **O que é Sincronizado**
- ✅ Custos de billing (períodos mensais)
- ✅ Métricas de produtos anunciados
- ✅ Status de campanhas
- ✅ Renovação automática de tokens

---

## 🛠️ 10. TROUBLESHOOTING

### **Token Expirado**
```python
# O sistema renova automaticamente, mas se precisar forçar:
# Verifique tokens da empresa:
SELECT * FROM tokens WHERE user_id IN (
    SELECT user_id FROM users WHERE company_id = 15
);
```

### **Métricas Zeradas**
- Verifique se o produto está em uma campanha ativa
- Confirme se há orçamento disponível
- Verifique período selecionado (pode não ter dados)

### **Erro ao Criar Campanha**
- Confirme permissões da conta ML
- Verifique se orçamento é >= valor mínimo
- Certifique-se de ter produtos selecionados

---

## 📞 11. SUPORTE

### **Documentação Oficial ML**
- https://developers.mercadolivre.com.br/pt_br/product-ads

### **Logs do Sistema**
```bash
# Ver logs de publicidade
docker logs apiwolfx-api | grep "advertising"

# Ver logs de billing
docker logs apiwolfx-api | grep "billing"
```

---

## 🎯 12. ROADMAP FUTURO

### **Em Desenvolvimento**
- ⏳ Relatórios personalizados
- ⏳ Análise de palavras-chave
- ⏳ Segmentação avançada
- ⏳ Remarketing
- ⏳ Otimização automática de lances (IA)

### **Planejado**
- 📅 Alertas de performance
- 📅 Sugestões automáticas
- 📅 A/B testing de anúncios
- 📅 Integração com Google Analytics

---

**✅ Sistema completo e funcional para gestão de publicidade no Mercado Livre!**

**Última atualização:** Outubro 2025

