# Status de Pedidos e Envios - Mercado Livre

Documentação completa dos status de pedidos e envios do Mercado Livre, baseada na [documentação oficial da API](https://developers.mercadolivre.com.br/pt_br/gerenciamento-de-vendas).

---

## 📦 Status de Pedidos (Orders)

Os status de pedidos são retornados pelo endpoint `/orders/{order_id}` e representam o estado geral do pedido no sistema.

### Status Principais

| Status API | Status Interno | Descrição |
|------------|----------------|-----------|
| `confirmed` | `CONFIRMED` | Status inicial de uma order; ainda sem ter sido paga |
| `payment_required` | `PENDING` | O pagamento da order deve ter sido confirmado para exibir as informações do usuário |
| `payment_in_process` | `PENDING` | Há um pagamento relacionado à order, mais ainda não foi aprovado |
| `partially_paid` | `PARTIALLY_PAID` | A order tem um pagamento associado creditado, porém, insuficiente |
| `paid` | `PAID` | A order tem um pagamento associado aprovado |
| `ready_to_ship` | `PAID` | Pedido pronto para envio |
| `shipped` | `SHIPPED` | Pedido enviado |
| `delivered` | `DELIVERED` | Pedido entregue |
| `partially_refunded` | `PARTIALLY_REFUNDED` | A order tem devoluções parciais de seus pagamentos |
| `pending_cancel` | `PENDING_CANCEL` | Quando a order foi cancelada mas temos dificuldade para devolver o pagamento |
| `cancelled` | `CANCELLED` | Por alguma razão, a order não foi completada |
| `refunded` | `REFUNDED` | Pedido reembolsado completamente |
| `invalid` | `INVALID` | A order foi invalidada por vir de um comprador malicioso |

### Status Customizados (Sistema Interno)

| Status Interno | Descrição |
|----------------|-----------|
| `READY_TO_PREPARE` | ✨ **Status manual** para pedidos não-Fulfillment que estão prontos para preparação. Este status é definido manualmente pelo usuário e não é retornado pela API do Mercado Livre. Usado para separar pedidos não-Fulfillment que precisam ser preparados antes do envio. |

### Motivos de Cancelamento

Uma order pode ser cancelada pelos seguintes motivos:
- Requeria aprovação do pagamento para descontar do estoque, mas, no tempo de processo de aprovação, o item foi pausado/finalizado por falta de estoque
- Requeria pagamento, mas, após certo tempo, não foi paga, por isso é automaticamente cancelada
- Após uma transação ter sido efetuada, o vendedor é proibido no site por alguma razão
- Se por alguma razão o vendedor qualificar a operação como não concretizada, a order assume o "status = confirmed"

---

## 🚚 Status de Envios (Shipments)

Os status de envios são retornados pelo endpoint `/shipment_statuses` e representam o estado do envio físico do produto.

### Status Principais de Shipment

| Status API | Status Interno | Descrição |
|------------|----------------|-----------|
| `to_be_agreed` | `PENDING` | A ser acordado |
| `pending` | `PENDING` | Pendente |
| `handling` | `CONFIRMED` | Em preparação |
| `ready_to_ship` | `PAID` | Pronto para envio |
| `shipped` | `SHIPPED` | Enviado |
| `delivered` | `DELIVERED` | Entregue |
| `not_delivered` | `CANCELLED` | Não entregue |
| `not_verified` | `PENDING` | Não verificado |
| `cancelled` | `CANCELLED` | Cancelado |
| `closed` | `DELIVERED` | Fechado/Entregue |
| `error` | `CANCELLED` | Erro |
| `active` | `CONFIRMED` | Ativo |
| `not_specified` | `PENDING` | Não especificado |
| `stale_ready_to_ship` | `PAID` | Obsoleto pronto para envio |
| `stale_shipped` | `SHIPPED` | Obsoleto enviado |

---

## 🔍 Substatus de Envios

Os substatus fornecem informações mais detalhadas sobre o estado específico do envio. Cada status principal pode ter vários substatus.

### Substatus de `pending`

| Substatus | Status Interno | Descrição |
|-----------|----------------|-----------|
| `cost_exceeded` | `PENDING` | Custo excedido |
| `under_review` | `PENDING` | Em revisão (ex: fraude) |
| `reviewed` | `PENDING` | Revisado |
| `fraudulent` | `CANCELLED` | Fraudulento |
| `waiting_for_payment` | `PENDING` | Aguardando pagamento do frete |
| `shipment_paid` | `PAID` | Frete pago |
| `creating_route` | `PENDING` | Criando rota |
| `manufacturing` | `PENDING` | Em fabricação |
| `buffered` | `PENDING` | Em buffer |
| `creating_shipping_order` | `PENDING` | Criando ordem de envio |

### Substatus de `handling`

| Substatus | Status Interno | Descrição |
|-----------|----------------|-----------|
| `regenerating` | `CONFIRMED` | Regenerando |
| `waiting_for_label_generation` | `CONFIRMED` | Aguardando geração de etiqueta |
| `invoice_pending` | `CONFIRMED` | Nota fiscal pendente |
| `waiting_for_return_confirmation` | `CONFIRMED` | Aguardando confirmação de retorno |
| `return_confirmed` | `CONFIRMED` | Retorno confirmado |
| `manufacturing` | `CONFIRMED` | Em fabricação |
| `agency_unavailable` | `CONFIRMED` | Agência indisponível |

### Substatus de `ready_to_ship` (Fulfillment)

| Substatus | Status Interno | Descrição |
|-----------|----------------|-----------|
| `in_warehouse` | `PAID` | Processando no centro de distribuição |
| `ready_to_print` | `PAID` | Pronto para imprimir |
| `printed` | `PAID` | Impresso |
| `ready_to_pack` | `PAID` | Pronto para embalar |
| `packed` | `PAID` | Embalado |
| `in_pickup_list` | `PAID` | Na lista de coleta |
| `ready_for_pkl_creation` | `PAID` | Pronto para criação de PLP |
| `ready_for_pickup` | `PAID` | Pronto para coleta |
| `ready_for_dropoff` | `PAID` | Pronto para drop off |
| `picked_up` | `PAID` | Coletado |
| `dropped_off` | `PAID` | Entregue no ponto de coleta |
| `in_transit` | `SHIPPED` | Em trânsito |
| `in_hub` | `PAID` | No hub |
| `measures_ready` | `PAID` | Medidas e peso prontos |
| `waiting_for_carrier_authorization` | `PAID` | Aguardando autorização da transportadora |
| `authorized_by_carrier` | `PAID` | Autorizado pela transportadora MELI |
| `in_packing_list` | `PAID` | Na lista de embalagem |
| `in_plp` | `PAID` | Na PLP |
| `on_hold` | `PAID` | Em espera |
| `stale` | `PAID` | Obsoleto |
| `delayed` | `PAID` | Atrasado |
| `claimed_me` | `PAID` | Reivindicado pelo comprador |
| `waiting_for_last_mile_authorization` | `PAID` | Aguardando autorização da última milha |
| `rejected_in_hub` | `CANCELLED` | Rejeitado no hub |
| `on_route_to_pickup` | `PAID` | A caminho da coleta |
| `picking_up` | `PAID` | Coletando |
| `shipping_order_initialized` | `PAID` | Ordem de envio inicializada |
| `looking_for_driver` | `PAID` | Procurando motorista |

### Substatus de `shipped`

| Substatus | Status Interno | Descrição |
|-----------|----------------|-----------|
| `out_for_delivery` | `SHIPPED` | Saiu para entrega |
| `soon_deliver` | `SHIPPED` | Em breve será entregue |
| `delayed` | `SHIPPED` | Atrasado |
| `waiting_for_withdrawal` | `SHIPPED` | Aguardando retirada |
| `contact_with_carrier_required` | `SHIPPED` | Contato com transportadora necessário |
| `receiver_absent` | `SHIPPED` | Destinatário ausente |
| `reclaimed` | `SHIPPED` | Reclamado |
| `not_localized` | `SHIPPED` | Não localizado |
| `forwarded_to_third` | `SHIPPED` | Encaminhado para terceiro |
| `refused_delivery` | `SHIPPED` | Entrega recusada |
| `bad_address` | `SHIPPED` | Endereço incorreto |
| `changed_address` | `SHIPPED` | Endereço alterado |
| `negative_feedback` | `SHIPPED` | Feedback negativo |
| `need_review` | `SHIPPED` | Precisa revisar status da transportadora |
| `operator_intervention` | `SHIPPED` | Necessária intervenção do operador |
| `retained` | `SHIPPED` | Retido |
| `delivery_failed` | `SHIPPED` | Entrega falhou |
| `waiting_for_confirmation` | `SHIPPED` | Aguardando confirmação |
| `at_the_door` | `SHIPPED` | Na porta do comprador |
| `buyer_edt_limit_stale` | `SHIPPED` | Limite EDT do comprador obsoleto |
| `delivery_blocked` | `SHIPPED` | Entrega bloqueada |
| `awaiting_tax_documentation` | `SHIPPED` | Aguardando documentação fiscal |
| `dangerous_area` | `SHIPPED` | Área perigosa |
| `buyer_rescheduled` | `SHIPPED` | Comprador reagendou |
| `failover` | `SHIPPED` | Failover |
| `at_customs` | `SHIPPED` | Na alfândega |
| `delayed_at_customs` | `SHIPPED` | Atrasado na alfândega |
| `left_customs` | `SHIPPED` | Saiu da alfândega |
| `missing_sender_payment` | `SHIPPED` | Falta pagamento do remetente |
| `missing_sender_documentation` | `SHIPPED` | Falta documentação do remetente |
| `missing_recipient_documentation` | `SHIPPED` | Falta documentação do destinatário |
| `missing_recipient_payment` | `SHIPPED` | Falta pagamento do destinatário |
| `import_taxes_paid` | `SHIPPED` | Impostos de importação pagos |

### Substatus de `delivered`

| Substatus | Status Interno | Descrição |
|-----------|----------------|-----------|
| `damaged` | `DELIVERED` | Danificado |
| `fulfilled_feedback` | `DELIVERED` | Feedback do comprador |
| `no_action_taken` | `DELIVERED` | Nenhuma ação tomada pelo comprador |
| `double_refund` | `DELIVERED` | Reembolso duplo |
| `inferred` | `DELIVERED` | Entrega inferida |

### Substatus de `not_delivered`

| Substatus | Status Interno | Descrição |
|-----------|----------------|-----------|
| `returning_to_sender` | `CANCELLED` | Retornando ao remetente |
| `destroyed` | `CANCELLED` | Destruído |
| `to_review` | `CANCELLED` | Para revisão - Envio fechado |
| `waiting_for_withdrawal` | `CANCELLED` | Aguardando retirada |
| `negative_feedback` | `CANCELLED` | Feedback negativo forçou não entregue |
| `not_localized` | `CANCELLED` | Não localizado |
| `double_refund` | `CANCELLED` | Reembolso duplo |
| `cancelled_measurement_exceeded` | `CANCELLED` | Cancelado por medida excedida |
| `returned_to_hub` | `CANCELLED` | Retornado ao hub |
| `returned_to_agency` | `CANCELLED` | Retornado à agência |
| `picked_up_for_return` | `CANCELLED` | Coletado para retorno |
| `returning_to_warehouse` | `CANCELLED` | Retornando ao depósito |
| `returning_to_hub` | `CANCELLED` | Retornando ao hub |
| `soon_to_be_returned` | `CANCELLED` | Em breve será retornado |
| `return_failed` | `CANCELLED` | Retorno falhou |
| `in_storage` | `CANCELLED` | Em armazenamento |
| `pending_recovery` | `CANCELLED` | Recuperação pendente |
| `rejected_damaged` | `CANCELLED` | Rejeitado danificado |
| `refunded_by_delay` | `CANCELLED` | Reembolsado por atraso |
| `delayed_to_hub` | `CANCELLED` | Atrasado para hub |
| `shipment_stopped` | `CANCELLED` | Envio parado |
| `retained` | `CANCELLED` | Retido |
| `stolen` | `CANCELLED` | Roubado |
| `returned` | `CANCELLED` | Retornado |
| `confiscated` | `CANCELLED` | Confiscado |
| `lost` | `CANCELLED` | Perdido |
| `recovered` | `CANCELLED` | Recuperado |
| `returned_to_warehouse` | `CANCELLED` | Retornado ao depósito |
| `not_recovered` | `CANCELLED` | Não recuperado |
| `detained_at_customs` | `CANCELLED` | Detido na alfândega |
| `detained_at_origin` | `CANCELLED` | Detido na origem |
| `unclaimed` | `CANCELLED` | Não reivindicado pelo vendedor |
| `import_tax_rejected` | `CANCELLED` | Imposto de importação rejeitado |
| `import_tax_expired` | `CANCELLED` | Imposto de importação expirado |
| `rider_not_found` | `CANCELLED` | Entregador não encontrado |

### Substatus de `cancelled`

| Substatus | Status Interno | Descrição |
|-----------|----------------|-----------|
| `recovered` | `CANCELLED` | Recuperado |
| `label_expired` | `CANCELLED` | Etiqueta expirada |
| `cancelled_manually` | `CANCELLED` | Cancelado manualmente |
| `fraudulent` | `CANCELLED` | Cancelado fraudulento |
| `return_expired` | `CANCELLED` | Retorno expirado |
| `return_session_expired` | `CANCELLED` | Sessão de retorno expirada |
| `unfulfillable` | `CANCELLED` | Não pode ser cumprido |
| `closed_by_user` | `CANCELLED` | Usuário mudou tipo de envio e cancelou o anterior |
| `pack_splitted` | `CANCELLED` | Pack foi dividido pelo splitter do carrinho |
| `shipped_outside_me` | `CANCELLED` | Enviado fora do Mercado Envios |
| `shipped_outside_me_trusted` | `CANCELLED` | Enviado fora do Mercado Envios por vendedor confiável |
| `inferred_shipped` | `CANCELLED` | Envio inferido |
| `service_unavailable` | `CANCELLED` | Serviço indisponível |
| `dismissed` | `CANCELLED` | Dispensado |
| `time_expired` | `CANCELLED` | Tempo expirado |
| `pack_partially_cancelled` | `CANCELLED` | Pack parcialmente cancelado |
| `rejected_manually` | `CANCELLED` | Rejeitado manualmente |
| `closed_store` | `CANCELLED` | Loja fechada |
| `out_of_range` | `CANCELLED` | Fora do alcance |

---

## 🔄 Prioridade de Mapeamento

O sistema segue esta ordem de prioridade ao determinar o status de um pedido:

1. **Status Manual** - Se o pedido tem `status_manual = true`, respeita o status manual a menos que o novo status da API seja mais avançado ou seja um status final
2. **Substatus (fulfillment)** - Mais específico e preciso
3. **Status de Shipment** - Mais confiável que o status do pedido
4. **Status do Pedido (Order)** - Fallback quando não há informações de envio

### Exemplo de Fluxo

```
Status Manual (READY_TO_PREPARE) → Preservado se API retornar PAID ou menos avançado
    ↓ (se não houver status manual ou se API for mais avançada)
Substatus "in_warehouse" → PAID (prioridade máxima)
    ↓ (se não houver)
Shipment Status "ready_to_ship" → PAID
    ↓ (se não houver)
Order Status "paid" → PAID (fallback)
```

---

## 📝 Notas Importantes

### Tags de Pedidos

Além dos status, os pedidos podem ter **tags** que indicam informações adicionais:

- `delivered` - Pedido entregue
- `paid` - Pedido pago
- `not_delivered` - Não entregue
- `pack_order` - Pedido de pack
- `test_order` - Pedido de teste
- `mshops` - Pedido do Mercado Shops
- `fraud_risk_detected` - Risco de fraude detectado
- `no_shipping` - Sem envio

### Status Especiais

- **`partially_refunded` com tag `delivered`**: Se um pedido tem status `partially_refunded` mas possui a tag `delivered`, o sistema considera como `DELIVERED` em vez de `PARTIALLY_REFUNDED`.

### Fulfillment

Para pedidos com logística **Full (Fulfillment)**, os substatus são prioritários para determinar o estado real do pedido, pois representam informações mais precisas sobre o processamento no centro de distribuição.

### Status Manual (`READY_TO_PREPARE`)

O sistema suporta um status customizado **`READY_TO_PREPARE`** que não existe na API do Mercado Livre. Este status é usado internamente para marcar manualmente pedidos **não-Fulfillment** que estão prontos para preparação.

#### Características:

- **Definição Manual**: O status `READY_TO_PREPARE` só pode ser definido manualmente através da interface do sistema (não vem da API do Mercado Livre)
- **Preservação**: Quando um pedido tem status manual (`status_manual = true`), a sincronização automática via API respeita este status:
  - **Atualiza apenas se**: o novo status da API for mais avançado na hierarquia ou for um status final (CANCELLED, DELIVERED, REFUNDED, etc.)
  - **Preserva se**: o novo status da API for igual ou menos avançado que o status manual atual
- **Uso**: Principalmente para pedidos não-Fulfillment que precisam ser preparados manualmente antes do envio

#### Hierarquia de Status:

```
PENDING (1) → CONFIRMED (2) → READY_TO_PREPARE (3) → PAID (4) → SHIPPED (5) → DELIVERED (6)
```

Status finais (nível 0) sempre atualizam independente de ser manual:
- `CANCELLED`, `PENDING_CANCEL`, `REFUNDED`, `PARTIALLY_REFUNDED`, `INVALID`

#### Campos no Banco de Dados:

- `status_manual` (BOOLEAN): Indica se o status foi definido manualmente
- `status_manual_date` (TIMESTAMP): Data da última alteração manual do status

---

## 🔗 Referências

- [Documentação oficial - Gerenciar orders](https://developers.mercadolivre.com.br/pt_br/gerenciamento-de-vendas)
- [Documentação oficial - Gerenciar envios](https://developers.mercadolivre.com.br/pt_br/gerenciamento-de-envios)
- [Documentação oficial - Envios Fulfillment](https://developers.mercadolivre.com.br/pt_br/envios-fulfillment)
- [Documentação oficial - Status de pedidos ME1](https://developers.mercadolivre.com.br/pt_br/status-de-pedidos-rastreamento)

---

**Última atualização:** 29/10/2025  
**Versão do código:** Baseado na documentação oficial do Mercado Livre (atualizada em 2025)  
**Status Customizado:** `READY_TO_PREPARE` implementado em 29/10/2025

