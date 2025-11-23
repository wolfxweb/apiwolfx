# Pedidos do Mercado Livre

## O que é esta funcionalidade?

A funcionalidade de Pedidos do Mercado Livre permite visualizar, filtrar e gerenciar todos os pedidos recebidos através do Mercado Livre, incluindo atualização de status e controle de entregas.

## Como Acessar

- **Menu**: "Mercado Livre" → "Pedidos"
- **URL direta**: `/ml/orders`

## Objetivo

- Visualizar todos os pedidos recebidos
- Filtrar pedidos por diversos critérios
- Atualizar status interno dos pedidos
- Acompanhar entregas
- Controlar processamento de pedidos
- Exportar dados de pedidos

---

## Passo a Passo

### Visualizar Lista de Pedidos

1. **Acesse a página de Pedidos**
   - No menu, clique em "Mercado Livre" → "Pedidos"

2. **Visualize a lista de pedidos**
   - Cada pedido mostra: número, comprador, produtos, valor, status, data
   - Use a paginação para navegar entre páginas

3. **Veja o resumo**
   - Total de pedidos
   - Valor total
   - Outras métricas relevantes

### Filtrar Pedidos

1. **Clique em "Filtros"** no topo da página

2. **Configure os filtros desejados**
   - **Busca rápida**: Por código, comprador ou produto
   - **Conta ML**: Selecione uma conta específica
   - **Período**: Hoje, esta semana, este mês, personalizado
   - **Status**: Pendente, confirmado, enviado, entregue, cancelado
   - **Tipo de envio**: Mercado Envios, Full, etc.
   - **Valor**: Faixa de valores

3. **Aplique os filtros**
   - Clique em "Aplicar" ou "Filtrar"
   - A lista será atualizada

4. **Limpe os filtros**
   - Clique em "Limpar" para remover todos os filtros

### Visualizar Detalhes de um Pedido

1. **Na lista de pedidos**
   - Clique no pedido desejado

2. **Visualize todas as informações**
   - **Dados do Pedido**: Número, data, valor total
   - **Comprador**: Nome, endereço, contato
   - **Produtos**: Lista de itens, quantidades, preços
   - **Envio**: Tipo, endereço de entrega, código de rastreamento
   - **Pagamento**: Forma de pagamento, status
   - **Status**: Status atual e histórico

### Atualizar Status Interno do Pedido

1. **Na página de detalhes do pedido**
   - Localize a seção de status interno

2. **Selecione o novo status**
   - **Aguardando Processamento**: Pedido recebido, aguardando início
   - **Separação**: Produtos sendo separados
   - **Expedição**: Produtos sendo preparados para envio
   - **Pronto para Envio**: Aguardando coleta/entrega à transportadora
   - **Enviado**: Pedido enviado ao cliente

3. **Salve a alteração**
   - O status será atualizado
   - Isso não altera o status no Mercado Livre, apenas no sistema interno

### Sincronizar Pedidos

1. **Clique em "Atualizar pedidos"** no menu de ações

2. **Aguarde a sincronização**
   - O sistema buscará novos pedidos do Mercado Livre
   - Pedidos existentes serão atualizados

3. **Verifique os resultados**
   - Novos pedidos aparecerão na lista
   - Atualizações serão aplicadas

**Nota**: A sincronização também pode acontecer automaticamente via webhooks.

### Importar Pedidos

1. **Clique em "Importar pedidos"** no menu de ações

2. **Configure o período**
   - Selecione o período desejado
   - Ou importe todos os pedidos disponíveis

3. **Confirme a importação**
   - Os pedidos serão importados do Mercado Livre
   - Aguarde a conclusão do processo

### Adicionar Código de Rastreamento

1. **Na página de detalhes do pedido**
   - Localize a seção de envio

2. **Informe o código de rastreamento**
   - Digite o código fornecido pela transportadora
   - Salve a informação

3. **O código será registrado**
   - Pode ser usado para acompanhamento
   - Pode ser sincronizado com o Mercado Livre (se aplicável)

### Exportar Pedidos

1. **Use a opção de exportação** (se disponível)
   - Pode estar no menu de ações
   - Ou em um botão específico

2. **Selecione o formato**
   - Excel, CSV, PDF, etc.

3. **Configure o que exportar**
   - Todos os pedidos ou apenas os filtrados
   - Campos a incluir

4. **Baixe o arquivo**
   - O arquivo será gerado e disponibilizado para download

---

## Recursos Disponíveis

### Informações Exibidas:

- **Dados do Pedido**
  - Número do pedido (ML)
  - Data e hora
  - Valor total
  - Status no ML
  - Status interno

- **Comprador**
  - Nome
  - Endereço de entrega
  - Contato

- **Produtos**
  - Lista de itens
  - Quantidades
  - Preços unitários
  - Valores totais

- **Envio**
  - Tipo de envio
  - Endereço completo
  - Código de rastreamento
  - Status de entrega

- **Pagamento**
  - Forma de pagamento
  - Status do pagamento
  - Valor pago

### Ações Disponíveis:

- Visualizar lista de pedidos
- Filtrar por diversos critérios
- Visualizar detalhes completos
- Atualizar status interno
- Sincronizar pedidos
- Importar pedidos
- Adicionar código de rastreamento
- Exportar pedidos
- Remover pedidos (se aplicável)

---

## Dicas e Observações

### Sincronização Automática:
- Pedidos podem ser recebidos automaticamente via webhooks
- Isso garante atualização em tempo real
- Verifique se os webhooks estão configurados

### Atualização de Estoque:
- Quando um pedido é recebido, o estoque pode ser atualizado automaticamente
- Produtos Full apenas registram baixa, produtos normais sincronizam com ML
- Cada pedido processa o estoque apenas uma vez

### Status Interno vs Status ML:
- O status interno é apenas para controle interno
- Não altera o status no Mercado Livre automaticamente
- Use para organizar o processamento

### Múltiplas Contas:
- Se você tem várias contas do ML, filtre por conta
- Cada conta pode ter seus próprios pedidos
- Gerencie cada conta separadamente

### Filtros Úteis:
- Use filtros para encontrar pedidos específicos rapidamente
- Combine múltiplos filtros para buscas precisas
- Salve filtros frequentes se a opção estiver disponível

### Cuidados:
- Não exclua pedidos sem necessidade (mantenha histórico)
- Mantenha status atualizados para melhor controle
- Verifique informações antes de processar

---

## Perguntas Frequentes

**P: Os pedidos são atualizados automaticamente?**
R: Sim, se os webhooks estiverem configurados. Você também pode sincronizar manualmente.

**P: O que acontece com o estoque quando recebo um pedido?**
R: O estoque é atualizado automaticamente. Produtos normais são sincronizados com ML, produtos Full apenas registram baixa.

**P: Posso alterar o status do pedido no Mercado Livre através do sistema?**
R: Depende da funcionalidade. O status interno é separado do status no ML.

**P: Como vejo apenas pedidos de uma conta específica?**
R: Use o filtro "Conta ML" para selecionar a conta desejada.

**P: Posso exportar os pedidos para Excel?**
R: Depende da funcionalidade disponível. Verifique se há opção de exportação.

**P: O que significa cada status interno?**
R: Os status ajudam a controlar o processamento: Aguardando → Separação → Expedição → Pronto → Enviado.

**P: Posso adicionar observações aos pedidos?**
R: Depende da funcionalidade. Algumas versões permitem adicionar notas.

---

**Próximo passo**: Consulte o manual de "Estoque" para entender como os pedidos afetam o estoque automaticamente.

