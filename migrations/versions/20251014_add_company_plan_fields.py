"""add company plan fields

Revision ID: 20251014_add_company_plan_fields
Revises: 20251013_fix_orderstatus_enum
Create Date: 2025-10-14 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251014_add_company_plan_fields'
down_revision = '20251013_fix_orderstatus_enum'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar novos campos na tabela companies
    op.add_column('companies', sa.Column('plan_expires_at', sa.DateTime(), nullable=True))
    op.add_column('companies', sa.Column('max_catalog_monitoring', sa.Integer(), nullable=True, server_default='5'))
    op.add_column('companies', sa.Column('ai_analysis_limit', sa.Integer(), nullable=True, server_default='10'))
    op.add_column('companies', sa.Column('ai_analysis_extra_package', sa.Integer(), nullable=True, server_default='0'))


def downgrade():
    # Remover colunas adicionadas
    op.drop_column('companies', 'ai_analysis_extra_package')
    op.drop_column('companies', 'ai_analysis_limit')
    op.drop_column('companies', 'max_catalog_monitoring')
    op.drop_column('companies', 'plan_expires_at')

