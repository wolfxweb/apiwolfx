# Integração OpenAI via MCP (Model Context Protocol) - Documentação Completa

> **📖 Documentação Oficial**: Este documento é baseado na documentação oficial da OpenAI disponível em: https://platform.openai.com/docs/overview

Este documento explica como usar a API da OpenAI no projeto usando o SDK oficial, incluindo a criação de agentes (Assistants API) lançada recentemente.

## 📚 Documentação Oficial da OpenAI

### Acesse a Documentação Completa:

- **Visão Geral**: https://platform.openai.com/docs/overview
- **Assistants API Overview**: https://platform.openai.com/docs/assistants/overview
- **Assistants Quickstart**: https://platform.openai.com/docs/assistants/quickstart
- **API Reference**: https://platform.openai.com/docs/api-reference
- **Models**: https://platform.openai.com/docs/models

### Conteúdo da Documentação Oficial:

A documentação oficial da OpenAI em https://platform.openai.com/docs/overview contém:

1. **Visão Geral da API**
   - Introdução aos modelos disponíveis
   - Guias de início rápido
   - Exemplos de código
   - Melhores práticas

2. **Assistants API (Agentes)**
   - Como criar assistentes (agentes)
   - Gerenciamento de threads (conversas)
   - Execução de runs
   - Uso de ferramentas (tools)
   - Code Interpreter
   - File Search
   - Function Calling

3. **Chat Completions**
   - Como fazer chamadas de chat
   - Gerenciamento de mensagens
   - Streaming de respostas
   - Parâmetros e configurações

4. **Modelos Disponíveis**
   - GPT-4 Turbo
   - GPT-4
   - GPT-3.5 Turbo
   - O1 (raciocínio)
   - E outros modelos especializados

5. **Guias e Tutoriais**
   - Text Generation
   - Function Calling
   - Embeddings
   - Fine-tuning
   - Rate Limits
   - Error Handling

## 📦 Instalação

O SDK da OpenAI já foi adicionado ao `requirements.txt`:

```txt
openai==1.12.0
```

Para instalar no container Docker:

```bash
docker compose exec api pip install openai==1.12.0
```

Ou reconstruir a imagem:

```bash
docker compose build --no-cache api
docker compose up -d api
```

## 🔑 Configuração

A chave da API deve ser configurada na variável de ambiente `OPENAI_API_KEY`:

### No arquivo `.env`:

```env
OPENAI_API_KEY=sk-...
```

### No `docker-compose.yml`:

A variável já está configurada:

```yaml
environment:
  - OPENAI_API_KEY=${OPENAI_API_KEY:-}
```

## 💻 Uso Básico - Chat Completions

### Exemplo Básico

```python
from openai import OpenAI

# Inicializar cliente
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Fazer uma chamada
response = client.chat.completions.create(
    model="gpt-4-turbo-preview",
    messages=[
        {"role": "system", "content": "Você é um assistente útil."},
        {"role": "user", "content": "Olá, como você está?"}
    ],
    temperature=0.7,
    max_tokens=1000
)

# Extrair resposta
answer = response.choices[0].message.content
print(answer)
```

## 🤖 Assistants API - Criação de Agentes

> **Documentação Oficial**: https://platform.openai.com/docs/assistants/overview

A Assistants API permite criar agentes autônomos que podem:
- Manter contexto de conversas através de threads
- Usar ferramentas (tools) como code interpreter, file search, function calling
- Processar múltiplas mensagens em sequência
- Executar tarefas complexas de forma autônoma

### 1. Criando um Assistente (Agente)

> **Referência**: https://platform.openai.com/docs/assistants/how-it-works/creating-assistants

