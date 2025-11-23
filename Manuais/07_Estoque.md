# Gerenciamento de Estoque

## O que é esta funcionalidade?

A funcionalidade de Estoque permite gerenciar as quantidades de produtos, visualizar movimentações, controlar depósitos e sincronizar automaticamente o estoque com anúncios do Mercado Livre.

## Como Acessar

- **Menu**: "Cadastros" → "Estoque"
- **URL direta**: `/estoque`

## Objetivo

- Controlar quantidades de produtos em estoque
- Visualizar movimentações de entrada e saída
- Gerenciar múltiplos depósitos/armazéns
- Sincronizar estoque automaticamente com Mercado Livre
- Acompanhar histórico de movimentações

---

## Passo a Passo

### Visualizar Estoque por Produto

1. **Acesse a página de Estoque**
   - No menu, clique em "Cadastros" → "Estoque"

2. **Selecione a aba "Estoque"**
   - Esta é a aba padrão ao acessar a página

3. **Visualize a lista de produtos**
   - Cada produto mostra:
     - Nome do produto
     - Quantidade disponível
     - Quantidade reservada
     - Quantidade total
     - Status de sincronização com ML

4. **Use a busca para filtrar**
   - Digite o nome ou código do produto na barra de busca
   - A lista será filtrada automaticamente

### Atualizar Quantidade de Estoque

1. **Na lista de produtos**
   - Localize o produto que deseja atualizar

2. **Clique em "Editar"** ou no ícone de edição
   - Uma modal ou página de edição será aberta

3. **Informe a nova quantidade**
   - Digite a quantidade desejada
   - Ou ajuste a quantidade atual (aumentar/diminuir)

4. **Selecione o depósito** (se houver múltiplos)
   - Escolha em qual depósito a alteração será feita

5. **Adicione uma observação** (opcional)
   - Descreva o motivo da alteração
   - Exemplo: "Entrada de mercadoria", "Ajuste de inventário"

6. **Salve a alteração**
   - Clique em "Salvar" ou "Atualizar"

7. **Sincronize com Mercado Livre** (se aplicável)
   - Após salvar, o sistema pode sincronizar automaticamente
   - Ou clique em "Sincronizar com ML" se a opção estiver disponível
   - Aguarde a confirmação de sincronização

### Visualizar Movimentações

1. **Acesse a aba "Movimentação"**
   - Clique na aba "Movimentação" no topo da página

2. **Visualize o histórico**
   - Lista todas as movimentações de estoque
   - Mostra: data, produto, tipo (entrada/saída), quantidade, observação

3. **Filtre as movimentações**
   - Por período (data inicial e final)
   - Por produto
   - Por tipo de movimentação
   - Por depósito

4. **Visualize detalhes**
   - Clique em uma movimentação para ver mais detalhes

### Registrar Entrada de Estoque

1. **Na aba "Estoque"**
   - Localize o produto que recebeu entrada

2. **Clique em "Editar"**
   - Abra a modal/página de edição

3. **Aumente a quantidade**
   - Digite a nova quantidade total
   - Ou informe a quantidade a ser adicionada

4. **Adicione observação**
   - Exemplo: "Recebimento de pedido do fornecedor X"
   - Inclua número da nota fiscal se aplicável

5. **Salve e sincronize**
   - Salve a alteração
   - Sincronize com Mercado Livre se necessário

### Registrar Saída de Estoque

1. **Na aba "Estoque"**
   - Localize o produto que teve saída

2. **Clique em "Editar"**
   - Abra a modal/página de edição

3. **Diminua a quantidade**
   - Digite a nova quantidade total
   - Ou informe a quantidade a ser retirada

4. **Adicione observação**
   - Exemplo: "Venda - Pedido ML123456"
   - Inclua informações relevantes

5. **Salve e sincronize**
   - Salve a alteração
   - Sincronize com Mercado Livre se necessário

**Nota**: Saídas por vendas podem ser registradas automaticamente quando um pedido é recebido do Mercado Livre.

### Gerenciar Depósitos

1. **Acesse a aba "Depósitos"**
   - Clique na aba "Depósitos" no topo da página

