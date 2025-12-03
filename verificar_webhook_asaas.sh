#!/bin/bash

echo "📋 Guia Completo: Como Testar Webhook do Asaas"
echo "================================================"
echo ""

echo "1️⃣ CONFIGURAR WEBHOOK NO ASAAS:"
echo "   Sandbox: https://sandbox.asaas.com"
echo "   - Minha Conta > Integrações > Webhook para cobranças"
echo "   - URL: https://963b5189936e.ngrok-free.app/api/asaas/webhooks"
echo "   - Eventos: PAYMENT_CONFIRMED, PAYMENT_RECEIVED"
echo ""

echo "2️⃣ TESTAR ENDPOINT LOCAL:"
echo "   curl -X GET https://963b5189936e.ngrok-free.app/api/asaas/webhooks/test"
echo ""

echo "3️⃣ VERIFICAR LOGS EM TEMPO REAL:"
echo "   docker logs -f apiwolfx-api | grep -E 'webhook|PAYMENT|package_'"
echo ""

echo "4️⃣ TESTAR COM PAGAMENTO REAL:"
echo "   Use o payment_id real do banco:"
echo "   SELECT id, asaas_payment_id, externalReference FROM token_package_purchases WHERE payment_status = 'pending';"
echo ""

echo "5️⃣ VERIFICAR LOGS DO ASAAS:"
echo "   No painel Asaas: Integrações > Webhook > LOG"
echo "   Verifique se há tentativas de envio e status das respostas"
echo ""

echo "6️⃣ TESTAR MANUALMENTE COM CURL:"
echo "   Substitua PAYMENT_ID e EXTERNAL_REF pelos valores reais do banco"
echo ""
cat << 'CURL_EXAMPLE'
curl -X POST "https://963b5189936e.ngrok-free.app/api/asaas/webhooks" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "PAYMENT_CONFIRMED",
    "payment": {
      "id": "PAYMENT_ID_AQUI",
      "status": "CONFIRMED",
      "externalReference": "EXTERNAL_REF_AQUI"
    }
  }'
CURL_EXAMPLE
echo ""

echo "✅ Script criado! Execute: ./verificar_webhook_asaas.sh"
