# 🧪 Guia Completo de Testes - Integração Mercado Pago

Este guia apresenta todas as formas de testar a integração com o Mercado Pago no projeto WolfX.

## 📋 Índice

1. [Configuração Inicial](#configuração-inicial)
2. [Testes Automatizados](#testes-automatizados)
3. [Testes via API](#testes-via-api)
4. [Testes via Frontend](#testes-via-frontend)
5. [Testes de Webhook](#testes-de-webhook)
6. [Cartões de Teste](#cartões-de-teste)
7. [Troubleshooting](#troubleshooting)

## 🔧 Configuração Inicial

### Verificar Configurações

As configurações estão em `app/config/settings.py`:

```python
# Modo Sandbox (teste)
self.mp_sandbox = True
self.mp_access_token = "TEST-6252941991597570-101508-8a3bfcd3429a9f409e028c0b5c42eb35-1979794691"
self.mp_public_key = "TEST-50c8e464-533c-4054-add8-09668b41cada"
```

### Iniciar o Servidor

```bash
# No diretório do projeto
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🚀 Testes Automatizados

### 1. Teste Básico (Recomendado para iniciantes)

```bash
python test_mercado_pago_simple.py
```

**O que testa:**
- ✅ Conexão com API do Mercado Pago
- ✅ Busca de métodos de pagamento
- ✅ Criação de preferência de pagamento

**Saída esperada:**
```
🚀 Testando integração Mercado Pago - Funcionalidades Básicas

1️⃣ Testando métodos de pagamento...
✅ 15 métodos de pagamento encontrados
   - Visa (visa)
   - Mastercard (master)
   - PIX (pix)
   - Boleto (bolbradesco)
   - Débito (debit_card)

2️⃣ Testando criação de preferência...
✅ Preferência criada com sucesso!
   ID: 1234567890-abcdef
   URL: https://www.mercadopago.com.br/checkout/v1/redirect?pref_id=...

🎉 Testes básicos passaram com sucesso!
```

### 2. Teste Completo

```bash
python test_mercado_pago.py
```

**O que testa:**
- ✅ Todos os testes básicos
- ✅ Teste de parcelamentos
- ✅ Criação de pagamento de teste
- ✅ Simulação de webhook
- ✅ Fluxo completo de pagamento

## 🌐 Testes via API

### 1. Testar Métodos de Pagamento

```bash
curl -X GET "http://localhost:8000/api/payments/payment-methods"
```

### 2. Testar Parcelamentos

```bash
curl -X GET "http://localhost:8000/api/payments/installments?amount=100&payment_method_id=credit_card"
```

### 3. Criar Preferência de Pagamento

```bash
curl -X POST "http://localhost:8000/api/payments/create-preference" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "title": "Plano Pro WolfX",
        "quantity": 1,
        "unit_price": 59.90
      }
    ],
    "payer": {
      "email": "teste@wolfx.com.br",
      "name": "Cliente Teste"
    },
    "back_urls": {
      "success": "https://wolfx.com.br/success",
      "failure": "https://wolfx.com.br/failure",
      "pending": "https://wolfx.com.br/pending"
    },
    "external_reference": "test_001"
  }'
```

### 4. Criar Pagamento de Teste

```bash
curl -X POST "http://localhost:8000/api/payments/test-payment?amount=100"
```

### 5. Processar Pagamento com Cartão

```bash
curl -X POST "http://localhost:8000/api/payments/process" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_amount": 59.90,
    "description": "Assinatura WolfX Pro",
    "payment_method_id": "credit_card",
    "payer": {
      "email": "teste@wolfx.com.br",
      "identification": {
        "type": "CPF",
        "number": "12345678901"
      },
      "first_name": "João",
      "last_name": "Silva"
    },
    "installments": 1,
    "token": "TOKEN_DO_CARTAO_AQUI"
  }'
```

## 🎨 Testes via Frontend

### Acessar Página de Teste

1. Abra o navegador
2. Acesse: `http://localhost:8000/checkout-example.html`
3. Preencha o formulário com dados de teste
4. Teste diferentes métodos de pagamento

### Dados de Teste para o Frontend

**Email:** `teste@wolfx.com.br`
**Nome:** `João Silva`
**CPF:** `123.456.789-01`
**Cartão de Teste:** `4111 1111 1111 1111`
**CVV:** `123`
**Validade:** Qualquer data futura

## 🔔 Testes de Webhook

### 1. Configurar Webhook no Mercado Pago

1. Acesse o [Painel do Mercado Pago](https://www.mercadopago.com.br/developers)
2. Vá em "Suas integrações" > "Webhooks"
3. Adicione a URL: `https://seu-dominio.com/api/payments/webhooks/mercadopago`

### 2. Testar Webhook Localmente

Use o ngrok para expor sua aplicação local:

```bash
# Instalar ngrok
npm install -g ngrok

# Expor porta 8000
ngrok http 8000

# Usar a URL fornecida no painel do Mercado Pago
```

### 3. Simular Webhook

```bash
curl -X POST "http://localhost:8000/api/payments/webhooks/mercadopago" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1234567890,
    "live_mode": false,
    "type": "payment",
    "date_created": "2024-01-15T10:30:00.000Z",
    "application_id": 1234567890,
    "user_id": 987654321,
    "version": 1,
    "api_version": "v1",
    "action": "payment.created",
    "data": {
      "id": "1234567890"
    }
  }'
```

## 💳 Cartões de Teste

### Cartões Aprovados

| Bandeira | Número | CVV | Validade |
|----------|--------|-----|----------|
| Visa | 4111 1111 1111 1111 | 123 | Qualquer futura |
| Mastercard | 5555 5555 5555 4444 | 123 | Qualquer futura |
| American Express | 3753 651535 56885 | 1234 | Qualquer futura |

### Cartões Rejeitados

| Bandeira | Número | CVV | Motivo |
|----------|--------|-----|--------|
| Visa | 4000 0000 0000 0002 | 123 | Cartão recusado |
| Mastercard | 5555 5555 5555 4445 | 123 | Cartão recusado |

### PIX de Teste

Para PIX, use qualquer email válido. O Mercado Pago gerará um QR Code de teste.

## 🔍 Troubleshooting

### Problemas Comuns

#### 1. Erro de Conexão
```
❌ Erro nos testes: HTTPSConnectionPool(host='api.mercadopago.com', port=443)
```

**Solução:** Verifique sua conexão com a internet e as credenciais.

#### 2. Token Inválido
```
❌ Erro: Invalid access token
```

**Solução:** Verifique se o `MP_ACCESS_TOKEN` está correto no arquivo de configuração.

#### 3. Preferência não criada
```
❌ Erro: Invalid preference data
```

**Solução:** Verifique se todos os campos obrigatórios estão preenchidos.

### Logs de Debug

Para ver logs detalhados, adicione no início dos scripts:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Verificar Status da API

```bash
curl -X GET "https://api.mercadopago.com/v1/payment_methods" \
  -H "Authorization: Bearer TEST-6252941991597570-101508-8a3bfcd3429a9f409e028c0b5c42eb35-1979794691"
```

## 📊 Monitoramento

### 1. Logs da Aplicação

Os logs são salvos automaticamente. Procure por:
- ✅ Sucessos: `✅ Pagamento criado`
- ❌ Erros: `❌ Erro ao criar pagamento`

### 2. Painel do Mercado Pago

Acesse o [Painel de Desenvolvimento](https://www.mercadopago.com.br/developers) para:
- Ver transações de teste
- Configurar webhooks
- Monitorar logs da API

## 🚀 Próximos Passos

Após os testes bem-sucedidos:

1. **Configurar Webhooks** no painel do Mercado Pago
2. **Testar em Produção** com credenciais reais
3. **Implementar Tratamento de Erros** robusto
4. **Adicionar Logs** para monitoramento
5. **Configurar Alertas** para falhas

## 📞 Suporte

- **Documentação Oficial:** [Mercado Pago Developers](https://www.mercadopago.com.br/developers)
- **Status da API:** [Status Page](https://status.mercadopago.com/)
- **Suporte Técnico:** [Suporte Mercado Pago](https://www.mercadopago.com.br/developers/support)

---

**🎉 Parabéns!** Sua integração com o Mercado Pago está funcionando perfeitamente!
