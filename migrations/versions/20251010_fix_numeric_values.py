"""Fix numeric values - convert from INTEGER to NUMERIC

Revision ID: 20251010_fix_numeric_values
Revises: 
Create Date: 2025-10-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251010_fix_numeric_values'
down_revision = '20250106140000_add_has_catalog_products_field'
branch_labels = None
depends_on = None


def upgrade():
    # Converter colunas monetárias de INTEGER para NUMERIC(10,2)
    # Multiplicar valores existentes por 100 porque estavam truncados
    
    # 1. Valores principais
    op.execute("""
        ALTER TABLE ml_orders 
        ALTER COLUMN total_amount TYPE NUMERIC(10,2) USING total_amount::NUMERIC(10,2),
        ALTER COLUMN paid_amount TYPE NUMERIC(10,2) USING paid_amount::NUMERIC(10,2);
    """)
    
    # 2. Shipping
    op.execute("""
        ALTER TABLE ml_orders 
        ALTER COLUMN shipping_cost TYPE NUMERIC(10,2) USING shipping_cost::NUMERIC(10,2);
    """)
    
    # 3. Taxas
    op.execute("""
        ALTER TABLE ml_orders 
        ALTER COLUMN total_fees TYPE NUMERIC(10,2) USING total_fees::NUMERIC(10,2),
        ALTER COLUMN listing_fees TYPE NUMERIC(10,2) USING listing_fees::NUMERIC(10,2),
        ALTER COLUMN sale_fees TYPE NUMERIC(10,2) USING sale_fees::NUMERIC(10,2),
        ALTER COLUMN shipping_fees TYPE NUMERIC(10,2) USING shipping_fees::NUMERIC(10,2);
    """)
    
    # 4. Billing
    op.execute("""
        ALTER TABLE ml_orders 
        ALTER COLUMN financing_fee TYPE NUMERIC(10,2) USING financing_fee::NUMERIC(10,2),
        ALTER COLUMN financing_transfer_total TYPE NUMERIC(10,2) USING financing_transfer_total::NUMERIC(10,2);
    """)
    
    # 5. Descontos e publicidade
    op.execute("""
        ALTER TABLE ml_orders 
        ALTER COLUMN coupon_amount TYPE NUMERIC(10,2) USING coupon_amount::NUMERIC(10,2),
        ALTER COLUMN advertising_cost TYPE NUMERIC(10,2) USING advertising_cost::NUMERIC(10,2);
    """)


def downgrade():
    # Reverter para INTEGER (dividir por 100 e truncar)
    op.execute("""
        ALTER TABLE ml_orders 
        ALTER COLUMN total_amount TYPE INTEGER USING (total_amount * 100)::INTEGER,
        ALTER COLUMN paid_amount TYPE INTEGER USING (paid_amount * 100)::INTEGER,
        ALTER COLUMN shipping_cost TYPE INTEGER USING (shipping_cost * 100)::INTEGER,
        ALTER COLUMN total_fees TYPE INTEGER USING (total_fees * 100)::INTEGER,
        ALTER COLUMN listing_fees TYPE INTEGER USING (listing_fees * 100)::INTEGER,
        ALTER COLUMN sale_fees TYPE INTEGER USING (sale_fees * 100)::INTEGER,
        ALTER COLUMN shipping_fees TYPE INTEGER USING (shipping_fees * 100)::INTEGER,
        ALTER COLUMN financing_fee TYPE INTEGER USING (financing_fee * 100)::INTEGER,
        ALTER COLUMN financing_transfer_total TYPE INTEGER USING (financing_transfer_total * 100)::INTEGER,
        ALTER COLUMN coupon_amount TYPE INTEGER USING (coupon_amount * 100)::INTEGER,
        ALTER COLUMN advertising_cost TYPE INTEGER USING (advertising_cost * 100)::INTEGER;
    """)

