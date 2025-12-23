# Como Adicionar o Servidor MCP no Cursor

Este guia explica como adicionar o servidor MCP da API SELVEZ no Cursor IDE, tanto para **desenvolvimento local** quanto para **produção**.

## Método Rápido (Recomendado)

Execute o script fornecido:

```bash
cd /Users/wolfx/Documents/wolfx/apiwolfx
python3 add_mcp_to_cursor.py
```

O script perguntará se você quer usar:
- **Development** (local - http://localhost:8000)
- **Production** (produção - https://www.selvez.com.br)

Ou você pode especificar diretamente:

```bash
# Para desenvolvimento
python3 add_mcp_to_cursor.py development

# Para produção
python3 add_mcp_to_cursor.py production
```

## Configuração Manual

### Para Desenvolvimento (Local)

1. Abra o arquivo `~/.cursor/mcp.json`

2. Adicione a seguinte configuração:

```json
{
  "mcpServers": {
    "selvez-api-development": {
      "command": "/Users/wolfx/anaconda3/bin/python3",
      "args": ["-m", "app.mcp"],
      "cwd": "/Users/wolfx/Documents/wolfx/apiwolfx",
      "env": {
        "DATABASE_URL": "postgresql://postgres:97452c28f62db6d77be083917b698660@pgadmin.wolfx.com.br:5432/comercial",
        "API_BASE_URL": "http://localhost:8000",
        "PYTHONPATH": "/Users/wolfx/Documents/wolfx/apiwolfx",
        "ENVIRONMENT": "development"
      }
    }
  }
}
```

### Para Produção

1. Abra o arquivo `~/.cursor/mcp.json`

2. Adicione a seguinte configuração:

```json
{
  "mcpServers": {
    "selvez-api-production": {
      "command": "/Users/wolfx/anaconda3/bin/python3",
      "args": ["-m", "app.mcp"],
      "cwd": "/Users/wolfx/Documents/wolfx/apiwolfx",
      "env": {
        "DATABASE_URL": "postgresql://api_user:%40Wolfx20202025@207.231.108.38:5432/selvez",
        "API_BASE_URL": "https://www.selvez.com.br",
        "PYTHONPATH": "/Users/wolfx/Documents/wolfx/apiwolfx",
        "ENVIRONMENT": "production"
      }
    }
  }
}
```

**Importante:**
- Ajuste o caminho do `command` para o seu Python (`which python3`)
- Ajuste o `cwd` para o diretório raiz do seu projeto
- Para produção, certifique-se de que a API está acessível em https://www.selvez.com.br

## Usar Ambos os Ambientes Simultaneamente

Você pode ter **ambos** os servidores configurados ao mesmo tempo:

```json
{
  "mcpServers": {
    "selvez-api-development": {
      "command": "/Users/wolfx/anaconda3/bin/python3",
      "args": ["-m", "app.mcp"],
      "cwd": "/Users/wolfx/Documents/wolfx/apiwolfx",
      "env": {
        "API_BASE_URL": "http://localhost:8000",
        "ENVIRONMENT": "development"
      }
    },
    "selvez-api-production": {
      "command": "/Users/wolfx/anaconda3/bin/python3",
      "args": ["-m", "app.mcp"],
      "cwd": "/Users/wolfx/Documents/wolfx/apiwolfx",
      "env": {
        "API_BASE_URL": "https://www.selvez.com.br",
        "ENVIRONMENT": "production"
      }
    }
  }
}
```

Assim você terá duas instâncias do servidor MCP disponíveis no Cursor, uma para cada ambiente.

## Próximos Passos

1. **Fechar completamente o Cursor** (Cmd+Q no Mac)
2. **Reabrir o Cursor**
3. O servidor MCP será carregado automaticamente

## Autenticação

### Para Desenvolvimento

Faça login na API local:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "seu_email", "password": "sua_senha"}' \
  -c cookies.txt
```

Extraia o `session_token` dos cookies e use nas ferramentas MCP.

### Para Produção

Faça login na API de produção:

```bash
curl -X POST https://www.selvez.com.br/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "seu_email", "password": "sua_senha"}' \
  -c cookies.txt
```

## Verificar se Está Funcionando

No Cursor:

1. Abra o Command Palette (Cmd+Shift+P)
2. Procure por "MCP" ou "Model Context Protocol"
3. Você deve ver as ferramentas disponíveis do servidor configurado

## Ferramentas Disponíveis

Você terá acesso a 34+ ferramentas, incluindo:

### Cadastros
- `list_internal_products` - Lista produtos internos
- `get_internal_product` - Obtém detalhes de um produto
- `create_internal_product` - Cria novo produto
- `get_stock` - Consulta estoque
- `list_fornecedores` - Lista fornecedores
- `list_ordem_compra` - Lista ordens de compra

### Mercado Livre
- `list_ml_products` - Lista anúncios ML
- `list_ml_orders` - Lista pedidos ML
- `get_ml_order` - Obtém detalhes de pedido
- E muitas outras...

Consulte `app/mcp/README.md` para a lista completa.

## Troubleshooting

### Erro: "API não acessível"

**Para desenvolvimento:**
- Verifique se a API está rodando: `curl http://localhost:8000/`
- Verifique se a porta 8000 está correta

**Para produção:**
- Verifique se a API está online: `curl https://www.selvez.com.br/`
- Verifique se há problemas de CORS ou firewall

### Erro: "Module not found"

- Instale as dependências: `pip install -r requirements.txt`
- Verifique se o PYTHONPATH está configurado corretamente

### Servidor não inicia

Execute manualmente para ver os erros:
```bash
cd /Users/wolfx/Documents/wolfx/apiwolfx
python3 -m app.mcp
```

### Ferramentas não aparecem

- Reinicie o Cursor completamente
- Verifique se o arquivo mcp.json está com JSON válido
- Verifique os logs do Cursor (View → Output → MCP)

## Diferenças entre Ambientes

| Aspecto | Development | Production |
|---------|-------------|------------|
| URL API | http://localhost:8000 | https://www.selvez.com.br |
| Banco de Dados | comercial (dev) | selvez (prod) |
| Login | http://localhost:8000/auth/login | https://www.selvez.com.br/auth/login |
| Quando usar | Desenvolvimento/testes locais | Acessar dados reais de produção |

## Mais Informações

- Consulte `app/mcp/README.md` para detalhes das ferramentas
- Consulte `app/mcp/config.py` para configurações do servidor
