# Deploy em Produção - celx.com.br

Este documento contém os comandos para atualizar a aplicação em produção.

## Pré-requisitos

- Acesso SSH ao servidor de produção
- Permissões de root ou sudo no servidor
- Docker Swarm configurado
- Rede `server` criada no Docker Swarm
- Chave SSH configurada para acesso ao GitHub

# Clonar se não existir
if [ ! -d "/root/apiwolfx" ]; then
    cd /root && git clone https://github.com/wolfxweb/apiwolfx.git
fi

# Depois fazer o deploy
cd /root/apiwolfx && \
git pull origin main && \
docker build -t celx_ml_api:latest . && \
docker service update --force --image celx_ml_api:latest celx_ml_api_api && \
sleep 10 && \
docker service ps celx_ml_api_api


## Configuração Inicial: Secret SSH do GitHub

**IMPORTANTE:** Execute este passo apenas uma vez, antes do primeiro deploy:

```bash
# No servidor, criar o secret do Docker Swarm com a chave SSH
# (Substitua /root/.ssh/id_rsa pelo caminho da sua chave SSH)
cat /root/.ssh/id_rsa | docker secret create github_ssh_key -

# Verificar se o secret foi criado
docker secret ls | grep github_ssh_key
```

**Nota:** Se você não tiver uma chave SSH configurada no servidor, crie uma:

```bash
# Gerar nova chave SSH (se não existir)
ssh-keygen -t ed25519 -C "deploy@celx.com.br" -f /root/.ssh/id_rsa -N ""

# Adicionar a chave pública ao GitHub (copie o conteúdo e adicione em GitHub Settings > SSH Keys)
cat /root/.ssh/id_rsa.pub
```

## Comandos para Atualizar Produção

### Método Rápido: Redeploy Simples (Recomendado)

**No servidor, após fazer commit e push no git:**

```bash
# 1. Garantir que o docker-compose.prod.yml está atualizado no /root
# (O container já faz git clone automaticamente, mas se quiser forçar atualização)

# 2. Executar redeploy simples
docker stack deploy -c /root/docker-compose.prod.yml celx_ml_api

# 3. Aguardar e verificar
sleep 20
docker service logs celx_ml_api_api --tail 20
```

**Ou usar o script simples:**

```bash
# No servidor, criar o script:
cat > /root/redeploy.sh << 'EOF'
#!/bin/bash
echo "🚀 Redeploy..."
docker stack deploy -c /root/docker-compose.prod.yml celx_ml_api
sleep 20
docker service logs celx_ml_api_api --tail 10
echo "✅ Pronto!"
EOF

chmod +x /root/redeploy.sh

# Depois, sempre que quiser atualizar:
/root/redeploy.sh
```

### Método 1: Usando Script Completo (Mais Detalhado)

**No seu computador local:**

```bash
# 1. Fazer commit e push das alterações
git add .
git commit -m "Atualização para produção"
git push
```

**No servidor:**

```bash
# 2. Conectar ao servidor
ssh root@seu-servidor

# 3. Copiar o script para o servidor (se não existir)
# Do seu computador local:
scp deploy-production.sh root@seu-servidor:/root/

# 4. No servidor, dar permissão de execução e executar
cd /root
chmod +x deploy-production.sh

# 5. Se o repositório for privado, definir o token do GitHub
export GITHUB_TOKEN=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

# 6. Executar o script
./deploy-production.sh
```

**Nota:** O script baixa automaticamente o `docker-compose.prod.yml` do repositório. Se o repositório for privado, defina a variável `GITHUB_TOKEN` antes de executar.

### Método 2: Manual (Passo a Passo)

### 1. Conectar ao Servidor

```bash
ssh root@seu-servidor
```

### 2. Copiar Arquivo docker-compose.prod.yml

**No seu computador local:**
```bash
scp docker-compose.prod.yml root@seu-servidor:/root/
```

**OU no servidor (se o repositório for público):**
```bash
curl https://raw.githubusercontent.com/wolfxweb/apiwolfx/main/docker-compose.prod.yml \
  -o /root/docker-compose.prod.yml

# Verificar se o arquivo foi baixado corretamente
cat /root/docker-compose.prod.yml | head -20
```

### 3. Atualizar o Stack Docker Swarm

```bash
# Atualizar o stack com o novo arquivo
docker stack deploy -c /root/docker-compose.prod.yml celx_ml_api

# Aguardar alguns segundos para o serviço iniciar
sleep 15
```

### 4. Verificar Status do Serviço

```bash
# Verificar se o serviço está rodando
docker service ps celx_ml_api_api

# Ver logs do serviço
docker service logs celx_ml_api_api --tail 50

# Verificar se o uvicorn iniciou corretamente
docker service logs celx_ml_api_api --tail 20 | grep -i uvicorn
```

### 5. Reiniciar o Traefik (se necessário)

