# Script de Teste - Integração Asaas

Este script testa a integração completa com o Asaas:
1. Criação de cliente
2. Criação de cobrança
3. Verificação de webhook

## Dados do Teste

- **Nome**: Carlos Eduardo
- **CPF**: 00401584976
- **Email**: carlos.eduardo@teste.com

## Como Executar

### 1. Certifique-se de que as variáveis de ambiente estão configuradas

```bash
# Verificar se ASAAS_API_KEY está configurada
echo $ASAAS_API_KEY
```

Ou configure no arquivo `.env`:
```
ASAAS_API_KEY=your_asaas_api_key_here
ASAAS_WEBHOOK_URL=https://your-domain.com/api/asaas/webhooks
```

### 2. Executar o script

```bash
python test_asaas_integration.py
```

Ou:

```bash
python3 test_asaas_integration.py
```

## O que o script faz

1. **Cria Cliente no Asaas**
   - Cria o cliente "Carlos Eduardo" com CPF 00401584976
   - Retorna o ID do cliente criado

2. **Cria Cobrança**
   - Cria uma cobrança de R$ 99,90 via PIX
   - Vencimento: hoje
   - Retorna o `invoiceUrl` para pagamento

3. **Busca Cobrança**
   - Verifica se a cobrança foi criada corretamente
   - Mostra status e detalhes

4. **Simula Webhook**
   - Mostra como seria o webhook enviado pelo Asaas
   - Verifica se a URL do webhook está configurada

## Resultado Esperado

O script deve:
- ✅ Criar o cliente com sucesso
- ✅ Criar a cobrança com sucesso
- ✅ Retornar um `invoiceUrl` válido
- ✅ Mostrar os dados do webhook que seriam enviados

## Testando o Webhook Real

Para testar o webhook real:

1. **Configure o webhook no painel do Asaas:**
   - Acesse: https://sandbox.asaas.com (sandbox) ou https://www.asaas.com (produção)
   - Vá em Configurações > Webhooks
   - Adicione a URL: `https://your-domain.com/api/asaas/webhooks`

2. **Faça o pagamento:**
   - Use o `invoiceUrl` retornado pelo script
   - No sandbox, use dados de teste:
     - PIX: qualquer QR Code de teste
     - Boleto: aguarde vencimento ou pague via código de barras

3. **Verifique os logs do servidor:**
   - O webhook será recebido em `/api/asaas/webhooks`
   - Verifique os logs para confirmar o recebimento

## Ambiente Sandbox vs Produção

- **Sandbox**: `https://sandbox.asaas.com/api/v3`
  - Use para testes
  - Dados de teste não geram cobranças reais

- **Produção**: `https://api.asaas.com/v3`
  - Use apenas quando estiver pronto
  - Gera cobranças reais

O script detecta automaticamente o ambiente baseado na configuração.

## Troubleshooting

### Erro: "ASAAS_API_KEY não configurada"
- Verifique se a variável está no `.env`
- Ou exporte: `export ASAAS_API_KEY=your_key`

### Erro: "Cliente criado mas sem ID retornado"
- Verifique se a API key está correta
- Verifique se está usando o ambiente correto (sandbox/produção)

### Invoice URL não disponível
- Verifique os logs do script
- Pode ser que o Asaas não retorne `invoiceUrl` imediatamente
- Tente buscar o pagamento novamente após alguns segundos

