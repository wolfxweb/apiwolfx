"""add_stock_module

Revision ID: 20250120
Revises: 20251020_add_card_fields_to_financial_accounts
Create Date: 2025-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250120'
down_revision = '20251020_add_card_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Criar enum para WarehouseType
    op.execute("""
        CREATE TYPE warehousetype AS ENUM ('fulfillment', 'custom');
    """)
    
    # Criar enum para StockMovementType
    op.execute("""
        CREATE TYPE stockmovementtype AS ENUM ('in', 'out', 'adjustment', 'transfer', 'sale', 'purchase', 'reservation', 'release');
    """)
    
    # Criar tabela warehouses
    op.create_table('warehouses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', postgresql.ENUM('fulfillment', 'custom', name='warehousetype'), nullable=False),
        sa.Column('is_shared', sa.Boolean(), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('contact_info', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_warehouses_company_type', 'warehouses', ['company_id', 'type'], unique=False)
    op.create_index('ix_warehouses_status', 'warehouses', ['status'], unique=False)
    op.create_index(op.f('ix_warehouses_company_id'), 'warehouses', ['company_id'], unique=False)
    op.create_index(op.f('ix_warehouses_type'), 'warehouses', ['type'], unique=False)
    op.create_index(op.f('ix_warehouses_is_shared'), 'warehouses', ['is_shared'], unique=False)
    
    # Criar tabela product_stocks
    op.create_table('product_stocks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('internal_product_id', sa.Integer(), nullable=True),
        sa.Column('ml_item_id', sa.String(length=50), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('reserved_quantity', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('min_stock', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('max_stock', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('reorder_point', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('last_movement_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
        sa.ForeignKeyConstraint(['internal_product_id'], ['internal_products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_product_stocks_warehouse_product', 'product_stocks', ['warehouse_id', 'internal_product_id'], unique=False)
    op.create_index('ix_product_stocks_warehouse_ml_item', 'product_stocks', ['warehouse_id', 'ml_item_id'], unique=False)
    op.create_index(op.f('ix_product_stocks_company_id'), 'product_stocks', ['company_id'], unique=False)
    op.create_index(op.f('ix_product_stocks_warehouse_id'), 'product_stocks', ['warehouse_id'], unique=False)
    op.create_index(op.f('ix_product_stocks_internal_product_id'), 'product_stocks', ['internal_product_id'], unique=False)
    op.create_index(op.f('ix_product_stocks_ml_item_id'), 'product_stocks', ['ml_item_id'], unique=False)
    
    # Criar tabela stock_movements
    op.create_table('stock_movements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('product_stock_id', sa.Integer(), nullable=False),
        sa.Column('movement_type', postgresql.ENUM('in', 'out', 'adjustment', 'transfer', 'sale', 'purchase', 'reservation', 'release', name='stockmovementtype'), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('previous_quantity', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('new_quantity', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('reference_type', sa.String(length=50), nullable=True),
        sa.Column('reference_id', sa.Integer(), nullable=True),
        sa.Column('ml_order_id', sa.BigInteger(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
        sa.ForeignKeyConstraint(['product_stock_id'], ['product_stocks.id'], ),
        sa.ForeignKeyConstraint(['ml_order_id'], ['ml_orders.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_stock_movements_product_stock_date', 'stock_movements', ['product_stock_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_stock_movements_company_id'), 'stock_movements', ['company_id'], unique=False)
    op.create_index(op.f('ix_stock_movements_warehouse_id'), 'stock_movements', ['warehouse_id'], unique=False)
    op.create_index(op.f('ix_stock_movements_product_stock_id'), 'stock_movements', ['product_stock_id'], unique=False)
    op.create_index(op.f('ix_stock_movements_movement_type'), 'stock_movements', ['movement_type'], unique=False)
    op.create_index(op.f('ix_stock_movements_ml_order_id'), 'stock_movements', ['ml_order_id'], unique=False)
    op.create_index('ix_stock_movements_company_date', 'stock_movements', ['company_id', 'created_at'], unique=False)
    
    # Criar tabela stock_projections
    op.create_table('stock_projections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('internal_product_id', sa.Integer(), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('current_stock', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('average_daily_sales', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('days_of_stock', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('projected_stockout_date', sa.DateTime(), nullable=True),
        sa.Column('recommended_reorder_date', sa.DateTime(), nullable=True),
        sa.Column('recommended_quantity', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('turnover_rate', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('calculation_period_days', sa.Integer(), nullable=True),
        sa.Column('last_calculated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['internal_product_id'], ['internal_products.id'], ),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_stock_projections_product_warehouse', 'stock_projections', ['internal_product_id', 'warehouse_id'], unique=False)
    op.create_index(op.f('ix_stock_projections_company_id'), 'stock_projections', ['company_id'], unique=False)
    op.create_index(op.f('ix_stock_projections_internal_product_id'), 'stock_projections', ['internal_product_id'], unique=False)
    op.create_index(op.f('ix_stock_projections_warehouse_id'), 'stock_projections', ['warehouse_id'], unique=False)
    op.create_index(op.f('ix_stock_projections_last_calculated'), 'stock_projections', ['last_calculated_at'], unique=False)
    
    # Criar depósito fulfillment padrão (compartilhado)
    op.execute("""
        INSERT INTO warehouses (name, type, is_shared, status, created_at, updated_at)
        VALUES ('Fulfillment ML', 'fulfillment', true, 'active', now(), now())
        ON CONFLICT DO NOTHING;
    """)


def downgrade():
    # Remover tabelas
    op.drop_index(op.f('ix_stock_projections_last_calculated'), table_name='stock_projections')
    op.drop_index(op.f('ix_stock_projections_warehouse_id'), table_name='stock_projections')
    op.drop_index(op.f('ix_stock_projections_internal_product_id'), table_name='stock_projections')
    op.drop_index(op.f('ix_stock_projections_company_id'), table_name='stock_projections')
    op.drop_index('ix_stock_projections_product_warehouse', table_name='stock_projections')
    op.drop_table('stock_projections')
    
    op.drop_index('ix_stock_movements_company_date', table_name='stock_movements')
    op.drop_index(op.f('ix_stock_movements_ml_order_id'), table_name='stock_movements')
    op.drop_index(op.f('ix_stock_movements_movement_type'), table_name='stock_movements')
    op.drop_index(op.f('ix_stock_movements_product_stock_id'), table_name='stock_movements')
    op.drop_index(op.f('ix_stock_movements_warehouse_id'), table_name='stock_movements')
    op.drop_index(op.f('ix_stock_movements_company_id'), table_name='stock_movements')
    op.drop_index('ix_stock_movements_product_stock_date', table_name='stock_movements')
    op.drop_table('stock_movements')
    
    op.drop_index(op.f('ix_product_stocks_ml_item_id'), table_name='product_stocks')
    op.drop_index(op.f('ix_product_stocks_internal_product_id'), table_name='product_stocks')
    op.drop_index(op.f('ix_product_stocks_warehouse_id'), table_name='product_stocks')
    op.drop_index(op.f('ix_product_stocks_company_id'), table_name='product_stocks')
    op.drop_index('ix_product_stocks_warehouse_ml_item', table_name='product_stocks')
    op.drop_index('ix_product_stocks_warehouse_product', table_name='product_stocks')
    op.drop_table('product_stocks')
    
    op.drop_index(op.f('ix_warehouses_is_shared'), table_name='warehouses')
    op.drop_index(op.f('ix_warehouses_type'), table_name='warehouses')
    op.drop_index(op.f('ix_warehouses_company_id'), table_name='warehouses')
    op.drop_index('ix_warehouses_status', table_name='warehouses')
    op.drop_index('ix_warehouses_company_type', table_name='warehouses')
    op.drop_table('warehouses')
    
    # Remover enums
    op.execute("DROP TYPE IF EXISTS stockmovementtype;")
    op.execute("DROP TYPE IF EXISTS warehousetype;")

