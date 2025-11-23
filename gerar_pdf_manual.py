#!/usr/bin/env python3
"""
Script para gerar PDF único a partir de todos os arquivos Markdown dos manuais
"""
import os
import subprocess
import sys
from pathlib import Path

# Lista de arquivos na ordem correta
ARQUIVOS_MD = [
    "Manuais/00_INDICE_GERAL.md",
    "Manuais/01_Login_e_Registro.md",
    "Manuais/02_Perfil_do_Usuario.md",
    "Manuais/03_Dashboard_Principal.md",
    "Manuais/04_Planos_e_Assinaturas.md",
    "Manuais/06_Produtos_Internos.md",
    "Manuais/07_Estoque.md",
    "Manuais/08_Fornecedores.md",
    "Manuais/09_Ordem_de_Compra.md",
    "Manuais/10_Dashboard_ML.md",
    "Manuais/11_Anuncios_ML.md",
    "Manuais/12_Pedidos_ML.md",
    "Manuais/13_Publicidade_ML.md",
    "Manuais/14_Mais_Vendidos_ML.md",
    "Manuais/15_Contas_ML.md",
    "Manuais/16_Dashboard_Financeiro.md",
    "Manuais/17_Contas_a_Receber.md",
    "Manuais/18_Contas_a_Pagar.md",
    "Manuais/19_Fluxo_de_Caixa.md",
    "Manuais/20_Categorias_Financeiras.md",
    "Manuais/21_Centros_de_Custo.md",
    "Manuais/22_Contas_Bancarias.md",
    "Manuais/23_Chat_IA.md",
    "Manuais/24_Perguntas_ML.md",
    "Manuais/25_Pos_Venda_ML.md",
    "Manuais/adm/26_Planejamento_Financeiro.md",
    "Manuais/adm/27_Painel_Administrativo.md",
]

BASE_DIR = Path(__file__).parent
OUTPUT_MD = BASE_DIR / "Manual_Completo_Temp.md"
OUTPUT_PDF = BASE_DIR / "Manual_Completo_CELX.pdf"


def combinar_arquivos():
    """Combina todos os arquivos Markdown em um único arquivo"""
    print("📄 Combinando arquivos Markdown...")
    
    arquivos_encontrados = []
    arquivos_nao_encontrados = []
    
    with open(OUTPUT_MD, 'w', encoding='utf-8') as outfile:
        # Adicionar cabeçalho
        outfile.write("# Manual do Usuário - Sistema CELX\n\n")
        outfile.write("**Documentação Completa do Sistema**\n\n")
        outfile.write("---\n\n")
        
        for arquivo in ARQUIVOS_MD:
            filepath = BASE_DIR / arquivo
            if filepath.exists():
                arquivos_encontrados.append(arquivo)
                print(f"  ✓ {arquivo}")
                
                # Adicionar título do capítulo
                nome_capitulo = filepath.stem.replace('_', ' ').title()
                outfile.write(f"\n\n# {nome_capitulo}\n\n")
                outfile.write("---\n\n")
                
                # Ler e escrever conteúdo
                with open(filepath, 'r', encoding='utf-8') as infile:
                    conteudo = infile.read()
                    # Remover título principal se existir (já adicionamos acima)
                    linhas = conteudo.split('\n')
                    if linhas and linhas[0].startswith('#'):
                        linhas = linhas[1:]  # Pular primeira linha se for título
                    outfile.write('\n'.join(linhas))
                
                # Adicionar quebra de página
                outfile.write("\n\n\\newpage\n\n")
            else:
                arquivos_nao_encontrados.append(arquivo)
                print(f"  ✗ {arquivo} (não encontrado)")
    
    print(f"\n✅ Arquivo combinado criado: {OUTPUT_MD}")
    print(f"   Arquivos encontrados: {len(arquivos_encontrados)}")
    if arquivos_nao_encontrados:
        print(f"   Arquivos não encontrados: {len(arquivos_nao_encontrados)}")
    
    return len(arquivos_encontrados) > 0