```python
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Criar um assistente com GPT-5.1
    assistant = client.beta.assistants.create(
        name="Analisador de Produtos ML",
        instructions="""Você é um especialista em análise de produtos do Mercado Livre.
        Sua função é analisar produtos, identificar oportunidades de melhoria,
        sugerir otimizações de preço, SEO e marketing.""",
        model="gpt-5.1",  # GPT-5.1 - melhor para coding e tarefas agentic
        tools=[
            {"type": "code_interpreter"},  # Permite executar código Python
            {"type": "file_search"}        # Permite buscar em arquivos
        ],
        # GPT-5 usa reasoning_effort e verbosity ao invés de temperature
        reasoning_effort="medium",  # Nível médio de raciocínio (padrão)
        verbosity="medium"  # Nível médio de detalhamento (padrão)
    )

print(f"Assistente criado com ID: {assistant.id}")
```

### 2. Criando um Assistente com Funções Customizadas

> **Referência**: https://platform.openai.com/docs/assistants/tools/function-calling

```python
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Definir funções que o assistente pode chamar
functions = [
    {
        "type": "function",
        "function": {
            "name": "get_product_price",
            "description": "Busca o preço atual de um produto no Mercado Livre",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "ID do produto no ML"
                    }
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_product_price",
            "description": "Atualiza o preço de um produto",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "ID do produto"
                    },
                    "new_price": {
                        "type": "number",
                        "description": "Novo preço do produto"
                    }
                },
                "required": ["product_id", "new_price"]
            }
        }
    }
]

# Criar assistente com funções usando GPT-5.1
assistant = client.beta.assistants.create(
    name="Gerenciador de Preços ML",
    instructions="""Você é um assistente especializado em gerenciar preços de produtos.
    Use as funções disponíveis para buscar e atualizar preços quando solicitado.""",
    model="gpt-5.1",  # GPT-5.1 com melhor precisão
    tools=functions,
    # GPT-5 usa reasoning_effort para controlar profundidade do raciocínio
    reasoning_effort="high",  # Alto raciocínio para operações críticas
    verbosity="low"  # Respostas concisas para operações precisas
)
```

### 3. Usando um Assistente em uma Thread (Conversa)

> **Referência**: https://platform.openai.com/docs/assistants/how-it-works/managing-threads-and-messages

A Assistants API mantém memória automaticamente através das threads. Cada thread preserva todo o histórico de mensagens, permitindo conversas contextuais.

```python
from openai import OpenAI
import time

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 1. Criar uma thread (conversa)
thread = client.beta.threads.create()

# 2. Adicionar mensagem à thread
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="Analise o produto MLB123456789 e sugira melhorias de preço e SEO"
)

# 3. Executar o assistente na thread
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id
)

# 4. Aguardar conclusão (polling)
while run.status in ['queued', 'in_progress', 'cancelling']:
    time.sleep(1)
    run = client.beta.threads.runs.retrieve(
        thread_id=thread.id,
        run_id=run.id
    )

# 5. Obter resposta
if run.status == 'completed':
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    for message in messages.data:
        if message.role == 'assistant':
            print(message.content[0].text.value)
else:
    print(f"Erro: {run.status}")
```

### 3.1. Memória Persistente entre Threads

Para manter memória entre diferentes threads (conversas), você pode:

1. **Memória Compartilhada do Assistente**: Armazenar informações gerais sobre o usuário/empresa que são compartilhadas entre todas as threads
2. **Memória Específica da Thread**: Armazenar informações aprendidas durante uma conversa específica

```python
# Criar assistente com memória habilitada
assistant = client.beta.assistants.create(
    name="Assistente com Memória",
    instructions="Você é um assistente que lembra informações sobre o usuário.",
    model="gpt-5.1",
    reasoning_effort="medium",
    verbosity="medium"
)

# Ao usar o assistente, incluir memórias no contexto
memory_data = {
    "user_preferences": {
        "language": "pt-BR",
        "timezone": "America/Sao_Paulo"
    },
    "company_info": {
        "name": "Minha Empresa",
        "industry": "E-commerce"
    }
}

# A memória será automaticamente incluída nas mensagens quando habilitada
```

### 4. Gerenciamento de Runs

