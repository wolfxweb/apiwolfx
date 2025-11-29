# Recursos Humanos

## O que é esta funcionalidade?

A funcionalidade de Recursos Humanos permite cadastrar, gerenciar e controlar funcionários da empresa, incluindo criação de contas de usuário vinculadas, gestão de permissões individuais e integração com o módulo financeiro através de categorias e centros de custo.

## Como Acessar

- **Menu**: "Cadastros" → "RH"
- **URL direta**: `/hr`
- **Permissão**: Apenas usuários com permissão de administrador da empresa

## Objetivo

- Cadastrar funcionários da empresa
- Gerenciar informações pessoais e profissionais dos funcionários
- Criar contas de usuário vinculadas aos funcionários
- Configurar permissões individuais de acesso ao sistema
- Associar funcionários a categorias financeiras e centros de custo
- Controlar status dos funcionários (ativo, inativo, demitido)
- Sincronizar status entre funcionário e usuário do sistema

---

## Passo a Passo

### Cadastrar um Novo Funcionário

1. **Acesse a página de Recursos Humanos**
   - No menu, clique em "Cadastros" → "RH"

2. **Clique em "Novo Funcionário"**
   - Botão localizado no canto superior direito da página

3. **Preencha os dados pessoais**
   - **Nome Completo**: Nome completo do funcionário (obrigatório)
   - **CPF**: CPF do funcionário no formato 000.000.000-00 (obrigatório)
   - **RG**: Número do RG (opcional)
   - **Data de Nascimento**: Data de nascimento (opcional)
   - **E-mail**: E-mail de contato (opcional)
   - **Telefone**: Telefone de contato (opcional)

4. **Preencha os dados profissionais**
   - **Cargo**: Cargo/função do funcionário (opcional)
   - **Departamento**: Departamento ao qual pertence (opcional)
   - **Data de Admissão**: Data de admissão (obrigatório)
   - **Salário Base**: Salário base do funcionário (obrigatório)
   - **Tipo de Contrato**: Selecione o tipo (CLT, PJ, Estágio, Temporário)
   - **Carga Horária**: Horas mensais de trabalho (padrão: 220)

5. **Configure integração financeira (opcional)**
   - **Categoria Financeira (Conta Contábil)**: Selecione a categoria financeira para associar o funcionário
   - **Centro de Custo**: Selecione o centro de custo ao qual o funcionário está vinculado

6. **Configure conta de usuário (opcional)**
   - **E-mail para Login**: E-mail que será usado para login no sistema
   - **Senha**: Senha para acesso ao sistema
   - **Nível de Acesso**: Selecione o nível (Visualizador, Analista, Gerente)
   - **Nota**: Se você criar uma conta de usuário, o funcionário poderá fazer login no sistema

7. **Clique em "Salvar"**
   - O funcionário será cadastrado
   - Se uma conta de usuário foi criada, ela estará vinculada ao funcionário

### Visualizar Lista de Funcionários

1. **Na página de Recursos Humanos**
   - A lista de funcionários é exibida automaticamente em formato de tabela

2. **Use os filtros disponíveis**
   - **Status**: Filtre por status (Todos, Ativos, Inativos, Afastados)
   - **Buscar**: Digite para buscar por nome, CPF, e-mail ou cargo

3. **Visualize as informações**
   - A tabela mostra: ID, Nome, CPF, Cargo, Departamento, Salário Base, Status
   - Clique no ícone de visualização para ver detalhes completos

### Visualizar Detalhes de um Funcionário

1. **Na lista de funcionários**
   - Clique no ícone de visualização (olho) na coluna "Ações"

2. **Visualize as informações**
   - **Aba "Informações"**: Dados pessoais, profissionais e contratuais
   - **Aba "Permissões"**: Permissões de acesso ao sistema (se tiver conta de usuário)

3. **Edite o funcionário**
   - Clique no botão "Editar" no topo da página
   - Faça as alterações necessárias
   - Clique em "Salvar"

### Editar um Funcionário

1. **Acesse os detalhes do funcionário**
   - Clique no ícone de visualização na lista

2. **Clique em "Editar"**
   - Botão localizado no canto superior direito

3. **Faça as alterações desejadas**
   - Você pode alterar qualquer campo do funcionário
   - **Status**: Altere o status (Ativo, Inativo, Demitido)
     - **Importante**: Ao inativar ou demitir um funcionário, o usuário vinculado também será inativado e perderá acesso ao sistema
     - Ao reativar um funcionário, o usuário também será reativado

4. **Atualize a conta de usuário (se aplicável)**
   - Altere o e-mail, senha ou nível de acesso
   - Se o funcionário não tinha conta, você pode criar uma agora
   - Se remover o e-mail, a conta será desvinculada

5. **Clique em "Salvar"**
   - As alterações serão salvas
   - O status do usuário será sincronizado automaticamente

### Configurar Permissões de Acesso

1. **Acesse os detalhes do funcionário**
   - O funcionário deve ter uma conta de usuário vinculada

