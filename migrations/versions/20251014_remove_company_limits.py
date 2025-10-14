"""remove company limits

Revision ID: 20251014_remove_company_limits
Revises: 20251013_fix_orderstatus_enum
Create Date: 2025-10-14 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251014_remove_company_limits'
down_revision = '20251013_fix_orderstatus_enum'
branch_labels = None
depends_on = None


def upgrade():
    # Remover colunas max_users e max_ml_accounts da tabela companies
    op.drop_column('companies', 'max_users')
    op.drop_column('companies', 'max_ml_accounts')


def downgrade():
    # Restaurar colunas se necessário
    op.add_column('companies', sa.Column('max_users', sa.Integer(), nullable=True, server_default='10'))
    op.add_column('companies', sa.Column('max_ml_accounts', sa.Integer(), nullable=True, server_default='5'))

