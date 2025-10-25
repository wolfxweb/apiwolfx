#!/usr/bin/env python3
"""
Teste dos elementos HTML da seção de custos
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_html_elements():
    """Teste dos elementos HTML"""
    print("🧪 Teste dos Elementos HTML da Seção de Custos")
    print("=" * 60)
    
    # Elementos que devem existir
    required_elements = [
        'gross-revenue',
        'ml-fees-value',
        'ml-fees-percent',
        'shipping-fees-value',
        'shipping-fees-percent',
        'discounts-value',
        'discounts-percent',
        'product-cost-value',
        'product-cost-percent',
        'taxes-value',
        'taxes-percent',
        'other-costs-value',
        'other-costs-detail',
        'marketing-value',
        'marketing-percent',
        'total-costs-value',
        'total-costs-percent',
        'net-profit-value',
        'net-profit-margin',
        'avg-profit-value',
        'avg-profit-detail'
    ]
    
    print(f"📋 Elementos necessários: {len(required_elements)}")
    for element in required_elements:
        print(f"   🔍 {element}")
    
    # Ler o arquivo HTML
    html_file = "/Users/wolfx/Documents/wolfx/apiwolfx/app/views/templates/ads_analytics_dashboard.html"
    
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"\n📊 Verificando elementos no arquivo HTML:")
        found_elements = []
        missing_elements = []
        
        for element in required_elements:
            if f'id="{element}"' in content:
                found_elements.append(element)
                print(f"   ✅ {element} - ENCONTRADO")
            else:
                missing_elements.append(element)
                print(f"   ❌ {element} - NÃO ENCONTRADO")
        
        print(f"\n📈 Resumo:")
        print(f"   ✅ Elementos encontrados: {len(found_elements)}")
        print(f"   ❌ Elementos faltando: {len(missing_elements)}")
        
        if missing_elements:
            print(f"\n❌ Elementos faltando:")
            for element in missing_elements:
                print(f"   - {element}")
        else:
            print(f"\n✅ Todos os elementos HTML estão presentes!")
        
        return {
            "success": True,
            "found_elements": len(found_elements),
            "missing_elements": len(missing_elements),
            "missing_list": missing_elements
        }
    
    except Exception as e:
        print(f"❌ Erro ao ler arquivo HTML: {e}")
        return {"success": False, "error": str(e)}

def main():
    """Função principal"""
    print("🧪 Teste dos Elementos HTML da Seção de Custos")
    print("=" * 60)
    print()
    
    result = test_html_elements()
    
    print("\n" + "=" * 60)
    if result and result.get("success"):
        if result.get("missing_elements", 0) == 0:
            print("✅ TODOS OS ELEMENTOS HTML ESTÃO PRESENTES!")
            print("💡 O problema pode estar em:")
            print("   🔍 JavaScript não executando")
            print("   🔍 Dados não chegando do backend")
            print("   🔍 Erro na função updateCostsAndMargins")
            print("   🔍 Console do navegador com erros")
        else:
            print("❌ ELEMENTOS HTML FALTANDO!")
            print(f"📊 Elementos faltando: {result.get('missing_elements', 0)}")
            print("💡 Adicionar os elementos faltantes no HTML")
    else:
        print("❌ Erro na verificação!")
        if result:
            print(f"Erro: {result.get('error', 'Desconhecido')}")

if __name__ == "__main__":
    main()
