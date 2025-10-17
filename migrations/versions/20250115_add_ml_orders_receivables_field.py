"""Add ml_orders_as_receivables field to companies table

Revision ID: 20250115_add_ml_orders_receivables_field
Revises: 20251014_remove_company_limits
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250115_add_ml_orders_receivables_field'
down_revision = '20251014_remove_company_limits'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar coluna para controlar se pedidos do ML devem ser contas a receber
    op.add_column('companies', sa.Column('ml_orders_as_receivables', sa.Boolean(), nullable=False, server_default='true'))


def downgrade():
    # Remover a coluna
    op.drop_column('companies', 'ml_orders_as_receivables')
