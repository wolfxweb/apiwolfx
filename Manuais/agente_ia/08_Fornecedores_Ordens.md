# Ferramentas: Fornecedores e Ordens de Compra

## Visão Geral

Ferramentas para consulta e gestão de fornecedores e ordens de compra. Permitem ao agente de IA acessar informações sobre fornecedores, ordens de compra e seus itens.

---

## Ferramentas a Serem Criadas

As seguintes ferramentas são necessárias para gestão completa de fornecedores e ordens de compra, mas ainda não estão implementadas:

---

## get_suppliers

### Objetivo
Lista fornecedores da empresa, permitindo filtrar por status, nome, CNPJ e outros critérios.

### Tabelas Associadas
- **fornecedores** - Tabela de fornecedores

### Parâmetros (Propostos)
- **search** (string, opcional) - Busca por nome, CNPJ ou nome fantasia
- **ativo** (boolean, opcional) - Se deve retornar apenas fornecedores ativos (true) ou inativos (false)
- **limit** (integer, opcional, padrão: 50) - Limite de resultados
- **offset** (integer, opcional, padrão: 0) - Offset para paginação

### Retorno (Proposto)
```json
{
  "fornecedores": [
    {
      "id": 123,
      "nome": "Fornecedor ABC Ltda",
      "nome_fantasia": "ABC Fornecedores",
      "cnpj": "12.345.678/0001-90",
      "email": "contato@abc.com.br",
      "telefone": "(11) 1234-5678",
      "cidade": "São Paulo",
      "estado": "SP",
      "ativo": true
    }
  ],
  "total": 1
}
```

### Exemplo de Uso
```
get_suppliers({
  "search": "ABC",
  "ativo": true,
  "limit": 20
})
```

### Observações
- Busca case-insensitive e parcial
- Retorna apenas fornecedores da empresa do usuário
- Campos traduzidos para português

### Status
❌ **Não implementada** - Precisa ser criada

---

## get_supplier_details

### Objetivo
Obtém detalhes completos de um fornecedor específico, incluindo informações de contato, endereço, dados bancários e observações.

### Tabelas Associadas
- **fornecedores** - Tabela de fornecedores

### Parâmetros (Propostos)
- **supplier_id** (integer, obrigatório) - ID do fornecedor

### Retorno (Proposto)
```json
{
  "fornecedor": {
    "id": 123,
    "nome": "Fornecedor ABC Ltda",
    "nome_fantasia": "ABC Fornecedores",
    "cnpj": "12.345.678/0001-90",
    "inscricao_estadual": "123.456.789.012",
    "inscricao_municipal": "987.654.321",
    "contato": {
      "nome": "João Silva",
      "email": "contato@abc.com.br",
      "telefone": "(11) 1234-5678",
      "celular": "(11) 98765-4321",
      "site": "https://www.abc.com.br"
    },
    "endereco": {
      "cep": "01234-567",
      "logradouro": "Rua Exemplo",
      "numero": "123",
      "complemento": "Sala 45",
      "bairro": "Centro",
      "cidade": "São Paulo",
      "estado": "SP",
      "pais": "Brasil"
    },
    "dados_bancarios": {
      "banco": "Banco do Brasil",
      "agencia": "1234-5",
      "conta": "12345-6",
      "tipo_conta": "corrente",
      "pix": "contato@abc.com.br"
    },
    "observacoes": "Fornecedor preferencial para produtos eletrônicos",
    "ativo": true,
    "data_cadastro": "2025-01-15T10:00:00",
    "ultima_atualizacao": "2025-11-20T14:30:00"
  }
}
```

### Exemplo de Uso
```
get_supplier_details({
  "supplier_id": 123
})
```

### Observações
- Retorna erro se o fornecedor não for encontrado ou não pertencer à empresa
- Todos os campos traduzidos para português
- Dados bancários e PIX podem ser sensíveis - considerar permissões

### Status
❌ **Não implementada** - Precisa ser criada

---

## get_purchase_orders

