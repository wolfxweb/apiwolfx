#!/bin/bash
# Script para gerar PDF usando um container Docker dedicado

echo "============================================================"
echo "📚 Gerador de PDF - Manual do Sistema CELX"
echo "============================================================"

# Construir imagem se necessário
if ! docker images | grep -q gerador-pdf; then
    echo "🔨 Construindo imagem Docker para geração de PDF..."
    docker build -f Dockerfile.pdf -t gerador-pdf .
fi

# Executar container e gerar PDF
echo "🚀 Gerando PDF..."
docker run --rm \
    -v "$(pwd):/app" \
    -w /app \
    gerador-pdf

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ PDF gerado com sucesso!"
    echo "   Arquivo: Manual_Completo_CELX.pdf"
    
    # Limpar arquivo temporário se existir
    if [ -f "Manual_Completo_Temp.md" ]; then
        rm Manual_Completo_Temp.md
        echo "   Arquivo temporário removido."
    fi
else
    echo ""
    echo "❌ Erro ao gerar PDF."
    exit 1
fi