def verificar_pandoc():
    """Verifica se pandoc está instalado"""
    try:
        result = subprocess.run(['pandoc', '--version'], 
                              capture_output=True, 
                              text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def converter_com_pandoc():
    """Converte Markdown para PDF usando pandoc"""
    print("\n🔄 Convertendo para PDF usando pandoc...")
    
    try:
        cmd = [
            'pandoc',
            str(OUTPUT_MD),
            '-o', str(OUTPUT_PDF),
            '--pdf-engine=xelatex',
            '--toc',
            '--toc-depth=2',
            '-V', 'geometry:margin=2.5cm',
            '-V', 'fontsize=11pt',
            '-V', 'documentclass=article',
            '-V', 'colorlinks=true',
            '-V', 'linkcolor=blue',
            '--highlight-style=tango',
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ PDF gerado com sucesso: {OUTPUT_PDF}")
            print(f"   Tamanho: {OUTPUT_PDF.stat().st_size / 1024 / 1024:.2f} MB")
            return True
        else:
            print(f"❌ Erro ao gerar PDF:")
            print(result.stderr)
            return False
            
    except FileNotFoundError:
        print("❌ pandoc não encontrado. Tentando instalar...")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def converter_com_python():
    """Converte Markdown para PDF usando bibliotecas Python"""
    print("\n🔄 Convertendo para PDF usando bibliotecas Python...")
    
    try:
        # Tentar usar markdown2pdf
        try:
            from markdown2pdf import convert_markdown_to_pdf
            convert_markdown_to_pdf(str(OUTPUT_MD), str(OUTPUT_PDF))
            print(f"✅ PDF gerado com sucesso: {OUTPUT_PDF}")
            return True
        except ImportError:
            pass
        
        # Tentar usar weasyprint
        try:
            import markdown
            from weasyprint import HTML, CSS
            
            with open(OUTPUT_MD, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
            
            # Adicionar CSS básico
            html_doc = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    @page {{
                        size: A4;
                        margin: 2.5cm;
                    }}
                    body {{
                        font-family: Arial, sans-serif;
                        font-size: 11pt;
                        line-height: 1.6;
                    }}
                    h1 {{
                        page-break-before: always;
                        border-bottom: 2px solid #333;
                        padding-bottom: 10px;
                    }}
                    h2 {{
                        margin-top: 30px;
                        border-bottom: 1px solid #ccc;
                        padding-bottom: 5px;
                    }}
                    code {{
                        background-color: #f4f4f4;
                        padding: 2px 5px;
                        border-radius: 3px;
                    }}
                    pre {{
                        background-color: #f4f4f4;
                        padding: 10px;
                        border-radius: 5px;
                        overflow-x: auto;
                    }}
                </style>
            </head>
            <body>
            {html_content}
            </body>
            </html>
            """
            
            HTML(string=html_doc).write_pdf(OUTPUT_PDF)
            print(f"✅ PDF gerado com sucesso: {OUTPUT_PDF}")
            return True
            
        except ImportError:
            print("❌ Bibliotecas necessárias não encontradas.")
            print("   Instale com: pip install markdown weasyprint")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao gerar PDF: {e}")
        return False


def main():
    """Função principal"""
    print("=" * 60)
    print("📚 Gerador de PDF - Manual do Sistema CELX")
    print("=" * 60)
    
    # Combinar arquivos
    if not combinar_arquivos():
        print("\n❌ Nenhum arquivo encontrado. Verifique os caminhos.")
        sys.exit(1)
    
    # Tentar converter com pandoc primeiro
    if verificar_pandoc():
        if converter_com_pandoc():
            # Limpar arquivo temporário
            if OUTPUT_MD.exists():
                OUTPUT_MD.unlink()
            print("\n🎉 Processo concluído com sucesso!")
            sys.exit(0)
    
    # Se pandoc não funcionou, tentar com Python
    print("\n⚠️  pandoc não disponível. Tentando método alternativo...")
    if converter_com_python():
        # Limpar arquivo temporário
        if OUTPUT_MD.exists():
            OUTPUT_MD.unlink()
        print("\n🎉 Processo concluído com sucesso!")
        sys.exit(0)
    
    # Se nenhum método funcionou
    print("\n❌ Não foi possível gerar o PDF.")
    print("\nOpções:")
    print("1. Instale pandoc: brew install pandoc basictex (macOS)")
    print("2. Ou instale bibliotecas Python: pip install markdown weasyprint")
    print(f"\nArquivo Markdown combinado disponível em: {OUTPUT_MD}")
    print("Você pode convertê-lo manualmente usando pandoc ou outra ferramenta.")
    sys.exit(1)


if __name__ == "__main__":
    main()

