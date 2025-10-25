#!/usr/bin/env python3
"""
Verificar dados de billing no banco
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from sqlalchemy import text

def check_billing_data():
    """Verificar dados de billing no banco"""
    print("🔍 Verificando Dados de Billing no Banco")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # 1. Verificar se as tabelas existem
        print(f"\n📊 1. Verificando Tabelas:")
        
        # Verificar ml_billing_periods
        try:
            result = db.execute(text("""
                SELECT COUNT(*) as count 
                FROM ml_billing_periods 
                WHERE company_id = :company_id
            """), {"company_id": company_id})
            periods_count = result.fetchone().count
            print(f"   📅 Períodos de billing: {periods_count}")
        except Exception as e:
            print(f"   ❌ Erro ao verificar períodos: {e}")
            periods_count = 0
        
        # Verificar ml_billing_charges
        try:
            result = db.execute(text("""
                SELECT COUNT(*) as count 
                FROM ml_billing_charges 
                WHERE company_id = :company_id
            """), {"company_id": company_id})
            charges_count = result.fetchone().count
            print(f"   💳 Cobranças de billing: {charges_count}")
        except Exception as e:
            print(f"   ❌ Erro ao verificar cobranças: {e}")
            charges_count = 0
        
        # 2. Verificar dados recentes
        if periods_count > 0:
            print(f"\n📊 2. Dados Recentes:")
            
            # Últimos períodos
            result = db.execute(text("""
                SELECT 
                    period_from,
                    period_to,
                    total_amount,
                    advertising_cost,
                    sale_fees,
                    shipping_fees
                FROM ml_billing_periods 
                WHERE company_id = :company_id
                ORDER BY period_from DESC
                LIMIT 5
            """), {"company_id": company_id})
            
            periods = result.fetchall()
            for period in periods:
                print(f"   📅 {period.period_from} a {period.period_to}")
                print(f"      💰 Total: R$ {period.total_amount:.2f}")
                print(f"      🎯 Marketing: R$ {period.advertising_cost:.2f}")
                print(f"      💳 Sale Fees: R$ {period.sale_fees:.2f}")
                print(f"      🚚 Shipping: R$ {period.shipping_fees:.2f}")
        
        # 3. Verificar se há dados de ML Orders
        print(f"\n📊 3. Dados de ML Orders:")
        
        try:
            result = db.execute(text("""
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(advertising_cost) as total_advertising,
                    SUM(sale_fees) as total_sale_fees,
                    SUM(shipping_cost) as total_shipping
                FROM ml_orders 
                WHERE company_id = :company_id
                AND date_created >= CURRENT_DATE - INTERVAL '30 days'
            """), {"company_id": company_id})
            
            orders_data = result.fetchone()
            print(f"   📦 Total de pedidos (30 dias): {orders_data.total_orders}")
            print(f"   🎯 Marketing total: R$ {orders_data.total_advertising:.2f}")
            print(f"   💳 Sale Fees total: R$ {orders_data.total_sale_fees:.2f}")
            print(f"   🚚 Shipping total: R$ {orders_data.total_shipping:.2f}")
            
        except Exception as e:
            print(f"   ❌ Erro ao verificar pedidos: {e}")
        
        return {
            "success": True,
            "periods_count": periods_count,
            "charges_count": charges_count,
            "has_billing_data": periods_count > 0 or charges_count > 0
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
    print("🔍 Verificando Dados de Billing no Banco")
    print("=" * 60)
    print()
    
    result = check_billing_data()
    
    print("\n" + "=" * 60)
    if result and result.get("success"):
        print("📊 RESUMO DOS DADOS:")
        print(f"📅 Períodos de billing: {result.get('periods_count', 0)}")
        print(f"💳 Cobranças de billing: {result.get('charges_count', 0)}")
        print(f"🎯 Tem dados de billing: {'Sim' if result.get('has_billing_data') else 'Não'}")
        
        if not result.get('has_billing_data'):
            print("\n💡 POSSÍVEIS CAUSAS:")
            print("   - Cron job de billing não executou ainda")
            print("   - Dados de billing não foram sincronizados")
            print("   - Sistema usando estimativas em vez de dados reais")
            print("\n🔧 SOLUÇÕES:")
            print("   - Executar sincronização manual de billing")
            print("   - Verificar configuração do cron job")
            print("   - Verificar tokens de acesso do Mercado Livre")
    else:
        print("❌ Erro ao verificar dados!")

if __name__ == "__main__":
    main()
