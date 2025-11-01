#!/usr/bin/env python3
"""
Script de teste para verificar todas as informações retornadas pela API de highlights
"""
import sys
import os
import json
import requests
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from app.models.saas_models import User, MLAccount
from app.services.token_manager import TokenManager
from app.services.highlights_service import HighlightsService

def print_section(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def print_dict(data, indent=0):
    """Imprime dicionário de forma formatada"""
    prefix = "  " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            print(f"{prefix}{key}:")
            print_dict(value, indent + 1)
        elif isinstance(value, list):
            print(f"{prefix}{key}: [lista com {len(value)} itens]")
            if len(value) > 0 and isinstance(value[0], dict):
                print(f"{prefix}  Primeiro item:")
                print_dict(value[0], indent + 2)
        else:
            print(f"{prefix}{key}: {value}")

def test_raw_api(access_token, site_id, category_id):
    """Testa a API raw do Mercado Livre"""
    print_section(f"1. TESTE DIRETO DA API DO MERCADO LIVRE")
    
    base_url = "https://api.mercadolibre.com"
    url = f"{base_url}/highlights/{site_id}/category/{category_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    print(f"URL: {url}")
    print(f"Headers: {dict((k, v[:50] + '...' if len(str(v)) > 50 else v) for k, v in headers.items())}")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\nResposta completa da API:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            print_section("Estrutura da Resposta")
            print(f"query_data: {data.get('query_data', {})}")
            content = data.get('content', [])
            print(f"\nTotal de itens retornados: {len(content)}")
            
            if content:
                print("\nPrimeiro item (raw):")
                print_dict(content[0])
                
                # Agrupar por tipo
                by_type = {}
                for item in content:
                    item_type = item.get('type', 'UNKNOWN')
                    if item_type not in by_type:
                        by_type[item_type] = []
                    by_type[item_type].append(item)
                
                print("\nDistribuição por tipo:")
                for item_type, items in by_type.items():
                    print(f"  {item_type}: {len(items)} itens")
                    if items:
                        print(f"    Exemplo ID: {items[0].get('id')}")
        else:
            print(f"Erro: {response.status_code}")
            print(response.text[:500])
            
    except Exception as e:
        print(f"Erro ao testar API: {e}")
        import traceback
        traceback.print_exc()

def test_search_api(item_ids, site_id):
    """Testa a API de search para buscar detalhes dos itens"""
    print_section(f"2. TESTE DA API DE SEARCH (Busca Pública)")
    
    base_url = "https://api.mercadolibre.com"
    
    # Testar com até 5 itens
    test_ids = item_ids[:5]
    ids_param = ",".join(test_ids)
    
    url = f"{base_url}/sites/{site_id}/search"
    params = {"ids": ids_param}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    print(f"URL: {url}")
    print(f"Parâmetros: {params}")
    print(f"IDs sendo testados: {test_ids}")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"\nTotal de resultados retornados: {len(results)}")
            
            for idx, item in enumerate(results, 1):
                print_section(f"Item {idx} do Search (ID: {item.get('id')})")
                print_dict(item)
        else:
            print(f"Erro: {response.status_code}")
            print(response.text[:500])
            
    except Exception as e:
        print(f"Erro ao testar Search API: {e}")
        import traceback
        traceback.print_exc()

def test_items_api(item_ids, access_token):
    """Testa a API /items para buscar detalhes"""
    print_section(f"3. TESTE DA API /ITEMS (Com Token)")
    
    base_url = "https://api.mercadolibre.com"
    
    # Testar com até 5 itens
    test_ids = item_ids[:5]
    ids_param = ",".join(test_ids)
    
    url = f"{base_url}/items"
    params = {"ids": ids_param}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    print(f"URL: {url}")
    print(f"Parâmetros: {params}")
    print(f"IDs sendo testados: {test_ids}")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nTotal de itens retornados: {len(data) if isinstance(data, list) else 'N/A'}")
            
            if isinstance(data, list):
                for idx, item in enumerate(data, 1):
                    if isinstance(item, dict) and "code" not in item:
                        print_section(f"Item {idx} do /items (ID: {item.get('id')})")
                        print_dict(item)
                    else:
                        print(f"\nItem {idx} (erro ou formato diferente):")
                        print_dict(item if isinstance(item, dict) else {"raw": str(item)})
            else:
                print("\nResposta (formato não list):")
                print_dict(data)
        else:
            print(f"Erro: {response.status_code}")
            print(response.text[:500])
            
    except Exception as e:
        print(f"Erro ao testar /items API: {e}")
        import traceback
        traceback.print_exc()

