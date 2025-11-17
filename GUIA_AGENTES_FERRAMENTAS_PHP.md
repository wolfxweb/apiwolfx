# Guia Completo: Implementação de Agentes e Ferramentas OpenAI em PHP

## 📋 Índice

1. [Visão Geral da Arquitetura](#visão-geral)
2. [Estrutura do Banco de Dados](#estrutura-banco)
3. [Criando Ferramentas (Tools)](#criando-ferramentas)
4. [Criando Agentes (Assistants)](#criando-agentes)
5. [Associando Ferramentas aos Agentes](#associando-ferramentas)
6. [Usando Agentes (Chat e Report)](#usando-agentes)
7. [Implementação em PHP](#implementação-php)
8. [Exemplos Práticos](#exemplos-práticos)

---

## 1. Visão Geral da Arquitetura {#visão-geral}

### Componentes Principais

1. **Ferramentas (Tools)**: Funções reutilizáveis que o agente pode chamar
2. **Agentes (Assistants)**: Configurações de IA com instruções, modelo e ferramentas
3. **Threads**: Conversas individuais (modo chat)
4. **Mensagens**: Histórico de mensagens em uma thread
5. **Uso (Usage)**: Log de tokens consumidos por empresa

### Fluxo de Funcionamento

```
Usuário → API → Agente → OpenAI API → Resposta
                ↓
            Ferramentas (se necessário)
                ↓
            Banco de Dados
```

---

## 2. Estrutura do Banco de Dados {#estrutura-banco}

### 2.1 Tabela: `openai_tools`

Armazena as definições de ferramentas reutilizáveis.

```sql
CREATE TABLE openai_tools (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    json_schema JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Campos:**
- `id`: ID único da ferramenta
- `name`: Nome único (ex: "get_product_core")
- `description`: Descrição da ferramenta
- `json_schema`: Schema JSON que define os parâmetros da função (formato OpenAI Function Calling)
- `is_active`: Se a ferramenta está ativa

### 2.2 Tabela: `openai_tool_handlers`

Mapeia o nome da ferramenta para a função que a executa.

```sql
CREATE TABLE openai_tool_handlers (
    id SERIAL PRIMARY KEY,
    tool_id INTEGER NOT NULL REFERENCES openai_tools(id) ON DELETE CASCADE,
    handler_name VARCHAR(150) NOT NULL,
    python_module VARCHAR(255),
    python_function VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tool_id, handler_name)
);
```

**Campos:**
- `tool_id`: Referência à ferramenta
- `handler_name`: Nome do handler (ex: "get_product_core")
- `python_module` / `python_function`: Para Python (em PHP, você usará classes/métodos)

### 2.3 Tabela: `openai_agent_tools`

Tabela pivot N:N que associa agentes a ferramentas.

```sql
CREATE TABLE openai_agent_tools (
    agent_id INTEGER NOT NULL REFERENCES openai_assistants(id) ON DELETE CASCADE,
    tool_id INTEGER NOT NULL REFERENCES openai_tools(id) ON DELETE CASCADE,
    config JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(agent_id, tool_id)
);
```

### 2.4 Tabela: `openai_assistants`

Armazena os agentes configurados.

```sql
CREATE TABLE openai_assistants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    assistant_id VARCHAR(255) NOT NULL UNIQUE,
    model VARCHAR(100) NOT NULL DEFAULT 'gpt-5.1',
    instructions TEXT NOT NULL,
    temperature NUMERIC(3,2),
    max_tokens INTEGER DEFAULT 4000,
    tools_config JSON,
    interaction_mode VARCHAR(50) DEFAULT 'report',
    use_case VARCHAR(100),
    memory_enabled BOOLEAN DEFAULT TRUE,
    memory_data JSON,
    initial_prompt TEXT,
    welcome_enabled BOOLEAN DEFAULT FALSE,
    welcome_use_model BOOLEAN DEFAULT FALSE,
    welcome_message TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    total_runs INTEGER DEFAULT 0,
    total_tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);
```

**Campos Importantes:**
- `model`: Modelo OpenAI (ex: "gpt-5.1", "gpt-5-nano", "gpt-4o")
- `instructions`: Instruções do sistema para o agente
- `temperature`: Para modelos GPT-4 e anteriores (NULL para GPT-5)
- `interaction_mode`: "chat" ou "report"
- `welcome_message`: Mensagem de boas-vindas configurável

### 2.5 Tabela: `openai_assistant_threads`

Threads de conversa (modo chat).

```sql
CREATE TABLE openai_assistant_threads (
    id SERIAL PRIMARY KEY,
    assistant_id INTEGER NOT NULL REFERENCES openai_assistants(id),
    company_id INTEGER NOT NULL REFERENCES companies(id),
    user_id INTEGER REFERENCES users(id),
    thread_id VARCHAR(255) NOT NULL UNIQUE,
    context_data JSON,
    memory_data JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ
);
```

### 2.6 Tabela: `openai_assistant_messages`

Mensagens individuais de uma thread.

```sql
CREATE TABLE openai_assistant_messages (
    id SERIAL PRIMARY KEY,
    thread_id INTEGER NOT NULL REFERENCES openai_assistant_threads(id),
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 3. Criando Ferramentas (Tools) {#criando-ferramentas}

### 3.1 Estrutura de uma Ferramenta

Uma ferramenta precisa de:
1. **Nome único** (ex: "get_product_core")
2. **Descrição** (o que a ferramenta faz)
3. **JSON Schema** (parâmetros que a função aceita, no formato OpenAI Function Calling)

### 3.2 Exemplo: Ferramenta "get_product_core"

**JSON Schema:**
```json
{
    "type": "object",
    "properties": {
        "product_id": {
            "type": "integer",
            "description": "ID do produto no banco de dados"
        }
    },
    "required": ["product_id"]
}
```

**SQL para Criar:**
```sql
INSERT INTO openai_tools (name, description, json_schema, is_active)
VALUES (
    'get_product_core',
    'Retorna dados essenciais do produto (preço, estoque, categoria, ML IDs)',
    '{"type":"object","properties":{"product_id":{"type":"integer","description":"ID do produto"}},"required":["product_id"]}'::jsonb,
    TRUE
)
RETURNING id;
```

**Handler (PHP):**
```php
class ToolHandler {
    public function get_product_core($args, $company_id, $user_id) {
        $product_id = $args['product_id'];
        
        // Consulta no banco com filtro por company_id
        $stmt = $pdo->prepare("
            SELECT id, ml_item_id, price, available_quantity, category_id, 
                   listing_type_id, seller_sku, title
            FROM ml_products
            WHERE id = :product_id AND company_id = :company_id
        ");
        $stmt->execute(['product_id' => $product_id, 'company_id' => $company_id]);
        $product = $stmt->fetch(PDO::FETCH_ASSOC);
        
        if (!$product) {
            return ['error' => 'Produto não encontrado'];
        }
        
        return [
            'id' => (int)$product['id'],
            'ml_item_id' => $product['ml_item_id'],
            'price' => (float)$product['price'],
            'available_quantity' => (int)$product['available_quantity'],
            'category_id' => $product['category_id'],
            'listing_type_id' => $product['listing_type_id'],
            'seller_sku' => $product['seller_sku'],
            'title' => $product['title']
        ];
    }
}
```

### 3.3 Exemplo: Ferramenta "get_orders"

**JSON Schema:**
```json
{
    "type": "object",
    "properties": {
        "start_date": {"type": "string", "description": "Data inicial (YYYY-MM-DD)"},
        "end_date": {"type": "string", "description": "Data final (YYYY-MM-DD)"},
        "status": {"oneOf": [
            {"type": "string"},
            {"type": "array", "items": {"type": "string"}}
        ]},
        "ml_item_id": {"type": "string"},
        "buyer_nickname": {"type": "string"},
        "limit": {"type": "integer", "default": 50, "minimum": 1, "maximum": 500},
        "offset": {"type": "integer", "default": 0, "minimum": 0}
    }
}
```

**Handler (PHP):**
```php
public function get_orders($args, $company_id, $user_id) {
    $start_date = $args['start_date'] ?? null;
    $end_date = $args['end_date'] ?? null;
    $status = $args['status'] ?? null;
    $ml_item_id = $args['ml_item_id'] ?? null;
    $buyer_nickname = $args['buyer_nickname'] ?? null;
    $limit = min(500, max(1, $args['limit'] ?? 50));
    $offset = max(0, $args['offset'] ?? 0);
    
    $sql = "SELECT ml_order_id, date_created, total_amount, status, 
                   sale_fees, shipping_cost, coupon_amount, order_items
            FROM ml_ordens
            WHERE company_id = :company_id";
    $params = ['company_id' => $company_id];
    
    if ($start_date) {
        $sql .= " AND date_created >= :start_date";
        $params['start_date'] = $start_date;
    }
    if ($end_date) {
        $sql .= " AND date_created <= :end_date";
        $params['end_date'] = $end_date;
    }
    if ($status) {
        if (is_array($status)) {
            $placeholders = [];
            foreach ($status as $i => $s) {
                $key = "status_$i";
                $placeholders[] = ":$key";
                $params[$key] = $s;
            }
            $sql .= " AND status IN (" . implode(',', $placeholders) . ")";
        } else {
            $sql .= " AND status = :status";
            $params['status'] = $status;
        }
    }
    if ($ml_item_id) {
        $sql .= " AND order_items::text LIKE :ml_item_id";
        $params['ml_item_id'] = "%\"$ml_item_id\"%";
    }
    if ($buyer_nickname) {
        $sql .= " AND buyer_nickname = :buyer_nickname";
        $params['buyer_nickname'] = $buyer_nickname;
    }
    
    $sql .= " ORDER BY date_created DESC LIMIT :limit OFFSET :offset";
    $params['limit'] = $limit;
    $params['offset'] = $offset;
    
    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    $orders = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    $result = [];
    foreach ($orders as $order) {
        $result[] = [
            'id' => $order['ml_order_id'],
            'date' => $order['date_created'],
            'total_amount' => (float)$order['total_amount'],
            'status' => $order['status'],
            'sale_fees' => (float)$order['sale_fees'],
            'shipping_cost' => (float)$order['shipping_cost'],
            'coupon_amount' => (float)$order['coupon_amount']
        ];
    }
    
    return ['orders' => $result];
}
```

---

## 4. Criando Agentes (Assistants) {#criando-agentes}

### 4.1 Estrutura de um Agente

Um agente precisa de:
1. **Nome** e **Descrição**
2. **Modelo** (ex: "gpt-5.1", "gpt-5-nano")
3. **Instruções** (system prompt)
4. **Modo de Interação** ("chat" ou "report")
5. **Configurações de Tokens** (max_tokens)
6. **Parâmetros do Modelo** (temperature para GPT-4, reasoning_effort/verbosity para GPT-5)

### 4.2 Exemplo: Agente "Analise produto"

**SQL para Criar:**
```sql
INSERT INTO openai_assistants (
    name, description, assistant_id, model, instructions,
    temperature, max_tokens, interaction_mode, use_case,
    memory_enabled, is_active
)
VALUES (
    'Analise produto',
    'Agente especializado em análise de produtos do Mercado Livre',
    'local_1_' || extract(epoch from now())::bigint,  -- ID temporário
    'gpt-5-nano',
    'Você é um especialista em análise de produtos do Mercado Livre.
    
Para iniciar uma análise, você deve:
1. Solicitar ao usuário o código do produto (ML item ID) ou o nome do produto
2. Se o usuário informar o nome, use a ferramenta search_products_by_name para buscar opções
3. Se o usuário informar o código, use resolve_product_by_code para confirmar
4. Após identificar o produto, use as ferramentas disponíveis para coletar dados:
   - get_product_core: dados essenciais
   - get_product_attributes: atributos e variações
   - get_orders_by_item: pedidos recentes
   - get_sales_aggregates: agregados de vendas
   - get_billing_breakdown: quebra de faturamento
   - get_ads_metrics_by_item: métricas de anúncios
   - get_product_cost_config: configuração de custos
5. Analise os dados coletados e forneça insights acionáveis

Sempre filtre consultas pelo company_id do usuário logado.',
    NULL,  -- temperature (NULL para GPT-5)
    4000,
    'chat',
    'Análise de produtos',
    TRUE,
    TRUE
)
RETURNING id;
```

**Nota sobre `assistant_id`:**
- Para Chat Completions (GPT-5), você pode usar um ID local (ex: "local_1_1234567890")
- Para Assistants API, precisa ser um ID válido da OpenAI (começa com "asst_")

### 4.3 Configurações por Modelo

**GPT-5 (gpt-5.1, gpt-5-nano, etc.):**
- `temperature`: NULL (não usado)
- `reasoning_effort`: "minimal", "low", "medium", "high" (opcional)
- `verbosity`: "low", "medium", "high" (opcional)
- `max_tokens` ou `max_completion_tokens` (depende do modelo)

**GPT-4 e anteriores:**
- `temperature`: 0.0 a 2.0
- `max_tokens`: Limite de tokens

**Modelos o1, o3, o4:**
- Não suportam `temperature` nem `tools`

---

## 5. Associando Ferramentas aos Agentes {#associando-ferramentas}

### 5.1 Associar Ferramenta a um Agente

```sql
INSERT INTO openai_agent_tools (agent_id, tool_id, config)
VALUES (
    :agent_id,  -- ID do agente
    :tool_id,   -- ID da ferramenta
    NULL        -- Config opcional (JSONB)
)
ON CONFLICT (agent_id, tool_id) DO NOTHING;
```

### 5.2 Listar Ferramentas de um Agente

```sql
SELECT t.id, t.name, t.description, t.json_schema
FROM openai_tools t
INNER JOIN openai_agent_tools at ON t.id = at.tool_id
WHERE at.agent_id = :agent_id
  AND t.is_active = TRUE
ORDER BY t.name;
```

### 5.3 Remover Associação

```sql
DELETE FROM openai_agent_tools
WHERE agent_id = :agent_id AND tool_id = :tool_id;
```

---

## 6. Usando Agentes (Chat e Report) {#usando-agentes}

### 6.1 Modo Chat

**Fluxo:**
1. Criar ou obter thread
2. Adicionar mensagem do usuário
3. Chamar OpenAI API (Chat Completions ou Assistants API)
4. Processar tool calls (se houver)
5. Retornar resposta final
6. Salvar mensagens no banco

**Exemplo de Requisição (PHP):**
```php
POST /api/openai/assistants/use/chat
Content-Type: application/json

{
    "assistant_id": 1,
    "message": "Analise o produto MLB5573654248",
    "thread_id": null,  // null para nova conversa
    "context_data": {
        "product_id": 610,
        "analysis_json": "{...}"  // JSON opcional para substituir [[INFO]]
    }
}
```

**Resposta:**
```json
{
    "success": true,
    "response": "Análise do produto...",
    "thread_id": "thread_abc123",
    "usage": {
        "prompt_tokens": 1500,
        "completion_tokens": 800,
        "total_tokens": 2300
    }
}
```

### 6.2 Modo Report

Similar ao chat, mas gera um relatório completo de uma vez.

**Exemplo:**
```php
POST /api/openai/assistants/use/report
Content-Type: application/json

{
    "assistant_id": 1,
    "query": "Gere relatório de vendas do último mês",
    "context_data": {
        "start_date": "2025-10-01",
        "end_date": "2025-10-31"
    }
}
```

### 6.3 Processamento de Tool Calls

Quando o agente chama uma ferramenta:

1. **OpenAI retorna:**
```json
{
    "role": "assistant",
    "content": null,
    "tool_calls": [
        {
            "id": "call_abc123",
            "type": "function",
            "function": {
                "name": "get_product_core",
                "arguments": "{\"product_id\": 610}"
            }
        }
    ]
}
```

2. **Sistema executa a função:**
```php
$toolHandler = new ToolHandler();
$result = $toolHandler->get_product_core(
    json_decode($tool_call['function']['arguments'], true),
    $company_id,
    $user_id
);
```

3. **Envia resultado de volta:**
```json
{
    "role": "tool",
    "tool_call_id": "call_abc123",
    "content": "{\"id\":610,\"ml_item_id\":\"MLB5573654248\",...}"
}
```

4. **OpenAI processa e retorna resposta final**

---

## 7. Implementação em PHP {#implementação-php}

### 7.1 Classe Principal: OpenAI Assistant Service

```php
<?php

class OpenAIAssistantService {
    private $db;
    private $openaiClient;
    private $toolHandler;
    
    public function __construct($db, $openaiApiKey) {
        $this->db = $db;
        $this->openaiClient = new \GuzzleHttp\Client([
            'base_uri' => 'https://api.openai.com/v1/',
            'headers' => [
                'Authorization' => 'Bearer ' . $openaiApiKey,
                'Content-Type' => 'application/json',
                'OpenAI-Beta' => 'assistants=v2'  // Para Assistants API v2
            ]
        ]);
        $this->toolHandler = new ToolHandler($db);
    }
    
    /**
     * Usa um agente em modo chat
     */
    public function useAssistantChat($assistantId, $message, $threadId = null, $contextData = [], $companyId = null, $userId = null) {
        // 1. Buscar agente no banco
        $assistant = $this->getAssistant($assistantId);
        if (!$assistant || !$assistant['is_active']) {
            throw new Exception("Agente não encontrado ou inativo");
        }
        
        // 2. Criar ou obter thread
        if (!$threadId) {
            $threadId = $this->createThread($assistantId, $companyId, $userId, $contextData);
        } else {
            $thread = $this->getThread($threadId);
            if (!$thread || $thread['company_id'] != $companyId) {
                throw new Exception("Thread não encontrada ou acesso negado");
            }
        }
        
        // 3. Carregar histórico de mensagens
        $previousMessages = $this->getThreadMessages($threadId);
        
        // 4. Processar mensagem de boas-vindas (se configurada)
        if (empty($previousMessages) && $assistant['welcome_enabled']) {
            if (!$assistant['welcome_use_model']) {
                // Mensagem fixa
                $this->saveMessage($threadId, 'assistant', $assistant['welcome_message']);
                if (empty($message)) {
                    return [
                        'success' => true,
                        'response' => $assistant['welcome_message'],
                        'thread_id' => $threadId,
                        'usage' => ['prompt_tokens' => 0, 'completion_tokens' => 0, 'total_tokens' => 0]
                    ];
                }
            } else {
                // Usar modelo para gerar mensagem
                $message = $assistant['welcome_message'];
            }
        }
        
        // 5. Substituir [[USUARIO]] no initial_prompt
        if ($assistant['initial_prompt'] && strpos($assistant['initial_prompt'], '[[USUARIO]]') !== false) {
            $message = str_replace('[[USUARIO]]', $message, $assistant['initial_prompt']);
        }
        
        // 6. Substituir [[INFO]] nas instruções (se context_data contém analysis_json)
        $instructions = $assistant['instructions'];
        if (isset($contextData['analysis_json']) && strpos($instructions, '[[INFO]]') !== false) {
            $instructions = str_replace('[[INFO]]', json_encode($contextData['analysis_json']), $instructions);
        }
        
        // 7. Construir array de mensagens
        $messages = [];
        
        // System message
        $messages[] = [
            'role' => 'system',
            'content' => $instructions
        ];
        
        // Histórico
        foreach ($previousMessages as $msg) {
            $messages[] = [
                'role' => $msg['role'],
                'content' => $msg['content']
            ];
        }
        
        // Mensagem atual do usuário
        $messages[] = [
            'role' => 'user',
            'content' => $message
        ];
        
        // Salvar mensagem do usuário no banco
        $this->saveMessage($threadId, 'user', $message);
        
        // 8. Carregar ferramentas do agente
        $tools = $this->loadAgentTools($assistantId);
        
        // 9. Preparar parâmetros da API
        $chatParams = [
            'model' => $assistant['model'],
            'messages' => $messages
        ];
        
        // Adicionar max_tokens ou max_completion_tokens
        if ($this->needsMaxCompletionTokens($assistant['model'])) {
            $chatParams['max_completion_tokens'] = $assistant['max_tokens'];
        } else {
            $chatParams['max_tokens'] = $assistant['max_tokens'];
        }
        
        // Adicionar parâmetros específicos do modelo
        if ($this->isGPT5Model($assistant['model'])) {
            if (isset($assistant['tools_config']['reasoning_effort'])) {
                $chatParams['reasoning_effort'] = $assistant['tools_config']['reasoning_effort'];
            }
            if (isset($assistant['tools_config']['verbosity'])) {
                $chatParams['verbosity'] = $assistant['tools_config']['verbosity'];
            }
        } else if (!$this->isReasoningModel($assistant['model'])) {
            if ($assistant['temperature'] !== null) {
                $chatParams['temperature'] = (float)$assistant['temperature'];
            }
        }
        
        // Adicionar ferramentas
        if ($tools) {
            $chatParams['tools'] = $tools;
        }
        
        // 10. Processar com tool calls (loop até resposta final)
        $result = $this->processChatWithTools($chatParams, $tools, $threadId, $companyId, $userId);
        
        // 11. Atualizar thread
        $this->updateThread($threadId, ['last_message_at' => date('Y-m-d H:i:s')]);
        
        return $result;
    }
    
    /**
     * Processa chat com suporte a tool calls
     */
    private function processChatWithTools($chatParams, $tools, $threadId, $companyId, $userId, $maxIterations = 10) {
        $iteration = 0;
        $totalUsage = ['prompt_tokens' => 0, 'completion_tokens' => 0, 'total_tokens' => 0];
        
        while ($iteration < $maxIterations) {
            $iteration++;
            
            // Chamar OpenAI API
            $response = $this->openaiClient->post('chat/completions', [
                'json' => $chatParams
            ]);
            
            $responseData = json_decode($response->getBody(), true);
            $message = $responseData['choices'][0]['message'];
            $usage = $responseData['usage'];
            
            // Acumular uso
            $totalUsage['prompt_tokens'] += $usage['prompt_tokens'];
            $totalUsage['completion_tokens'] += $usage['completion_tokens'];
            $totalUsage['total_tokens'] += $usage['total_tokens'];
            
            // Verificar se há tool calls
            if (isset($message['tool_calls']) && !empty($message['tool_calls'])) {
                // Adicionar mensagem do assistente com tool calls
                $chatParams['messages'][] = $message;
                
                // Executar cada tool call
                foreach ($message['tool_calls'] as $toolCall) {
                    $functionName = $toolCall['function']['name'];
                    $functionArgs = json_decode($toolCall['function']['arguments'], true);
                    
                    // Executar função
                    $toolResult = $this->toolHandler->execute($functionName, $functionArgs, $companyId, $userId);
                    
                    // Adicionar resultado como mensagem tool
                    $chatParams['messages'][] = [
                        'role' => 'tool',
                        'tool_call_id' => $toolCall['id'],
                        'content' => json_encode($toolResult)
                    ];
                }
                
                // Continuar loop para próxima iteração
                continue;
            } else {
                // Resposta final
                $responseText = $message['content'] ?? '';
                
                // Salvar mensagem do assistente
                $this->saveMessage($threadId, 'assistant', $responseText);
                
                return [
                    'success' => true,
                    'response' => $responseText,
                    'usage' => $totalUsage
                ];
            }
        }
        
        // Máximo de iterações atingido
        return [
            'success' => false,
            'error' => "Máximo de iterações ($maxIterations) atingido"
        ];
    }
    
    /**
     * Carrega ferramentas de um agente
     */
    private function loadAgentTools($assistantId) {
        $stmt = $this->db->prepare("
            SELECT t.name, t.json_schema
            FROM openai_tools t
            INNER JOIN openai_agent_tools at ON t.id = at.tool_id
            WHERE at.agent_id = :agent_id
              AND t.is_active = TRUE
        ");
        $stmt->execute(['agent_id' => $assistantId]);
        $tools = $stmt->fetchAll(PDO::FETCH_ASSOC);
        
        $result = [];
        foreach ($tools as $tool) {
            $schema = json_decode($tool['json_schema'], true);
            $result[] = [
                'type' => 'function',
                'function' => [
                    'name' => $tool['name'],
                    'description' => $schema['description'] ?? '',
                    'parameters' => $schema
                ]
            ];
        }
        
        return $result;
    }
    
    // Métodos auxiliares...
    private function getAssistant($id) {
        $stmt = $this->db->prepare("SELECT * FROM openai_assistants WHERE id = :id");
        $stmt->execute(['id' => $id]);
        return $stmt->fetch(PDO::FETCH_ASSOC);
    }
    
    private function createThread($assistantId, $companyId, $userId, $contextData) {
        $threadId = 'thread_' . uniqid() . '_' . time();
        $stmt = $this->db->prepare("
            INSERT INTO openai_assistant_threads (assistant_id, company_id, user_id, thread_id, context_data)
            VALUES (:assistant_id, :company_id, :user_id, :thread_id, :context_data)
            RETURNING id
        ");
        $stmt->execute([
            'assistant_id' => $assistantId,
            'company_id' => $companyId,
            'user_id' => $userId,
            'thread_id' => $threadId,
            'context_data' => json_encode($contextData)
        ]);
        $result = $stmt->fetch(PDO::FETCH_ASSOC);
        return $result['id'];
    }
    
    private function getThread($threadId) {
        $stmt = $this->db->prepare("SELECT * FROM openai_assistant_threads WHERE thread_id = :thread_id");
        $stmt->execute(['thread_id' => $threadId]);
        return $stmt->fetch(PDO::FETCH_ASSOC);
    }
    
    private function getThreadMessages($threadId) {
        $stmt = $this->db->prepare("
            SELECT role, content
            FROM openai_assistant_messages
            WHERE thread_id = :thread_id
            ORDER BY created_at ASC
        ");
        $stmt->execute(['thread_id' => $threadId]);
        return $stmt->fetchAll(PDO::FETCH_ASSOC);
    }
    
    private function saveMessage($threadId, $role, $content) {
        $stmt = $this->db->prepare("
            INSERT INTO openai_assistant_messages (thread_id, role, content)
            VALUES (:thread_id, :role, :content)
        ");
        $stmt->execute([
            'thread_id' => $threadId,
            'role' => $role,
            'content' => $content
        ]);
    }
    
    private function updateThread($threadId, $data) {
        $fields = [];
        $params = ['thread_id' => $threadId];
        foreach ($data as $key => $value) {
            $fields[] = "$key = :$key";
            $params[$key] = $value;
        }
        $stmt = $this->db->prepare("
            UPDATE openai_assistant_threads
            SET " . implode(', ', $fields) . "
            WHERE thread_id = :thread_id
        ");
        $stmt->execute($params);
    }
    
    private function isGPT5Model($model) {
        return strpos($model, 'gpt-5') === 0;
    }
    
    private function isReasoningModel($model) {
        return strpos($model, 'o1') === 0 || strpos($model, 'o3') === 0 || strpos($model, 'o4') === 0;
    }
    
    private function needsMaxCompletionTokens($model) {
        return strpos($model, 'gpt-5-nano') === 0;
    }
}
```

### 7.2 Classe: Tool Handler

```php
<?php

class ToolHandler {
    private $db;
    
    public function __construct($db) {
        $this->db = $db;
    }
    
    /**
     * Executa uma função de ferramenta
     */
    public function execute($functionName, $args, $companyId, $userId) {
        if (!method_exists($this, $functionName)) {
            return ['error' => "Função $functionName não encontrada"];
        }
        
        try {
            return $this->$functionName($args, $companyId, $userId);
        } catch (Exception $e) {
            return ['error' => $e->getMessage()];
        }
    }
    
    /**
     * get_product_core
     */
    private function get_product_core($args, $companyId, $userId) {
        $productId = (int)$args['product_id'];
        
        $stmt = $this->db->prepare("
            SELECT id, ml_item_id, price, available_quantity, category_id,
                   listing_type_id, seller_sku, title
            FROM ml_products
            WHERE id = :product_id AND company_id = :company_id
        ");
        $stmt->execute(['product_id' => $productId, 'company_id' => $companyId]);
        $product = $stmt->fetch(PDO::FETCH_ASSOC);
        
        if (!$product) {
            return ['error' => 'Produto não encontrado'];
        }
        
        return [
            'id' => (int)$product['id'],
            'ml_item_id' => $product['ml_item_id'],
            'price' => (float)$product['price'],
            'available_quantity' => (int)$product['available_quantity'],
            'category_id' => $product['category_id'],
            'listing_type_id' => $product['listing_type_id'],
            'seller_sku' => $product['seller_sku'],
            'title' => $product['title']
        ];
    }
    
    /**
     * get_orders
     */
    private function get_orders($args, $companyId, $userId) {
        $start_date = $args['start_date'] ?? null;
        $end_date = $args['end_date'] ?? null;
        $status = $args['status'] ?? null;
        $ml_item_id = $args['ml_item_id'] ?? null;
        $buyer_nickname = $args['buyer_nickname'] ?? null;
        $limit = min(500, max(1, $args['limit'] ?? 50));
        $offset = max(0, $args['offset'] ?? 0);
        
        $sql = "SELECT ml_order_id, date_created, total_amount, status, 
                       sale_fees, shipping_cost, coupon_amount, order_items
                FROM ml_ordens
                WHERE company_id = :company_id";
        $params = ['company_id' => $companyId];
        
        if ($start_date) {
            $sql .= " AND date_created >= :start_date";
            $params['start_date'] = $start_date;
        }
        if ($end_date) {
            $sql .= " AND date_created <= :end_date";
            $params['end_date'] = $end_date;
        }
        if ($status) {
            if (is_array($status)) {
                $placeholders = [];
                foreach ($status as $i => $s) {
                    $key = "status_$i";
                    $placeholders[] = ":$key";
                    $params[$key] = $s;
                }
                $sql .= " AND status IN (" . implode(',', $placeholders) . ")";
            } else {
                $sql .= " AND status = :status";
                $params['status'] = $status;
            }
        }
        if ($ml_item_id) {
            $sql .= " AND order_items::text LIKE :ml_item_id";
            $params['ml_item_id'] = "%\"$ml_item_id\"%";
        }
        if ($buyer_nickname) {
            $sql .= " AND buyer_nickname = :buyer_nickname";
            $params['buyer_nickname'] = $buyer_nickname;
        }
        
        $sql .= " ORDER BY date_created DESC LIMIT :limit OFFSET :offset";
        $params['limit'] = $limit;
        $params['offset'] = $offset;
        
        $stmt = $this->db->prepare($sql);
        $stmt->execute($params);
        $orders = $stmt->fetchAll(PDO::FETCH_ASSOC);
        
        $result = [];
        foreach ($orders as $order) {
            $result[] = [
                'id' => $order['ml_order_id'],
                'date' => $order['date_created'],
                'total_amount' => (float)$order['total_amount'],
                'status' => $order['status'],
                'sale_fees' => (float)$order['sale_fees'],
                'shipping_cost' => (float)$order['shipping_cost'],
                'coupon_amount' => (float)$order['coupon_amount']
            ];
        }
        
        return ['orders' => $result];
    }
    
    // Outras funções...
}
```

---

## 8. Exemplos Práticos {#exemplos-práticos}

### 8.1 Criar Ferramenta via API

```php
POST /api/openai/tools
Content-Type: application/json

{
    "name": "get_product_sales",
    "description": "Lista vendas de um produto no período",
    "json_schema": {
        "type": "object",
        "properties": {
            "product_id": {"type": "integer"},
            "ml_item_id": {"type": "string"},
            "start_date": {"type": "string"},
            "end_date": {"type": "string"},
            "status": {"oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]},
            "limit": {"type": "integer", "default": 50},
            "offset": {"type": "integer", "default": 0}
        }
    },
    "handler_name": "get_product_sales",
    "is_active": true
}
```

### 8.2 Criar Agente via API

```php
POST /api/openai/assistants
Content-Type: application/json

{
    "name": "Analise produto",
    "description": "Agente para análise de produtos",
    "model": "gpt-5-nano",
    "instructions": "Você é um especialista em análise de produtos...",
    "max_tokens": 4000,
    "interaction_mode": "chat",
    "use_case": "Análise de produtos",
    "welcome_enabled": true,
    "welcome_use_model": false,
    "welcome_message": "Olá! Para começar, informe o código do produto ou o nome."
}
```

### 8.3 Associar Ferramenta a Agente

```php
PUT /api/openai/assistants/1/tools
Content-Type: application/json

{
    "tool_ids": [1, 2, 3, 4, 5]  // IDs das ferramentas
}
```

### 8.4 Usar Agente em Chat

```php
POST /api/openai/assistants/use/chat
Content-Type: application/json

{
    "assistant_id": 1,
    "message": "Analise o produto MLB5573654248",
    "context_data": {
        "product_id": 610
    }
}
```

---

## 9. Considerações Importantes

### 9.1 Segurança

- **Sempre filtrar por `company_id`** em todas as consultas de ferramentas
- Validar `user_id` para isolamento de dados
- Não expor dados de outras empresas

### 9.2 Performance

- Use índices nas tabelas (`company_id`, `user_id`, `assistant_id`, `thread_id`)
- Limite o número de iterações de tool calls (padrão: 10)
- Cache de ferramentas carregadas por agente

### 9.3 Monitoramento

- Registre uso de tokens por empresa (`openai_assistant_usage`)
- Monitore erros e timeouts
- Log de tool calls para debug

### 9.4 Modelos e APIs

- **GPT-5**: Use Chat Completions (não Assistants API para gpt-5-nano)
- **GPT-4**: Pode usar Assistants API ou Chat Completions
- **o1, o3, o4**: Não suportam tools

---

## 10. Conclusão

Este guia fornece uma base completa para implementar agentes e ferramentas OpenAI em PHP. Adapte conforme suas necessidades específicas e sempre consulte a documentação oficial da OpenAI para atualizações.

**Documentação Oficial:**
- https://platform.openai.com/docs/assistants/overview
- https://platform.openai.com/docs/api-reference/chat/create
- https://platform.openai.com/docs/guides/function-calling

---

## 11. Anexos

### 11.1 Script SQL Completo para Criar Tabelas

```sql
-- Tabela de ferramentas
CREATE TABLE IF NOT EXISTS openai_tools (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    json_schema JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_openai_tools_active ON openai_tools (is_active);

-- Handlers
CREATE TABLE IF NOT EXISTS openai_tool_handlers (
    id SERIAL PRIMARY KEY,
    tool_id INTEGER NOT NULL REFERENCES openai_tools(id) ON DELETE CASCADE,
    handler_name VARCHAR(150) NOT NULL,
    python_module VARCHAR(255),
    python_function VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_tool_handler_name ON openai_tool_handlers (tool_id, handler_name);

-- Pivot agente<->ferramenta
CREATE TABLE IF NOT EXISTS openai_agent_tools (
    agent_id INTEGER NOT NULL REFERENCES openai_assistants(id) ON DELETE CASCADE,
    tool_id INTEGER NOT NULL REFERENCES openai_tools(id) ON DELETE CASCADE,
    config JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(agent_id, tool_id)
);

CREATE INDEX IF NOT EXISTS ix_openai_agent_tools_agent ON openai_agent_tools (agent_id);
CREATE INDEX IF NOT EXISTS ix_openai_agent_tools_tool ON openai_agent_tools (tool_id);
```

### 11.2 Exemplo de JSON Schema Completo

```json
{
    "type": "object",
    "properties": {
        "product_id": {
            "type": "integer",
            "description": "ID do produto no banco de dados"
        },
        "ml_item_id": {
            "type": "string",
            "description": "ID do item no Mercado Livre"
        },
        "start_date": {
            "type": "string",
            "format": "date",
            "description": "Data inicial no formato YYYY-MM-DD"
        },
        "end_date": {
            "type": "string",
            "format": "date",
            "description": "Data final no formato YYYY-MM-DD"
        },
        "status": {
            "oneOf": [
                {
                    "type": "string",
                    "enum": ["paid", "pending", "cancelled"]
                },
                {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["paid", "pending", "cancelled"]
                    }
                }
            ],
            "description": "Status do pedido (string única ou array)"
        },
        "limit": {
            "type": "integer",
            "default": 50,
            "minimum": 1,
            "maximum": 500,
            "description": "Número máximo de resultados"
        },
        "offset": {
            "type": "integer",
            "default": 0,
            "minimum": 0,
            "description": "Número de resultados para pular"
        }
    },
    "required": ["product_id"]
}
```

---

**Versão:** 1.0  
**Data:** 2025-11-16  
**Autor:** Documentação baseada na implementação Python atual

