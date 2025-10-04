"""Fix ml_order_id field type

Revision ID: 196099bd573d
Revises: d47b12a95c94
Create Date: 2025-10-04 20:53:42.731339

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '196099bd573d'
down_revision: Union[str, None] = 'd47b12a95c94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Alterar o tipo do campo ml_order_id de VARCHAR para BIGINT
    # Primeiro, remover o índice único
    op.drop_index('ix_ml_orders_ml_order_id', table_name='ml_orders')
    
    # Alterar o tipo da coluna usando conversão explícita
    op.execute('ALTER TABLE ml_orders ALTER COLUMN ml_order_id TYPE BIGINT USING ml_order_id::BIGINT')
    
    # Recriar o índice único com o novo tipo
    op.create_index('ix_ml_orders_ml_order_id', 'ml_orders', ['ml_order_id'], unique=True)


def downgrade() -> None:
    # Remover o índice único
    op.drop_index('ix_ml_orders_ml_order_id', table_name='ml_orders')
    
    # Reverter o tipo da coluna para VARCHAR usando conversão explícita
    op.execute('ALTER TABLE ml_orders ALTER COLUMN ml_order_id TYPE VARCHAR(50) USING ml_order_id::VARCHAR(50)')
    
    # Recriar o índice único com o tipo original
    op.create_index('ix_ml_orders_ml_order_id', 'ml_orders', ['ml_order_id'], unique=True)
