"""add invoice fields to ml_orders

Revision ID: add_invoice_fields
Revises: 
Create Date: 2025-10-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_invoice_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar campos de nota fiscal na tabela ml_orders
    op.add_column('ml_orders', sa.Column('invoice_emitted', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('ml_orders', sa.Column('invoice_emitted_at', sa.DateTime(), nullable=True))
    op.add_column('ml_orders', sa.Column('invoice_number', sa.String(20), nullable=True))
    op.add_column('ml_orders', sa.Column('invoice_series', sa.String(10), nullable=True))
    op.add_column('ml_orders', sa.Column('invoice_key', sa.String(44), nullable=True))
    op.add_column('ml_orders', sa.Column('invoice_xml_url', sa.String(500), nullable=True))
    op.add_column('ml_orders', sa.Column('invoice_pdf_url', sa.String(500), nullable=True))
    
    # Criar índice para otimizar consultas por status de nota fiscal
    op.create_index('ix_ml_orders_invoice_emitted', 'ml_orders', ['invoice_emitted'])


def downgrade():
    # Remover índice
    op.drop_index('ix_ml_orders_invoice_emitted', table_name='ml_orders')
    
    # Remover colunas
    op.drop_column('ml_orders', 'invoice_pdf_url')
    op.drop_column('ml_orders', 'invoice_xml_url')
    op.drop_column('ml_orders', 'invoice_key')
    op.drop_column('ml_orders', 'invoice_series')
    op.drop_column('ml_orders', 'invoice_number')
    op.drop_column('ml_orders', 'invoice_emitted_at')
    op.drop_column('ml_orders', 'invoice_emitted')

