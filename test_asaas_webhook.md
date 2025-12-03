# Guia de Teste do Webhook do Asaas

## 1. Verificar Configuração no Asaas

### Sandbox (Desenvolvimento)
1. Acesse: https://sandbox.asaas.com
2. Vá em: **Minha Conta** > **Integrações** > **Webhook para cobranças**
3. Verifique se está configurado:
   - URL: `https://963b5189936e.ngrok-free.app/api/asaas/webhooks`
   - Webhook Ativado: ✅
   - Eventos selecionados:
     - ✅ PAYMENT_CONFIRMED
     - ✅ PAYMENT_RECEIVED
     - ✅ PAYMENT_OVERDUE
     - ✅ PAYMENT_REFUNDED

### Produção
1. Acesse: https://www.asaas.com
2. Mesmo caminho: **Minha Conta** > **Integrações** > **Webhook para cobranças**

## 2. Testar Endpoint de Teste

### Teste 1: Verificar se o endpoint está acessível
```bash
curl -X GET "https://963b5189936e.ngrok-free.app/api/asaas/webhooks/test"
```

### Teste 2: Enviar notificação simulada
```bash
curl -X POST "https://963b5189936e.ngrok-free.app/api/asaas/webhooks/test?event_type=PAYMENT_CONFIRMED&payment_id=pay_test_123&external_reference=package_1_company_27"
```

## 3. Testar Webhook Real (Formato do Asaas)

```bash
curl -X POST "https://963b5189936e.ngrok-free.app/api/asaas/webhooks" \
  -H "Content-Type: application/json" \
  -H "asaas-access-token: seu_token_aqui" \
  -d '{
    "event": "PAYMENT_CONFIRMED",
    "payment": {
      "id": "pay_mqok54zv1eb61saz",
      "customer": "cus_000007271242",
      "value": 99.90,
      "netValue": 99.90,
      "originalValue": 99.90,
      "status": "CONFIRMED",
      "billingType": "CREDIT_CARD",
      "dueDate": "2025-12-02",
      "paymentDate": "2025-12-02",
      "externalReference": "package_1_company_27",
      "description": "Pacote de Tokens: Teste (10000 tokens)"
    }
  }'
```

## 4. Verificar Logs do Container

```bash
# Ver logs em tempo real
docker logs -f apiwolfx-api

# Filtrar apenas webhooks
docker logs apiwolfx-api --tail 500 | grep -E "webhook|PAYMENT|package_|externalReference|ai_tokens"

# Ver últimas 100 linhas
docker logs apiwolfx-api --tail 100
```

## 5. Verificar no Banco de Dados

```sql
-- Ver compras pendentes
SELECT id, company_id, package_id, asaas_payment_id, payment_status, purchased_at
FROM token_package_purchases
WHERE payment_status = 'pending'
ORDER BY purchased_at DESC;

-- Ver tokens da empresa
SELECT id, name, ai_tokens_purchased
FROM companies
WHERE id = 27; -- Substitua pelo ID da empresa

-- Ver compras confirmadas
SELECT id, company_id, package_id, asaas_payment_id, payment_status, confirmed_at
FROM token_package_purchases
WHERE payment_status = 'confirmed'
ORDER BY confirmed_at DESC;
```

## 6. Testar com Pagamento Real no Sandbox

1. Criar um pagamento via API
2. No sandbox, confirmar manualmente o pagamento
3. Verificar se o webhook foi recebido
4. Verificar se os tokens foram atualizados

## 7. Usar o Simulador do Asaas (Sandbox)

No painel do Asaas Sandbox:
1. Vá em: **Cobranças** > **Criar Cobrança**
2. Crie uma cobrança de teste
3. Use o **Simulador de Vendas** para confirmar o pagamento
4. O webhook deve ser enviado automaticamente

## 8. Verificar Logs do Asaas

No painel do Asaas:
1. Vá em: **Integrações** > **Webhook para cobranças**
2. Clique em **Acesse o LOG para Webhook de Cobranças**
3. Verifique se há tentativas de envio
4. Veja se houve erros (status diferente de 200)
