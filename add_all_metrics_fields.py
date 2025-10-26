#!/usr/bin/env python3
"""
Adicionar todos os campos de métricas da API ML
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.config.database import SessionLocal, engine
from sqlalchemy import text

def add_metrics_fields():
    db = SessionLocal()
    
    try:
        print("\n" + "="*80)
        print("📊 ADICIONANDO NOVOS CAMPOS DE MÉTRICAS")
        print("="*80 + "\n")
        
        # Novos campos a adicionar
        new_columns = [
            # Vendas Diretas
            "ALTER TABLE ml_campaign_metrics ADD COLUMN IF NOT EXISTS direct_items_quantity INTEGER DEFAULT 0",
            "ALTER TABLE ml_campaign_metrics ADD COLUMN IF NOT EXISTS direct_units_quantity INTEGER DEFAULT 0",
            "ALTER TABLE ml_campaign_metrics ADD COLUMN IF NOT EXISTS direct_amount FLOAT DEFAULT 0",
            
            # Vendas Indiretas
            "ALTER TABLE ml_campaign_metrics ADD COLUMN IF NOT EXISTS indirect_items_quantity INTEGER DEFAULT 0",
            "ALTER TABLE ml_campaign_metrics ADD COLUMN IF NOT EXISTS indirect_units_quantity INTEGER DEFAULT 0",
            "ALTER TABLE ml_campaign_metrics ADD COLUMN IF NOT EXISTS indirect_amount FLOAT DEFAULT 0",
            
            # Totais
            "ALTER TABLE ml_campaign_metrics ADD COLUMN IF NOT EXISTS advertising_items_quantity INTEGER DEFAULT 0",
            "ALTER TABLE ml_campaign_metrics ADD COLUMN IF NOT EXISTS units_quantity INTEGER DEFAULT 0",
            "ALTER TABLE ml_campaign_metrics ADD COLUMN IF NOT EXISTS total_amount FLOAT DEFAULT 0",
            
            # Orgânicas
            "ALTER TABLE ml_campaign_metrics ADD COLUMN IF NOT EXISTS organic_items_quantity INTEGER DEFAULT 0",
            "ALTER TABLE ml_campaign_metrics ADD COLUMN IF NOT EXISTS organic_units_quantity INTEGER DEFAULT 0",
            "ALTER TABLE ml_campaign_metrics ADD COLUMN IF NOT EXISTS organic_units_amount FLOAT DEFAULT 0",
            
            # Métricas Avançadas
            "ALTER TABLE ml_campaign_metrics ADD COLUMN IF NOT EXISTS acos FLOAT DEFAULT 0",
            "ALTER TABLE ml_campaign_metrics ADD COLUMN IF NOT EXISTS cvr FLOAT DEFAULT 0",
            "ALTER TABLE ml_campaign_metrics ADD COLUMN IF NOT EXISTS sov FLOAT DEFAULT 0"
        ]
        
        # Renomear campos antigos se necessário
        rename_columns = [
            "ALTER TABLE ml_campaign_metrics RENAME COLUMN conversions TO conversions_old",
            "ALTER TABLE ml_campaign_metrics RENAME COLUMN revenue TO revenue_old"
        ]
        
        print("1️⃣ Tentando renomear campos antigos...")
        for sql in rename_columns:
            try:
                db.execute(text(sql))
                column_name = sql.split("RENAME COLUMN ")[1].split(" TO")[0]
                print(f"   ✅ Renomeado: {column_name}")
            except Exception as e:
                if "does not exist" in str(e) or "não existe" in str(e):
                    print(f"   ⏭️  Coluna já renomeada")
                else:
                    print(f"   ⚠️  Erro ao renomear: {e}")
        
        db.commit()
        
        print(f"\n2️⃣ Adicionando {len(new_columns)} novos campos...")
        added = 0
        for sql in new_columns:
            try:
                db.execute(text(sql))
                column_name = sql.split("ADD COLUMN IF NOT EXISTS ")[1].split(" ")[0]
                print(f"   ✅ Adicionado: {column_name}")
                added += 1
            except Exception as e:
                if "already exists" in str(e) or "já existe" in str(e):
                    print(f"   ⏭️  Campo já existe")
                else:
                    print(f"   ❌ Erro: {e}")
        
        db.commit()
        
        # Verificar estrutura final
        print(f"\n3️⃣ Verificando estrutura final...")
        result = db.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'ml_campaign_metrics'
            ORDER BY ordinal_position
        """))
        
        columns = result.fetchall()
        print(f"   Total de colunas: {len(columns)}")
        print(f"\n   Campos:")
        for col in columns:
            print(f"      • {col[0]} ({col[1]})")
        
        print("\n" + "="*80)
        print(f"✅ MIGRAÇÃO CONCLUÍDA! {added} campos adicionados")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    
    finally:
        db.close()

if __name__ == "__main__":
    add_metrics_fields()

