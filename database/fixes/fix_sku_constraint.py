#!/usr/bin/env python3
"""
Script para corrigir constraint da tabela sku_management
"""
import sys
sys.path.append('/Users/wolfx/Documents/wolfx/apiwolfx')

from app.config.database import engine
from sqlalchemy import text

def fix_sku_constraint():
    """Remove constraint única do SKU e permite múltiplos registros"""
    
    print("=== CORRIGINDO CONSTRAINT DA TABELA SKU_MANAGEMENT ===\n")
    
    try:
        with engine.connect() as conn:
            # Remover constraint única do SKU
            print("🔧 Removendo constraint única do SKU...")
            try:
                drop_constraint_query = text("""
                    ALTER TABLE sku_management 
                    DROP CONSTRAINT IF EXISTS sku_management_sku_key
                """)
                conn.execute(drop_constraint_query)
                conn.commit()
                print("✅ Constraint única removida com sucesso!")
            except Exception as e:
                print(f"⚠️ Aviso: {e}")
            
            # Verificar se a constraint foi removida
            check_query = text("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'sku_management' 
                AND constraint_name = 'sku_management_sku_key'
            """)
            
            result = conn.execute(check_query).fetchone()
            if result:
                print("❌ Constraint ainda existe")
            else:
                print("✅ Constraint removida com sucesso!")
        
        print("\n🎉 Tabela 'sku_management' corrigida!")
        
    except Exception as e:
        print(f"❌ Erro ao corrigir tabela: {e}")

if __name__ == "__main__":
    fix_sku_constraint()

