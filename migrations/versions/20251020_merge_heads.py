"""merge multiple heads

Revision ID: 20251020_merge_heads
Revises: 20250113_catalog_monitoring, 20250115_add_ml_orders_receivables_field, 20251013_add_superadmin_table, 20251014_add_company_plan_fields, 20251014_add_plan_fields
Create Date: 2025-10-20 00:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251020_merge_heads'
down_revision = (
    '20250113_catalog_monitoring',
    '20250115_add_ml_orders_receivables_field',
    '20251013_add_superadmin_table',
    '20251014_add_company_plan_fields',
    '20251014_add_plan_fields',
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge point; no operations
    pass


def downgrade() -> None:
    # Cannot automatically unmerge branches
    pass


