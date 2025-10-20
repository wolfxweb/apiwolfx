"""add card fields to financial_accounts

Revision ID: 20251020_add_card_fields
Revises: 
Create Date: 2025-10-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251020_add_card_fields'
down_revision = '20251020_merge_heads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add optional credit card fields
    with op.batch_alter_table('financial_accounts') as batch_op:
        batch_op.add_column(sa.Column('card_number', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('invoice_due_day', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove columns
    with op.batch_alter_table('financial_accounts') as batch_op:
        batch_op.drop_column('invoice_due_day')
        batch_op.drop_column('card_number')