> **Referência**: https://platform.openai.com/docs/assistants/how-it-works/runs-and-run-steps

```python
# Verificar status de um run
run = client.beta.threads.runs.retrieve(
    thread_id=thread.id,
    run_id=run.id
)

# Status possíveis:
# - queued: Aguardando processamento
# - in_progress: Em execução
# - requires_action: Precisa de ação (ex: function calling)
# - completed: Concluído com sucesso
# - failed: Falhou
# - cancelled: Cancelado
# - expired: Expirado

# Listar todos os runs de uma thread
runs = client.beta.threads.runs.list(thread_id=thread.id)

# Cancelar um run em execução
client.beta.threads.runs.cancel(
    thread_id=thread.id,
    run_id=run.id
)
```

### 5. Function Calling com Assistants

> **Referência**: https://platform.openai.com/docs/assistants/tools/function-calling

Quando um assistente precisa chamar uma função, o run terá status `requires_action`:

```python
# Verificar se precisa executar funções
if run.status == 'requires_action':
    tool_calls = run.required_action.submit_tool_outputs.tool_calls
    
    tool_outputs = []
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        
        # Executar função local
        if function_name == "get_product_price":
            result = get_product_price_from_db(function_args["product_id"])
        elif function_name == "update_product_price":
            result = update_product_price_in_db(
                function_args["product_id"],
                function_args["new_price"]
            )
        
        tool_outputs.append({
            "tool_call_id": tool_call.id,
            "output": json.dumps(result)
        })
    
    # Enviar resultados de volta
    run = client.beta.threads.runs.submit_tool_outputs(
        thread_id=thread.id,
        run_id=run.id,
        tool_outputs=tool_outputs
    )
    
    # Aguardar conclusão novamente
    run = wait_for_completion(thread.id, run.id)
```

## 🛠️ Ferramentas (Tools) para Agentes

### Code Interpreter

> **Referência**: https://platform.openai.com/docs/assistants/tools/code-interpreter

Permite que o agente execute código Python:

```python
assistant = client.beta.assistants.create(
    name="Analisador de Dados",
    model="gpt-5.1",  # GPT-5.1 com melhor precisão e eficiência
    tools=[{"type": "code_interpreter"}],
    instructions="Use Python para analisar dados e gerar gráficos quando necessário.",
    # GPT-5 usa reasoning_effort e verbosity
    reasoning_effort="medium",  # Raciocínio médio para análises
    verbosity="high"  # Respostas detalhadas com gráficos e explicações
)
```

**Capacidades do Code Interpreter:**
- Executar código Python
- Gerar gráficos e visualizações
- Processar dados e fazer cálculos
- Criar arquivos temporários

### File Search

> **Referência**: https://platform.openai.com/docs/assistants/tools/file-search

Permite buscar informações em arquivos:

```python
# Primeiro, fazer upload de arquivos
file = client.files.create(
    file=open("documento.pdf", "rb"),
    purpose="assistants"
)

# Criar assistente com file_search
assistant = client.beta.assistants.create(
    name="Assistente de Documentação",
    model="gpt-4-turbo-preview",
    tools=[{"type": "file_search"}],
    tool_resources={
        "file_search": {
            "vector_store_ids": [vector_store.id]
        }
    },
    instructions="Use file_search para encontrar informações relevantes nos documentos."
)
```

### Function Calling

> **Referência**: https://platform.openai.com/docs/assistants/tools/function-calling

Permite chamar funções customizadas do seu sistema:

```python
assistant = client.beta.assistants.create(
    name="Agente de Integração",
    model="gpt-4-turbo-preview",
    tools=[
        {
            "type": "function",
            "function": {
                "name": "get_order_status",
                "description": "Busca status de um pedido",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string"}
                    },
                    "required": ["order_id"]
                }
            }
        }
    ]
)
```

## 📚 Modelos Disponíveis

> **Referência Completa**: https://platform.openai.com/docs/models

