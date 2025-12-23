# Plano de Implementação - Módulo Pós-venda (Claims e Devoluções)

## 1. Visão Geral

Este documento descreve a implementação completa do módulo de **Pós-venda** do Mercado Livre, que gerencia **Claims (Reclamações)** e **Returns (Devoluções)**. No sistema, este módulo é chamado de "Pós-venda".

### 1.1 Conceitos Importantes

**Claims (Reclamações):**
- Podem ser do tipo `mediations` (mediações) ou `returns` (devoluções)
- `mediations`: Quando o Mercado Livre intervém na disputa entre comprador e vendedor
- `returns`: Solicitações diretas de devolução pelo comprador

**Returns (Devoluções):**
- Solicitações de devolução de produtos
- Podem estar relacionadas a um pedido (`order_id`)
- Têm diferentes status e resoluções

### 1.2 Estado Atual do Sistema

**O que já existe:**
- ✅ `MLClaimsService` com método `get_returns_metrics()` (parcial)
- ✅ Notificação de claims recebida (`_process_claim_notification`) mas não implementada
- ✅ Dashboard mostra KPI de devoluções
- ✅ Página de mensagens pós-venda (`ml_messages.html`)

**O que falta:**
- ❌ Modelo de dados completo para claims e returns
- ❌ Processamento completo de notificações de claims
- ❌ Interface para visualizar e gerenciar claims
- ❌ Ações sobre claims (aceitar, rejeitar, responder, etc.)
- ❌ Sincronização de claims com ML
- ❌ Histórico completo de claims

## 2. Documentação da API do Mercado Livre

### 2.1 Endpoints Principais

Baseado na documentação oficial do Mercado Livre:

#### 2.1.1 Buscar Claims
```
GET /post-purchase/v1/claims/search
```

**Parâmetros:**
- `type`: `mediations` ou `returns`
- `limit`: Número de resultados (padrão: 20, máximo: 100)
- `offset`: Paginação
- `sort`: Ordenação (ex: `date_created:desc`)
- `status`: Filtrar por status (opcional)
- `order_id`: Filtrar por pedido (opcional)

**Resposta:**
```json
{
  "data": [
    {
      "id": "123456789",
      "type": "returns",
      "status": "opened",
      "resource_id": "2000001234567890",
      "date_created": "2024-01-01T12:00:00.000Z",
      "date_updated": "2024-01-02T10:00:00.000Z",
      "resolution": {
        "reason": "item_returned",
        "status": "accepted"
      },
      "buyer": {
        "id": 123456789,
        "nickname": "COMPRADOR123"
      },
      "seller": {
        "id": 987654321,
        "nickname": "VENDEDOR123"
      }
    }
  ],
  "paging": {
    "total": 50,
    "offset": 0,
    "limit": 20
  }
}
```

#### 2.1.2 Obter Detalhes de um Claim
```
GET /post-purchase/v1/claims/{claim_id}
```

**Resposta:**
```json
{
  "id": "123456789",
  "type": "returns",
  "status": "opened",
  "resource_id": "2000001234567890",
  "date_created": "2024-01-01T12:00:00.000Z",
  "date_updated": "2024-01-02T10:00:00.000Z",
  "resolution": {
    "reason": "item_returned",
    "status": "accepted",
    "date": "2024-01-02T10:00:00.000Z"
  },
  "buyer": {
    "id": 123456789,
    "nickname": "COMPRADOR123"
  },
  "seller": {
    "id": 987654321,
    "nickname": "VENDEDOR123"
  },
  "messages": [
    {
      "id": "msg_123",
      "from": "buyer",
      "text": "Produto chegou com defeito",
      "date": "2024-01-01T12:30:00.000Z"
    }
  ],
  "evidences": [
    {
      "id": "evid_123",
      "type": "image",
      "url": "https://..."
    }
  ]
}
```

#### 2.1.3 Aceitar Claim
```
POST /post-purchase/v1/claims/{claim_id}/accept
```

**Body:**
```json
{
  "message": "Aceito a devolução"
}
```

#### 2.1.4 Rejeitar Claim
```
POST /post-purchase/v1/claims/{claim_id}/reject
```

**Body:**
```json
{
  "message": "Motivo da rejeição"
}
```

#### 2.1.5 Responder Claim
```
POST /post-purchase/v1/claims/{claim_id}/messages
```

**Body:**
```json
{
  "message": "Texto da resposta"
}
```

#### 2.1.6 Buscar Returns Específicos
```
GET /post-purchase/v1/returns/search
```

Similar ao endpoint de claims, mas focado em returns.

### 2.2 Status de Claims

**Status possíveis:**
- `opened`: Claim aberto
- `closed`: Claim fechado
- `cancelled`: Claim cancelado
- `expired`: Claim expirado

**Resolution Reasons (para devoluções):**
- `item_returned`: Produto devolvido
- `return_canceled`: Devolução cancelada
- `return_expired`: Devolução expirada
- `warehouse_decision`: Decisão do warehouse
- `warehouse_timeout`: Timeout do warehouse
- `low_cost`: Custo de envio > valor produto
- `coverage_decision`: Cobertura aplicada
- `no_bpp`: Sem cobertura

