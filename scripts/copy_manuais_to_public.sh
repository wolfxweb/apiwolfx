#!/bin/bash
# Script para copiar manuais para public/manuais

echo "📚 Copiando manuais para public/manuais..."

# Criar diretórios se não existirem
mkdir -p public/manuais/agente_ia

# Copiar manuais gerais
if [ -d "manuais" ]; then
    echo "📄 Copiando manuais gerais..."
    cp -r manuais/*.md public/manuais/ 2>/dev/null || true
    echo "✅ Manuais gerais copiados"
else
    echo "⚠️ Diretório manuais não encontrado"
fi

# Copiar manuais de agente IA
if [ -d "manuais/agente_ia" ]; then
    echo "🤖 Copiando manuais de agente IA..."
    cp -r manuais/agente_ia/*.md public/manuais/agente_ia/ 2>/dev/null || true
    echo "✅ Manuais de agente IA copiados"
else
    echo "⚠️ Diretório manuais/agente_ia não encontrado"
fi

echo "🎉 Concluído!"

