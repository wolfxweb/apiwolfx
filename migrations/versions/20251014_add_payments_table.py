"""placeholder payments table migration (no-op)

Revision ID: 20251014_add_payments_table
Revises: 20251013_fix_orderstatus_enum
Create Date: 2025-10-14 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251014_add_payments_table'
down_revision = '20251013_fix_orderstatus_enum'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op placeholder to satisfy historical reference
    pass


def downgrade() -> None:
    # No-op
    pass


