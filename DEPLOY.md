# 🚀 Deploy da Aplicação

## 📁 Arquivos Docker Compose

### 1️⃣ `docker-compose.yml` - Desenvolvimento Local
**Uso:** Desenvolvimento na sua máquina com ngrok

```bash
# Subir aplicação local
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar
docker-compose down
```

**Características:**
- Porta: 8000
- ngrok para túnel (opcional)
- PostgreSQL externo: pgadmin.wolfx.com.br

---

### 2️⃣ `docker-compose.prod.yml` - Produção
**Uso:** Deploy em servidor com domínio wolfx.com.br

```bash
# Deploy em produção
./deploy-production.sh

# OU manualmente:
docker-compose -f docker-compose.prod.yml up -d --build

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f

# Parar
docker-compose -f docker-compose.prod.yml down
```

**Características:**
- ✅ SSL/HTTPS automático (Let's Encrypt)
- ✅ Traefik como proxy reverso
- ✅ Domínio: wolfx.com.br
- ✅ Credenciais de produção Mercado Pago
- ✅ Portas 80 e 443

---

## 🔧 Deploy em Produção (Passo a Passo)

### Pré-requisitos
1. ✅ DNS configurado: `wolfx.com.br` → IP do servidor
2. ✅ Portas 80 e 443 abertas no firewall
3. ✅ Docker e Docker Compose instalados

### Executar Deploy
```bash
# 1. Clone o repositório (se ainda não fez)
git clone seu-repositorio
cd apiwolfx

# 2. Execute o script de deploy
chmod +x deploy-production.sh
./deploy-production.sh
```

### Após o Deploy
1. **Configurar Webhook do Mercado Pago:**
   - URL: `https://wolfx.com.br/payment/webhooks/mercadopago`
   - Painel: https://www.mercadopago.com.br/developers/panel/app/534913383560219/webhooks

2. **Verificar aplicação:**
   - Site: https://wolfx.com.br
   - API Docs: https://wolfx.com.br/docs
   - Traefik Dashboard: http://seu-ip:8080

3. **Monitorar logs:**
   ```bash
   docker-compose -f docker-compose.prod.yml logs -f api
   docker-compose -f docker-compose.prod.yml logs -f traefik
   ```

---

## 🔄 Atualizar Produção

```bash
# 1. Fazer pull das alterações
git pull origin main

# 2. Rebuild e redeploy
docker-compose -f docker-compose.prod.yml up -d --build

# 3. Verificar logs
docker-compose -f docker-compose.prod.yml logs -f api
```

---

## 📊 Comandos Úteis

### Ver status dos containers
```bash
docker-compose -f docker-compose.prod.yml ps
```

### Reiniciar um serviço específico
```bash
docker-compose -f docker-compose.prod.yml restart api
docker-compose -f docker-compose.prod.yml restart traefik
```

### Ver logs de um serviço
```bash
docker-compose -f docker-compose.prod.yml logs -f api
docker-compose -f docker-compose.prod.yml logs -f traefik
```

### Executar comando dentro do container
```bash
docker-compose -f docker-compose.prod.yml exec api bash
```

### Limpar tudo e reiniciar
```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## 🆘 Troubleshooting

### SSL não funciona
```bash
# Verificar logs do Traefik
docker-compose -f docker-compose.prod.yml logs traefik

# Verificar se portas estão abertas
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### Aplicação não responde
```bash
# Ver logs
docker-compose -f docker-compose.prod.yml logs api

# Reiniciar
docker-compose -f docker-compose.prod.yml restart api
```

### Webhook não funciona
1. Verificar URL configurada no Mercado Pago
2. Testar manualmente:
```bash
curl -X POST https://wolfx.com.br/payment/webhooks/mercadopago \
  -H "Content-Type: application/json" \
  -d '{"action":"payment.updated","data":{"id":"12345"}}'
```

