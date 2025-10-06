#!/usr/bin/env python3
"""
Script para testar a sincronização automática
"""
import sys
sys.path.append('/Users/wolfx/Documents/wolfx/apiwolfx')

from app.services.auto_sync_service import AutoSyncService

def test_auto_sync():
    """Testa a sincronização automática"""
    print("=== TESTE DE SINCRONIZAÇÃO AUTOMÁTICA ===\n")
    
    try:
        # Criar serviço
        auto_sync = AutoSyncService()
        
        # Testar sincronização
        print("🔄 Iniciando sincronização automática...")
        result = auto_sync.sync_today_orders()
        
        if result.get("success"):
            print("✅ Sincronização automática executada com sucesso!")
            print(f"📊 Resultado: {result.get('message', 'N/A')}")
            print(f"🏢 Contas processadas: {result.get('accounts_processed', 0)}")
            print(f"📦 Total de pedidos: {result.get('total_orders', 0)}")
        else:
            print(f"❌ Erro na sincronização: {result.get('error', 'Erro desconhecido')}")
        
        # Status do serviço
        print(f"\n📋 Status do serviço:")
        status = auto_sync.get_sync_status()
        print(f"   • Ativo: {status.get('service_active', False)}")
        print(f"   • Intervalo: {status.get('sync_interval_minutes', 0)} minutos")
        print(f"   • Última sync: {status.get('last_sync', 'N/A')}")
        print(f"   • Próxima sync: {status.get('next_sync_in_minutes', 0)} minutos")
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")

if __name__ == "__main__":
    test_auto_sync()