def test_service(access_token, site_id, category_id):
    """Testa o serviço HighlightsService"""
    print_section(f"4. TESTE DO HIGHLIGHTS SERVICE")
    
    db = SessionLocal()
    try:
        # Buscar um usuário para usar no serviço
        user = db.query(User).filter(User.company_id == 15).first()
        if not user:
            print("Erro: Usuário não encontrado para company_id 15")
            return
        
        service = HighlightsService(db)
        result = service.get_category_highlights(category_id, user.id)
        
        print(f"\nSucesso: {result.get('success')}")
        print(f"Total de highlights: {result.get('total', 0)}")
        
        if result.get('success'):
            highlights = result.get('highlights', [])
            print(f"\nProcessados {len(highlights)} highlights")
            
            # Agrupar por tipo
            by_type = {}
            for highlight in highlights:
                item_type = highlight.get('type', 'UNKNOWN')
                if item_type not in by_type:
                    by_type[item_type] = []
                by_type[item_type].append(highlight)
            
            print("\nDistribuição por tipo (após processamento):")
            for item_type, items in by_type.items():
                print(f"\n  {item_type}: {len(items)} itens")
                
                # Mostrar exemplo completo
                if items:
                    example = items[0]
                    print(f"\n  Exemplo completo (primeiro {item_type}):")
                    print_dict(example)
                    
                    # Verificar campos preenchidos
                    filled_fields = {k: v for k, v in example.items() if v and v != 0 and v != ""}
                    empty_fields = {k: v for k, v in example.items() if not v or v == 0 or v == ""}
                    
                    print(f"\n  Campos PREENCHIDOS ({len(filled_fields)}):")
                    for k, v in filled_fields.items():
                        if isinstance(v, str) and len(v) > 100:
                            print(f"    {k}: {v[:100]}...")
                        else:
                            print(f"    {k}: {v}")
                    
                    print(f"\n  Campos VAZIOS ({len(empty_fields)}):")
                    for k, v in empty_fields.items():
                        print(f"    {k}: {v}")
        else:
            print(f"Erro: {result.get('error')}")
            
    except Exception as e:
        print(f"Erro ao testar serviço: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def main():
    """Função principal"""
    print_section("TESTE COMPLETO - API HIGHLIGHTS MERCADO LIVRE")
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    db = SessionLocal()
    try:
        # Buscar usuário e token
        user = db.query(User).filter(User.company_id == 15).first()
        if not user:
            print("Erro: Usuário não encontrado para company_id 15")
            return
        
        # Buscar conta ML ativa
        ml_account = db.query(MLAccount).filter(
            MLAccount.company_id == 15,
            MLAccount.status == "ACTIVE"
        ).first()
        
        if not ml_account:
            print("Erro: Conta ML ativa não encontrada")
            return
        
        site_id = ml_account.site_id or "MLB"
        print(f"\nSite ID: {site_id}")
        print(f"ML User ID: {ml_account.ml_user_id}")
        
        # Obter token
        token_manager = TokenManager(db)
        access_token = token_manager.get_valid_token(user.id)
        
        if not access_token:
            print("Erro: Token não encontrado")
            return
        
        print(f"Token obtido: {access_token[:20]}...")
        
        # Usar uma categoria de teste (Acessórios para Veículos -> Acessórios de Carros)
        category_id = "MLB1747"  # Acessórios de Carros e Caminhonetes
        
        print(f"\nCategoria de teste: {category_id}")
        print("(Acessórios de Carros e Caminhonetes)")
        
        # 1. Testar API raw
        test_raw_api(access_token, site_id, category_id)
        
        # Obter IDs dos itens retornados
        base_url = "https://api.mercadolibre.com"
        url = f"{base_url}/highlights/{site_id}/category/{category_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            content = data.get('content', [])
            item_ids = [item.get('id') for item in content if item.get('id')]
            
            # Separar por tipo
            item_ids_only = [item.get('id') for item in content if item.get('type') in ['ITEM', 'USER_PRODUCT']]
            
            if item_ids_only:
                # 2. Testar Search API
                test_search_api(item_ids_only, site_id)
                
                # 3. Testar Items API
                test_items_api(item_ids_only, access_token)
        
        # 4. Testar Service
        test_service(access_token, site_id, category_id)
        
        print_section("TESTE CONCLUÍDO")
        
    except Exception as e:
        print(f"Erro geral: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()

