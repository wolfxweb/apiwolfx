#!/bin/bash
# Script para corrigir erro de ProgrammingError em produção
# Execute este script no servidor de produção

FILE_PATH="/app/app/controllers/ml_claims_controller.py"
BACKUP_PATH="/app/app/controllers/ml_claims_controller.py.backup.$(date +%Y%m%d_%H%M%S)"

echo "🔧 Corrigindo erro de ProgrammingError em produção..."
echo "📁 Arquivo: $FILE_PATH"

# Fazer backup
if [ -f "$FILE_PATH" ]; then
    cp "$FILE_PATH" "$BACKUP_PATH"
    echo "✅ Backup criado: $BACKUP_PATH"
else
    echo "❌ Arquivo não encontrado: $FILE_PATH"
    exit 1
fi

# Verificar se o import já existe
if grep -q "from sqlalchemy.exc import ProgrammingError, OperationalError" "$FILE_PATH"; then
    echo "✅ Import já existe no arquivo"
    exit 0
fi

# Adicionar import após a linha 9 (depois de "from sqlalchemy import and_, or_")
sed -i '9a\
from sqlalchemy.exc import ProgrammingError, OperationalError
' "$FILE_PATH"

# Verificar se foi adicionado corretamente
if grep -q "from sqlalchemy.exc import ProgrammingError, OperationalError" "$FILE_PATH"; then
    echo "✅ Import adicionado com sucesso!"
    echo ""
    echo "📋 Verificando sintaxe Python..."
    python3 -m py_compile "$FILE_PATH" && echo "✅ Sintaxe OK" || echo "❌ Erro de sintaxe"
    echo ""
    echo "🔄 Reinicie o serviço para aplicar as mudanças"
else
    echo "❌ Erro ao adicionar import"
    echo "🔄 Restaurando backup..."
    cp "$BACKUP_PATH" "$FILE_PATH"
    exit 1
fi