### Objetivo
Lista ordens de compra da empresa, permitindo filtrar por status, fornecedor, período e outros critérios.

### Tabelas Associadas
- **ordem_compra** - Tabela de ordens de compra
- **fornecedores** - Tabela de fornecedores (para filtros)

### Parâmetros (Propostos)
- **start_date** (string, opcional) - Data inicial no formato YYYY-MM-DD
- **end_date** (string, opcional) - Data final no formato YYYY-MM-DD
- **status** (string ou array, opcional) - Status da ordem (pendente, em_cotacao, aprovada, rejeitada, em_andamento, entregue, cancelada)
- **fornecedor_id** (integer, opcional) - ID do fornecedor
- **search** (string, opcional) - Busca por número da ordem
- **limit** (integer, opcional, padrão: 50) - Limite de resultados
- **offset** (integer, opcional, padrão: 0) - Offset para paginação

### Retorno (Proposto)
```json
{
  "ordens": [
    {
      "id": 456,
      "numero_ordem": "OC-2025-001",
      "data_ordem": "2025-11-01",
      "data_entrega_prevista": "2025-11-15",
      "data_entrega_real": null,
      "status": "em_andamento",
      "fornecedor": {
        "id": 123,
        "nome": "Fornecedor ABC Ltda"
      },
      "valor_total": 5000.00,
      "desconto": 100.00,
      "valor_final": 4900.00,
      "moeda": "BRL",
      "total_itens": 5
    }
  ],
  "total": 1
}
```

### Exemplo de Uso
```
get_purchase_orders({
  "start_date": "2025-11-01",
  "end_date": "2025-11-30",
  "status": "em_andamento",
  "limit": 20
})
```

### Observações
- Retorna apenas ordens da empresa do usuário
- Status pode ser string única ou array de strings
- Inclui informações resumidas do fornecedor
- Todos os campos traduzidos para português

### Status
❌ **Não implementada** - Precisa ser criada

---

## get_purchase_order_details

### Objetivo
Obtém detalhes completos de uma ordem de compra específica, incluindo todos os itens, fornecedor, transportadora e informações completas.

### Tabelas Associadas
- **ordem_compra** - Tabela de ordens de compra
- **ordem_compra_item** - Tabela de itens da ordem
- **ordem_compra_link** - Tabela de links externos da ordem
- **fornecedores** - Tabela de fornecedores

### Parâmetros (Propostos)
- **order_id** (integer, obrigatório) - ID da ordem de compra
- **include_items** (boolean, opcional, padrão: true) - Se deve incluir todos os itens
- **include_links** (boolean, opcional, padrão: true) - Se deve incluir links externos

### Retorno (Proposto)
```json
{
  "ordem": {
    "id": 456,
    "numero_ordem": "OC-2025-001",
    "data_ordem": "2025-11-01",
    "data_entrega_prevista": "2025-11-15",
    "data_entrega_real": null,
    "status": "em_andamento",
    "fornecedor": {
      "id": 123,
      "nome": "Fornecedor ABC Ltda",
      "cnpj": "12.345.678/0001-90",
      "email": "contato@abc.com.br"
    },
    "transportadora": {
      "id": 789,
      "nome": "Transportadora XYZ"
    },
    "valores": {
      "valor_total": 5000.00,
      "desconto": 100.00,
      "valor_final": 4900.00,
      "moeda": "BRL",
      "cotacao_moeda": 1.0
    },
    "tipo_ordem": "nacional",
    "condicoes_pagamento": "30 dias",
    "prazo_entrega": "15 dias úteis",
    "observacoes": "Ordem de compra para reposição de estoque"
  },
  "itens": [
    {
      "id": 101,
      "produto_id": 50,
      "produto_nome": "Produto ABC",
      "produto_codigo": "PROD-001",
      "quantidade": 10,
      "valor_unitario": 100.00,
      "valor_total": 1000.00,
      "observacoes": "Produto com garantia de 1 ano"
    }
  ],
  "links": [
    {
      "id": 201,
      "nome": "Cotação Original",
      "url": "https://example.com/cotacao/123",
      "descricao": "Link para cotação no site do fornecedor"
    }
  ],
  "resumo": {
    "total_itens": 5,
    "quantidade_total": 50,
    "valor_total": 5000.00,
    "valor_final": 4900.00
  }
}
```