### Modelos Recomendados (2024-2025):

#### GPT-5 (Mais Recente):
- **gpt-5.1**: Melhor modelo para coding e tarefas agentic com raciocínio configurável
- **gpt-5**: Modelo anterior de raciocínio inteligente para coding e tarefas agentic
- **gpt-5-pro**: Versão mais inteligente e precisa do GPT-5
- **gpt-5-mini**: Versão mais rápida e econômica para tarefas bem definidas
- **gpt-5-nano**: Versão mais rápida e econômica do GPT-5

#### GPT-5 Codex (Otimizado para Coding):
- **gpt-5.1-codex**: Versão do GPT-5.1 otimizada para coding agentic no Codex
- **gpt-5-codex**: Versão do GPT-5 otimizada para coding agentic no Codex

#### GPT-4 (Anteriores):
- **gpt-4-turbo-preview**: Modelo anterior, ainda eficiente
- **gpt-4o**: Modelo otimizado para velocidade e custo
- **gpt-4o-mini**: Versão menor do GPT-4o, mais econômica
- **gpt-3.5-turbo**: Mais rápido e econômico para tarefas simples

#### Modelos de Raciocínio (SEM temperature e SEM tools):
- **o1-preview**: Modelo de raciocínio avançado (para análises complexas)
- **o1-mini**: Versão menor do o1, mais rápida
- **o3-preview**: Modelo de raciocínio mais recente
- **o3-mini**: Versão menor do o3, mais rápida

### 🆕 GPT-5 - Características Especiais:

O **GPT-5** introduz uma arquitetura unificada com roteamento inteligente e novos parâmetros de controle:

1. **Arquitetura Dual:**
   - **GPT-5-main**: Otimizado para consultas rápidas e diretas
   - **GPT-5-thinking**: Para problemas complexos que exigem raciocínio aprofundado
   - Roteador automático decide qual usar baseado na complexidade da consulta

2. **Parâmetros Especiais do GPT-5 (Diferentes dos Modelos Anteriores):**
   
   **⚠️ IMPORTANTE**: O GPT-5 usa parâmetros diferentes do `temperature` tradicional:
   
   - **`reasoning_effort`** (substitui/complementa temperature):
     - Controla o nível de profundidade do raciocínio antes de responder
     - Valores: `"minimal"`, `"low"`, `"medium"`, `"high"`
     - `"minimal"`: Respostas mais rápidas com raciocínio superficial
     - `"low"`: Raciocínio básico, bom para tarefas simples
     - `"medium"`: Equilíbrio entre velocidade e profundidade (padrão recomendado)
     - `"high"`: Raciocínio profundo, ideal para problemas complexos
   
   - **`verbosity`** (controla detalhamento):
     - Controla o comprimento e nível de detalhe das respostas
     - Valores: `"low"`, `"medium"`, `"high"`
     - `"low"`: Respostas concisas e diretas
     - `"medium"`: Equilíbrio entre concisão e detalhe (padrão)
     - `"high"`: Respostas detalhadas e elaboradas
   
   - ✅ **Suporta tools** (code_interpreter, file_search, function calling)
   - ✅ **Suporta max_tokens**
   - ✅ **Melhor precisão** - 45% menos erros factuais que GPT-4o
   - ✅ **Contexto expandido** - até 272k tokens de entrada e 128k de saída (400k total na API)

3. **Diferenças dos Modelos Anteriores:**
   - **NÃO usa `temperature`** como parâmetro principal (usa `reasoning_effort` e `verbosity`)
   - Raciocínio integrado e automático (não precisa selecionar modo manualmente)
   - Respostas mais rápidas e eficientes (usa menos tokens)
   - Melhor compreensão de contexto em conversas longas
   - Modos adaptáveis (Mini, Nano, Thinking) para diferentes necessidades

### Seleção de Modelo por Caso de Uso:

