# Documento Técnico: Sistema de Chat com Agentes e Ferramentas OpenAI

## Índice

1. [Visão Executiva e Valor de Negócio](#1-visão-executiva-e-valor-de-negócio)
2. [Arquitetura do Sistema](#2-arquitetura-do-sistema)
3. [Componentes Principais](#3-componentes-principais)
4. [Fluxos de Funcionamento](#4-fluxos-de-funcionamento)
5. [Casos de Uso Práticos](#5-casos-de-uso-práticos)
6. [Segurança e Isolamento](#6-segurança-e-isolamento)
7. [Monitoramento e Métricas](#7-monitoramento-e-métricas)
8. [Roadmap e Próximos Passos](#8-roadmap-e-próximos-passos)

---

## 1. Visão Executiva e Valor de Negócio

### 1.1 Problema que Resolve

O mercado de e-commerce, especialmente no Mercado Livre, gera volumes massivos de dados sobre produtos, vendas, pedidos e performance. Analisar esses dados manualmente consome tempo significativo e limita a capacidade de tomada de decisão rápida e baseada em dados.

**Desafios identificados:**
- Análise manual de produtos demora horas ou dias
- Consultas complexas requerem conhecimento técnico de SQL
- Dificuldade em cruzar informações de múltiplas fontes (vendas, marketing, estoque)
- Falta de insights acionáveis em linguagem natural
- Necessidade de especialistas para interpretar dados

### 1.2 Solução Proposta

Sistema de chat inteligente com agentes de IA que permite aos usuários interagir com dados do negócio usando linguagem natural. Os agentes podem executar consultas complexas, analisar resultados e fornecer recomendações acionáveis através de uma interface conversacional simples.

**Características principais:**
- Interface de chat intuitiva (similar ao ChatGPT)
- Agentes especializados por caso de uso
- Ferramentas reutilizáveis para consultas ao banco de dados
- Análise automática de dados com insights acionáveis
- Histórico de conversas persistente
- Isolamento seguro por empresa e usuário

### 1.3 Benefícios Principais

**Para Usuários:**
- **Produtividade**: Redução de 80-90% no tempo de análise de produtos
- **Acessibilidade**: Não requer conhecimento técnico (SQL, APIs)
- **Insights Rápidos**: Respostas em segundos vs. horas de análise manual
- **Disponibilidade 24/7**: Agentes sempre disponíveis para consultas
- **Aprendizado Contínuo**: Agentes melhoram com mais uso

**Para o Negócio:**
- **Escalabilidade**: Atende múltiplos usuários simultaneamente sem degradação
- **Redução de Custos**: Menos necessidade de analistas dedicados
- **Tomada de Decisão Rápida**: Insights em tempo real para ações imediatas
- **Padronização**: Análises consistentes seguindo melhores práticas
- **Rastreabilidade**: Histórico completo de consultas e recomendações

### 1.4 Diferenciais Competitivos

1. **Ferramentas Customizadas**: Sistema permite criar ferramentas específicas para o domínio do negócio (análise de produtos, consulta de pedidos, métricas de marketing)

2. **Isolamento Multi-tenant**: Cada empresa tem seus próprios agentes, conversas e dados isolados, garantindo privacidade e segurança

3. **Configuração Flexível**: Agentes podem ser configurados com diferentes modelos, instruções e ferramentas, adaptando-se a diferentes necessidades

4. **Memória Persistente**: Agentes podem manter contexto entre conversas, aprendendo preferências e padrões de uso

5. **Monitoramento Granular**: Tracking detalhado de uso de tokens por empresa, permitindo controle de custos e otimização

6. **Integração Nativa**: Integrado diretamente com o sistema existente, acessando dados em tempo real sem necessidade de sincronização

### 1.5 ROI e Impacto

**Métricas de Impacto Esperadas:**
- **Tempo de Análise**: Redução de 4-8 horas para 5-10 minutos por análise
- **Produtividade**: 10x mais análises realizadas no mesmo período
- **Precisão**: Análises padronizadas reduzem erros humanos
- **Satisfação**: Interface intuitiva aumenta adoção e satisfação do usuário

**Retorno sobre Investimento:**
- **Redução de Custos Operacionais**: Menos necessidade de equipe dedicada a análises
- **Aumento de Receita**: Decisões mais rápidas e baseadas em dados aumentam conversão
- **Eficiência**: Automação libera tempo para atividades estratégicas
- **Competitividade**: Capacidade de reagir rapidamente a mudanças de mercado

---

## 2. Arquitetura do Sistema

### 2.1 Visão Geral dos Componentes

O sistema é composto por cinco camadas principais:

```
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE APRESENTAÇÃO                    │
│  (Interface Web - Chat UI, SuperAdmin Panel)                │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    CAMADA DE API                             │
│  (FastAPI Routes - Autenticação, Roteamento)                │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                 CAMADA DE SERVIÇOS                           │
│  (OpenAI Assistant Service, Tool Execution)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              CAMADA DE INTEGRAÇÃO                             │
│  (OpenAI API - Chat Completions, Assistants API)             │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              CAMADA DE DADOS                                 │
│  (PostgreSQL - Agentes, Ferramentas, Threads, Mensagens)     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Diagrama de Arquitetura Detalhado

```
                    ┌──────────────┐
                    │   Usuário    │
                    └──────┬───────┘
                           │
                           │ HTTP Request
                           ▼
            ┌──────────────────────────────┐
            │   Frontend (Chat Interface)  │
            │   - Lista de conversas        │
            │   - Interface de chat         │
            │   - Upload de arquivos        │
            └──────────────┬───────────────┘
                           │
                           │ REST API
                           ▼
        ┌───────────────────────────────────────┐
        │      API Routes (FastAPI)             │
        │  - /api/openai/assistants/use/chat    │
        │  - /api/openai/assistants/threads     │
        │  - /api/openai/assistants/available   │
        └──────────────┬────────────────────────┘
                       │
                       │ Service Layer
                       ▼
    ┌──────────────────────────────────────────────┐
    │     OpenAI Assistant Service                 │
    │  - Gerencia agentes e threads                │
    │  - Processa mensagens                       │
    │  - Executa tool calls                       │
    │  - Gerencia memória persistente             │
    └──────────┬───────────────────┬───────────────┘
               │                   │
               │                   │
    ┌──────────▼──────────┐  ┌────▼──────────────┐
    │   OpenAI API        │  │  Tool Executor     │
    │  (Chat Completions) │  │  - get_orders     │
    │                     │  │  - get_product_    │
    │                     │  │    sales          │
    └─────────────────────┘  └────┬──────────────┘
                                   │
                                   │ Database Queries
                                   ▼
                    ┌──────────────────────────────┐
                    │    PostgreSQL Database       │
                    │  - openai_assistants         │
                    │  - openai_tools              │
                    │  - openai_agent_tools        │
                    │  - openai_assistant_threads  │
                    │  - openai_assistant_messages │
                    │  - openai_assistant_usage     │
                    └──────────────────────────────┘
```

### 2.3 Separação de Responsabilidades

**Camada de Apresentação:**
- Renderização da interface de chat
- Gerenciamento de estado da conversa (frontend)
- Upload e processamento de arquivos
- Exibição de histórico de conversas

**Camada de API:**
- Autenticação e autorização
- Validação de requisições
- Roteamento de endpoints
- Tratamento de erros HTTP

**Camada de Serviços:**
- Lógica de negócio para agentes
- Gerenciamento de threads e mensagens
- Processamento de tool calls
- Integração com OpenAI API
- Execução de ferramentas customizadas

**Camada de Integração:**
- Comunicação com OpenAI API
- Tratamento de respostas da API
- Gerenciamento de tokens e limites
- Fallback entre diferentes APIs (Chat Completions vs Assistants API)

**Camada de Dados:**
- Persistência de agentes, ferramentas e conversas
- Isolamento por empresa e usuário
- Índices para performance
- Logs de uso e auditoria

### 2.4 Integração com OpenAI API

O sistema utiliza duas APIs da OpenAI de forma híbrida:

**Chat Completions API (Principal):**
- Usado para modelos GPT-5 (gpt-5-nano, gpt-5.1, etc.)
- Suporta Function Calling (ferramentas customizadas)
- Mais flexível e compatível com modelos mais recentes
- Parâmetros específicos: `reasoning_effort`, `verbosity`, `max_completion_tokens`

**Assistants API v2 (Fallback):**
- Usado quando necessário Code Interpreter ou File Search
- Suporta apenas modelos compatíveis (gpt-4-turbo, etc.)
- Gerenciamento automático de threads na OpenAI
- Menos flexível, mas oferece recursos avançados

**Decisão Automática:**
O sistema escolhe automaticamente qual API usar baseado em:
- Modelo selecionado (compatibilidade)
- Ferramentas habilitadas (Code Interpreter/File Search requerem Assistants API)
- Parâmetros do modelo (GPT-5 requer Chat Completions)

---

## 3. Componentes Principais

### 3.1 Agentes (Assistants)

Agentes são configurações de IA que definem como o sistema interage com os usuários. Cada agente possui:

**Configurações Básicas:**
- **Nome e Descrição**: Identificação e propósito do agente
- **Modelo**: Modelo da OpenAI a ser usado (gpt-5-nano, gpt-5.1, o1-preview, etc.)
- **Instruções**: Comportamento e regras do agente (em linguagem natural)
- **Modo de Interação**: Chat (conversacional) ou Report (relatório único)

**Parâmetros de Modelo:**
- **Temperature**: Criatividade (0.0-2.0) - não usado em modelos GPT-5
- **Max Tokens**: Limite de tokens na resposta
- **Reasoning Effort**: Profundidade de raciocínio (GPT-5: minimal, low, medium, high)
- **Verbosity**: Nível de detalhamento (GPT-5: low, medium, high)

**Recursos Avançados:**
- **Memória Persistente**: Habilita memória compartilhada entre conversas
- **Dados de Memória**: Informações compartilhadas (JSON) entre todas as threads
- **Prompt Inicial**: Template com tags substituíveis (ex: `[[USUARIO]]`, `[[INFO]]`)
- **Mensagem de Boas-vindas**: Mensagem automática ao iniciar nova conversa
- **Caso de Uso**: Categoria do agente (ex: "Análise de produtos")

**Exemplo de Agente:**
- **Nome**: "Analise produto"
- **Modelo**: gpt-5-nano
- **Modo**: Chat
- **Caso de Uso**: Análise de produtos
- **Ferramentas**: get_orders, get_product_sales, search_products_by_name, resolve_product_by_code

### 3.2 Ferramentas (Tools)

Ferramentas são funções reutilizáveis que os agentes podem chamar para executar ações no sistema. Cada ferramenta possui:

**Definição:**
- **Nome**: Identificador único (ex: "get_orders")
- **Descrição**: Explicação do que a ferramenta faz
- **Schema JSON**: Definição dos parâmetros (formato OpenAI Function Calling)
- **Handler**: Função que executa a ferramenta no backend

**Tipos de Ferramentas:**

1. **Ferramentas de Consulta:**
   - `get_orders`: Consulta pedidos com filtros (data, status, produto, comprador)
   - `get_product_sales`: Lista vendas de um produto no período
   - `search_products_by_name`: Busca produtos pelo nome
   - `resolve_product_by_code`: Resolve produto por código (ID, SKU, ML item ID)

2. **Ferramentas de Análise:**
   - `get_product_core`: Dados essenciais do produto
   - `get_sales_aggregates`: Agregados de vendas
   - `get_billing_breakdown`: Quebra de faturamento
   - `compute_margin_db`: Cálculo de margem

3. **Ferramentas de Competição:**
   - `get_catalog_competitors_db`: Concorrentes do catálogo
   - `simulate_price_candidates`: Simulação de preços

**Reutilização:**
- Ferramentas podem ser associadas a múltiplos agentes
- Uma ferramenta criada uma vez pode ser usada por qualquer agente
- Facilita manutenção e padronização

### 3.3 Threads e Mensagens

**Threads (Conversas):**
- Representam uma conversa individual entre usuário e agente
- Isoladas por empresa (`company_id`) e usuário (`user_id`)
- Possuem contexto persistente (`context_data`)
- Memória específica da thread (`memory_data`)
- Histórico completo de mensagens

**Mensagens:**
- Armazenam cada interação na conversa
- Tipos: `system`, `user`, `assistant`, `tool`
- Ordenadas por timestamp
- Permitem reconstrução completa do histórico

**Isolamento:**
- Usuários de uma empresa não veem conversas de outra
- Usuários dentro da mesma empresa não veem conversas uns dos outros
- Garante privacidade e segurança dos dados

### 3.4 Monitoramento

**Tracking de Tokens:**
- Registro de tokens usados por requisição
- Separação: `prompt_tokens`, `completion_tokens`, `total_tokens`
- Agregação por empresa, agente e período
- Permite controle de custos e otimização

**Métricas de Uso:**
- Total de execuções por agente
- Total de tokens consumidos por agente
- Última data de uso
- Histórico completo de requisições

**Logs e Auditoria:**
- Registro de todas as interações
- Status de execução (pending, completed, failed)
- Mensagens de erro para debugging
- Duração de execução para análise de performance

---

## 4. Fluxos de Funcionamento

### 4.1 Fluxo de Chat com Ferramentas

```
1. Usuário envia mensagem
   │
   ▼
2. Sistema identifica agente e thread
   │
   ▼
3. Carrega histórico de mensagens da thread
   │
   ▼
4. Adiciona mensagem do usuário ao histórico
   │
   ▼
5. Carrega ferramentas associadas ao agente
   │
   ▼
6. Prepara requisição para OpenAI API
   │
   ▼
7. Envia para OpenAI (Chat Completions)
   │
   ▼
8. OpenAI retorna resposta
   │
   ├─► Resposta final → Salva mensagem → Retorna ao usuário
   │
   └─► Tool calls → Executa ferramentas → Adiciona resultados → Volta ao passo 6
```

**Detalhamento do Loop de Tool Calls:**

1. **Agente decide usar ferramenta**: OpenAI retorna `tool_calls` em vez de resposta final
2. **Sistema executa ferramentas**: Para cada tool call, executa a função correspondente
3. **Adiciona resultados**: Resultados são adicionados como mensagens `tool` no histórico
4. **Reenvia para OpenAI**: Histórico completo (incluindo resultados) é enviado novamente
5. **Repete até resposta final**: Loop continua até agente retornar resposta final sem tool calls

**Limite de Iterações:**
- Máximo de 10 iterações por requisição
- Previne loops infinitos
- Retorna resposta parcial se limite atingido

### 4.2 Fluxo de Criação de Agente

```
1. SuperAdmin acessa painel de agentes
   │
   ▼
2. Preenche formulário:
   - Nome, descrição, modelo
   - Instruções (rich text editor)
   - Parâmetros (temperature, max_tokens, etc.)
   - Modo de interação (chat/report)
   - Mensagem de boas-vindas
   │
   ▼
3. Sistema valida dados
   │
   ▼
4. Salva agente no banco de dados
   │
   ▼
5. Agente fica disponível para uso
```

**Configurações Importantes:**
- Instruções definem comportamento do agente
- Modelo determina capacidades e custo
- Ferramentas são associadas separadamente (aba "Ferramentas")

### 4.3 Fluxo de Criação de Ferramenta

```
1. SuperAdmin acessa painel de ferramentas
   │
   ▼
2. Define ferramenta:
   - Nome único
   - Descrição
   - Schema JSON (parâmetros)
   │
   ▼
3. Sistema valida schema
   │
   ▼
4. Salva ferramenta no banco
   │
   ▼
5. Desenvolvedor implementa handler
   (função que executa a ferramenta)
   │
   ▼
6. Ferramenta fica disponível para associação
```

**Schema JSON:**
Define os parâmetros que a ferramenta aceita, seguindo formato OpenAI Function Calling:
- Tipos de dados (string, integer, array, etc.)
- Descrições para cada parâmetro
- Valores padrão
- Validações (mínimo, máximo, enum)

### 4.4 Fluxo de Associação Agente-Ferramenta

```
1. SuperAdmin edita agente
   │
   ▼
2. Acessa aba "Ferramentas"
   │
   ▼
3. Visualiza lista de ferramentas disponíveis
   │
   ▼
4. Marca checkboxes das ferramentas desejadas
   │
   ▼
5. Salva associações
   │
   ▼
6. Sistema atualiza tabela openai_agent_tools
   │
   ▼
7. Agente passa a ter acesso às ferramentas
```

**Vantagens:**
- Associação flexível: um agente pode ter múltiplas ferramentas
- Reutilização: uma ferramenta pode ser usada por múltiplos agentes
- Fácil manutenção: adicionar/remover ferramentas sem alterar agente

### 4.5 Fluxo de Processamento de Tool Calls

```
1. OpenAI retorna tool_calls
   │
   ▼
2. Para cada tool call:
   │
   ├─► Identifica nome da ferramenta
   │
   ├─► Valida parâmetros contra schema
   │
   ├─► Busca handler da ferramenta
   │
   ├─► Executa função com parâmetros
   │
   ├─► Captura resultado
   │
   └─► Adiciona mensagem "tool" ao histórico
   │
   ▼
3. Reenvia histórico completo para OpenAI
   │
   ▼
4. OpenAI processa resultados e retorna resposta final
```

**Tratamento de Erros:**
- Erros de validação: retorna mensagem de erro ao agente
- Erros de execução: captura e inclui no resultado
- Timeout: limita tempo de execução de ferramentas
- Rollback: desfaz transações em caso de erro crítico

---

## 5. Casos de Uso Práticos

### 5.1 Análise de Produtos

**Cenário:**
Usuário precisa analisar performance de um produto no Mercado Livre para tomar decisões de preço, estoque e marketing.

**Fluxo de Uso:**
1. Usuário acessa interface de chat
2. Seleciona agente "Analise produto"
3. Informa código do produto (ML item ID) ou nome
4. Agente identifica produto usando ferramentas
5. Agente consulta dados usando múltiplas ferramentas:
   - `get_product_core`: Dados básicos
   - `get_product_sales`: Vendas do período
   - `get_orders`: Pedidos recentes
   - `get_billing_breakdown`: Faturamento e comissões
6. Agente analisa dados e fornece insights:
   - Margem de lucro
   - Performance de vendas
   - Competitividade de preço
   - Recomendações de ação

**Exemplo de Interação:**
```
Usuário: "Analise o produto MLB5573654248"

Agente: "Analisando produto MLB5573654248...
[Usa ferramentas para coletar dados]

Com base na análise dos últimos 30 dias:

📊 PERFORMANCE
- Vendas: 45 unidades
- Receita: R$ 12.450,00
- Ticket médio: R$ 276,67

💰 FINANCEIRO
- Margem bruta: 32,5%
- Custo total: R$ 8.402,25
- Lucro líquido: R$ 4.047,75

🎯 RECOMENDAÇÕES
1. Preço competitivo: está na média do mercado
2. Estoque: considerar reposição (15 unidades restantes)
3. Marketing: aumentar investimento em ads (ROAS positivo)"
```

**Benefícios:**
- Análise completa em segundos
- Insights acionáveis imediatos
- Não requer conhecimento técnico
- Histórico de análises disponível

### 5.2 Consulta de Pedidos

**Cenário:**
Usuário precisa encontrar pedidos específicos para análise ou atendimento ao cliente.

**Fluxo de Uso:**
1. Usuário pergunta sobre pedidos
2. Agente usa ferramenta `get_orders` com filtros
3. Retorna lista de pedidos com informações relevantes
4. Permite refinamento da busca

**Exemplo de Interação:**
```
Usuário: "Mostre os pedidos do produto MLB5573654248 dos últimos 7 dias"

Agente: "Buscando pedidos...
[Executa get_orders com filtros]

Encontrei 12 pedidos do produto MLB5573654248:

1. Pedido #12345 - 15/11/2025 - R$ 299,90 - Status: Pago
2. Pedido #12346 - 16/11/2025 - R$ 299,90 - Status: Enviado
...

Deseja mais detalhes de algum pedido específico?"
```

**Benefícios:**
- Busca flexível por múltiplos critérios
- Resultados formatados e legíveis
- Permite refinamento iterativo
- Integrado com contexto da conversa

### 5.3 Análise de Vendas

**Cenário:**
Usuário precisa entender performance de vendas de um produto ou período.

**Fluxo de Uso:**
1. Usuário solicita análise de vendas
2. Agente usa `get_product_sales` com parâmetros
3. Agrega e analisa dados
4. Fornece insights e tendências

**Exemplo de Interação:**
```
Usuário: "Como estão as vendas do produto MLB5573654248 este mês?"

Agente: "Analisando vendas...
[Executa get_product_sales]

📈 VENDAS DO MÊS (Novembro 2025)

Total de unidades: 45
Receita total: R$ 12.450,00
Pedidos pagos: 42
Taxa de conversão: 94,4%

📊 COMPARAÇÃO
- Mês anterior: 38 unidades (+18,4%)
- Média diária: 1,5 unidades
- Melhor dia: 15/11 (5 unidades)

💡 INSIGHTS
- Crescimento positivo em relação ao mês anterior
- Taxa de conversão acima da média
- Recomendação: manter estratégia atual"
```

### 5.4 Outros Casos de Uso Potenciais

**Suporte ao Cliente:**
- Agente especializado em atendimento
- Consulta histórico de pedidos do cliente
- Sugere respostas baseadas em contexto
- Escala para casos complexos

**Análise de Marketing:**
- Agente focado em métricas de ads
- Analisa ROAS, CAC, conversão
- Sugere ajustes de campanhas
- Otimiza investimento em marketing

**Gestão de Estoque:**
- Agente para controle de estoque
- Identifica produtos com baixa rotação
- Sugere reposições
- Alerta sobre estoque crítico

**Análise Financeira:**
- Agente para análise financeira
- Calcula margens e lucros
- Identifica oportunidades de otimização
- Gera relatórios financeiros

---

## 6. Segurança e Isolamento

### 6.1 Isolamento por Empresa (company_id)

**Implementação:**
- Todas as tabelas relacionadas a agentes possuem `company_id`
- Queries sempre filtram por `company_id` do usuário logado
- Impossível acessar dados de outras empresas

**Tabelas com Isolamento:**
- `openai_assistant_threads`: Conversas isoladas por empresa
- `openai_assistant_messages`: Mensagens isoladas por empresa
- `openai_assistant_usage`: Logs de uso isolados por empresa

**Benefícios:**
- Privacidade garantida entre empresas
- Compliance com LGPD
- Prevenção de vazamento de dados
- Auditoria por empresa

### 6.2 Isolamento por Usuário (user_id)

**Implementação:**
- Threads possuem `user_id` opcional
- Quando presente, usuários da mesma empresa não veem conversas uns dos outros
- Permite privacidade individual dentro da empresa

**Cenários:**
- **Sem user_id**: Conversa compartilhada pela empresa
- **Com user_id**: Conversa privada do usuário

**Benefícios:**
- Privacidade individual
- Histórico pessoal de consultas
- Permite casos de uso compartilhados ou privados

### 6.3 Controle de Acesso

**Níveis de Acesso:**

1. **Usuário Regular:**
   - Pode usar agentes ativos
   - Pode criar e gerenciar próprias conversas
   - Não pode criar/editar agentes ou ferramentas

2. **SuperAdmin:**
   - Acesso completo ao sistema
   - Pode criar/editar agentes
   - Pode criar/editar ferramentas
   - Pode associar ferramentas a agentes
   - Pode ver métricas de uso

**Autenticação:**
- Baseada em sessão (`session_token`)
- Validação em cada requisição
- Timeout de sessão configurável

### 6.4 Logs e Auditoria

**Registros Mantidos:**
- Todas as requisições de uso de agentes
- Tokens consumidos por requisição
- Status de execução (sucesso/falha)
- Mensagens de erro
- Timestamps de todas as operações

**Tabela de Auditoria:**
- `openai_assistant_usage`: Registro completo de uso
- Campos: empresa, usuário, agente, tokens, status, data
- Permite análise de uso e custos
- Facilita debugging de problemas

**Benefícios:**
- Rastreabilidade completa
- Análise de custos por empresa
- Identificação de problemas
- Compliance e auditoria

---

## 7. Monitoramento e Métricas

### 7.1 Tracking de Tokens

**Métricas Coletadas:**
- **Prompt Tokens**: Tokens enviados para OpenAI (input)
- **Completion Tokens**: Tokens retornados pela OpenAI (output)
- **Total Tokens**: Soma de prompt + completion

**Agregações:**
- Por empresa
- Por agente
- Por período (dia, semana, mês)
- Por usuário (opcional)

**Uso:**
- Controle de custos
- Otimização de prompts
- Identificação de uso excessivo
- Planejamento de orçamento

### 7.2 Histórico de Conversas

**Armazenamento:**
- Todas as mensagens são persistidas
- Threads mantêm histórico completo
- Permite retomar conversas
- Facilita análise de padrões de uso

**Funcionalidades:**
- Lista de conversas por usuário
- Busca em histórico
- Exportação de conversas
- Análise de tópicos mais consultados

### 7.3 Performance e Otimização

**Métricas de Performance:**
- Tempo de resposta por requisição
- Número de iterações (tool calls) por requisição
- Taxa de sucesso/falha
- Uso de cache (quando implementado)

**Otimizações Implementadas:**
- Índices no banco de dados para queries rápidas
- Limite de iterações para prevenir loops
- Timeout em execução de ferramentas
- Validação de parâmetros antes de execução

**Melhorias Futuras:**
- Cache de resultados de ferramentas
- Compressão de histórico de mensagens
- Processamento assíncrono para requisições longas
- Rate limiting por empresa

---

## 8. Roadmap e Próximos Passos

### 8.1 Funcionalidades Futuras

**Curto Prazo (1-3 meses):**
- **Exportação de Conversas**: Permitir exportar conversas em PDF/CSV
- **Templates de Agentes**: Criar agentes a partir de templates pré-configurados
- **Análise de Sentimento**: Adicionar análise de sentimento em feedbacks
- **Notificações**: Alertas quando agentes detectam situações críticas

**Médio Prazo (3-6 meses):**
- **Agentes Especializados**: Criar agentes para casos de uso específicos (suporte, marketing, financeiro)
- **Integração com Webhooks**: Permitir que agentes acionem ações externas
- **Análise Preditiva**: Previsões de vendas e tendências usando histórico
- **Dashboard de Métricas**: Interface visual para análise de uso e performance

**Longo Prazo (6-12 meses):**
- **Aprendizado Contínuo**: Agentes que melhoram com feedback dos usuários
- **Multi-idioma**: Suporte a múltiplos idiomas nas conversas
- **Integração com Outras APIs**: Conectar com outras fontes de dados
- **Agentes Colaborativos**: Múltiplos agentes trabalhando juntos em uma tarefa

### 8.2 Melhorias Planejadas

**Performance:**
- Implementar cache de resultados de ferramentas
- Otimizar queries ao banco de dados
- Processamento assíncrono para análises longas
- Compressão de histórico de mensagens

**Usabilidade:**
- Interface de chat mais rica (markdown, tabelas, gráficos)
- Sugestões automáticas de perguntas
- Atalhos de teclado
- Modo escuro

**Funcionalidades:**
- Busca semântica no histórico
- Agrupamento de conversas por tópico
- Compartilhamento de conversas entre usuários
- Favoritar conversas importantes

### 8.3 Expansão de Casos de Uso

**Áreas de Expansão:**
- **E-commerce**: Análise de catálogo, otimização de listings
- **Logística**: Rastreamento de envios, otimização de rotas
- **Financeiro**: Análise de fluxo de caixa, previsões
- **Marketing**: Otimização de campanhas, análise de concorrência
- **Suporte**: Atendimento automatizado, resolução de problemas

**Integrações Futuras:**
- Mercado Livre API (já integrado)
- Sistemas de ERP
- Plataformas de e-mail marketing
- Ferramentas de analytics
- Sistemas de CRM

### 8.4 Considerações Técnicas

**Escalabilidade:**
- Sistema projetado para escalar horizontalmente
- Banco de dados com índices otimizados
- Cache para reduzir carga
- Rate limiting para prevenir abuso

**Manutenibilidade:**
- Código modular e bem documentado
- Testes automatizados
- Logs detalhados para debugging
- Documentação técnica completa

**Segurança:**
- Auditoria contínua de segurança
- Atualizações regulares de dependências
- Validação rigorosa de inputs
- Criptografia de dados sensíveis

---

## Conclusão

O sistema de chat com agentes e ferramentas OpenAI representa uma evolução significativa na forma como os usuários interagem com dados do negócio. Ao combinar a potência da IA generativa com ferramentas customizadas e isolamento seguro, o sistema oferece uma solução escalável, flexível e poderosa para análise de dados e tomada de decisão.

**Principais Diferenciais:**
- Interface intuitiva e acessível
- Ferramentas reutilizáveis e customizáveis
- Isolamento seguro multi-tenant
- Monitoramento completo de uso e custos
- Arquitetura escalável e manutenível

**Próximos Passos:**
Com a base sólida implementada, o foco agora está em expandir casos de uso, melhorar performance e adicionar funcionalidades que aumentem ainda mais o valor entregue aos usuários.

---

**Documento criado em:** 2025-11-17  
**Versão:** 1.0  
**Autor:** Equipe de Desenvolvimento

