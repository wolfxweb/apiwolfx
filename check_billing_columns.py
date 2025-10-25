#!/usr/bin/env python3
"""
Verificar colunas e dados salvos na tabela ml_billing_periods
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from sqlalchemy import text
from datetime import datetime

def check_billing_columns():
    """Verificar colunas e dados da tabela ml_billing_periods"""
    print("🔍 Verificando Colunas e Dados da Tabela ml_billing_periods")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        # 1. Verificar estrutura da tabela
        print("📊 1. ESTRUTURA DA TABELA ml_billing_periods")
        print("-" * 50)
        
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'ml_billing_periods'
            ORDER BY ordinal_position
        """))
        
        columns = result.fetchall()
        
        if columns:
            print("   📋 Colunas encontradas:")
            for col in columns:
                print(f"      🔹 {col.column_name}: {col.data_type} ({'NULL' if col.is_nullable == 'YES' else 'NOT NULL'})")
                if col.column_default:
                    print(f"         Default: {col.column_default}")
        else:
            print("   ❌ Tabela não encontrada!")
            return False
        
        # 2. Verificar dados salvos
        print(f"\n📊 2. DADOS SALVOS NA TABELA")
        print("-" * 50)
        
        result = db.execute(text("""
            SELECT 
                id,
                company_id,
                period_from,
                period_to,
                advertising_cost,
                sale_fees,
                shipping_fees,
                is_closed,
                created_at,
                updated_at
            FROM ml_billing_periods 
            ORDER BY period_from DESC
        """))
        
        billing_data = result.fetchall()
        
        if billing_data:
            print(f"   📊 Total de registros: {len(billing_data)}")
            print()
            
            for i, row in enumerate(billing_data, 1):
                print(f"   📅 Registro {i}:")
                print(f"      🆔 ID: {row.id}")
                print(f"      🏢 Company ID: {row.company_id}")
                print(f"      📅 Período: {row.period_from} a {row.period_to}")
                print(f"      💰 Marketing: R$ {float(row.advertising_cost or 0):.2f}")
                print(f"      💰 Sale Fees: R$ {float(row.sale_fees or 0):.2f}")
                print(f"      💰 Shipping: R$ {float(row.shipping_fees or 0):.2f}")
                print(f"      🔒 Fechado: {row.is_closed}")
                print(f"      📅 Criado: {row.created_at}")
                print(f"      📅 Atualizado: {row.updated_at}")
                print()
        else:
            print("   ❌ Nenhum dado encontrado!")
        
        # 3. Verificar tabela ml_billing_charges
        print(f"\n📊 3. TABELA ml_billing_charges")
        print("-" * 50)
        
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'ml_billing_charges'
            ORDER BY ordinal_position
        """))
        
        charges_columns = result.fetchall()
        
        if charges_columns:
            print("   📋 Colunas encontradas:")
            for col in charges_columns:
                print(f"      🔹 {col.column_name}: {col.data_type} ({'NULL' if col.is_nullable == 'YES' else 'NOT NULL'})")
        else:
            print("   ❌ Tabela ml_billing_charges não encontrada!")
        
        # 4. Verificar dados em ml_billing_charges
        result = db.execute(text("SELECT COUNT(*) as total FROM ml_billing_charges"))
        charges_count = result.fetchone()
        
        if charges_count:
            print(f"   📊 Total de registros em ml_billing_charges: {charges_count.total}")
        
        # 5. Verificar como os dados estão sendo salvos
        print(f"\n📊 4. ANÁLISE DOS DADOS SALVOS")
        print("-" * 50)
        
        if billing_data:
            # Agrupar por company_id
            companies = {}
            for row in billing_data:
                company_id = row.company_id
                if company_id not in companies:
                    companies[company_id] = []
                companies[company_id].append(row)
            
            for company_id, periods in companies.items():
                print(f"   🏢 Company ID {company_id}:")
                print(f"      📊 Períodos: {len(periods)}")
                
                # Verificar sobreposições
                periods_sorted = sorted(periods, key=lambda x: x.period_from)
                overlaps = []
                
                for i in range(len(periods_sorted) - 1):
                    current = periods_sorted[i]
                    next_period = periods_sorted[i + 1]
                    
                    if current.period_to >= next_period.period_from:
                        overlaps.append((current, next_period))
                
                if overlaps:
                    print(f"      ⚠️  Sobreposições encontradas: {len(overlaps)}")
                    for overlap in overlaps:
                        print(f"         📅 {overlap[0].period_from} a {overlap[0].period_to}")
                        print(f"         📅 {overlap[1].period_from} a {overlap[1].period_to}")
                else:
                    print(f"      ✅ Sem sobreposições")
                
                # Calcular totais
                total_marketing = sum(float(p.advertising_cost or 0) for p in periods)
                total_sale_fees = sum(float(p.sale_fees or 0) for p in periods)
                total_shipping = sum(float(p.shipping_fees or 0) for p in periods)
                
                print(f"      💰 Marketing Total: R$ {total_marketing:.2f}")
                print(f"      💰 Sale Fees Total: R$ {total_sale_fees:.2f}")
                print(f"      💰 Shipping Total: R$ {total_shipping:.2f}")
                print()
        
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
    print("🔍 Verificação das Colunas e Dados de Billing")
    print("=" * 70)
    print()
    
    success = check_billing_columns()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ VERIFICAÇÃO CONCLUÍDA!")
    else:
        print("❌ Erro na verificação!")

if __name__ == "__main__":
    main()
