# 🚀 Guia de Integração Asaas - Pagamentos Recorrentes

## ✅ Implementação Completa

A integração com Asaas para pagamentos recorrentes foi implementada com sucesso!

## 📋 Arquivos Criados

1. **`app/services/asaas_service.py`** - Serviço principal para comunicação com API Asaas
2. **`app/models/asaas_models.py`** - Modelos Pydantic para validação de dados
3. **`app/controllers/asaas_controller.py`** - Controller com lógica de negócio
4. **`app/routes/asaas_routes.py`** - Rotas da API REST
5. **`database/fixes/2025_11_19_add_asaas_columns_to_subscriptions.py`** - Migration para adicionar colunas

## 🔧 Configuração

### 1. Obter Credenciais Asaas

1. Acesse: https://www.asaas.com/
2. Crie uma conta ou faça login
3. Vá em **Minha Conta** → **Integração**
4. Clique em **Gerar API Key**
5. Copie a API Key gerada

### 2. Configurar Variáveis de Ambiente

#### Desenvolvimento (`.env`):
```bash
ASAAS_API_KEY=sua_api_key_aqui
ASAAS_WEBHOOK_TOKEN=token_webhook_opcional
ASAAS_WEBHOOK_URL=https://seu-ngrok.ngrok-free.app/api/asaas/webhooks
```

#### Produção (`portainer.env` e `docker-compose.prod.yml`):
```bash
ASAAS_API_KEY=sua_api_key_producao
ASAAS_WEBHOOK_TOKEN=token_webhook_producao
ASAAS_WEBHOOK_URL=https://celx.com.br/api/asaas/webhooks
```

### 3. Executar Migration

A migration será executada automaticamente no startup do container. Se precisar executar manualmente:

```python
python database/fixes/2025_11_19_add_asaas_columns_to_subscriptions.py
```

## 📡 Endpoints da API

### Criar Assinatura
```
POST /api/asaas/subscriptions
```

**Body:**
```json
{
  "plan_id": "1",
  "subscriber_data": {
    "name": "João Silva",
    "email": "joao@exemplo.com",
    "phone": "(11) 98765-4321",
    "cpf": "12345678901",
    "billing_type": "CREDIT_CARD",
    "credit_card_token": "token_do_cartao"
  }
}
```

### Buscar Assinatura
```
GET /api/asaas/subscriptions/{subscription_id}
```

### Cancelar Assinatura
```
DELETE /api/asaas/subscriptions/{subscription_id}
```

### Webhook (receber notificações)
```
POST /api/asaas/webhooks
```

## 🔄 Fluxo de Assinatura

1. **Cliente escolhe plano** → Frontend chama `/api/asaas/subscriptions`
2. **Backend cria cliente no Asaas** (se não existir)
3. **Backend cria assinatura no Asaas** com dados do plano
4. **Backend salva assinatura no banco local**
5. **Asaas processa pagamento** (PIX/Boleto/Cartão)
6. **Webhook notifica status** → Sistema atualiza assinatura

## 📊 Tipos de Cobrança Suportados

- `BOLETO` - Boleto bancário
- `CREDIT_CARD` - Cartão de crédito
- `PIX` - PIX (pagamento instantâneo)
- `DEBIT_CARD` - Cartão de débito

## 🔄 Ciclos de Cobrança

- `WEEKLY` - Semanal
- `BIWEEKLY` - Quinzenal
- `MONTHLY` - Mensal
- `QUARTERLY` - Trimestral
- `SEMIANNUALLY` - Semestral
- `YEARLY` - Anual

## 🔔 Eventos de Webhook

O Asaas envia webhooks para os seguintes eventos:

- `PAYMENT_CONFIRMED` - Pagamento confirmado
- `PAYMENT_RECEIVED` - Pagamento recebido
- `PAYMENT_OVERDUE` - Pagamento vencido
- `PAYMENT_REFUNDED` - Pagamento estornado

## 🧪 Testes

### Ambiente Sandbox

O Asaas usa `sandbox.asaas.com` para testes. O sistema detecta automaticamente o ambiente:

- **Desenvolvimento**: `https://sandbox.asaas.com/api/v3`
- **Produção**: `https://api.asaas.com/v3`

### Testar Criação de Assinatura

```bash
curl -X POST http://localhost:8000/api/asaas/subscriptions \
  -H "Content-Type: application/json" \
  -H "Cookie: session_token=seu_token" \
  -d '{
    "plan_id": "1",
    "subscriber_data": {
      "name": "Teste",
      "email": "teste@exemplo.com",
      "billing_type": "PIX"
    }
  }'
```

## 📝 Próximos Passos

1. ✅ Configurar credenciais no `.env`
2. ✅ Executar migration (automático no startup)
3. ⏳ Configurar webhook no painel Asaas
4. ⏳ Atualizar frontend para usar endpoints Asaas
5. ⏳ Testar criação de assinatura em sandbox

## 🔗 Links Úteis

- **Documentação Asaas**: https://docs.asaas.com/
- **Painel Asaas**: https://www.asaas.com/
- **API Reference**: https://docs.asaas.com/reference

## ⚠️ Importante

- A API Key do Asaas deve ser mantida em segredo
- Configure o webhook no painel Asaas apontando para: `https://seu-dominio.com/api/asaas/webhooks`
- Use ambiente sandbox para testes antes de ir para produção

