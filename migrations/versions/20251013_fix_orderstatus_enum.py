"""fix orderstatus enum values

Revision ID: 20251013_fix_orderstatus_enum
Revises: 
Create Date: 2025-10-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251013_fix_orderstatus_enum'
down_revision = '20251010_fix_numeric_values'
branch_labels = None
depends_on = None


def upgrade():
    # Alterar o enum orderstatus para usar valores em maiúsculo
    op.execute("""
        -- Criar novo enum com valores em maiúsculo
        CREATE TYPE orderstatus_new AS ENUM ('PENDING', 'CONFIRMED', 'PAID', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'REFUNDED');
        
        -- Atualizar coluna status para usar o novo enum
        ALTER TABLE ml_orders ALTER COLUMN status TYPE orderstatus_new USING (
            CASE status::text
                WHEN 'pending' THEN 'PENDING'::orderstatus_new
                WHEN 'confirmed' THEN 'CONFIRMED'::orderstatus_new
                WHEN 'paid' THEN 'PAID'::orderstatus_new
                WHEN 'shipped' THEN 'SHIPPED'::orderstatus_new
                WHEN 'delivered' THEN 'DELIVERED'::orderstatus_new
                WHEN 'cancelled' THEN 'CANCELLED'::orderstatus_new
                WHEN 'refunded' THEN 'REFUNDED'::orderstatus_new
                ELSE 'PENDING'::orderstatus_new
            END
        );
        
        -- Remover enum antigo
        DROP TYPE orderstatus;
        
        -- Renomear novo enum para nome original
        ALTER TYPE orderstatus_new RENAME TO orderstatus;
    """)


def downgrade():
    # Reverter para enum com valores em minúsculo
    op.execute("""
        -- Criar enum antigo com valores em minúsculo
        CREATE TYPE orderstatus_old AS ENUM ('pending', 'confirmed', 'paid', 'shipped', 'delivered', 'cancelled', 'refunded');
        
        -- Atualizar coluna status para usar o enum antigo
        ALTER TABLE ml_orders ALTER COLUMN status TYPE orderstatus_old USING (
            CASE status::text
                WHEN 'PENDING' THEN 'pending'::orderstatus_old
                WHEN 'CONFIRMED' THEN 'confirmed'::orderstatus_old
                WHEN 'PAID' THEN 'paid'::orderstatus_old
                WHEN 'SHIPPED' THEN 'shipped'::orderstatus_old
                WHEN 'DELIVERED' THEN 'delivered'::orderstatus_old
                WHEN 'CANCELLED' THEN 'cancelled'::orderstatus_old
                WHEN 'REFUNDED' THEN 'refunded'::orderstatus_old
                ELSE 'pending'::orderstatus_old
            END
        );
        
        -- Remover enum novo
        DROP TYPE orderstatus;
        
        -- Renomear enum antigo para nome original
        ALTER TYPE orderstatus_old RENAME TO orderstatus;
    """)

