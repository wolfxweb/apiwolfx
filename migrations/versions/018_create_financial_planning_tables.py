"""Create financial planning tables

Revision ID: 018_create_financial_planning_tables
Revises: 017_add_ml_orders_field
Create Date: 2025-10-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '018_create_financial_planning_tables'
down_revision = '20251020_merge_heads'
branch_labels = None
depends_on = None


def upgrade():
    # Create financial_planning table
    op.create_table('financial_planning',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_financial_planning_id'), 'financial_planning', ['id'], unique=False)
    op.create_index(op.f('ix_financial_planning_company_id'), 'financial_planning', ['company_id'], unique=False)

    # Create monthly_planning table
    op.create_table('monthly_planning',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('planning_id', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('expected_revenue', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('expected_margin_percent', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('expected_margin_value', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['planning_id'], ['financial_planning.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_monthly_planning_id'), 'monthly_planning', ['id'], unique=False)

    # Create cost_center_planning table
    op.create_table('cost_center_planning',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('monthly_planning_id', sa.Integer(), nullable=False),
        sa.Column('cost_center_id', sa.Integer(), nullable=False),
        sa.Column('max_spending', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['cost_center_id'], ['cost_centers.id'], ),
        sa.ForeignKeyConstraint(['monthly_planning_id'], ['monthly_planning.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cost_center_planning_id'), 'cost_center_planning', ['id'], unique=False)

    # Create category_planning table
    op.create_table('category_planning',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cost_center_planning_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('max_spending', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['financial_categories.id'], ),
        sa.ForeignKeyConstraint(['cost_center_planning_id'], ['cost_center_planning.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_category_planning_id'), 'category_planning', ['id'], unique=False)


def downgrade():
    # Drop tables in reverse order
    op.drop_index(op.f('ix_category_planning_id'), table_name='category_planning')
    op.drop_table('category_planning')
    
    op.drop_index(op.f('ix_cost_center_planning_id'), table_name='cost_center_planning')
    op.drop_table('cost_center_planning')
    
    op.drop_index(op.f('ix_monthly_planning_id'), table_name='monthly_planning')
    op.drop_table('monthly_planning')
    
    op.drop_index(op.f('ix_financial_planning_company_id'), table_name='financial_planning')
    op.drop_index(op.f('ix_financial_planning_id'), table_name='financial_planning')
    op.drop_table('financial_planning')