```python
# Para coding e tarefas agentic (RECOMENDADO - mais preciso)
model = "gpt-5.1"  # Melhor para coding e tarefas agentic

# Para coding agentic no Codex
model = "gpt-5.1-codex"  # ou "gpt-5-codex"

# Para análises complexas com raciocínio inteligente
model = "gpt-5"  # ou "gpt-5-pro" para mais precisão

# Para tarefas bem definidas (rápido e econômico)
model = "gpt-5-mini"  # ou "gpt-5-nano" para máxima velocidade

# Para análises complexas com agentes (alternativa GPT-4)
model = "gpt-4-turbo-preview"

# Para tarefas simples e rápidas
model = "gpt-3.5-turbo"

# Para raciocínio matemático e lógico complexo (SEM tools)
model = "o1-preview"  # ou "o3-preview" para versão mais recente

# Para balance entre custo e qualidade
model = "gpt-4o"  # ou "gpt-4o-mini" para economia
```

## 🔧 Parâmetros Comuns

### ⚠️ Diferenças entre Modelos:

#### Modelos GPT-4 e Anteriores (usam `temperature`):
```python
assistant = client.beta.assistants.create(
    model="gpt-4-turbo-preview",
    temperature=0.7,  # 0.0 - 2.0
    # ...
)
```

**Temperature (0.0 - 2.0):**
- **0.0**: Respostas mais determinísticas e focadas (ideal para operações críticas)
- **0.3-0.5**: Para análises técnicas e precisas
- **0.7**: Equilíbrio entre criatividade e precisão (padrão)
- **1.0+**: Respostas mais criativas e variadas (para conteúdo criativo)

#### Modelos GPT-5 (usam `reasoning_effort` e `verbosity`):
```python
assistant = client.beta.assistants.create(
    model="gpt-5.1",
    reasoning_effort="medium",  # "minimal", "low", "medium", "high"
    verbosity="medium",  # "low", "medium", "high"
    # ...
)
```

**Reasoning Effort** (controla profundidade do raciocínio):
- **`"minimal"`**: Respostas mais rápidas com raciocínio superficial
  - Use para: Tarefas simples, respostas rápidas, operações básicas
- **`"low"`**: Raciocínio básico
  - Use para: Tarefas bem definidas, consultas diretas
- **`"medium"`**: Equilíbrio entre velocidade e profundidade (padrão recomendado)
  - Use para: Maioria dos casos, análises gerais, tarefas moderadas
- **`"high"`**: Raciocínio profundo e detalhado
  - Use para: Problemas complexos, análises profundas, operações críticas

**Verbosity** (controla nível de detalhamento):
- **`"low"`**: Respostas concisas e diretas
  - Use para: Operações precisas, respostas curtas, comandos simples
- **`"medium"`**: Equilíbrio entre concisão e detalhe (padrão)
  - Use para: Maioria dos casos, relatórios gerais
- **`"high"`**: Respostas detalhadas e elaboradas
  - Use para: Análises completas, explicações detalhadas, relatórios extensos

**Exemplos de Combinações:**
```python
# Operações críticas (precisas e rápidas)
reasoning_effort="high", verbosity="low"

# Análises gerais (equilíbrio)
reasoning_effort="medium", verbosity="medium"

# Relatórios detalhados (profundos e completos)
reasoning_effort="high", verbosity="high"

# Respostas rápidas (superficiais e concisas)
reasoning_effort="minimal", verbosity="low"
```

### Max Tokens
- Limite máximo de tokens na resposta
- **4000**: Padrão para análises longas
- **1000**: Para respostas curtas
- **8000+**: Para relatórios muito detalhados
- **GPT-5**: Suporta até 128k tokens de saída

### Timeout
- Tempo máximo de espera (em segundos)
- **180.0**: 3 minutos (padrão para análises complexas)
- **300.0**: 5 minutos (para agentes com múltiplas etapas)

## 🛠️ Tratamento de Erros

> **Referência**: https://platform.openai.com/docs/guides/error-codes