### 2.3 Notificações

**Topic:** `claims` ou `post_purchase`

**Estrutura da notificação:**
```json
{
  "_id": "notification_id",
  "resource": "/post-purchase/v1/claims/123456789",
  "user_id": 987654321,
  "topic": "claims",
  "application_id": 1234567890,
  "attempts": 1,
  "sent": "2024-01-01T12:00:00.000Z",
  "received": "2024-01-01T12:00:00.000Z"
}
```

## 3. Modelo de Dados

### 3.1 Tabela: `ml_claims`

```sql
CREATE TABLE ml_claims (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    ml_account_id INTEGER NOT NULL REFERENCES ml_accounts(id),
    
    -- Identificadores ML
    ml_claim_id VARCHAR(50) UNIQUE NOT NULL,
    ml_order_id VARCHAR(50),
    ml_buyer_id VARCHAR(50),
    ml_seller_id VARCHAR(50),
    
    -- Tipo e Status
    claim_type VARCHAR(20) NOT NULL, -- 'mediations' ou 'returns'
    status VARCHAR(20) NOT NULL, -- 'opened', 'closed', 'cancelled', 'expired'
    
    -- Resolução
    resolution_reason VARCHAR(50),
    resolution_status VARCHAR(50),
    resolution_date TIMESTAMP,
    
    -- Datas
    date_created TIMESTAMP NOT NULL,
    date_updated TIMESTAMP,
    date_closed TIMESTAMP,
    
    -- Dados do comprador
    buyer_nickname VARCHAR(255),
    
    -- Dados completos (JSON)
    claim_data JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_sync TIMESTAMP,
    
    -- Índices
    INDEX idx_ml_claims_company_id (company_id),
    INDEX idx_ml_claims_ml_account_id (ml_account_id),
    INDEX idx_ml_claims_ml_claim_id (ml_claim_id),
    INDEX idx_ml_claims_status (status),
    INDEX idx_ml_claims_type (claim_type),
    INDEX idx_ml_claims_date_created (date_created)
);
```

### 3.2 Tabela: `ml_claim_messages`

```sql
CREATE TABLE ml_claim_messages (
    id SERIAL PRIMARY KEY,
    claim_id INTEGER NOT NULL REFERENCES ml_claims(id) ON DELETE CASCADE,
    
    -- Identificadores ML
    ml_message_id VARCHAR(50) UNIQUE NOT NULL,
    
    -- Dados da mensagem
    from_type VARCHAR(20) NOT NULL, -- 'buyer', 'seller', 'system'
    message_text TEXT NOT NULL,
    
    -- Datas
    date_created TIMESTAMP NOT NULL,
    
    -- Dados completos (JSON)
    message_data JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Índices
    INDEX idx_ml_claim_messages_claim_id (claim_id),
    INDEX idx_ml_claim_messages_ml_message_id (ml_message_id)
);
```

### 3.3 Tabela: `ml_claim_evidences`

```sql
CREATE TABLE ml_claim_evidences (
    id SERIAL PRIMARY KEY,
    claim_id INTEGER NOT NULL REFERENCES ml_claims(id) ON DELETE CASCADE,
    
    -- Identificadores ML
    ml_evidence_id VARCHAR(50) UNIQUE NOT NULL,
    
    -- Dados da evidência
    evidence_type VARCHAR(20), -- 'image', 'video', 'document'
    evidence_url VARCHAR(500),
    
    -- Dados completos (JSON)
    evidence_data JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Índices
    INDEX idx_ml_claim_evidences_claim_id (claim_id)
);
```

## 4. Arquitetura da Solução

### 4.1 Estrutura de Arquivos

```
app/
├── models/
│   └── saas_models.py (adicionar modelos MLClaim, MLClaimMessage, MLClaimEvidence)
├── controllers/
│   └── ml_claims_controller.py (NOVO - controller completo)
├── services/
│   └── ml_claims_service.py (EXPANDIR - adicionar todos os métodos)
├── routes/
│   └── ml_claims_routes.py (NOVO - rotas da API)
└── views/
    └── templates/
        └── ml_claims.html (NOVO - interface de gerenciamento)
```

### 4.2 Fluxo de Processamento

1. **Notificação recebida** → `_process_claim_notification()`
2. **Extrair claim_id** do resource
3. **Buscar detalhes** via API `GET /post-purchase/v1/claims/{claim_id}`
4. **Salvar/atualizar** no banco de dados
5. **Notificar usuário** (se necessário)

### 4.3 Sincronização Manual

1. **Usuário clica em "Sincronizar"**
2. **Buscar claims** via API com filtros
3. **Processar cada claim** encontrado
4. **Atualizar interface** com novos dados

## 5. Funcionalidades a Implementar

### 5.1 Backend

#### 5.1.1 MLClaimsService (Expandir)

