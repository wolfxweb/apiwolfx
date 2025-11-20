"""
Migration: Adicionar colunas Asaas na tabela subscriptions
Data: 2025-11-19
"""
import logging
from sqlalchemy import text
from app.config.database import SessionLocal

logger = logging.getLogger(__name__)


def add_asaas_columns_to_subscriptions():
    """
    Adiciona colunas relacionadas ao Asaas na tabela subscriptions
    Esta função é idempotente e pode ser executada múltiplas vezes sem problemas
    """
    db = SessionLocal()
    try:
        print("🔧 [MIGRATION] Verificando colunas Asaas na tabela subscriptions...")
        logger.info("🔧 Adicionando colunas Asaas na tabela subscriptions...")
        
        # Verificar se as colunas já existem
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'subscriptions' 
            AND column_name IN ('asaas_subscription_id', 'asaas_customer_id', 'payment_provider', 'next_charge_date')
        """)
        
        existing_columns = [row[0] for row in db.execute(check_query).fetchall()]
        print(f"📋 [MIGRATION] Colunas existentes: {existing_columns}")
        
        # Adicionar colunas se não existirem
        if 'asaas_subscription_id' not in existing_columns:
            db.execute(text("""
                ALTER TABLE subscriptions 
                ADD COLUMN asaas_subscription_id VARCHAR(100)
            """))
            print("✅ [MIGRATION] Coluna asaas_subscription_id adicionada")
            logger.info("✅ Coluna asaas_subscription_id adicionada")
        else:
            print("ℹ️ [MIGRATION] Coluna asaas_subscription_id já existe")
        
        if 'asaas_customer_id' not in existing_columns:
            db.execute(text("""
                ALTER TABLE subscriptions 
                ADD COLUMN asaas_customer_id VARCHAR(100)
            """))
            print("✅ [MIGRATION] Coluna asaas_customer_id adicionada")
            logger.info("✅ Coluna asaas_customer_id adicionada")
        else:
            print("ℹ️ [MIGRATION] Coluna asaas_customer_id já existe")
        
        if 'payment_provider' not in existing_columns:
            db.execute(text("""
                ALTER TABLE subscriptions 
                ADD COLUMN payment_provider VARCHAR(20) DEFAULT 'asaas'
            """))
            print("✅ [MIGRATION] Coluna payment_provider adicionada")
            logger.info("✅ Coluna payment_provider adicionada")
        else:
            print("ℹ️ [MIGRATION] Coluna payment_provider já existe")
        
        if 'next_charge_date' not in existing_columns:
            db.execute(text("""
                ALTER TABLE subscriptions 
                ADD COLUMN next_charge_date TIMESTAMP
            """))
            print("✅ [MIGRATION] Coluna next_charge_date adicionada")
            logger.info("✅ Coluna next_charge_date adicionada")
        else:
            print("ℹ️ [MIGRATION] Coluna next_charge_date já existe")
        
        # Criar índices
        try:
            # Verificar se o índice já existe
            index_check = text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'subscriptions' 
                AND indexname = 'idx_subscriptions_asaas_subscription_id'
            """)
            index_exists = db.execute(index_check).fetchone()
            
            if not index_exists:
                db.execute(text("""
                    CREATE INDEX idx_subscriptions_asaas_subscription_id 
                    ON subscriptions(asaas_subscription_id)
                """))
                print("✅ [MIGRATION] Índice em asaas_subscription_id criado")
                logger.info("✅ Índice em asaas_subscription_id criado")
            else:
                print("ℹ️ [MIGRATION] Índice já existe")
        except Exception as e:
            print(f"⚠️ [MIGRATION] Erro ao criar índice: {e}")
            logger.warning(f"⚠️ Índice já existe ou erro ao criar: {e}")
        
        db.commit()
        print("✅ [MIGRATION] Colunas Asaas verificadas/criadas com sucesso!")
        logger.info("✅ Colunas Asaas adicionadas com sucesso!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ [MIGRATION] Erro ao adicionar colunas Asaas: {e}")
        logger.error(f"❌ Erro ao adicionar colunas Asaas: {e}")
        import traceback
        traceback.print_exc()
        # Não fazer raise para não quebrar o startup se já existir
        # Apenas logar o erro
    finally:
        db.close()


if __name__ == "__main__":
    add_asaas_columns_to_subscriptions()

