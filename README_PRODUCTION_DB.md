# Conexão com Banco de Produção (Selvez)

Este documento descreve como conectar a aplicação local ao banco de dados de produção do **selvez**.

## ⚠️ AVISO IMPORTANTE

**Você está conectando ao banco de PRODUÇÃO!** 
- Tenha muito cuidado com alterações nos dados
- Evite executar scripts de migração ou alterações em massa
- Use apenas para testes e consultas

## 🔧 Configuração

O arquivo `.env` já foi configurado com as seguintes variáveis:

```env
DATABASE_URL=postgresql://api_user:%40Wolfx20202025@207.231.108.38:5432/selvez
ENVIRONMENT=production
```

## 📋 Detalhes da Conexão

- **Host:** `207.231.108.38`
- **Porta:** `5432`
- **Usuário:** `api_user`
- **Senha:** `@Wolfx20202025` (codificada como `%40Wolfx20202025` na URL)
- **Database:** `selvez`

## 🚀 Como Usar

### 1. Aplicar Configuração

As configurações já foram aplicadas. Se precisar reaplicar:

```bash
./connect_production_db.sh
```

### 2. Reiniciar o Container

Para aplicar as mudanças, reinicie o container:

```bash
docker-compose restart api
```

### 3. Verificar Conexão

Teste se a conexão está funcionando:

```bash
./test_production_db_connection.sh
```

Ou verifique os logs:

```bash
docker logs apiwolfx-api --tail=50 | grep -i 'database\|connection\|error'
```

## 🔄 Voltar para Banco Local

Para voltar a usar o banco local (comercial):

```bash
# Restaurar backup
cp .env.backup* .env

# Ou editar manualmente
# DATABASE_URL=postgresql://postgres:97452c28f62db6d77be083917b698660@pgadmin.wolfx.com.br:5432/comercial
# ENVIRONMENT=local

docker-compose restart api
```

## 🛠️ Scripts Disponíveis

### `connect_production_db.sh`
Configura o `.env` para conectar ao banco de produção. Cria backup automático.

### `test_production_db_connection.sh`
Testa a conexão com o banco de produção e exibe informações da conexão.

## 📝 Notas Técnicas

- O arquivo `app/config/database.py` lê a variável `DATABASE_URL` primeiro
- Se `DATABASE_URL` não existir, usa `ENVIRONMENT` para determinar o banco
- A senha usa codificação URL: `@` = `%40`
- O timeout de conexão é de 30 segundos
- Pool de conexões: 5 conexões base, máximo 15 (5 + 10 overflow)

## 🐛 Troubleshooting

### Erro de conexão timeout
- Verifique se o IP `207.231.108.38` está acessível do seu local
- Verifique firewall/rede

### Erro de autenticação
- Verifique se a senha está codificada corretamente (`%40` para `@`)
- Confirme que o usuário `api_user` tem permissões

### Container não inicia
- Verifique os logs: `docker logs apiwolfx-api`
- Verifique se o arquivo `.env` existe e está correto