2. **Visualize os depósitos cadastrados**
   - Lista de todos os depósitos/armazéns

3. **Criar novo depósito** (se aplicável)
   - Clique em "Novo Depósito"
   - Informe nome e localização
   - Salve

4. **Editar depósito existente**
   - Clique em "Editar" no depósito desejado
   - Modifique as informações
   - Salve

### Sincronizar Estoque com Mercado Livre

1. **Após atualizar uma quantidade**
   - O sistema pode sincronizar automaticamente

2. **Ou sincronize manualmente**
   - Na lista de produtos, localize o produto
   - Clique em "Sincronizar com ML" ou botão similar
   - Aguarde a confirmação

3. **Verifique o status**
   - Produtos sincronizados mostrarão status de sucesso
   - Erros serão exibidos se houver problema

**Importante**: A sincronização atualiza todos os anúncios do Mercado Livre associados ao produto interno.

---

## Recursos Disponíveis

### Abas Disponíveis:

- **Estoque**: Visualização e edição de quantidades por produto
- **Movimentação**: Histórico de todas as movimentações
- **Depósitos**: Gerenciamento de depósitos/armazéns

### Informações Exibidas:

- **Quantidade Disponível**: Estoque disponível para venda
- **Quantidade Reservada**: Estoque reservado para pedidos
- **Quantidade Total**: Soma de disponível + reservado
- **Status ML**: Se está sincronizado com Mercado Livre
- **Última Movimentação**: Data da última alteração

### Ações Disponíveis:

- Editar quantidade de estoque
- Registrar entrada de mercadoria
- Registrar saída de mercadoria
- Sincronizar com Mercado Livre
- Visualizar movimentações
- Filtrar e buscar produtos
- Gerenciar depósitos
- Exportar relatórios (se disponível)

---

## Dicas e Observações

### Sincronização Automática:
- Quando um pedido é recebido do Mercado Livre, o estoque pode ser atualizado automaticamente
- Produtos "Full" (fulfillment) não precisam sincronização, apenas registro de baixa
- Produtos normais são sincronizados com todos os anúncios associados

### Múltiplos Anúncios:
- Um produto interno pode estar associado a vários anúncios do ML
- A sincronização atualiza todos os anúncios automaticamente
- Isso garante consistência entre todos os anúncios do mesmo produto

### Movimentações Automáticas:
- Vendas do Mercado Livre geram movimentações automaticamente
- Cada movimentação registra: pedido, data, quantidade, canal de venda
- O histórico completo fica disponível na aba "Movimentação"

### Cuidados:
- Verifique a quantidade antes de sincronizar com ML
- Produtos com anúncios fechados/pausados não serão atualizados
- Mantenha o estoque atualizado para evitar vendas sem estoque

### Organização:
- Use depósitos para organizar produtos por localização
- Adicione observações claras nas movimentações
- Consulte o histórico regularmente para controle

---

## Perguntas Frequentes

**P: O estoque é atualizado automaticamente quando recebo um pedido?**
R: Sim, quando um pedido é criado no Mercado Livre, o estoque é atualizado automaticamente e sincronizado com os anúncios.

**P: Preciso sincronizar manualmente após cada alteração?**
R: Depende. Algumas alterações sincronizam automaticamente. Para garantir, você pode sincronizar manualmente.

**P: O que acontece se eu atualizar o estoque de um produto associado a vários anúncios?**
R: Todos os anúncios associados ao produto serão atualizados com a nova quantidade.

**P: Produtos "Full" precisam sincronização?**
R: Não, produtos Full (fulfillment) apenas registram a baixa no estoque interno. A sincronização com ML não é necessária.

**P: Posso ter estoque negativo?**
R: Depende da configuração do sistema. Geralmente é permitido, mas pode gerar alertas.

**P: Como vejo o histórico de movimentações de um produto específico?**
R: Acesse a aba "Movimentação" e filtre pelo produto desejado.

**P: Posso exportar um relatório de estoque?**
R: Depende da funcionalidade disponível. Verifique se há opção de exportação na página.

---

**Próximo passo**: Consulte o manual de "Pedidos do Mercado Livre" para entender como os pedidos afetam o estoque automaticamente.