```bash
# Reiniciar o Traefik para forçar detecção de novos serviços
docker service update --force traefik_traefik

# Aguardar alguns segundos
sleep 10

# Verificar logs do Traefik
docker service logs traefik_traefik --tail 50 | grep -i celx
```

### 6. Testar Acesso

```bash
# Testar acesso HTTP (deve redirecionar para HTTPS)
curl -I http://celx.com.br/

# Testar acesso HTTPS (pode dar erro de certificado self-signed inicialmente)
curl -k -I https://celx.com.br/
```

## Comandos Úteis

### Ver Todos os Serviços

```bash
docker service ls
```

### Ver Logs em Tempo Real

```bash
# Logs do serviço API
docker service logs -f celx_ml_api_api

# Logs do Traefik
docker service logs -f traefik_traefik
```

### Remover o Serviço (se necessário)

```bash
# Remover apenas o serviço API
docker service rm celx_ml_api_api

# OU remover todo o stack
docker stack rm celx_ml_api
```

### Recriar o Serviço do Zero

```bash
# 1. Remover o serviço antigo
docker service rm celx_ml_api_api

# 2. Aguardar
sleep 5

# 3. Baixar arquivo atualizado
curl https://raw.githubusercontent.com/wolfxweb/apiwolfx/main/docker-compose.prod.yml \
  -o /root/docker-compose.prod.yml

# 4. Criar novo stack
docker stack deploy -c /root/docker-compose.prod.yml celx_ml_api

# 5. Aguardar e verificar
sleep 20
docker service ps celx_ml_api_api
```

### Verificar Configuração do Traefik

```bash
# Ver labels do serviço
docker service inspect celx_ml_api_api --format '{{range $k, $v := .Spec.Labels}}{{printf "%s=%s\n" $k $v}}{{end}}' | grep traefik

# Ver logs do Traefik para verificar detecção
docker exec $(docker ps -q --filter "name=traefik") cat /var/log/traefik/traefik.log | grep -i celx | tail -20
```

## Troubleshooting

### Serviço não inicia

```bash
# Ver erros detalhados
docker service ps celx_ml_api_api --no-trunc

# Ver logs completos
docker service logs celx_ml_api_api --tail 100
```

### Traefik não detecta o serviço

```bash
# Verificar se o serviço está na rede correta
docker service inspect celx_ml_api_api --format '{{json .Endpoint.Spec.Networks}}' | python3 -m json.tool

# Verificar se a rede server existe
docker network ls | grep server

# Reiniciar o Traefik
docker service update --force traefik_traefik
```

### Erro 404 no site

```bash
# Verificar se o Traefik detectou o serviço
docker exec $(docker ps -q --filter "name=traefik") cat /var/log/traefik/traefik.log | grep -i "celx-api" | tail -10

# Verificar se o serviço está acessível
docker exec $(docker ps -q --filter "name=celx_ml_api_api") curl -I http://localhost:8000/
```

### Problema com Git Clone

```bash
# Verificar se o token está configurado
docker service inspect celx_ml_api_api --format '{{range .Spec.TaskTemplate.ContainerSpec.Env}}{{printf "%s\n" .}}{{end}}' | grep GITHUB_TOKEN

# Ver logs do git clone
docker service logs celx_ml_api_api | grep -i "git\|clone\|fatal"
```

## Notas Importantes

1. **Token do GitHub**: O token está configurado no arquivo `docker-compose.prod.yml`. Se o repositório for privado, certifique-se de que o token tem permissões `repo`.

2. **Rede Docker**: O serviço precisa estar na rede `server` para o Traefik conseguir acessá-lo.

3. **Certificado SSL**: O Let's Encrypt pode levar alguns minutos para gerar o certificado na primeira vez. Enquanto isso, o site usará um certificado self-signed.

4. **Logs**: Os logs do Traefik estão em `/var/log/traefik/traefik.log` dentro do container.

5. **Atualizações**: Sempre baixe o arquivo `docker-compose.prod.yml` atualizado antes de fazer deploy.

## Estrutura de Deploy

```
┌─────────────────┐
│  GitHub Repo   │
│  (apiwolfx)    │
└────────┬────────┘
         │ git clone
         ▼
┌─────────────────┐
│  Docker Swarm   │
│  (celx_ml_api)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Traefik        │
│  (Reverse Proxy)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  celx.com.br    │
│  (HTTPS)        │
└─────────────────┘
```

## Checklist de Deploy

- [ ] Conectado ao servidor via SSH
- [ ] Arquivo `docker-compose.prod.yml` atualizado
- [ ] Stack atualizado com `docker stack deploy`
- [ ] Serviço iniciado corretamente (verificar logs)
- [ ] Traefik detectou o serviço (verificar logs)
- [ ] Site acessível via HTTPS
- [ ] Certificado SSL válido (pode levar alguns minutos)

