# 🧪 Contas de Teste Configuradas - Mercado Pago

## 📋 Contas Criadas no Painel do Mercado Pago

### **🏪 Vendedor (Conta Principal)**
- **User ID**: `2928362784`
- **Usuário**: `TESTUSER1840...`
- **Senha**: `6adKvt9d5U`
- **Email**: `test_user_1840...@testuser.com`
- **Função**: Receber pagamentos
- **Status**: Ativa

### **🛒 Comprador (Maria)**
- **User ID**: `2925610954`
- **Usuário**: `TESTUSER3971...`
- **Senha**: `QOjLnDF4WI`
- **Email**: `test_user_3971@testuser.com`
- **Função**: Realizar compras de teste
- **Status**: Ativa

## 🎯 Configuração do Sistema

O sistema foi configurado para usar automaticamente os dados da conta **Maria** quando estiver em modo sandbox:

```python
# Dados configurados no sistema
{
    "email": "test_user_3971@testuser.com",
    "name": "Maria",
    "surname": "Comprador",
    "identification": {
        "type": "CPF",
        "number": "12345678901"
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

## 🚀 Como Testar

### **1. Acessar a Página de Planos**
```
http://localhost:8000/auth/plans
```

### **2. Selecionar um Plano**
- Clique em "Assinar" em qualquer plano

### **3. Usar Cartões de Teste**
- **Para pagamento aprovado**: Use o cartão `4235647728025682`
- **Para pagamento rejeitado**: Use o cartão `4000000000000002`
- **Para pagamento pendente**: Use o cartão `4000000000000119`

### **4. Dados do Pagador**
- O sistema automaticamente usará os dados da **Maria**
- **Email**: `test_user_3971@testuser.com`
- **Nome**: `Maria`
- **CPF**: `12345678901`

## ⚠️ Importante

- ✅ **Sem validação de email** - A conta de Maria já está validada
- ✅ **Transações simuladas** - Nenhum dinheiro real será movimentado
- ✅ **Ambiente isolado** - Testes não afetam contas reais
- ✅ **Webhooks funcionais** - Notificações serão enviadas normalmente

## 🔐 Para Login no Painel

### **Acessar Painel do Vendedor:**
1. Vá para [Painel de Desenvolvedores](https://www.mercadopago.com.br/developers/panel)
2. Use as credenciais da conta **Vendedor**:
   - **Email**: `test_user_1840...@testuser.com`
   - **Senha**: `6adKvt9d5U`

### **Acessar Painel do Comprador:**
1. Vá para [Painel de Desenvolvedores](https://www.mercadopago.com.br/developers/panel)
2. Use as credenciais da conta **Maria**:
   - **Email**: `test_user_3971@testuser.com`
   - **Senha**: `QOjLnDF4WI`

## 📊 Endpoints de Teste

### **Obter Cartões de Teste:**
```bash
GET http://localhost:8000/api/payments/test-accounts/cards
```

### **Criar Preferência de Pagamento:**
```bash
POST http://localhost:8000/api/payments/create-preference
Content-Type: application/json

{
  "plan_name": "Básico",
  "amount": 29.90,
  "description": "Plano Básico - Teste"
}
```

## 🎉 Status Atual

✅ **Contas de teste criadas**  
✅ **Sistema configurado**  
✅ **Cartões de teste disponíveis**  
✅ **Sem validação de email**  
✅ **Pronto para testes!**  

---

**Agora você pode testar pagamentos sem problemas de validação de email!** 🚀
