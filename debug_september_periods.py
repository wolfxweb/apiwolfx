#!/usr/bin/env python3
"""
Debug específico dos períodos para Setembro
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from sqlalchemy import text
from datetime import datetime

def debug_september_periods():
    """Debug específico dos períodos para Setembro"""
    print("🔍 Debug Específico dos Períodos para Setembro")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15
        start_date = datetime(2025, 9, 1)
        end_date = datetime(2025, 9, 30, 23, 59, 59)
        
        print(f"📅 Período solicitado: {start_date} a {end_date}")
        print()
        
        # 1. Verificar todos os períodos disponíveis
        print("📊 1. TODOS OS PERÍODOS DISPONÍVEIS")
        print("-" * 40)
        
        result = db.execute(text("""
            SELECT 
                id,
                period_from,
                period_to,
                advertising_cost,
                sale_fees,
                shipping_fees,
                is_closed,
                (period_to - period_from) as duration
            FROM ml_billing_periods 
            WHERE company_id = :company_id
            ORDER BY period_from
        """), {"company_id": company_id})
        
        all_periods = result.fetchall()
        
        for i, period in enumerate(all_periods, 1):
            print(f"   📅 Período {i}:")
            print(f"      🆔 ID: {period.id}")
            print(f"      📅 De: {period.period_from}")
            print(f"      📅 Até: {period.period_to}")
            print(f"      ⏱️  Duração: {period.duration}")
            print(f"      💰 Marketing: R$ {float(period.advertising_cost or 0):.2f}")
            print(f"      🔒 Fechado: {period.is_closed}")
            
            # Verificar sobreposição
            overlaps = (period.period_from <= end_date and period.period_to >= start_date)
            print(f"      🔍 Sobrepoem Setembro: {overlaps}")
            print()
        
        # 2. Testar condições da consulta
        print("📊 2. TESTE DAS CONDIÇÕES DA CONSULTA")
        print("-" * 40)
        
        for period in all_periods:
            print(f"   📅 Período {period.id}:")
            
            # Condição 1: Dentro do range
            inside_range = (period.period_from >= start_date and period.period_to <= end_date)
            print(f"      ✅ Dentro do range: {inside_range}")
            
            # Condição 2: Sobreposição com período curto
            overlaps = (period.period_from <= end_date and period.period_to >= start_date)
            duration_days = (period.period_to - period.period_from).days
            short_period = duration_days <= 45
            print(f"      ✅ Sobrepoem: {overlaps}")
            print(f"      ✅ Período curto (≤45 dias): {short_period} ({duration_days} dias)")
            
            # Resultado final
            condition1 = inside_range
            condition2 = (overlaps and short_period and period.period_from < start_date and period.period_to > end_date)
            final_result = condition1 or condition2
            
            print(f"      🎯 RESULTADO: {final_result}")
            print()
        
        # 3. Consulta simplificada
        print("📊 3. CONSULTA SIMPLIFICADA")
        print("-" * 40)
        
        result = db.execute(text("""
            SELECT 
                id,
                period_from,
                period_to,
                advertising_cost,
                sale_fees,
                shipping_fees,
                (period_to - period_from) as duration
            FROM ml_billing_periods 
            WHERE company_id = :company_id
            AND period_from <= :end_date 
            AND period_to >= :start_date
        """), {
            "company_id": company_id,
            "start_date": start_date,
            "end_date": end_date
        })
        
        overlapping_periods = result.fetchall()
        
        if overlapping_periods:
            print(f"   📊 Períodos que se sobrepõem: {len(overlapping_periods)}")
            for period in overlapping_periods:
                print(f"      📅 {period.period_from} a {period.period_to}")
                print(f"      💰 Marketing: R$ {float(period.advertising_cost or 0):.2f}")
                print(f"      ⏱️  Duração: {period.duration}")
        else:
            print(f"   ❌ Nenhum período se sobrepõe!")
        
        # 4. Recomendação
        print(f"\n📊 4. RECOMENDAÇÃO")
        print("-" * 40)
        
        if overlapping_periods:
            # Encontrar o período mais específico
            specific_periods = [p for p in overlapping_periods 
                               if p.period_from >= start_date and p.period_to <= end_date]
            
            if specific_periods:
                print(f"   ✅ Períodos específicos encontrados: {len(specific_periods)}")
                for period in specific_periods:
                    print(f"      📅 {period.period_from} a {period.period_to}")
                    print(f"      💰 Marketing: R$ {float(period.advertising_cost or 0):.2f}")
            else:
                print(f"   ⚠️  Nenhum período específico, usando sobreposições")
                # Pegar o período mais curto
                shortest = min(overlapping_periods, key=lambda p: (p.period_to - p.period_from).days)
                print(f"      📅 Período mais curto: {shortest.period_from} a {shortest.period_to}")
                print(f"      💰 Marketing: R$ {float(shortest.advertising_cost or 0):.2f}")
        
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
    print("🔍 Debug Específico dos Períodos para Setembro")
    print("=" * 60)
    print()
    
    success = debug_september_periods()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ DEBUG CONCLUÍDO!")
    else:
        print("❌ Erro no debug!")

if __name__ == "__main__":
    main()
