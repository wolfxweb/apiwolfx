#!/bin/bash

NGROK_URL="https://963b5189936e.ngrok-free.app"
WEBHOOK_URL="${NGROK_URL}/api/asaas/webhooks"

echo "🧪 Teste Completo do Webhook do Asaas"
echo "======================================"
echo ""

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Teste 1: Verificar se endpoint está acessível
echo -e "${YELLOW}1️⃣ Testando GET /api/asaas/webhooks/test${NC}"
response=$(curl -s -w "\n%{http_code}" -X GET "${WEBHOOK_URL}/test")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ Endpoint acessível${NC}"
    echo "$body" | jq '.' 2>/dev/null || echo "$body"
else
    echo -e "${RED}❌ Erro: HTTP $http_code${NC}"
    echo "$body"
fi
echo ""

# Teste 2: Enviar webhook de teste
echo -e "${YELLOW}2️⃣ Testando POST /api/asaas/webhooks/test (PAYMENT_CONFIRMED)${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST "${WEBHOOK_URL}/test?event_type=PAYMENT_CONFIRMED&payment_id=pay_test_123&external_reference=package_1_company_27")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ Webhook de teste processado${NC}"
    echo "$body" | jq '.' 2>/dev/null || echo "$body"
else
    echo -e "${RED}❌ Erro: HTTP $http_code${NC}"
    echo "$body"
fi
echo ""

# Teste 3: Enviar webhook real (formato Asaas)
echo -e "${YELLOW}3️⃣ Testando POST /api/asaas/webhooks (formato real do Asaas)${NC}"
webhook_payload='{
  "event": "PAYMENT_CONFIRMED",
  "payment": {
    "id": "pay_test_real_123",
    "customer": "cus_test_123",
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

response=$(curl -s -w "\n%{http_code}" -X POST "${WEBHOOK_URL}" \
  -H "Content-Type: application/json" \
  -d "$webhook_payload")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ Webhook real processado${NC}"
    echo "$body" | jq '.' 2>/dev/null || echo "$body"
else
    echo -e "${RED}❌ Erro: HTTP $http_code${NC}"
    echo "$body"
fi
echo ""

# Teste 4: Verificar logs do container
echo -e "${YELLOW}4️⃣ Verificando logs do container (últimas 20 linhas relacionadas a webhook)${NC}"
docker logs apiwolfx-api --tail 200 2>&1 | grep -E "webhook|PAYMENT|package_|externalReference|ai_tokens|TokenPackagePurchase" | tail -20 || echo "Nenhum log encontrado"
echo ""

echo -e "${GREEN}✅ Testes concluídos!${NC}"
echo ""
echo "📋 Próximos passos:"
echo "   1. Verifique os logs acima"
echo "   2. Verifique no banco se os tokens foram atualizados"
echo "   3. Configure o webhook no painel do Asaas se ainda não configurou"
