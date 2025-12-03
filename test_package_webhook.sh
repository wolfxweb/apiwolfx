#!/bin/bash

# Script para testar webhook de pacote de tokens

NGROK_URL="https://963b5189936e.ngrok-free.app"
WEBHOOK_URL="${NGROK_URL}/api/asaas/webhooks"

echo "🧪 Testando webhook de pacote de tokens..."
echo "📍 URL: ${WEBHOOK_URL}"
echo ""

# Primeiro, vamos verificar se há compras pendentes no banco
echo "1️⃣ Verificando compras pendentes..."
echo "   (Execute no banco: SELECT id, company_id, package_id, asaas_payment_id, payment_status, externalReference FROM token_package_purchases WHERE payment_status = 'pending' LIMIT 5;)"
echo ""

# Teste: Simular webhook PAYMENT_CONFIRMED com externalReference de pacote
echo "2️⃣ Enviando webhook PAYMENT_CONFIRMED para pacote de tokens..."
echo "   (Substitua PAYMENT_ID e EXTERNAL_REF pelos valores reais)"
echo ""

# Exemplo de webhook do Asaas conforme documentação
cat << 'WEBHOOK_EXAMPLE' | curl -X POST "${WEBHOOK_URL}" \
  -H "Content-Type: application/json" \
  -H "asaas-access-token: seu_token_aqui" \
  -d @- \
  -w "\n\nStatus: %{http_code}\n" \
  | jq '.' 2>/dev/null || cat

{
  "event": "PAYMENT_CONFIRMED",
  "payment": {
    "id": "pay_faxea4g5e748njvz",
    "customer": "cus_000000000000",
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
}
WEBHOOK_EXAMPLE

echo ""
echo "✅ Teste concluído!"
echo ""
echo "📋 Para verificar se os tokens foram atualizados:"
echo "   SELECT id, name, ai_tokens_purchased FROM companies WHERE id = COMPANY_ID;"
