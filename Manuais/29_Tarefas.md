# Tarefas e Atividades

## O que é esta funcionalidade?

A funcionalidade de Tarefas e Atividades permite criar, gerenciar e acompanhar tarefas da empresa, atribuindo responsáveis, definindo prazos, categorizando e associando a produtos. Todos os usuários da empresa podem visualizar todas as tarefas, facilitando a colaboração e o acompanhamento de atividades.

## Como Acessar

- **Menu**: "Cadastros" → "Tarefas"
- **URL direta**: `/tasks`
- **Permissão**: Todos os usuários podem visualizar. Apenas criadores, responsáveis ou administradores podem editar/excluir.

## Objetivo

- Criar e gerenciar tarefas da empresa
- Atribuir tarefas a usuários específicos
- Definir prazos e prioridades
- Categorizar tarefas por tipo
- Associar tarefas a produtos
- Acompanhar status e progresso das tarefas
- Filtrar e buscar tarefas facilmente

---

## Passo a Passo

### Criar uma Nova Tarefa

1. **Acesse a página de Tarefas**
   - No menu, clique em "Cadastros" → "Tarefas"

2. **Clique em "Nova Tarefa"**
   - Botão localizado no canto superior direito da página

3. **Preencha as informações básicas**
   - **Título**: Nome/título da tarefa (obrigatório)
   - **Descrição**: Descrição detalhada do que deve ser feito (opcional)
   - **Categoria**: Selecione a categoria (Vendas, Suporte, Desenvolvimento, Marketing, Financeiro, RH, Operacional, Outro)
   - **Prioridade**: Selecione a prioridade (Baixa, Média, Alta, Urgente)
   - **Data de Vencimento**: Data que a tarefa deve ser concluída (obrigatório)

4. **Atribua a tarefa (opcional)**
   - **Atribuído a**: Selecione um usuário da empresa para ser responsável pela tarefa
   - Se não atribuir, a tarefa ficará sem responsável

5. **Associe a um produto (opcional)**
   - **Produto**: Selecione um produto interno para associar à tarefa
   - Útil para tarefas relacionadas a produtos específicos

6. **Clique em "Salvar"**
   - A tarefa será criada com status "Pendente"
   - A tarefa aparecerá na lista para todos os usuários da empresa

### Visualizar Lista de Tarefas

1. **Na página de Tarefas**
   - A lista de tarefas é exibida automaticamente em formato de tabela

2. **Use os filtros disponíveis**
   - **Status**: Filtre por status (Todos, Pendente, Em Andamento, Aguardando, Concluída, Cancelada)
   - **Atribuído a**: Filtre por usuário responsável
   - **Buscar**: Digite para buscar por título ou descrição

3. **Visualize as informações**
   - A tabela mostra: Título, Produto, Atribuído a, Data de Vencimento, Prioridade, Status
   - Tarefas vencidas aparecem com fundo amarelo claro
   - Tarefas do dia aparecem com fundo amarelo mais claro

### Visualizar Detalhes de uma Tarefa

1. **Na lista de tarefas**
   - Clique no ícone de visualização (olho) na coluna "Ações"
   - Ou clique diretamente no título da tarefa

2. **Visualize as informações completas**
   - Todos os dados da tarefa
   - Informações do criador e responsável
   - Datas de criação, atualização e conclusão
   - Produto associado (se houver)

3. **Edite a tarefa (se tiver permissão)**
   - Se você for o criador, responsável ou administrador, poderá editar
   - Clique em "Editar Tarefa" para fazer alterações

### Editar uma Tarefa

1. **Acesse os detalhes da tarefa**
   - Clique no ícone de visualização na lista

2. **Clique em "Editar Tarefa"**
   - Botão localizado na página de detalhes
   - Disponível apenas se você tiver permissão

3. **Faça as alterações desejadas**
   - Você pode alterar: Título, Descrição, Categoria, Prioridade, Data de Vencimento, Responsável, Produto
   - **Nota**: Não é possível alterar o criador da tarefa

4. **Clique em "Salvar"**
   - As alterações serão salvas
   - A data de atualização será atualizada automaticamente

### Atualizar Status de uma Tarefa

1. **Acesse os detalhes da tarefa**
   - Clique no ícone de visualização na lista

2. **Selecione o novo status**
   - Use o dropdown "Status" na página de detalhes
   - Status disponíveis:
     - **Pendente**: Tarefa criada, ainda não iniciada
     - **Em Andamento**: Tarefa em execução
     - **Aguardando**: Tarefa aguardando algo (ex: resposta de terceiros)
     - **Concluída**: Tarefa finalizada
     - **Cancelada**: Tarefa cancelada

3. **Clique em "Salvar Status"**
   - O status será atualizado
   - Se marcar como "Concluída", a data de conclusão será registrada automaticamente

### Excluir uma Tarefa

