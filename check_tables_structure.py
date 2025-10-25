#!/usr/bin/env python3
"""
Verificar estrutura das tabelas de billing
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from sqlalchemy import text

def check_tables_structure():
    """Verificar estrutura das tabelas"""
    print("🔍 Verificando Estrutura das Tabelas")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # 1. Verificar se as tabelas existem
        print(f"\n📊 1. Verificando Existência das Tabelas:")
        
        # Verificar ml_billing_periods
        try:
            result = db.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'ml_billing_periods'
                ORDER BY ordinal_position
            """))
            columns = result.fetchall()
            print(f"   📅 Tabela ml_billing_periods:")
            for col in columns:
                print(f"      - {col.column_name}: {col.data_type}")
        except Exception as e:
            print(f"   ❌ Erro ao verificar ml_billing_periods: {e}")
        
        # Verificar ml_billing_charges
        try:
            result = db.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'ml_billing_charges'
                ORDER BY ordinal_position
            """))
            columns = result.fetchall()
            print(f"   💳 Tabela ml_billing_charges:")
            for col in columns:
                print(f"      - {col.column_name}: {col.data_type}")
        except Exception as e:
            print(f"   ❌ Erro ao verificar ml_billing_charges: {e}")
        
        # 2. Verificar dados simples
        print(f"\n📊 2. Verificando Dados Simples:")
        
        # Contar registros em ml_billing_periods
        try:
            result = db.execute(text("SELECT COUNT(*) as count FROM ml_billing_periods"))
            count = result.fetchone().count
            print(f"   📅 Total de períodos: {count}")
        except Exception as e:
            print(f"   ❌ Erro ao contar períodos: {e}")
        
        # Contar registros em ml_billing_charges
        try:
            result = db.execute(text("SELECT COUNT(*) as count FROM ml_billing_charges"))
            count = result.fetchone().count
            print(f"   💳 Total de cobranças: {count}")
        except Exception as e:
            print(f"   ❌ Erro ao contar cobranças: {e}")
        
        # 3. Verificar dados de ML Orders
        print(f"\n📊 3. Verificando ML Orders:")
        
        try:
            result = db.execute(text("""
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(COALESCE(advertising_cost, 0)) as total_advertising,
                    SUM(COALESCE(sale_fees, 0)) as total_sale_fees,
                    SUM(COALESCE(shipping_cost, 0)) as total_shipping
                FROM ml_orders 
                WHERE company_id = 15
                AND date_created >= CURRENT_DATE - INTERVAL '30 days'
            """))
            
            orders_data = result.fetchone()
            print(f"   📦 Total de pedidos (30 dias): {orders_data.total_orders}")
            print(f"   🎯 Marketing total: R$ {orders_data.total_advertising:.2f}")
            print(f"   💳 Sale Fees total: R$ {orders_data.total_sale_fees:.2f}")
            print(f"   🚚 Shipping total: R$ {orders_data.total_shipping:.2f}")
            
        except Exception as e:
            print(f"   ❌ Erro ao verificar pedidos: {e}")
        
        return {"success": True}
    
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
    finally:
        db.close()

def main():
    """Função principal"""
    print("🔍 Verificando Estrutura das Tabelas")
    print("=" * 60)
    print()
    
    result = check_tables_structure()
    
    print("\n" + "=" * 60)
    if result and result.get("success"):
        print("✅ Verificação concluída!")
    else:
        print("❌ Erro na verificação!")

if __name__ == "__main__":
    main()
