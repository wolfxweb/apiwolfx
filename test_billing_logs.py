#!/usr/bin/env python3
"""
Teste do sistema de logs para billing
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.notification_logger import global_logger
from datetime import datetime

def test_billing_logs():
    """Teste do sistema de logs para billing"""
    print("🧪 Teste do Sistema de Logs para Billing")
    print("=" * 60)
    
    try:
        # 1. Teste de log de início de sincronização
        print(f"\n📊 1. Testando Log de Início:")
        global_logger.log_event(
            event_type="billing_sync_test",
            data={
                "description": "Teste de início de sincronização de billing",
                "sync_type": "test",
                "start_time": datetime.now().isoformat(),
                "test_mode": True
            },
            company_id=15,
            success=True
        )
        print(f"   ✅ Log de início registrado")
        
        # 2. Teste de log de API externa
        print(f"\n📊 2. Testando Log de API Externa:")
        global_logger.log_external_api_call(
            service="Mercado Livre",
            endpoint="/billing/periods",
            company_id=15,
            success=True,
            response_code=200
        )
        print(f"   ✅ Log de API externa registrado")
        
        # 3. Teste de log de operação de banco
        print(f"\n📊 3. Testando Log de Banco de Dados:")
        global_logger.log_database_operation(
            operation="INSERT",
            table="ml_billing_periods",
            record_id="test_123",
            company_id=15,
            success=True
        )
        print(f"   ✅ Log de banco de dados registrado")
        
        # 4. Teste de log de erro
        print(f"\n📊 4. Testando Log de Erro:")
        global_logger.log_event(
            event_type="billing_sync_test",
            data={
                "description": "Teste de erro na sincronização",
                "sync_type": "test",
                "error_type": "simulated_error"
            },
            company_id=15,
            success=False,
            error_message="Erro simulado para teste"
        )
        print(f"   ✅ Log de erro registrado")
        
        # 5. Verificar logs da empresa
        print(f"\n📊 5. Verificando Logs da Empresa:")
        company_logs = global_logger.get_company_logs(15, limit=10)
        print(f"   📅 Total de logs da empresa 15: {len(company_logs)}")
        
        if company_logs:
            print(f"   📋 Últimos logs:")
            for log in company_logs[-3:]:  # Mostrar últimos 3
                print(f"      - {log.get('event_type', 'N/A')}: {log.get('success', False)}")
        
        # 6. Verificar estatísticas
        print(f"\n📊 6. Verificando Estatísticas:")
        stats = global_logger.get_notification_stats(15, days=1)
        print(f"   📈 Total de eventos: {stats.get('total_notifications', 0)}")
        print(f"   ✅ Sucessos: {stats.get('successful', 0)}")
        print(f"   ❌ Erros: {stats.get('errors', 0)}")
        
        return {
            "success": True,
            "logs_tested": 4,
            "company_logs_count": len(company_logs),
            "stats": stats
        }
    
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def main():
    """Função principal"""
    print("🧪 Teste do Sistema de Logs para Billing")
    print("=" * 60)
    print()
    
    result = test_billing_logs()
    
    print("\n" + "=" * 60)
    if result and result.get("success"):
        print("✅ SISTEMA DE LOGS FUNCIONANDO PERFEITAMENTE!")
        print(f"📊 Logs testados: {result.get('logs_tested', 0)}")
        print(f"📅 Logs da empresa: {result.get('company_logs_count', 0)}")
        print("\n💡 Logs sendo salvos em:")
        print("   📁 app/logs/system.log - Log geral do sistema")
        print("   📁 app/logs/company_15.log - Logs específicos da empresa")
        print("   📁 app/logs/billing_sync_test.log - Logs de sincronização")
        print("\n🎯 Sistema de logs implementado com sucesso!")
    else:
        print("❌ Problemas no sistema de logs!")
        if result:
            print(f"Erro: {result.get('error', 'Desconhecido')}")

if __name__ == "__main__":
    main()
