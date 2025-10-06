#!/usr/bin/env python3
"""
Script para remover todas as constraints únicas da tabela sku_management
"""
import sys
sys.path.append('/Users/wolfx/Documents/wolfx/apiwolfx')

from app.config.database import engine
from sqlalchemy import text

def fix_sku_constraint_final():
    """Remove todas as constraints únicas da tabela sku_management"""
    
    print("=== REMOVENDO TODAS AS CONSTRAINTS ÚNICAS ===\n")
    
    try:
        with engine.connect() as conn:
            # Listar todas as constraints únicas
            print("🔍 Listando constraints únicas...")
            list_constraints_query = text("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'sku_management' 
                AND constraint_type = 'UNIQUE'
            """)
            
            constraints = conn.execute(list_constraints_query).fetchall()
            print(f"Constraints encontradas: {[c[0] for c in constraints]}")
            
            # Remover cada constraint única
            for constraint in constraints:
                constraint_name = constraint[0]
                print(f"🔧 Removendo constraint: {constraint_name}")
                
                try:
                    drop_query = text(f"""
                        ALTER TABLE sku_management 
                        DROP CONSTRAINT IF EXISTS {constraint_name}
                    """)
                    conn.execute(drop_query)
                    conn.commit()
                    print(f"✅ Constraint {constraint_name} removida!")
                except Exception as e:
                    print(f"⚠️ Erro ao remover {constraint_name}: {e}")
            
            # Verificar se ainda há constraints únicas
            final_check = conn.execute(list_constraints_query).fetchall()
            if final_check:
                print(f"❌ Ainda existem constraints: {[c[0] for c in final_check]}")
            else:
                print("✅ Todas as constraints únicas foram removidas!")
        
        print("\n🎉 Tabela 'sku_management' corrigida completamente!")
        
    except Exception as e:
        print(f"❌ Erro ao corrigir tabela: {e}")

if __name__ == "__main__":
    fix_sku_constraint_final()

