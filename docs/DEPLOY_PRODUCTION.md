# Ver diferenças entre código local e VPS
cd /root/apiwolfx

# Buscar atualizações do repositório remoto (sem fazer merge)
git fetch origin

# Ver diferenças detalhadas entre código atual e remoto
git diff HEAD origin/main

# Ver apenas os nomes dos arquivos que mudaram
# git diff --name-only HEAD origin/main

# Ver resumo estatístico das mudanças
# git diff --stat HEAD origin/main

# Ver último commit no remoto
# git log origin/main -1 --oneline

# Atualizar código do GitHub
git pull origin main

# Fazer deploy
./deploy.sh