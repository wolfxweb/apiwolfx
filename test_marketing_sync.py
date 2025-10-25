#!/usr/bin/env python3
"""
Script para testar a sincronização de custos de marketing.

Uso:
    python test_marketing_sync.py

Este script:
1. Testa a sincronização de custos de marketing
2. Mostra resultados detalhados
3. Pode ser usado para debug e validação
"""
import asyncio
import sys
import os
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import get_db
from app.services.marketing_costs_service import MarketingCostsService
from app.services.marketing_sync_job import MarketingSyncJob

async def test_marketing_sync():
    """Testa a sincronização de custos de marketing"""
    print("🚀 Iniciando teste de sincronização de custos de marketing")
    print("=" * 60)
    
    try:
        # Obter sessão do banco
        db = next(get_db())
        
        # Testar serviço de marketing
        marketing_service = MarketingCostsService(db)
        
        print("📊 Testando serviço de marketing...")
        
        # Buscar primeira empresa ativa para teste
        from app.models.saas_models import Company
        company = db.query(Company).filter(Company.is_active == True).first()
        
        if not company:
            print("❌ Nenhuma empresa ativa encontrada")
            return
        
        print(f"🏢 Testando com empresa: {company.name} (ID: {company.id})")
        
        # Testar sincronização (último mês)
        print("\n🔄 Executando sincronização (último mês)...")
        result = marketing_service.sync_marketing_costs_for_company(company.id, months=1)
        
        if result["success"]:
            print(f"✅ Sincronização bem-sucedida!")
            print(f"   💰 Custo total: R$ {result['total_cost']:.2f}")
            print(f"   📦 Pedidos atualizados: {result['orders_updated']}")
            print(f"   🏪 Contas processadas: {result['accounts_processed']}")
            
            if result.get("accounts_data"):
                print("\n📋 Detalhes por conta:")
                for account in result["accounts_data"]:
                    print(f"   • {account['nickname']}: R$ {account['total_cost']:.2f} / {account['orders_updated']} pedidos")
        else:
            print(f"❌ Erro na sincronização: {result.get('error', 'Erro desconhecido')}")
        
        # Testar resumo de marketing
        print("\n📈 Testando resumo de marketing...")
        summary = marketing_service.get_marketing_summary(company.id, months=3)
        
        if summary:
            print(f"✅ Resumo encontrado:")
            print(f"   💰 Custo total: R$ {summary['total_cost']:.2f}")
            print(f"   📦 Total de pedidos: {summary['total_orders']}")
            print(f"   📊 Custo médio por pedido: R$ {summary['average_cost_per_order']:.2f}")
            
            if summary.get("monthly_breakdown"):
                print("\n📅 Breakdown mensal:")
                for month, data in summary["monthly_breakdown"].items():
                    print(f"   • {month}: R$ {data['cost']:.2f} / {data['orders']} pedidos")
        
        # Testar job de sincronização
        print("\n🤖 Testando job de sincronização...")
        job = MarketingSyncJob()
        job_result = await job.run_sync_for_company(company.id, months=1)
        
        if job_result["success"]:
            print(f"✅ Job executado com sucesso!")
            print(f"   💰 Custo total: R$ {job_result['total_cost']:.2f}")
            print(f"   📦 Pedidos atualizados: {job_result['orders_updated']}")
        else:
            print(f"❌ Erro no job: {job_result.get('error', 'Erro desconhecido')}")
        
        print("\n" + "=" * 60)
        print("✅ Teste concluído com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()

async def test_all_companies_sync():
    """Testa sincronização para todas as empresas"""
    print("🚀 Testando sincronização para todas as empresas")
    print("=" * 60)
    
    try:
        job = MarketingSyncJob()
        result = await job.run_sync_for_all_companies(months=1)
        
        if result["success"]:
            print(f"✅ Sincronização concluída!")
            print(f"   🏢 Empresas processadas: {result['companies_processed']}")
            print(f"   💰 Custo total: R$ {result['total_cost']:.2f}")
            print(f"   📦 Total de pedidos: {result['total_orders']}")
            
            if result.get("companies_with_errors", 0) > 0:
                print(f"   ⚠️ Empresas com erro: {result['companies_with_errors']}")
                if result.get("errors"):
                    print("\n❌ Erros encontrados:")
                    for error in result["errors"]:
                        print(f"   • {error['company_name']}: {error['error']}")
        else:
            print(f"❌ Erro na sincronização: {result.get('error', 'Erro desconhecido')}")
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Função principal"""
    print("🧪 Teste de Sincronização de Custos de Marketing")
    print("=" * 60)
    print(f"⏰ Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Executar testes
    asyncio.run(test_marketing_sync())
    
    print("\n" + "=" * 60)
    print("🎯 Teste de uma empresa concluído!")
    print()
    
    # Perguntar se quer testar todas as empresas
    try:
        response = input("Deseja testar sincronização para todas as empresas? (s/N): ").strip().lower()
        if response in ['s', 'sim', 'y', 'yes']:
            print()
            asyncio.run(test_all_companies_sync())
    except KeyboardInterrupt:
        print("\n\n⏹️ Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
    
    print("\n🏁 Teste finalizado!")

if __name__ == "__main__":
    main()
