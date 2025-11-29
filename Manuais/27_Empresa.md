# Empresa

## O que é esta funcionalidade?

A funcionalidade de Empresa permite visualizar e editar todas as informações cadastrais e configurações da sua empresa no sistema, incluindo dados fiscais, endereço, regime tributário e parâmetros de impostos.

## Como Acessar

- **Menu**: "Cadastros" → "Empresa"
- **URL direta**: `/auth/company/edit`

## Objetivo

- Visualizar e atualizar dados cadastrais da empresa
- Configurar informações fiscais e tributárias
- Definir parâmetros de impostos para cálculos automáticos
- Configurar endereço completo da empresa
- Gerenciar configurações gerais do sistema

---

## Passo a Passo

### Visualizar Dados da Empresa

1. **Acesse a página de Empresa**
   - No menu, clique em "Cadastros" → "Empresa"
   - Ou acesse diretamente `/auth/company/edit`

2. **Visualize as informações**
   - A página exibe todas as informações cadastrais organizadas em seções
   - Navegue pelas diferentes seções para ver todos os dados

### Editar Identificação da Empresa

1. **Na seção "Identificação da Empresa"**
   - **Nome da Empresa**: Nome completo da empresa (obrigatório)
   - **Slug**: Identificador único gerado automaticamente (somente leitura)
   - **Domínio**: Domínio da empresa (se aplicável)
   - **Descrição**: Descrição breve da empresa

2. **Preencha os dados cadastrais**
   - **Razão Social**: Razão social completa da empresa
   - **Nome Fantasia**: Nome fantasia da empresa
   - **CNPJ**: CNPJ da empresa (formato: XX.XXX.XXX/XXXX-XX)
   - **Inscrição Estadual (IE)**: Inscrição estadual (se aplicável)
   - **Inscrição Municipal (IM)**: Inscrição municipal (se aplicável)
   - **Regime Tributário**: Selecione o regime (Simples Nacional, Lucro Presumido ou Lucro Real)

3. **Clique em "Salvar"** para salvar as alterações

### Configurar Endereço

1. **Na seção "Endereço"**
   - **CEP**: CEP da empresa (o sistema pode buscar automaticamente)
   - **Endereço**: Logradouro (rua, avenida, etc.)
   - **Número**: Número do endereço
   - **Complemento**: Complemento (apto, sala, etc.)
   - **Bairro**: Bairro
   - **Cidade**: Cidade
   - **Estado**: Estado (UF)
   - **País**: País (padrão: Brasil)

2. **Preencha todos os campos** e clique em "Salvar"

### Configurar Impostos e Tributação

1. **Selecione o Regime Tributário**
   - O sistema exibirá campos diferentes conforme o regime selecionado

2. **Para Simples Nacional:**
   - **Alíquota do Simples Nacional (%)**: Alíquota aplicável
   - **Faturamento Anual**: Faturamento anual estimado

3. **Para Lucro Presumido ou Lucro Real:**
   - **Alíquota IR (%)**: Alíquota de Imposto de Renda
   - **Alíquota CSLL (%)**: Alíquota de Contribuição Social sobre o Lucro Líquido
   - **Alíquota PIS (%)**: Alíquota de PIS
   - **Alíquota COFINS (%)**: Alíquota de COFINS
   - **Alíquota ICMS (%)**: Alíquota de ICMS
   - **Alíquota ISS (%)**: Alíquota de ISS
   - **Faturamento Anual**: Faturamento anual estimado

4. **Para Lucro Real (campos adicionais):**
   - **Alíquota IR Real (%)**: Alíquota de IR no regime real
   - **Alíquota CSLL Real (%)**: Alíquota de CSLL no regime real
   - **Alíquota PIS Real (%)**: Alíquota de PIS no regime real
   - **Alíquota COFINS Real (%)**: Alíquota de COFINS no regime real
   - **Alíquota ICMS Real (%)**: Alíquota de ICMS no regime real
   - **Alíquota ISS Real (%)**: Alíquota de ISS no regime real

5. **Clique em "Salvar"** para salvar as configurações

### Configurar Parâmetros Adicionais

1. **Na seção "Configurações"**
   - **Percentual de Marketing (%)**: Percentual padrão para custos de marketing
   - **Custo Adicional por Pedido**: Custo adicional aplicado a cada pedido
   - **Pedidos ML como Recebíveis**: Marque se pedidos do Mercado Livre devem ser tratados como contas a receber

2. **Clique em "Salvar"** para salvar as configurações

---

## Recursos Disponíveis

### Seção: Identificação da Empresa
- Nome da empresa (obrigatório)
- Slug (gerado automaticamente)
- Domínio
- Descrição
- Razão Social
- Nome Fantasia
- CNPJ
- Inscrições (Estadual e Municipal)
- Regime Tributário

### Seção: Endereço
- CEP
- Logradouro
- Número
- Complemento
- Bairro
- Cidade
- Estado (UF)
- País

### Seção: Impostos e Tributação
- Campos dinâmicos baseados no regime tributário selecionado
- Alíquotas de impostos (IR, CSLL, PIS, COFINS, ICMS, ISS)
- Faturamento anual
- Campos específicos para Lucro Real

### Seção: Configurações
- Percentual de Marketing
- Custo Adicional por Pedido
- Opção para tratar pedidos ML como recebíveis

---

## Dicas e Observações

### Preenchimento de Dados:
- O campo "Nome da Empresa" é obrigatório
- O CNPJ deve estar no formato correto (XX.XXX.XXX/XXXX-XX)
- O regime tributário determina quais campos de impostos serão exibidos
- Alguns campos são opcionais, mas recomendamos preencher para cálculos mais precisos

### Impostos:
- As alíquotas configuradas aqui são usadas em cálculos automáticos do sistema
- Verifique sempre se as alíquotas estão atualizadas conforme a legislação vigente
- O faturamento anual é importante para cálculos de impostos proporcionais

### Endereço:
- O CEP pode ser usado para busca automática de endereço (se implementado)
- Mantenha o endereço sempre atualizado para emissão de documentos fiscais

### Configurações:
- O percentual de marketing é usado em análises de produtos
- O custo adicional por pedido é aplicado automaticamente em cálculos
- A opção "Pedidos ML como Recebíveis" afeta como os pedidos aparecem no módulo financeiro

### Segurança:
- Apenas usuários com permissão de administrador da empresa podem editar essas informações
- As alterações são salvas imediatamente ao clicar em "Salvar"

---

## Perguntas Frequentes

**P: Posso alterar o CNPJ da empresa?**
R: Sim, mas é importante verificar se não há dados vinculados ao CNPJ anterior. Em caso de dúvida, entre em contato com o suporte.

**P: O que acontece se eu mudar o regime tributário?**
R: Os campos de impostos serão atualizados automaticamente para refletir o novo regime. Você precisará preencher as novas alíquotas.

**P: Preciso preencher todos os campos de impostos?**
R: Não, mas recomendamos preencher para que o sistema possa fazer cálculos mais precisos. Os campos obrigatórios variam conforme o regime tributário.

**P: Como atualizo o endereço?**
R: Basta editar os campos na seção "Endereço" e clicar em "Salvar".

**P: O slug pode ser alterado?**
R: Não, o slug é gerado automaticamente e não pode ser alterado para manter a consistência do sistema.

**P: As configurações de impostos afetam cálculos existentes?**
R: As alterações afetam apenas novos cálculos. Cálculos já realizados não são alterados retroativamente.

---

**Próximo passo**: Após configurar a empresa, consulte os manuais de "Produtos Internos" e "Fornecedores" para começar a cadastrar seus produtos e fornecedores.