**Métodos a adicionar:**
- `get_claims()`: Buscar lista de claims com filtros
- `get_claim_details(claim_id)`: Buscar detalhes de um claim específico
- `accept_claim(claim_id, message)`: Aceitar um claim
- `reject_claim(claim_id, message)`: Rejeitar um claim
- `send_message(claim_id, message)`: Enviar mensagem em um claim
- `sync_claims(company_id, ml_account_id)`: Sincronizar todos os claims
- `get_claim_messages(claim_id)`: Buscar mensagens de um claim
- `get_claim_evidences(claim_id)`: Buscar evidências de um claim

#### 5.1.2 MLClaimsController (Novo)

**Métodos:**
- `process_notification(resource, ml_user_id, company_id)`: Processar notificação
- `sync_claims(company_id, user_id, ml_account_id)`: Sincronizar claims
- `get_claims(company_id, filters)`: Listar claims
- `get_claim_details(claim_id)`: Detalhes de um claim
- `accept_claim(claim_id, message)`: Aceitar claim
- `reject_claim(claim_id, message)`: Rejeitar claim
- `send_message(claim_id, message)`: Enviar mensagem

#### 5.1.3 Rotas API (Novo arquivo: `ml_claims_routes.py`)

**Endpoints:**
- `GET /api/ml/claims` - Listar claims
- `GET /api/ml/claims/{claim_id}` - Detalhes de um claim
- `POST /api/ml/claims/{claim_id}/accept` - Aceitar claim
- `POST /api/ml/claims/{claim_id}/reject` - Rejeitar claim
- `POST /api/ml/claims/{claim_id}/messages` - Enviar mensagem
- `POST /api/ml/claims/sync` - Sincronizar claims

### 5.2 Frontend

#### 5.2.1 Página Principal (`ml_claims.html`)

**Funcionalidades:**
- Lista de claims com filtros:
  - Status (aberto, fechado, cancelado)
  - Tipo (mediação, devolução)
  - Período (data de criação)
  - Pedido específico
- Cards/tabela com informações principais:
  - ID do claim
  - Tipo (badge)
  - Status (badge colorido)
  - Pedido relacionado (link)
  - Comprador
  - Data de criação
  - Última atualização
- Ações rápidas:
  - Ver detalhes
  - Aceitar
  - Rejeitar
  - Responder

#### 5.2.2 Modal/Modal de Detalhes

**Conteúdo:**
- Informações completas do claim
- Histórico de mensagens (chat)
- Evidências (imagens/vídeos)
- Informações do pedido relacionado
- Timeline de eventos
- Ações disponíveis (aceitar, rejeitar, responder)

#### 5.2.3 Integração com Menu

- Adicionar item "Pós-venda" no menu "Atendimento"
- Submenu: "Reclamações e Devoluções"
- Link: `/claims` ou `/pos-venda/claims`

## 6. Implementação Detalhada

### 6.1 Fase 1: Modelos e Estrutura Base

1. Criar modelos SQLAlchemy (`MLClaim`, `MLClaimMessage`, `MLClaimEvidence`)
2. Criar migrations para as tabelas
3. Adicionar DDL no `main.py` para criação automática

### 6.2 Fase 2: Serviço e Controller

1. Expandir `MLClaimsService` com todos os métodos
2. Criar `MLClaimsController` completo
3. Implementar `_process_claim_notification()` no `MLNotificationsController`

### 6.3 Fase 3: Rotas e API

1. Criar `ml_claims_routes.py`
2. Registrar rotas no `main.py`
3. Implementar todos os endpoints

### 6.4 Fase 4: Frontend

1. Criar `ml_claims.html`
2. Implementar JavaScript para:
   - Carregar lista de claims
   - Filtros e busca
   - Ações (aceitar, rejeitar, responder)
   - Modal de detalhes
   - Sincronização

### 6.5 Fase 5: Integração e Testes

1. Integrar com menu existente
2. Testar notificações
3. Testar sincronização manual
4. Testar todas as ações

## 7. Considerações Importantes

### 7.1 Rate Limits

- API de claims tem rate limit específico
- Implementar retry com backoff exponencial
- Cachear resultados quando possível

### 7.2 Permissões

- Verificar se o token tem permissão para gerenciar claims
- Validar que o claim pertence à empresa do usuário

### 7.3 Notificações

- Processar notificações em background
- Garantir idempotência (não processar a mesma notificação duas vezes)
- Logar todas as ações para auditoria

### 7.4 Sincronização

- Permitir sincronização manual
- Considerar sincronização automática periódica (opcional)
- Mostrar status de última sincronização

## 8. Referências

- [Documentação ML - Reclamações e Devoluções](https://developers.mercadolivre.com.br/pt_br/reclamações-e-devoluções)
- [API Post-Purchase](https://api.mercadolibre.com/post-purchase/v1/claims/search)
- [Notificações ML](https://developers.mercadolivre.com.br/pt_br/recebendo-notificacoes)

## 9. Próximos Passos

1. Revisar e aprovar este plano
2. Criar modelos de dados
3. Implementar serviços e controllers
4. Criar rotas da API
5. Desenvolver interface frontend
6. Testar integração completa
7. Documentar uso para usuários finais