### Exemplo de Uso
```
get_purchase_order_details({
  "order_id": 456,
  "include_items": true,
  "include_links": true
})
```

### Observações
- Retorna erro se a ordem não for encontrada ou não pertencer à empresa
- Todos os itens da ordem são incluídos
- Links externos são opcionais
- Campos traduzidos para português
- Valores monetários são números (float)

### Status
❌ **Não implementada** - Precisa ser criada

---

## get_supplier_purchase_orders

### Objetivo
Lista todas as ordens de compra de um fornecedor específico, permitindo análise de histórico de compras.

### Tabelas Associadas
- **ordem_compra** - Tabela de ordens de compra
- **fornecedores** - Tabela de fornecedores

### Parâmetros (Propostos)
- **supplier_id** (integer, obrigatório) - ID do fornecedor
- **start_date** (string, opcional) - Data inicial no formato YYYY-MM-DD
- **end_date** (string, opcional) - Data final no formato YYYY-MM-DD
- **status** (string ou array, opcional) - Status das ordens
- **limit** (integer, opcional, padrão: 50) - Limite de resultados
- **offset** (integer, opcional, padrão: 0) - Offset para paginação

### Retorno (Proposto)
```json
{
  "fornecedor": {
    "id": 123,
    "nome": "Fornecedor ABC Ltda"
  },
  "ordens": [
    {
      "id": 456,
      "numero_ordem": "OC-2025-001",
      "data_ordem": "2025-11-01",
      "status": "entregue",
      "valor_final": 4900.00,
      "total_itens": 5
    }
  ],
  "total": 1,
  "estatisticas": {
    "total_ordens": 10,
    "valor_total": 50000.00,
    "ordens_entregues": 8,
    "ordens_pendentes": 2
  }
}
```

### Exemplo de Uso
```
get_supplier_purchase_orders({
  "supplier_id": 123,
  "start_date": "2025-01-01",
  "end_date": "2025-11-30"
})
```

### Observações
- Retorna estatísticas agregadas do fornecedor
- Útil para análise de relacionamento com fornecedores
- Todos os campos traduzidos para português

### Status
❌ **Não implementada** - Precisa ser criada

---

## Resumo das Ferramentas

| Ferramenta | Objetivo | Status |
|------------|----------|--------|
| get_suppliers | Lista fornecedores | ❌ Não implementada |
| get_supplier_details | Detalhes de um fornecedor | ❌ Não implementada |
| get_purchase_orders | Lista ordens de compra | ❌ Não implementada |
| get_purchase_order_details | Detalhes de uma ordem de compra | ❌ Não implementada |
| get_supplier_purchase_orders | Ordens de compra de um fornecedor | ❌ Não implementada |

---

## Notas de Implementação

Para implementar essas ferramentas, será necessário:

1. **Integração com modelos existentes**:
   - `Fornecedor` - Modelo de fornecedores
   - `OrdemCompra` - Modelo de ordens de compra
   - `OrdemCompraItem` - Modelo de itens da ordem
   - `OrdemCompraLink` - Modelo de links externos

2. **Validações necessárias**:
   - Verificar se os registros pertencem à empresa do usuário
   - Validar IDs de fornecedores e ordens
   - Validar períodos de datas
   - Verificar permissões para dados sensíveis (dados bancários)

3. **Tratamento de erros**:
   - Fornecedor não encontrado
   - Ordem não encontrada
   - Período inválido
   - Acesso negado

4. **Tradução de campos**:
   - Todos os nomes de campos devem estar em português
   - Nenhum nome de coluna do banco deve aparecer no retorno
   - Valores monetários como números (float)
   - Datas em formato ISO

---

**Última atualização**: Novembro 2025

