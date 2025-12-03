#!/bin/bash

# Script para testar o webhook do Asaas

NGROK_URL="https://963b5189936e.ngrok-free.app"
WEBHOOK_URL="${NGROK_URL}/api/asaas/webhooks"

echo "🧪 Testando webhook do Asaas..."
echo "📍 URL: ${WEBHOOK_URL}"
echo ""

# Teste 1: Verificar se o endpoint está acessível
echo "1️⃣ Testando GET /api/asaas/webhooks/test"
curl -X GET "${WEBHOOK_URL}/test" \
  -H "Content-Type: application/json" \
  -w "\n\nStatus: %{http_code}\n" \
  | jq '.' 2>/dev/null || cat

echo ""
echo "---"
echo ""

# Teste 2: Enviar notificação de pagamento confirmado (assinatura)
echo "2️⃣ Testando POST /api/asaas/webhooks/test (PAYMENT_CONFIRMED - Assinatura)"
curl -X POST "${WEBHOOK_URL}/test?event_type=PAYMENT_CONFIRMED&payment_id=pay_test_123&subscription_id=sub_test_123" \
  -H "Content-Type: application/json" \
  -w "\n\nStatus: %{http_code}\n" \
  | jq '.' 2>/dev/null || cat

echo ""
echo "---"
echo ""

# Teste 3: Enviar notificação de pagamento confirmado (pacote de tokens)
echo "3️⃣ Testando POST /api/asaas/webhooks/test (PAYMENT_CONFIRMED - Pacote de Tokens)"
curl -X POST "${WEBHOOK_URL}/test?event_type=PAYMENT_CONFIRMED&payment_id=pay_test_456&external_reference=package_1_company_1" \
  -H "Content-Type: application/json" \
  -w "\n\nStatus: %{http_code}\n" \
  | jq '.' 2>/dev/null || cat

echo ""
echo "---"
echo ""

# Teste 4: Enviar notificação real (simulando formato do Asaas)
echo "4️⃣ Testando POST /api/asaas/webhooks (formato real do Asaas)"
curl -X POST "${WEBHOOK_URL}" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "PAYMENT_CONFIRMED",
    "payment": {
      "id": "pay_real_test_789",
      "subscription": "sub_real_test_789",
      "status": "CONFIRMED",
      "value": 99.90,
      "dueDate": "2024-02-01",
      "paymentDate": "2024-02-01",
      "externalReference": "package_1_company_1"
    }
  }' \
  -w "\n\nStatus: %{http_code}\n" \
  | jq '.' 2>/dev/null || cat

echo ""
echo "✅ Testes concluídos!"