### Erros Comuns e Soluções

```python
from openai import OpenAI, APIError, RateLimitError, APITimeoutError

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

try:
    response = client.chat.completions.create(...)
except RateLimitError as e:
    # Limite de requisições excedido
    print(f"Rate limit: {e}")
    # Implementar backoff exponencial
    time.sleep(60)
except APITimeoutError as e:
    # Timeout na requisição
    print(f"Timeout: {e}")
    # Tentar novamente ou aumentar timeout
except APIError as e:
    # Erro geral da API
    print(f"API Error: {e.status_code}: {e.message}")
except Exception as e:
    # Outros erros
    print(f"Erro inesperado: {e}")
```

### Retry Logic com Backoff Exponencial

```python
import time
from openai import OpenAI, RateLimitError

def call_with_retry(client, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(...)
        except RateLimitError:
            wait_time = (2 ** attempt) * 60  # 60s, 120s, 240s
            print(f"Aguardando {wait_time}s antes de tentar novamente...")
            time.sleep(wait_time)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(5)
    raise Exception("Máximo de tentativas excedido")
```

## 📊 Monitoramento e Custos

> **Referência**: https://platform.openai.com/docs/guides/rate-limits

### Verificar Uso de Tokens

```python
response = client.chat.completions.create(...)

usage = response.usage
print(f"Tokens de entrada: {usage.prompt_tokens}")
print(f"Tokens de saída: {usage.completion_tokens}")
print(f"Total: {usage.total_tokens}")

# Calcular custo aproximado (valores de exemplo)
cost_per_1k_input = 0.01  # $0.01 por 1k tokens de entrada
cost_per_1k_output = 0.03  # $0.03 por 1k tokens de saída

cost = (usage.prompt_tokens / 1000 * cost_per_1k_input) + \
       (usage.completion_tokens / 1000 * cost_per_1k_output)
print(f"Custo aproximado: ${cost:.4f}")
```

### Monitorar Runs de Agentes

```python
# Verificar status de um run
run = client.beta.threads.runs.retrieve(
    thread_id=thread_id,
    run_id=run_id
)

print(f"Status: {run.status}")
print(f"Iniciado em: {run.created_at}")
print(f"Completado em: {run.completed_at}")

# Verificar uso de tokens do run
if run.usage:
    print(f"Tokens usados: {run.usage.total_tokens}")
```

## 📖 Documentação Oficial Completa - Links Diretos

### Documentação Principal:

- **Visão Geral**: https://platform.openai.com/docs/overview
- **API Reference**: https://platform.openai.com/docs/api-reference
- **Guia de Início Rápido**: https://platform.openai.com/docs/quickstart

### Assistants API (Agentes):

- **Assistants Overview**: https://platform.openai.com/docs/assistants/overview
- **Assistants Quickstart**: https://platform.openai.com/docs/assistants/quickstart
- **Como Funciona**: https://platform.openai.com/docs/assistants/how-it-works
- **Criando Assistants**: https://platform.openai.com/docs/assistants/how-it-works/creating-assistants
- **Gerenciando Threads**: https://platform.openai.com/docs/assistants/how-it-works/managing-threads-and-messages
- **Runs e Run Steps**: https://platform.openai.com/docs/assistants/how-it-works/runs-and-run-steps

### Ferramentas (Tools):

- **Code Interpreter**: https://platform.openai.com/docs/assistants/tools/code-interpreter
- **File Search**: https://platform.openai.com/docs/assistants/tools/file-search
- **Function Calling**: https://platform.openai.com/docs/assistants/tools/function-calling

### Modelos:

- **Modelos Disponíveis**: https://platform.openai.com/docs/models
- **Guia de Modelos**: https://platform.openai.com/docs/guides/model-ratios

### Guias e Tutoriais:

