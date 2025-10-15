# 🧪 Guia de Contas de Teste - Mercado Pago

## 📋 Visão Geral

Este guia explica como usar as contas de teste do Mercado Pago para testar sua integração sem transações reais e sem validação de email.

## 🎯 Tipos de Contas de Teste

### 1. **🏪 Vendedor (Seller)**
- Conta que recebe os pagamentos
- Configurada com suas credenciais de aplicação
- Usada para criar preferências de pagamento

### 2. **🛒 Comprador (Buyer)**
- Conta que realiza os pagamentos
- Usada para simular compras
- Não requer validação de email

### 3. **🔗 Integrador (Integrator)**
- Para integrações marketplace
- Opcional para a maioria dos casos

## 🚀 Como Usar

### **Configurar Ambiente de Teste**

```bash
# Configurar ambiente completo (vendedor + comprador)
POST /api/payments/test-accounts/setup-environment
```

**Resposta:**
```json
{
  "message": "Ambiente de teste configurado com sucesso",
  "accounts": {
    "seller": {
      "id": "123456789",
      "nickname": "TEST_USER_123456789",
      "email": "test_user_123456789@testuser.com",
      "account_type": "seller"
    },
    "buyer": {
      "id": "987654321",
      "nickname": "TEST_USER_987654321", 
      "email": "test_user_987654321@testuser.com",
      "account_type": "buyer"
    }
  },
  "test_cards": {
    "approved": {
      "number": "4235647728025682",
      "security_code": "123",
      "expiration_month": "11",
      "expiration_year": "2025"
    }
  }
}
```

### **Criar Conta Específica**

```bash
# Criar conta de comprador
POST /api/payments/test-accounts/create?account_type=buyer&country=BR&description=Comprador Teste

# Criar conta de vendedor
POST /api/payments/test-accounts/create?account_type=seller&country=BR&description=Vendedor Teste
```

### **Obter Cartões de Teste**

```bash
GET /api/payments/test-accounts/cards?country=BR
```

**Resposta:**
```json
{
  "message": "Cartões de teste para BR",
  "test_cards": {
    "approved": {
      "number": "4235647728025682",
      "security_code": "123",
      "expiration_month": "11",
      "expiration_year": "2025",
      "cardholder": {
        "name": "APRO",
        "identification": {
          "type": "CPF",
          "number": "12345678901"
        }
      }
    },
    "rejected": {
      "number": "4000000000000002",
      "security_code": "123",
      "expiration_month": "11",
      "expiration_year": "2025",
      "cardholder": {
        "name": "OTHE",
        "identification": {
          "type": "CPF",
          "number": "12345678901"
        }
      }
    },
    "pending": {
      "number": "4000000000000119",
      "security_code": "123",
      "expiration_month": "11",
      "expiration_year": "2025",
      "cardholder": {
        "name": "PEND",
        "identification": {
          "type": "CPF",
          "number": "12345678901"
        }
      }
    }
  }
}
```

## 💳 Cartões de Teste Disponíveis

### **✅ Pagamentos Aprovados**
- **Número**: `4235647728025682`
- **CVV**: `123`
- **Vencimento**: `11/2025`
- **Nome**: `APRO`
- **CPF**: `12345678901`

### **❌ Pagamentos Rejeitados**
- **Número**: `4000000000000002`
- **CVV**: `123`
- **Vencimento**: `11/2025`
- **Nome**: `OTHE`
- **CPF**: `12345678901`

### **⏳ Pagamentos Pendentes**
- **Número**: `4000000000000119`
- **CVV**: `123`
- **Vencimento**: `11/2025`
- **Nome**: `PEND`
- **CPF**: `12345678901`

## 🔐 Autenticação de Contas de Teste

### **Para Login no Painel do Mercado Pago:**

1. Acesse o [Painel de Desenvolvedores](https://www.mercadopago.com.br/developers/panel)
2. Use as credenciais da conta de teste:
   - **Email**: O email retornado na criação da conta
   - **Senha**: A senha gerada automaticamente
3. **Se solicitado código de verificação**: Use os últimos 6 dígitos do `User ID` da conta de teste

## 🧪 Fluxo de Teste Completo

### **1. Configurar Ambiente**
```bash
curl -X POST "http://localhost:8000/api/payments/test-accounts/setup-environment"
```

### **2. Criar Preferência de Pagamento**
```bash
curl -X POST "http://localhost:8000/api/payments/create-preference" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_name": "Básico",
    "amount": 29.90,
    "description": "Plano Básico - Teste"
  }'
```

### **3. Testar Pagamento**
- Use a URL da preferência retornada
- Use os cartões de teste fornecidos
- **Sem validação de email!** ✨

### **4. Verificar Webhook**
- O webhook será chamado automaticamente
- Verifique os logs do container

## ⚠️ Limitações e Considerações

### **Limitações:**
- Máximo de 15 contas de teste simultâneas
- Contas inativas por 60 dias são removidas automaticamente
- Não é possível deletar contas de teste

### **Importante:**
- **Use apenas em ambiente sandbox**
- **Nunca use dados de teste em produção**
- **Mantenha as credenciais de teste seguras**

## 🎯 Vantagens

✅ **Sem validação de email**  
✅ **Transações simuladas**  
✅ **Teste de todos os cenários**  
✅ **Sem custos**  
✅ **Ambiente isolado**  

## 🚀 Próximos Passos

1. **Configure o ambiente de teste**
2. **Teste os pagamentos com cartões de teste**
3. **Valide os webhooks**
4. **Teste cenários de erro e sucesso**
5. **Quando estiver pronto, mude para produção**

---

## 📞 Suporte

Para dúvidas sobre contas de teste:
- [Documentação Oficial Mercado Pago](https://www.mercadopago.com.br/developers/pt/docs/checkout-bricks/integration-test/test-accounts)
- [Central de Ajuda](https://help.mercadopago.com.br/)
