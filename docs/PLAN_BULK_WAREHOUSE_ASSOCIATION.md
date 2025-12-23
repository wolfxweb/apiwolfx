# Plano: Associação em Massa de Anúncios a Depósitos

## Objetivo
Adicionar funcionalidade para associar anúncios em massa a depósitos na tela de produtos internos, permitindo configurar automaticamente:
- Anúncios "Full" (fulfillment) → depósito de fulfillment
- Anúncios normais → depósito selecionado pelo usuário

## Arquivos a Modificar

### 1. `app/views/templates/internal_products.html`
- **Linha ~758**: Adicionar botão "Associar em Massa" ao lado do título "Anúncios Associados"
- **Após linha ~1840**: Adicionar modal para configuração em massa com:
  - Campo para selecionar depósito para anúncios "Full"
  - Campo para selecionar depósito para anúncios normais
  - Botão para aplicar configuração
- **Após função `renderAnnouncementsTable`**: Adicionar função JavaScript `openBulkWarehouseModal(productId)` que:
  - Abre o modal
  - Carrega lista de depósitos disponíveis
  - Preenche automaticamente o depósito de fulfillment se existir
- **Após função `saveAnnouncementWarehouseConfig`**: Adicionar função `saveBulkWarehouseConfig(productId)` que:
  - Coleta anúncios do cache
  - Separa anúncios Full dos normais
  - Chama API para configurar em massa
  - Atualiza a tabela após sucesso

### 2. `app/routes/stock_routes.py`
- **Após linha ~638**: Adicionar nova rota `POST /api/stock/products/{internal_product_id}/announcements/bulk-warehouse` que:
  - Recebe `warehouse_id_fulfillment` (opcional) e `warehouse_id_normal` (opcional)
  - Valida autenticação
  - Chama controller para processar em massa

### 3. `app/controllers/stock_controller.py`
- **Após método `configure_announcement_warehouse`**: Adicionar método `bulk_configure_announcement_warehouse` que:
  - Recebe `company_id`, `internal_product_id`, `warehouse_id_fulfillment`, `warehouse_id_normal`
  - Chama serviço para processar em massa

### 4. `app/services/stock_service.py`
- **Após método `configure_announcement_warehouse`**: Adicionar método `bulk_configure_announcement_warehouse` que:
  - Busca todos os anúncios do produto interno via `InternalProductService`
  - Identifica quais são Full (`is_fulfillment === true`)
  - Para cada anúncio Full: configura `warehouse_id_fulfillment` se fornecido
  - Para cada anúncio normal: configura `warehouse_id_normal` se fornecido
  - Usa `configure_announcement_warehouse` internamente para cada anúncio
  - Retorna resumo com quantos foram configurados e quais tiveram erro

## Detalhes de Implementação

### Modal de Configuração em Massa
- Título: "Associar Depósitos em Massa"
- Campos:
  - "Depósito para anúncios Full (Fulfillment)": Select com depósitos do tipo fulfillment
  - "Depósito para anúncios normais": Select com todos os depósitos
- Botões: "Cancelar" e "Aplicar Configuração"
- Mostrar contador: "X anúncios Full, Y anúncios normais serão configurados"

### Lógica de Identificação
- Usar campo `announcement.is_fulfillment` para identificar anúncios Full
- Se `warehouse_id_fulfillment` não for fornecido, pular anúncios Full
- Se `warehouse_id_normal` não for fornecido, pular anúncios normais

### Tratamento de Erros
- Se algum anúncio falhar, continuar com os demais
- Retornar lista de erros no final
- Mostrar toast com resumo: "X configurados com sucesso, Y com erro"

### Atualização da Interface
- Após sucesso, recarregar anúncios do produto
- Atualizar cache de anúncios
- Re-renderizar tabela de anúncios

## Ordem de Implementação
1. Adicionar botão e modal no HTML
2. Adicionar funções JavaScript para abrir modal e carregar depósitos
3. Criar endpoint de API para bulk configuration
4. Implementar lógica no controller
5. Implementar lógica no serviço
6. Adicionar função JavaScript para salvar e atualizar interface

