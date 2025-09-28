# 🐳 API Mercado Livre - Docker

Guia completo para executar a API Mercado Livre usando Docker com MySQL e phpMyAdmin.

## 📋 Pré-requisitos

- **Docker** (versão 20.10+)
- **Docker Compose** (versão 2.0+)
- **Git** (para clonar o repositório)

## 🚀 Instalação e Execução

### 1. Clone o Repositório
```bash
git clone https://github.com/seu-usuario/apiwolfx.git
cd apiwolfx
```

### 2. Execute com Docker
```bash
# Método 1: Script automatizado
./run_docker.sh

# Método 2: Comandos manuais
docker-compose up --build -d
```

### 3. Inicializar Banco de Dados
```bash
# Executar script de inicialização
docker-compose exec api python scripts/init_db.py
```

## 🌐 URLs Disponíveis

| Serviço | URL | Descrição |
|---------|-----|-----------|
| **API** | http://localhost:8000 | API principal |
| **Documentação** | http://localhost:8000/docs | Swagger UI |
| **phpMyAdmin** | http://localhost:8080 | Interface do banco |
| **Health Check** | http://localhost:8000/health | Status da API |

## 🗄️ Banco de Dados

### Credenciais
- **Host**: localhost:3306
- **Usuário**: root
- **Senha**: password
- **Banco**: apiwolfx

### Tabelas Criadas
- `users` - Usuários do Mercado Livre
- `tokens` - Tokens de acesso
- `products` - Produtos dos usuários
- `categories` - Categorias do ML
- `api_logs` - Logs da API

## 🔧 Comandos Úteis

### Gerenciar Containers
```bash
# Ver status dos containers
docker-compose ps

# Ver logs
docker-compose logs -f

# Parar todos os containers
docker-compose down

# Parar e remover volumes
docker-compose down -v

# Reiniciar um serviço específico
docker-compose restart api
```

### Acessar Container
```bash
# Acessar container da API
docker-compose exec api bash

# Acessar banco de dados
docker-compose exec db mysql -u root -p
```

### Backup do Banco
```bash
# Fazer backup
docker-compose exec db mysqldump -u root -p apiwolfx > backup.sql

# Restaurar backup
docker-compose exec -T db mysql -u root -p apiwolfx < backup.sql
```

## 📊 Monitoramento

### Logs da Aplicação
```bash
# Ver logs em tempo real
docker-compose logs -f api

# Ver logs do banco
docker-compose logs -f db

# Ver logs do phpMyAdmin
docker-compose logs -f phpmyadmin
```

### Estatísticas
```bash
# Uso de recursos
docker stats

# Espaço usado
docker system df
```

## 🔐 Configuração

### Variáveis de Ambiente
As configurações estão no arquivo `docker-compose.yml`:

```yaml
environment:
  - DATABASE_URL=mysql://root:password@db:3306/apiwolfx
  - ML_APP_ID=6987936494418444
  - ML_CLIENT_SECRET=puvG9Z7XBgICZg5yK3t0PAXAmnco18Tl
  - ML_REDIRECT_URI=http://localhost:8000/api/callback
```

### Personalizar Configurações
1. Edite o arquivo `docker-compose.yml`
2. Reinicie os containers:
```bash
docker-compose down
docker-compose up -d
```

## 🐛 Solução de Problemas

### Container não inicia
```bash
# Ver logs de erro
docker-compose logs api

# Reconstruir container
docker-compose build --no-cache api
docker-compose up -d api
```

### Banco de dados não conecta
```bash
# Verificar se o MySQL está rodando
docker-compose ps db

# Reiniciar banco
docker-compose restart db

# Ver logs do banco
docker-compose logs db
```

### Porta já em uso
```bash
# Verificar portas em uso
netstat -tulpn | grep :8000
netstat -tulpn | grep :3306
netstat -tulpn | grep :8080

# Parar processos que usam as portas
sudo kill -9 <PID>
```

## 📈 Performance

### Otimizações
- **MySQL**: Configurado com pool de conexões
- **FastAPI**: Uvicorn com workers
- **Volumes**: Dados persistentes

### Escalabilidade
```bash
# Executar múltiplas instâncias da API
docker-compose up --scale api=3

# Usar nginx como load balancer
# (configuração adicional necessária)
```

## 🔄 Atualizações

### Atualizar Código
```bash
# Parar containers
docker-compose down

# Atualizar código
git pull

# Reconstruir e iniciar
docker-compose up --build -d
```

### Atualizar Dependências
```bash
# Reconstruir com novas dependências
docker-compose build --no-cache
docker-compose up -d
```

## 📚 Documentação Adicional

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [MySQL Docker](https://hub.docker.com/_/mysql)
- [phpMyAdmin Docker](https://hub.docker.com/r/phpmyadmin/phpmyadmin)

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

---

**Desenvolvido com ❤️ para integração com Mercado Livre usando Docker**
