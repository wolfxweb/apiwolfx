# Como Gerar PDF dos Manuais

Este documento explica como gerar um PDF único a partir de todos os arquivos Markdown dos manuais do sistema.

## Método 1: Usando Docker (Recomendado)

O método mais simples é usar o script Docker que já tem todas as dependências configuradas:

```bash
./gerar_pdf_com_docker.sh
```

Este script:
1. Constrói uma imagem Docker com pandoc e LaTeX
2. Combina todos os arquivos Markdown em ordem
3. Gera o PDF `Manual_Completo_CELX.pdf`
4. Remove arquivos temporários

## Método 2: Usando o Container Existente

Se o container `apiwolfx-api` já estiver rodando, você pode instalar pandoc nele:

```bash
./gerar_pdf_docker.sh
```

## Método 3: Executar Script Python Diretamente

Se você tiver pandoc instalado localmente:

```bash
python3 gerar_pdf_manual.py
```

**Requisitos:**
- pandoc instalado
- LaTeX (xelatex) instalado

**No macOS:**
```bash
brew install pandoc basictex
```

## Arquivos Gerados

- `Manual_Completo_CELX.pdf` - PDF final com todos os manuais
- `Manual_Completo_Temp.md` - Arquivo Markdown temporário (removido automaticamente)

## Estrutura do PDF

O PDF contém:
1. Índice Geral
2. Todos os 27 manuais em ordem
3. Tabela de conteúdos automática
4. Formatação profissional

## Solução de Problemas

### Erro: "pandoc não encontrado"
- Use o método Docker: `./gerar_pdf_com_docker.sh`
- Ou instale pandoc localmente

### Erro: "LaTeX não encontrado"
- O script Docker já inclui LaTeX
- Para instalação local: `brew install basictex` (macOS)

### PDF muito grande
- O PDF gerado tem aproximadamente 0.2-0.5 MB
- Se necessário, ajuste as margens no script `gerar_pdf_manual.py`