2. **Vá para a aba "Permissões"**
   - Se o funcionário não tiver conta, você verá um aviso para criar uma

3. **Configure as permissões**
   - Cada menu e submenu tem uma opção de acesso
   - Marque as caixas para permitir acesso aos menus desejados
   - Desmarque para negar acesso

4. **Clique em "Salvar Permissões"**
   - As permissões serão salvas
   - O funcionário terá acesso apenas aos menus permitidos

### Inativar um Funcionário

1. **Edite o funcionário**
   - Acesse os detalhes e clique em "Editar"

2. **Altere o Status**
   - Selecione "Inativo" ou "Demitido" no campo Status

3. **Salve as alterações**
   - O funcionário será marcado como inativo
   - Se houver usuário vinculado, ele também será inativado e perderá acesso ao sistema

---

## Recursos Disponíveis

### Cadastro de Funcionário
- Dados pessoais: Nome, CPF, RG, Data de Nascimento, E-mail, Telefone
- Dados profissionais: Cargo, Departamento, Data de Admissão
- Dados contratuais: Salário Base, Tipo de Contrato, Carga Horária
- Integração financeira: Categoria Financeira, Centro de Custo
- Conta de usuário: E-mail, Senha, Nível de Acesso

### Gestão de Funcionários
- Lista completa de funcionários
- Filtros por status
- Busca por nome, CPF, e-mail ou cargo
- Visualização detalhada
- Edição completa de dados
- Controle de status (Ativo, Inativo, Demitido)

### Permissões Individuais
- Configuração granular de acesso por menu e submenu
- Permissões específicas para cada funcionário
- Controle independente de acesso

### Sincronização com Usuários
- Criação automática de conta de usuário
- Sincronização de status (ativo/inativo)
- Sincronização de nome (primeiro nome e sobrenome)
- Inativação automática de usuário ao inativar funcionário

---

## Dicas e Observações

### Cadastro de Funcionário:
- O CPF é obrigatório e deve ser único
- A data de admissão é obrigatória
- O salário base é obrigatório e usado em cálculos de folha de pagamento
- Você pode criar a conta de usuário no momento do cadastro ou depois

### Conta de Usuário:
- Não é obrigatório criar conta de usuário para todos os funcionários
- Apenas funcionários com conta podem fazer login no sistema
- O e-mail usado para login deve ser único no sistema
- O nível de acesso determina permissões padrão, mas pode ser personalizado

### Permissões:
- As permissões só podem ser configuradas se o funcionário tiver conta de usuário
- Usuários com nível "company_admin" têm acesso total automaticamente
- As permissões são verificadas em tempo real ao acessar menus

### Status do Funcionário:
- **Ativo**: Funcionário ativo na empresa
- **Inativo**: Funcionário inativo (usuário também inativado)
- **Demitido**: Funcionário demitido (usuário também inativado)
- Ao inativar ou demitir, o usuário perde acesso imediatamente

### Integração Financeira:
- Associar funcionário a categoria financeira e centro de custo facilita a gestão financeira
- Essas informações são usadas em relatórios e análises financeiras

### Segurança:
- Apenas administradores da empresa podem gerenciar funcionários
- As senhas são armazenadas de forma segura (hash)
- O CPF é validado para evitar duplicatas

---

## Perguntas Frequentes

**P: Posso cadastrar um funcionário sem criar conta de usuário?**
R: Sim, a conta de usuário é opcional. Você pode criar depois se necessário.

**P: O que acontece se eu inativar um funcionário?**
R: O funcionário será marcado como inativo e, se houver usuário vinculado, ele também será inativado e perderá acesso ao sistema.

**P: Como reativar um funcionário?**
R: Edite o funcionário e altere o status para "Ativo". O usuário vinculado também será reativado automaticamente.

**P: Posso alterar o CPF de um funcionário?**
R: Não é recomendado, pois o CPF é usado como identificador único. Se necessário, entre em contato com o suporte.

**P: Como configurar permissões para um funcionário?**
R: Acesse os detalhes do funcionário, vá para a aba "Permissões" e marque os menus que ele pode acessar. O funcionário precisa ter uma conta de usuário.

**P: O funcionário pode ter acesso a tudo mesmo sem ser administrador?**
R: Sim, você pode configurar permissões individuais para dar acesso a todos os menus, mesmo que o nível de acesso seja "Visualizador" ou "Analista".

**P: Posso associar um funcionário a mais de uma categoria financeira?**
R: Não, cada funcionário pode estar associado a apenas uma categoria financeira e um centro de custo.

**P: O que acontece se eu remover o e-mail do funcionário?**
R: A conta de usuário será desvinculada, mas não será excluída. O funcionário perderá acesso ao sistema.

---

**Próximo passo**: Após cadastrar funcionários, consulte o manual de "Tarefas" para atribuir tarefas aos funcionários ou o manual de "Dashboard Financeiro" para visualizar informações financeiras relacionadas aos funcionários.