- **Text Generation**: https://platform.openai.com/docs/guides/text-generation
- **Chat Completions**: https://platform.openai.com/docs/guides/text-generation/chat-completions-api
- **Function Calling Guide**: https://platform.openai.com/docs/guides/function-calling
- **Streaming**: https://platform.openai.com/docs/guides/text-generation/streaming-completions-api
- **Embeddings**: https://platform.openai.com/docs/guides/embeddings
- **Fine-tuning**: https://platform.openai.com/docs/guides/fine-tuning

### Recursos Adicionais:

- **Rate Limits**: https://platform.openai.com/docs/guides/rate-limits
- **Error Codes**: https://platform.openai.com/docs/guides/error-codes
- **Pricing**: https://openai.com/api/pricing
- **Safety Best Practices**: https://platform.openai.com/docs/guides/safety-best-practices

### SDK e Recursos:

- **SDK Python GitHub**: https://github.com/openai/openai-python
- **SDK Python Docs**: https://github.com/openai/openai-python/blob/main/README.md
- **AgentKit**: https://openai.com/agent-platform
- **DevDay 2024**: https://openai.com/devday
- **Cookbook (Exemplos)**: https://cookbook.openai.com/

## 🔍 Verificação de Instalação

Para verificar se o SDK está instalado corretamente:

```bash
docker compose exec api python -c "from openai import OpenAI; print('✅ OpenAI SDK instalado com sucesso')"
```

Para testar a criação de um assistente:

```bash
docker compose exec api python -c "
from openai import OpenAI
import os
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
assistant = client.beta.assistants.create(
    name='Test Assistant',
    instructions='You are a helpful assistant.',
    model='gpt-4-turbo-preview'
)
print(f'✅ Assistente criado: {assistant.id}')
"
```

## ⚠️ Notas Importantes

### Custos
- Cada chamada consome tokens. Monitore o uso na dashboard: https://platform.openai.com/usage
- Modelos diferentes têm custos diferentes (GPT-4 é mais caro que GPT-3.5)
- Assistants API pode ter custos adicionais para ferramentas como code interpreter
- **Pricing**: https://openai.com/api/pricing

### Rate Limits
- A API tem limites de requisições por minuto/hora
- Implemente retry logic com backoff exponencial
- Considere usar filas para processar requisições em lote
- **Rate Limits Guide**: https://platform.openai.com/docs/guides/rate-limits

### Segurança
- **NUNCA** commite a chave da API no código
- Use sempre variáveis de ambiente
- Revogue chaves comprometidas imediatamente
- Use chaves diferentes para desenvolvimento e produção
- **Safety Best Practices**: https://platform.openai.com/docs/guides/safety-best-practices

### Modelos
- Alguns modelos podem estar em preview e sujeitos a mudanças
- Verifique a documentação para modelos mais recentes: https://platform.openai.com/docs/models
- Modelos preview podem ter limitações ou custos diferentes

### Assistants API
- Assistants mantêm estado e podem acumular custos
- Delete assistants não utilizados para economizar
- Threads também ocupam espaço, limpe threads antigas periodicamente
- **Assistants Overview**: https://platform.openai.com/docs/assistants/overview

## 🚀 Próximos Passos

1. **Acesse a documentação oficial**: https://platform.openai.com/docs/overview
2. **Configure a `OPENAI_API_KEY`** no arquivo `.env`
3. **Teste Chat Completions** básico para verificar conexão
4. **Crie seu primeiro Assistente** usando os exemplos acima
5. **Implemente Function Calling** para integrar com suas APIs
6. **Monitore custos** na dashboard da OpenAI
7. **Otimize modelos** escolhendo o mais adequado para cada caso

## 📝 Exemplo Completo: Sistema de Análise com Agente

