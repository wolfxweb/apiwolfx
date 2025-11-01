# Fluxo do Webhook e Callback - Mercado Livre

## 📋 Resumo do Fluxo

### 1️⃣ **OAuth Callback** (`/api/callback`)

Quando o usuário autoriza a aplicação no Mercado Livre:

**Parâmetros recebidos:**
- `code`: Código de autorização (único, uso único)
- `state`: ID do usuário logado no sistema (user_id)
- `error`: (opcional) Se houver erro na autorização

**O que o callback faz:**
1. Troca `code` por `access_token` via `POST /oauth/token`
2. Usa `access_token` para chamar `GET /users/me`
3. **`/users/me` retorna:**
   ```json
   {
     "id": 1979794691,           // ← ml_user_id (INT)
     "nickname": "WOLFXDISTRIBUIDORA",
     "email": "...",
     "first_name": "...",
     "last_name": "...",
     "country_id": "BR",
     "site_id": "MLB",
     "permalink": "..."
   }
   ```
4. Salva `MLAccount` com:
   - `ml_user_id`: `str(user_info["id"])` ← **IMPORTANTE: como STRING**
   - `company_id`: Do usuário logado (via `state`)
   - Outros dados do `user_info`

### 2️⃣ **Webhook Notifications** (`/api/notifications`)

O Mercado Livre envia notificações POST para esta URL quando há eventos.

**Estrutura da notificação:**
```json
{
  "_id": "id_unico",
  "resource": "/orders/123456",
  "user_id": 1979794691,          // ← ml_user_id (INT)
  "topic": "orders_v2",
  "application_id": 6987936494418444,
  "attempts": 1,
  "sent": "2024-01-01T12:00:00.000Z",
  "received": "2024-01-01T12:00:00.000Z"
}
```

**Como identificamos a conta:**
1. Extrai `ml_user_id` do campo `user_id` (int)
2. Busca `MLAccount` onde `ml_user_id == str(webhook_user_id)`
3. Obtém `company_id` da `MLAccount` encontrada
4. Processa a notificação para aquela empresa

## ⚠️ PROBLEMA COMUM

**Inconsistência de tipo:**
- Webhook envia `user_id` como **INT** (ex: `1979794691`)
- Banco armazena `ml_user_id` como **STRING** (ex: `"1979794691"`)
- **Solução:** Sempre converter para string ao salvar e ao buscar

## ✅ COMO IDENTIFICAR A CONTA NO CALLBACK

**O callback retorna:**
- `user_info["id"]` → Este é o `ml_user_id` que será usado nas notificações
- Este valor deve ser salvo como `string` na tabela `ml_accounts.ml_user_id`

**Exemplo:**
```python
# ✅ CORRETO
ml_account = MLAccount(
    ml_user_id=str(user_info["id"]),  # Converte para string
    ...
)

# ❌ ERRADO (pode causar problemas de comparação)
ml_account = MLAccount(
    ml_user_id=user_info["id"],  # Pode salvar como int
    ...
)
```

## ✅ COMO IDENTIFICAR A CONTA NO WEBHOOK

```python
# Na notificação
ml_user_id = notification_data.get("user_id")  # int (ex: 1979794691)

# Busca no banco
ml_account = db.query(MLAccount).filter(
    MLAccount.ml_user_id == str(ml_user_id),  # Compara como string
    MLAccount.status == MLAccountStatus.ACTIVE
).first()

company_id = ml_account.company_id if ml_account else None
```

## 🔍 DEBUGGING

Para verificar se a identificação está funcionando:

```python
# Verificar contas cadastradas
from app.config.database import SessionLocal
from app.models.saas_models import MLAccount

db = SessionLocal()
accounts = db.query(MLAccount).all()
for acc in accounts:
    print(f"ML Account ID: {acc.id}")
    print(f"Company ID: {acc.company_id}")
    print(f"ML User ID: {acc.ml_user_id} (tipo: {type(acc.ml_user_id)})")
    print(f"Nickname: {acc.nickname}")
```

## 📝 CHECKLIST

- [ ] Callback sempre salva `ml_user_id` como **STRING**
- [ ] Webhook sempre compara `ml_user_id` como **STRING**
- [ ] Logs mostram `ml_user_id` usado na busca
- [ ] Verificar se `MLAccount` está `ACTIVE` ao buscar
- [ ] Verificar se há tokens válidos para a conta

