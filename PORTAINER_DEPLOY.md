# 🚀 Deploy no Portainer via GitHub

## 📋 Como Funciona

1. **Você faz push para o GitHub** → `git push origin main`
2. **GitHub Actions faz o build** da imagem Docker automaticamente
3. **Imagem é publicada** no GitHub Container Registry (ghcr.io)
4. **Portainer puxa a imagem** e faz deploy automático

---

## 🔧 Configuração Inicial (Fazer UMA VEZ)

### 1. Ativar GitHub Actions

1. Vá em: https://github.com/wolfxweb/apiwolfx/settings/actions
2. Em **Actions permissions**, marque: ✅ **Allow all actions and reusable workflows**
3. Salvar

### 2. Ativar GitHub Container Registry

1. Vá em: https://github.com/wolfxweb/apiwolfx/settings/packages
2. Em **Package creation**, marque: ✅ **Public** (ou Private se preferir)
3. Após o primeiro build, vá em: https://github.com/wolfxweb?tab=packages
4. Clique no pacote `apiwolfx`
5. Em **Package settings** → **Change visibility** → Marque **Public**

### 3. Fazer o Primeiro Build

```bash
git add .
git commit -m "Setup GitHub Actions"
git push origin main
```

Aguarde alguns minutos e verifique em:
- https://github.com/wolfxweb/apiwolfx/actions

A imagem estará em:
- `ghcr.io/wolfxweb/apiwolfx:latest`

---

## 🐳 Configurar Portainer

### Opção 1: Deploy via Git (Recomendado - Auto-atualiza)

No Portainer:

1. **Stacks** → **Add Stack**
2. **Nome**: `apiwolfx-production`
3. **Build method**: ✅ **Repository**

**Repository settings:**
```
Authentication: ✅ Ativado
Username: wolfxweb
Personal Access Token: [SEU_TOKEN_DO_GITHUB]

Repository URL: https://github.com/wolfxweb/apiwolfx
Repository reference: refs/heads/main
Compose path: docker-compose.prod.yml
```

4. **GitOps updates**: ✅ **Ativar**
   - **Polling interval**: 5 minutos
   - **Re-pull image**: ✅ Ativar
   - **Force redeployment**: ✅ Ativar

5. **Deploy the stack**

### Opção 2: Deploy Manual (Copiar/Colar)

1. **Stacks** → **Add Stack**
2. **Nome**: `apiwolfx-production`
3. **Build method**: ✅ **Web editor**
4. Cole o conteúdo do arquivo `docker-compose.prod.yml`
5. **Deploy the stack**

---

## 🔄 Fluxo de Atualização Automática

### Com GitOps Ativado (Opção 1):

```bash
# 1. Fazer alteração no código
vim app/main.py

# 2. Commit e push
git add .
git commit -m "Nova feature"
git push origin main

# 3. Aguardar GitHub Actions fazer build (2-3 min)
# 4. Portainer detecta e atualiza automaticamente (5 min)
```

**Total: ~8 minutos para deploy automático!** ✨

### Sem GitOps (Opção 2):

```bash
# 1. Fazer alteração e push
git push origin main

# 2. No Portainer:
# Stacks → apiwolfx-production → ✅ Pull and redeploy
```

---

## 🔍 Verificar Deploy

### Ver logs do GitHub Actions
```
https://github.com/wolfxweb/apiwolfx/actions
```

### Ver imagem publicada
```
https://github.com/wolfxweb?tab=packages
```

### Testar aplicação
```bash
curl https://wolfx.com.br
curl https://wolfx.com.br/docs
```

---

## 📦 Comandos Úteis

### Ver imagens no GitHub
```bash
# Baixar imagem localmente (se quiser testar)
docker pull ghcr.io/wolfxweb/apiwolfx:latest
docker run -p 8000:8000 ghcr.io/wolfxweb/apiwolfx:latest
```

### Forçar rebuild no GitHub Actions
1. Vá em: https://github.com/wolfxweb/apiwolfx/actions
2. Clique em **Build and Push Docker Image**
3. Clique em **Run workflow** → **Run workflow**

### Ver logs no Portainer
1. **Stacks** → `apiwolfx-production`
2. Clique no container `api` → **Logs**

---

## 🆘 Troubleshooting

### Erro: "no image specified"
**Causa**: Imagem ainda não foi publicada no GitHub Container Registry

**Solução**:
1. Verificar se GitHub Actions rodou: https://github.com/wolfxweb/apiwolfx/actions
2. Verificar se a imagem foi publicada: https://github.com/wolfxweb?tab=packages
3. Se não houver imagem, rodar manualmente:
   ```bash
   docker build -t ghcr.io/wolfxweb/apiwolfx:latest .
   docker push ghcr.io/wolfxweb/apiwolfx:latest
   ```

### Erro: "Ignoring unsupported options: build"
**Causa**: Portainer não suporta `build:` no docker-compose

**Solução**: Já corrigido! O `docker-compose.prod.yml` agora usa apenas `image:` (sem build)

### Imagem não atualiza no Portainer
**Solução**:
1. No Portainer, vá em **Stacks** → `apiwolfx-production`
2. Clique em **✅ Pull and redeploy**
3. Ou ative **GitOps updates** para auto-atualização

---

## ✅ Checklist de Deploy

Antes de fazer deploy:

- [ ] GitHub Actions configurado e funcionando
- [ ] Primeira imagem publicada no ghcr.io
- [ ] DNS configurado: `wolfx.com.br` → IP do servidor
- [ ] Portas 80 e 443 abertas no firewall
- [ ] Portainer configurado com Git ou Web editor
- [ ] GitOps ativado (para auto-deploy)
- [ ] Webhook do Mercado Pago configurado: `https://wolfx.com.br/payment/webhooks/mercadopago`
- [ ] SSL/HTTPS funcionando (Let's Encrypt)

---

## 🎯 Resumo

**Desenvolvimento → Produção em 3 passos:**

```bash
# 1. Fazer alteração
vim app/main.py

# 2. Commit e push
git add . && git commit -m "Update" && git push

# 3. Aguardar deploy automático (8 min) ✨
# Ou forçar no Portainer: Pull and redeploy
```

Simples assim! 🚀

