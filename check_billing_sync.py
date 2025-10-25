#!/usr/bin/env python3
"""
Verificar se o cron job de billing está funcionando e baixando dados atualizados
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from sqlalchemy import text
from datetime import datetime, timedelta
import subprocess
import os

def check_billing_sync():
    """Verificar se o cron job de billing está funcionando"""
    print("🔍 Verificando Sincronização de Billing")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Verificar logs de billing
        print("📊 Teste 1: Verificar Logs de Billing")
        print("-" * 40)
        
        log_files = [
            'app/logs/billing_sync_test.log',
            'app/logs/company_15.log',
            'app/logs/system.log'
        ]
        
        for log_file in log_files:
            if os.path.exists(log_file):
                print(f"   📄 {log_file}:")
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-5:]:  # Últimas 5 linhas
                        print(f"      {line.strip()}")
            else:
                print(f"   ❌ {log_file}: Não encontrado")
        
        # Verificar dados mais recentes
        print(f"\n📊 Teste 2: Dados Mais Recentes")
        print("-" * 40)
        
        result = db.execute(text("""
            SELECT 
                period_from,
                period_to,
                advertising_cost,
                sale_fees,
                shipping_fees,
                is_closed,
                created_at,
                updated_at
            FROM ml_billing_periods 
            WHERE company_id = :company_id
            ORDER BY created_at DESC, updated_at DESC, period_from DESC
            LIMIT 5
        """), {
            "company_id": company_id
        })
        
        billing_data = result.fetchall()
        
        if billing_data:
            print(f"   📊 Períodos mais recentes:")
            for row in billing_data:
                print(f"      📅 {row.period_from} a {row.period_to}")
                print(f"         💰 Marketing: R$ {float(row.advertising_cost or 0):.2f}")
                print(f"         💰 Sale Fees: R$ {float(row.sale_fees or 0):.2f}")
                print(f"         💰 Shipping: R$ {float(row.shipping_fees or 0):.2f}")
                print(f"         🔒 Fechado: {row.is_closed}")
                print(f"         📅 Criado: {row.created_at}")
                print(f"         📅 Atualizado: {row.updated_at}")
                print()
        else:
            print(f"   ❌ Nenhum período de billing encontrado")
        
        # Verificar se há períodos para o mês atual
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        print(f"📊 Teste 3: Períodos do Mês Atual ({current_month}/{current_year})")
        print("-" * 40)
        
        result_current = db.execute(text("""
            SELECT 
                period_from,
                period_to,
                advertising_cost,
                is_closed
            FROM ml_billing_periods 
            WHERE company_id = :company_id
            AND (
                EXTRACT(MONTH FROM period_from) = :month 
                OR EXTRACT(MONTH FROM period_to) = :month
            )
            AND EXTRACT(YEAR FROM period_from) = :year
            ORDER BY period_from DESC
        """), {
            "company_id": company_id,
            "month": current_month,
            "year": current_year
        })
        
        current_data = result_current.fetchall()
        
        if current_data:
            print(f"   ✅ Períodos encontrados para {current_month}/{current_year}:")
            for row in current_data:
                print(f"      📅 {row.period_from} a {row.period_to} - Marketing: R$ {float(row.advertising_cost or 0):.2f}")
        else:
            print(f"   ❌ Nenhum período encontrado para {current_month}/{current_year}")
            print(f"   💡 Sugestão: Executar cron job para baixar dados atualizados")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def main():
    """Função principal"""
    print("🔍 Verificando Sincronização de Billing")
    print("=" * 60)
    print()
    
    success = check_billing_sync()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ VERIFICAÇÃO CONCLUÍDA!")
        print("💡 Próximos passos:")
        print("   1. Executar cron job manualmente se necessário")
        print("   2. Verificar se dados estão sendo atualizados")
        print("   3. Corrigir lógica de filtro se necessário")
    else:
        print("❌ Erro na verificação!")

if __name__ == "__main__":
    main()