1. **Na lista de tarefas**
   - Clique no ícone de exclusão (lixeira) na coluna "Ações"
   - Disponível apenas se você for o criador ou administrador

2. **Confirme a exclusão**
   - Uma modal de confirmação será exibida
   - Confirme que deseja excluir a tarefa

3. **A tarefa será excluída permanentemente**
   - Esta ação não pode ser desfeita

---

## Recursos Disponíveis

### Criação de Tarefa
- Título (obrigatório)
- Descrição detalhada
- Categoria (Vendas, Suporte, Desenvolvimento, Marketing, Financeiro, RH, Operacional, Outro)
- Prioridade (Baixa, Média, Alta, Urgente)
- Data de vencimento (obrigatório)
- Usuário responsável (opcional)
- Produto associado (opcional)

### Visualização e Filtros
- Lista completa de tarefas da empresa
- Filtros por status e responsável
- Busca por título ou descrição
- Indicadores visuais para tarefas vencidas e do dia
- Visualização detalhada de cada tarefa

### Gestão de Tarefas
- Edição completa (se tiver permissão)
- Atualização de status
- Exclusão (apenas criador ou administrador)
- Acompanhamento de datas (criação, atualização, conclusão)

### Permissões
- **Visualizar**: Todos os usuários da empresa podem ver todas as tarefas
- **Criar**: Qualquer usuário pode criar tarefas
- **Editar**: Criador, responsável ou administrador
- **Excluir**: Criador ou administrador
- **Atualizar Status**: Responsável ou administrador

---

## Dicas e Observações

### Criação de Tarefas:
- Sempre defina uma data de vencimento para facilitar o acompanhamento
- Use descrições claras e detalhadas para facilitar a execução
- Categorize adequadamente para facilitar filtros e relatórios
- Atribua responsáveis para garantir que a tarefa seja executada

### Prioridades:
- **Baixa**: Tarefas que podem ser feitas quando houver tempo
- **Média**: Tarefas normais do dia a dia
- **Alta**: Tarefas importantes que precisam de atenção
- **Urgente**: Tarefas críticas que precisam ser feitas imediatamente

### Status:
- Use "Aguardando" quando a tarefa depende de algo externo
- Marque como "Concluída" apenas quando realmente finalizada
- Use "Cancelada" se a tarefa não for mais necessária

### Indicadores Visuais:
- Tarefas vencidas aparecem com fundo amarelo claro
- Tarefas do dia aparecem com fundo amarelo mais claro
- Use esses indicadores para priorizar seu trabalho

### Associação com Produtos:
- Associe tarefas a produtos quando a tarefa estiver relacionada a um produto específico
- Isso facilita o rastreamento de atividades por produto

### Filtros e Busca:
- Use os filtros para focar em tarefas específicas
- A busca funciona em título e descrição
- Combine filtros e busca para encontrar tarefas rapidamente

### Colaboração:
- Como todos podem ver todas as tarefas, use isso para colaboração
- Comunique-se através da descrição ou comentários (se implementado)
- Atualize o status regularmente para manter a equipe informada

---

## Perguntas Frequentes

**P: Posso criar uma tarefa sem atribuir a ninguém?**
R: Sim, você pode criar tarefas sem responsável. Elas aparecerão na lista para todos visualizarem.

**P: Quem pode editar uma tarefa?**
R: O criador da tarefa, o responsável atribuído ou um administrador da empresa.

**P: Posso excluir uma tarefa que não criei?**
R: Apenas se você for administrador da empresa. Caso contrário, apenas o criador pode excluir.

**P: O que acontece quando marco uma tarefa como "Concluída"?**
R: A data de conclusão é registrada automaticamente e a tarefa permanece visível na lista (com status "Concluída").

**P: Posso alterar o criador de uma tarefa?**
R: Não, o criador é definido automaticamente quando a tarefa é criada e não pode ser alterado.

**P: Como saber quais tarefas estão vencidas?**
R: Tarefas vencidas aparecem com fundo amarelo claro na lista. Você também pode filtrar por status.

**P: Posso associar uma tarefa a mais de um produto?**
R: Não, cada tarefa pode estar associada a apenas um produto. Se necessário, crie tarefas separadas.

**P: Todos os usuários veem todas as tarefas?**
R: Sim, todos os usuários da empresa podem visualizar todas as tarefas, facilitando a colaboração e transparência.

**P: Posso criar tarefas para mim mesmo?**
R: Sim, você pode criar tarefas e atribuí-las a si mesmo ou a outros usuários.

**P: O que acontece se eu excluir uma tarefa?**
R: A tarefa será excluída permanentemente e não poderá ser recuperada. Esta ação não pode ser desfeita.

---

**Próximo passo**: Após criar tarefas, consulte o manual de "Recursos Humanos" para atribuir tarefas a funcionários específicos ou o manual de "Dashboard Principal" para visualizar um resumo das atividades.

