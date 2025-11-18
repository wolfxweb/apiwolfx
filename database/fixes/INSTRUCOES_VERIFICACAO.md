# Instruções para Verificar e Criar Tabelas OpenAI em Produção

## 📋 Passo a Passo

### 1. **Verificar o que existe**
Execute o script `VERIFICAR_TABELAS_OPENAI.sql` no banco de produção:

```sql
-- Execute este arquivo completo no banco de produção
-- Ele mostrará o que existe e o que está faltando
```

**Resultado esperado:**
- ✅ Todas as tabelas principais devem existir
- ✅ Todas as tabelas de ferramentas devem existir
- ✅ Todas as colunas extras devem existir
- ✅ Ferramentas `get_orders` e `get_product_sales` devem existir
- ✅ Agente "Analise produto" deve existir

### 2. **Criar o que estiver faltando**
Se a verificação mostrar itens faltando, execute o script `CRIAR_TABELAS_FALTANTES.sql`:

```sql
-- Execute este arquivo completo no banco de produção
-- Ele criará apenas o que estiver faltando (usa IF NOT EXISTS)
```

### 3. **Verificar novamente**
Execute novamente o script `VERIFICAR_TABELAS_OPENAI.sql` para confirmar que tudo foi criado.

## 📊 Tabelas que devem existir

### Tabelas Principais:
1. `openai_assistants` - Configuração dos agentes
2. `openai_assistant_threads` - Threads de conversação
3. `openai_assistant_messages` - Mensagens individuais
4. `openai_assistant_usage` - Registro de uso e tokens

### Tabelas de Ferramentas:
1. `openai_tools` - Ferramentas reutilizáveis
2. `openai_tool_handlers` - Handlers das ferramentas
3. `openai_agent_tools` - Associação agente ↔ ferramenta

## 🔍 Colunas Importantes

### `openai_assistants` deve ter:
- `memory_enabled` (BOOLEAN)
- `memory_data` (JSONB)
- `initial_prompt` (TEXT)
- `welcome_message` (TEXT)
- `welcome_enabled` (BOOLEAN)
- `welcome_use_model` (BOOLEAN)

## 🛠️ Ferramentas que devem existir

1. **get_orders** - Seleciona pedidos com filtros
2. **get_product_sales** - Lista vendas de um produto

## 🤖 Agente que deve existir

- **Analise produto** - Agente para análise de produtos do Mercado Livre

## ⚠️ Observações

- Os scripts usam `IF NOT EXISTS` e `ON CONFLICT`, então são seguros para executar múltiplas vezes
- Se alguma tabela já existir, o script não tentará recriá-la
- Se alguma coluna já existir, o script não tentará adicioná-la novamente
- As ferramentas serão criadas ou atualizadas (upsert)

## 🔧 Se algo der errado

Se encontrar erros ao executar os scripts:

1. Verifique se o usuário do banco tem permissões de CREATE TABLE
2. Verifique se as tabelas `companies` e `users` existem (são referenciadas por foreign keys)
3. Verifique os logs do PostgreSQL para mais detalhes

## 📝 Exemplo de Execução

```bash
# No terminal do servidor de produção
psql -U seu_usuario -d seu_banco -f VERIFICAR_TABELAS_OPENAI.sql

# Se faltar algo:
psql -U seu_usuario -d seu_banco -f CRIAR_TABELAS_FALTANTES.sql

# Verificar novamente:
psql -U seu_usuario -d seu_banco -f VERIFICAR_TABELAS_OPENAI.sql
```

