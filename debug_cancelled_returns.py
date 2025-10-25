#!/usr/bin/env python3
"""
Debug de vendas canceladas e devoluções
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.database import SessionLocal
from sqlalchemy import text
from datetime import datetime
import json

def debug_cancelled_returns():
    """Debug de vendas canceladas e devoluções"""
    print("🔍 Debug de Vendas Canceladas e Devoluções")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        company_id = 15  # wolfx ltda
        
        # Teste 1: Verificar pedidos cancelados
        print("📊 Teste 1: Pedidos Cancelados")
        print("-" * 40)
        
        result1 = db.execute(text("""
            SELECT 
                COUNT(*) as total_cancelled,
                SUM(total_amount) as cancelled_value,
                status
            FROM ml_orders 
            WHERE company_id = :company_id
            AND status = 'CANCELLED'
            AND date_created >= :start_date
            AND date_created <= :end_date
            GROUP BY status
        """), {
            "company_id": company_id,
            "start_date": datetime(2025, 10, 1),
            "end_date": datetime(2025, 10, 31, 23, 59, 59)
        })
        
        cancelled_data = result1.fetchall()
        
        if cancelled_data:
            for row in cancelled_data:
                print(f"   📦 Status: {row.status}")
                print(f"   📦 Total Cancelados: {row.total_cancelled}")
                print(f"   💰 Valor Cancelado: R$ {float(row.cancelled_value or 0):.2f}")
        else:
            print(f"   ❌ Nenhum pedido cancelado encontrado")
        
        # Teste 2: Verificar devoluções (mediations)
        print(f"\n📊 Teste 2: Devoluções (Mediations)")
        print("-" * 40)
        
        result2 = db.execute(text("""
            SELECT 
                ml_order_id,
                total_amount,
                mediations
            FROM ml_orders 
            WHERE company_id = :company_id
            AND mediations IS NOT NULL
            AND mediations::text != '[]'
            AND mediations::text != '{}'
            AND date_created >= :start_date
            AND date_created <= :end_date
            LIMIT 5
        """), {
            "company_id": company_id,
            "start_date": datetime(2025, 10, 1),
            "end_date": datetime(2025, 10, 31, 23, 59, 59)
        })
        
        returns_data = result2.fetchall()
        
        if returns_data:
            total_returns = 0
            total_returns_value = 0.0
            
            for row in returns_data:
                total_returns += 1
                total_returns_value += float(row.total_amount or 0)
                
                print(f"   🆔 Pedido: {row.ml_order_id}")
                print(f"   💰 Valor: R$ {float(row.total_amount or 0):.2f}")
                
                # Analisar mediations JSON
                try:
                    mediations = json.loads(row.mediations) if isinstance(row.mediations, str) else row.mediations
                    if isinstance(mediations, list):
                        print(f"   📋 Mediations: {len(mediations)} itens")
                        for i, mediation in enumerate(mediations[:2]):  # Mostrar apenas os 2 primeiros
                            print(f"      {i+1}. Status: {mediation.get('status', 'N/A')}")
                            print(f"         Tipo: {mediation.get('type', 'N/A')}")
                    else:
                        print(f"   📋 Mediations: {mediations}")
                except Exception as e:
                    print(f"   ❌ Erro ao parsear mediations: {e}")
                print()
            
            print(f"   📊 Total Devoluções: {total_returns}")
            print(f"   💰 Valor Total Devoluções: R$ {total_returns_value:.2f}")
        else:
            print(f"   ❌ Nenhuma devolução encontrada")
        
        # Teste 3: Verificar todos os status de pedidos
        print(f"\n📊 Teste 3: Todos os Status de Pedidos")
        print("-" * 40)
        
        result3 = db.execute(text("""
            SELECT 
                status,
                COUNT(*) as count,
                SUM(total_amount) as total_value
            FROM ml_orders 
            WHERE company_id = :company_id
            AND date_created >= :start_date
            AND date_created <= :end_date
            GROUP BY status
            ORDER BY count DESC
        """), {
            "company_id": company_id,
            "start_date": datetime(2025, 10, 1),
            "end_date": datetime(2025, 10, 31, 23, 59, 59)
        })
        
        status_data = result3.fetchall()
        
        print(f"   📊 Status dos Pedidos:")
        for row in status_data:
            print(f"      {row.status}: {row.count} pedidos (R$ {float(row.total_value or 0):.2f})")
        
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
    print("🔍 Debug de Vendas Canceladas e Devoluções")
    print("=" * 60)
    print()
    
    success = debug_cancelled_returns()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ DEBUG CONCLUÍDO!")
    else:
        print("❌ Erro no debug!")

if __name__ == "__main__":
    main()
