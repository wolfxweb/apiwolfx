#!/usr/bin/env python3
"""
Verificar se baixamos a fatura atual que está aberta
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from sqlalchemy import text
from datetime import datetime

def check_open_invoice():
    """Verificar fatura atual em aberto"""
    print("🔍 Verificando Fatura Atual em Aberto")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # 1. Verificar fatura atual (is_current = true)
        print(f"\n📊 1. Fatura Atual em Aberto:")
        result = db.execute(text("""
            SELECT 
                id,
                period_from,
                period_to,
                advertising_cost,
                sale_fees,
                shipping_fees,
                total_amount,
                unpaid_amount,
                paid_amount,
                is_current,
                is_closed,
                last_sync
            FROM ml_billing_periods 
            WHERE company_id = :company_id
            AND is_current = true
            ORDER BY period_from DESC
        """), {"company_id": company_id})
        
        current_invoices = result.fetchall()
        
        if current_invoices:
            print(f"   ✅ Faturas atuais encontradas: {len(current_invoices)}")
            for invoice in current_invoices:
                print(f"\n   📅 Fatura ID {invoice.id}:")
                print(f"      📅 Período: {invoice.period_from} a {invoice.period_to}")
                print(f"      🎯 Marketing: R$ {invoice.advertising_cost:.2f}")
                print(f"      💳 Sale Fees: R$ {invoice.sale_fees:.2f}")
                print(f"      🚚 Shipping: R$ {invoice.shipping_fees:.2f}")
                print(f"      💰 Total: R$ {invoice.total_amount:.2f}")
                print(f"      💳 Pago: R$ {invoice.paid_amount:.2f}")
                print(f"      💸 Em aberto: R$ {invoice.unpaid_amount:.2f}")
                print(f"      📊 Fechado: {invoice.is_closed}")
                print(f"      🔄 Última sync: {invoice.last_sync}")
        else:
            print(f"   ❌ Nenhuma fatura atual encontrada")
        
        # 2. Verificar faturas não fechadas
        print(f"\n📊 2. Faturas Não Fechadas:")
        result = db.execute(text("""
            SELECT 
                id,
                period_from,
                period_to,
                advertising_cost,
                total_amount,
                unpaid_amount,
                is_closed,
                last_sync
            FROM ml_billing_periods 
            WHERE company_id = :company_id
            AND is_closed = false
            ORDER BY period_from DESC
        """), {"company_id": company_id})
        
        open_invoices = result.fetchall()
        
        if open_invoices:
            print(f"   ✅ Faturas em aberto encontradas: {len(open_invoices)}")
            for invoice in open_invoices:
                print(f"\n   📅 Fatura ID {invoice.id}:")
                print(f"      📅 Período: {invoice.period_from} a {invoice.period_to}")
                print(f"      🎯 Marketing: R$ {invoice.advertising_cost:.2f}")
                print(f"      💰 Total: R$ {invoice.total_amount:.2f}")
                print(f"      💸 Em aberto: R$ {invoice.unpaid_amount:.2f}")
                print(f"      🔄 Última sync: {invoice.last_sync}")
        else:
            print(f"   ❌ Nenhuma fatura em aberto encontrada")
        
        # 3. Verificar última sincronização
        print(f"\n📊 3. Última Sincronização:")
        result = db.execute(text("""
            SELECT 
                MAX(last_sync) as last_sync,
                COUNT(*) as total_periods
            FROM ml_billing_periods 
            WHERE company_id = :company_id
        """), {"company_id": company_id})
        
        sync_info = result.fetchone()
        if sync_info:
            print(f"   🔄 Última sync: {sync_info.last_sync}")
            print(f"   📊 Total de períodos: {sync_info.total_periods}")
        
        # 4. Verificar se há dados recentes (últimos 7 dias)
        print(f"\n📊 4. Dados Recentes (Últimos 7 dias):")
        from datetime import timedelta
        recent_date = datetime.now() - timedelta(days=7)
        
        result = db.execute(text("""
            SELECT 
                COUNT(*) as recent_periods,
                SUM(advertising_cost) as recent_marketing,
                SUM(total_amount) as recent_total
            FROM ml_billing_periods 
            WHERE company_id = :company_id
            AND last_sync >= :recent_date
        """), {
            "company_id": company_id,
            "recent_date": recent_date
        })
        
        recent_data = result.fetchone()
        if recent_data and recent_data.recent_periods > 0:
            print(f"   ✅ Dados recentes encontrados:")
            print(f"      📅 Períodos recentes: {recent_data.recent_periods}")
            print(f"      🎯 Marketing recente: R$ {recent_data.recent_marketing:.2f}")
            print(f"      💰 Total recente: R$ {recent_data.recent_total:.2f}")
        else:
            print(f"   ⚠️  Nenhum dado recente encontrado")
            print(f"      📅 Buscando dados desde: {recent_date.strftime('%Y-%m-%d')}")
        
        return {
            "success": True,
            "current_invoices": len(current_invoices),
            "open_invoices": len(open_invoices),
            "has_recent_data": recent_data and recent_data.recent_periods > 0
        }
    
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
    finally:
        db.close()

def main():
    """Função principal"""
    print("🔍 Verificando Fatura Atual em Aberto")
    print("=" * 60)
    print()
    
    result = check_open_invoice()
    
    print("\n" + "=" * 60)
    if result and result.get("success"):
        print("✅ Verificação concluída!")
        print(f"📊 Faturas atuais: {result.get('current_invoices', 0)}")
        print(f"📊 Faturas em aberto: {result.get('open_invoices', 0)}")
        print(f"📊 Dados recentes: {'Sim' if result.get('has_recent_data') else 'Não'}")
        
        if result.get('current_invoices', 0) > 0:
            print("\n🎉 FATURA ATUAL EM ABERTO ENCONTRADA!")
            print("✅ Sistema baixou dados da fatura atual")
        else:
            print("\n⚠️  NENHUMA FATURA ATUAL ENCONTRADA!")
            print("💡 Pode ser necessário sincronizar novamente")
    else:
        print("❌ Erro na verificação!")

if __name__ == "__main__":
    main()
