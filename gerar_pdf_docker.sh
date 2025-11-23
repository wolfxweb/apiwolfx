#!/bin/bash
# Script para gerar PDF dos manuais usando o container Docker

echo "============================================================"
echo "📚 Gerador de PDF - Manual do Sistema CELX (Docker)"
echo "============================================================"

# Verificar se o container está rodando
if ! docker ps | grep -q apiwolfx-api; then
    echo "❌ Container apiwolfx-api não está rodando."
    echo "   Inicie o container com: docker-compose up -d"
    exit 1
fi

echo "📦 Verificando se pandoc está instalado no container..."
docker exec apiwolfx-api which pandoc > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "📥 Instalando pandoc e dependências no container..."
    docker exec apiwolfx-api bash -c "
        apt-get update && \
        apt-get install -y pandoc texlive-xetex texlive-fonts-recommended && \
        apt-get clean
    "
fi

echo "📄 Combinando arquivos Markdown..."
docker exec -w /app apiwolfx-api python3 gerar_pdf_manual.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ PDF gerado com sucesso!"
    echo "   Arquivo: Manual_Completo_CELX.pdf"
    echo ""
    echo "📋 Para copiar o PDF do container:"
    echo "   docker cp apiwolfx-api:/app/Manual_Completo_CELX.pdf ./"
else
    echo ""
    echo "❌ Erro ao gerar PDF. Verifique os logs acima."
    exit 1
fi

