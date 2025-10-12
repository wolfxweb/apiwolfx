"""add ml catalog monitoring and history

Revision ID: 20250113_catalog_monitoring
Revises: 20251010_fix_numeric_values
Create Date: 2025-01-13 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250113_catalog_monitoring'
down_revision = '20251010_fix_numeric_values'
branch_labels = None
depends_on = None


def upgrade():
    # Criar tabela de controle de monitoramento
    op.create_table(
        'ml_catalog_monitoring',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('catalog_product_id', sa.String(50), nullable=False),
        sa.Column('ml_product_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('activated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_check_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['ml_product_id'], ['ml_products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Índices para ml_catalog_monitoring
    op.create_index('ix_catalog_monitoring_company', 'ml_catalog_monitoring', ['company_id'])
    op.create_index('ix_catalog_monitoring_catalog_product', 'ml_catalog_monitoring', ['catalog_product_id'])
    op.create_index('ix_catalog_monitoring_is_active', 'ml_catalog_monitoring', ['is_active'])
    op.create_index('ix_catalog_monitoring_company_catalog', 'ml_catalog_monitoring', ['company_id', 'catalog_product_id'])
    op.create_index('ix_catalog_monitoring_active', 'ml_catalog_monitoring', ['company_id', 'is_active'])
    
    # Criar tabela de histórico
    op.create_table(
        'ml_catalog_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('catalog_product_id', sa.String(50), nullable=False),
        sa.Column('ml_product_id', sa.Integer(), nullable=True),
        sa.Column('monitoring_id', sa.Integer(), nullable=True),
        sa.Column('total_participants', sa.Integer(), server_default='0'),
        sa.Column('buy_box_winner_id', sa.String(50), nullable=True),
        sa.Column('buy_box_winner_price', sa.Integer(), nullable=True),
        sa.Column('company_position', sa.Integer(), nullable=True),
        sa.Column('company_price', sa.Integer(), nullable=True),
        sa.Column('company_has_buy_box', sa.Boolean(), server_default='false'),
        sa.Column('min_price', sa.Integer(), nullable=True),
        sa.Column('max_price', sa.Integer(), nullable=True),
        sa.Column('avg_price', sa.Integer(), nullable=True),
        sa.Column('median_price', sa.Integer(), nullable=True),
        sa.Column('total_available_quantity', sa.Integer(), server_default='0'),
        sa.Column('total_sold_quantity', sa.Integer(), server_default='0'),
        sa.Column('participants_snapshot', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('collected_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['ml_product_id'], ['ml_products.id'], ),
        sa.ForeignKeyConstraint(['monitoring_id'], ['ml_catalog_monitoring.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Índices para ml_catalog_history
    op.create_index('ix_catalog_history_company', 'ml_catalog_history', ['company_id'])
    op.create_index('ix_catalog_history_catalog_product', 'ml_catalog_history', ['catalog_product_id'])
    op.create_index('ix_catalog_history_ml_product', 'ml_catalog_history', ['ml_product_id'])
    op.create_index('ix_catalog_history_monitoring', 'ml_catalog_history', ['monitoring_id'])
    op.create_index('ix_catalog_history_collected_at', 'ml_catalog_history', ['collected_at'])
    op.create_index('ix_catalog_history_company_catalog', 'ml_catalog_history', ['company_id', 'catalog_product_id'])
    op.create_index('ix_catalog_history_company_collected', 'ml_catalog_history', ['company_id', 'collected_at'])


def downgrade():
    # Drop ml_catalog_history
    op.drop_index('ix_catalog_history_company_collected', 'ml_catalog_history')
    op.drop_index('ix_catalog_history_company_catalog', 'ml_catalog_history')
    op.drop_index('ix_catalog_history_collected_at', 'ml_catalog_history')
    op.drop_index('ix_catalog_history_monitoring', 'ml_catalog_history')
    op.drop_index('ix_catalog_history_ml_product', 'ml_catalog_history')
    op.drop_index('ix_catalog_history_catalog_product', 'ml_catalog_history')
    op.drop_index('ix_catalog_history_company', 'ml_catalog_history')
    op.drop_table('ml_catalog_history')
    
    # Drop ml_catalog_monitoring
    op.drop_index('ix_catalog_monitoring_active', 'ml_catalog_monitoring')
    op.drop_index('ix_catalog_monitoring_company_catalog', 'ml_catalog_monitoring')
    op.drop_index('ix_catalog_monitoring_is_active', 'ml_catalog_monitoring')
    op.drop_index('ix_catalog_monitoring_catalog_product', 'ml_catalog_monitoring')
    op.drop_index('ix_catalog_monitoring_company', 'ml_catalog_monitoring')
    op.drop_table('ml_catalog_monitoring')

