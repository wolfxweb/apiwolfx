# Servidor MCP para API SELVEZ

Servidor Model Context Protocol (MCP) que expõe os endpoints da API SELVEZ como ferramentas padronizadas, permitindo integração com sistemas externos, assistentes de IA e outras ferramentas compatíveis com MCP.

## Como Usar

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Executar o servidor MCP

```bash
python -m app.mcp
```

O servidor funciona via stdio (standard input/output), seguindo o protocolo JSON-RPC do MCP.

### 3. Configurar cliente MCP

Para usar com o Cursor ou outros clientes MCP compatíveis, configure no arquivo de configuração do cliente (ex: `.cursor/mcp_config.json`):

```json
{
  "mcpServers": {
    "selvez-api": {
      "command": "python",
      "args": ["-m", "app.mcp"],
      "env": {
        "DATABASE_URL": "${DATABASE_URL}",
        "API_BASE_URL": "http://localhost:8000"
      }
    }
  }
}
```

## Ferramentas Disponíveis

### Cadastros

#### Produtos Internos
- `list_internal_products` - Lista produtos internos
- `get_internal_product` - Obtém detalhes de um produto
- `create_internal_product` - Cria novo produto
- `update_internal_product` - Atualiza produto
- `delete_internal_product` - Remove produto
- `bulk_update_internal_products` - Atualização em massa
- `bulk_delete_internal_products` - Exclusão em massa
- `get_product_announcements` - Anúncios ML associados

#### Estoque
- `get_stock` - Consulta estoque
- `update_stock` - Atualiza quantidade
- `get_stock_projections` - Projeções de estoque
- `get_reorder_recommendations` - Recomendações de reposição

#### Fornecedores
- `list_fornecedores` - Lista fornecedores
- `get_fornecedor` - Obtém detalhes
- `create_fornecedor` - Cria fornecedor
- `update_fornecedor` - Atualiza fornecedor
- `delete_fornecedor` - Remove fornecedor
- `search_fornecedores` - Busca fornecedores
- `toggle_fornecedor_status` - Ativa/desativa

#### Ordens de Compra
- `list_ordem_compra` - Lista ordens
- `get_ordem_compra` - Obtém detalhes
- `create_ordem_compra` - Cria ordem
- `update_ordem_compra` - Atualiza ordem
- `delete_ordem_compra` - Remove ordem
- `receive_ordem_compra` - Registra recebimento

### Mercado Livre

#### Produtos/Anúncios ML
- `list_ml_products` - Lista anúncios ML
- `get_ml_product` - Obtém detalhes
- `predict_ml_category` - Prediz categoria
- `get_ml_categories` - Lista categorias

#### Pedidos ML
- `list_ml_orders` - Lista pedidos ML
- `get_ml_order` - Obtém detalhes
- `update_order_internal_status` - Atualiza status
- `sync_ml_orders` - Sincroniza pedidos

## Autenticação

Todas as ferramentas requerem o parâmetro `session_token` para autenticação. Este token deve ser obtido através do endpoint de login da API:

```
POST /auth/login
Body: { "email": "...", "password": "..." }
```

O token será retornado como cookie `session_token` que deve ser usado em todas as chamadas MCP.

## Exemplo de Uso

```python
# Exemplo de requisição JSON-RPC para listar produtos
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "list_internal_products",
    "arguments": {
      "session_token": "seu_token_aqui",
      "limit": 20,
      "status": "active"
    }
  }
}
```

## Desenvolvimento

Para adicionar novas ferramentas:

1. Criar handler em `app/mcp/handlers/` apropriado
2. Registrar a ferramenta usando `register_tool()`
3. Importar o módulo em `app/mcp/tools.py`

## Configuração

Variáveis de ambiente:
- `API_BASE_URL` - URL base da API (padrão: http://localhost:8000)
- `MCP_HTTP_TIMEOUT` - Timeout para requisições HTTP (padrão: 30s)
- `MCP_VERBOSE_LOGGING` - Habilitar logs detalhados (padrão: false)