```python
import os
import time
import json
from typing import Dict
from openai import OpenAI
from sqlalchemy.orm import Session

class MLProductAnalysisAgent:
    """Agente completo para análise de produtos do Mercado Livre"""
    
    def __init__(self, db: Session):
        self.db = db
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.assistant_id = self._get_or_create_assistant()
    
    def _get_or_create_assistant(self) -> str:
        """Obtém ou cria o assistente"""
        # Em produção, salvar assistant_id no banco de dados
            assistant = self.client.beta.assistants.create(
                name="Analisador de Produtos ML",
                instructions="""Você é um especialista em análise de produtos para marketplaces.
                
                Analise produtos do Mercado Livre fornecendo:
                1. Análise de preço e competitividade
                2. Sugestões de SEO
                3. Análise de margem e rentabilidade
                4. Recomendações priorizadas""",
                model="gpt-5.1",  # GPT-5.1 com melhor precisão e raciocínio automático
                tools=[{"type": "code_interpreter"}],
                # GPT-5 usa reasoning_effort e verbosity ao invés de temperature
                reasoning_effort="high",  # Raciocínio profundo para análises complexas
                verbosity="high"  # Respostas detalhadas com recomendações completas
            )
        return assistant.id
    
    def analyze_product(self, product_id: int, company_id: int) -> Dict:
        """Analisa um produto completo"""
        # Buscar dados do produto do banco
        from app.models.saas_models import MLProduct
        product = self.db.query(MLProduct).filter(
            MLProduct.id == product_id,
            MLProduct.company_id == company_id
        ).first()
        
        if not product:
            return {"success": False, "error": "Produto não encontrado"}
        
        # Preparar dados
        product_data = {
            "id": product.ml_item_id,
            "title": product.title,
            "price": float(product.price) if product.price else 0,
            "description": product.description,
            "category": product.category_name,
            "stock": product.available_quantity,
            "sold": product.sold_quantity
        }
        
        # Criar thread e analisar
        thread = self.client.beta.threads.create()
        
        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"Analise este produto: {json.dumps(product_data, indent=2)}"
        )
        
        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant_id
        )
        
        # Aguardar conclusão
        run = self._wait_for_run(thread.id, run.id)
        
        if run.status == 'completed':
            messages = self.client.beta.threads.messages.list(
                thread_id=thread.id,
                order="desc",
                limit=1
            )
            
            if messages.data:
                analysis = messages.data[0].content[0].text.value
                return {
                    "success": True,
                    "analysis": analysis,
                    "thread_id": thread.id
                }
        
        return {"success": False, "error": f"Status: {run.status}"}
    
    def _wait_for_run(self, thread_id: str, run_id: str, timeout: int = 300):
        """Aguarda conclusão de um run com timeout"""
        start = time.time()
        while time.time() - start < timeout:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            if run.status in ['completed', 'failed', 'cancelled']:
                return run
            time.sleep(1)
        raise TimeoutError("Run não completou a tempo")
```

## 🎯 Casos de Uso Práticos

### 1. Análise Automática de Produtos
- Criar agente que analisa produtos automaticamente
- Gerar relatórios de otimização
- Sugerir melhorias de preço e SEO

### 2. Suporte ao Cliente
- Agente que responde perguntas sobre pedidos
- Consulta status de envio
- Resolve problemas comuns

### 3. Análise de Concorrência
- Comparar preços com concorrentes
- Identificar oportunidades de mercado
- Sugerir estratégias de precificação

### 4. Geração de Conteúdo
- Criar descrições otimizadas de produtos
- Gerar títulos para SEO
- Criar conteúdo de marketing

## 📞 Suporte e Recursos

- **Documentação**: https://platform.openai.com/docs
- **Fórum da Comunidade**: https://community.openai.com/
- **Status da API**: https://status.openai.com/
- **Suporte**: https://help.openai.com/
- **Cookbook (Exemplos)**: https://cookbook.openai.com/

---

**📌 IMPORTANTE**: Para informações mais atualizadas e detalhadas, sempre consulte a documentação oficial em: **https://platform.openai.com/docs/overview**

**Última atualização**: Dezembro 2024  
**Versão do SDK**: 1.12.0  
**Status**: ✅ Pronto para uso com Assistants API
