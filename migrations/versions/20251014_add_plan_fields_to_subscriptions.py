"""add plan fields to subscriptions

Revision ID: 20251014_add_plan_fields
Revises: 20251013_fix_orderstatus_enum
Create Date: 2025-10-14 12:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251014_add_plan_fields'
down_revision = '20251013_fix_orderstatus_enum'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar novos campos para planos
    op.add_column('subscriptions', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('subscriptions', sa.Column('billing_cycle', sa.String(20), server_default='monthly', nullable=True))
    
    # Limites básicos
    op.add_column('subscriptions', sa.Column('max_users', sa.Integer(), server_default='10', nullable=True))
    op.add_column('subscriptions', sa.Column('max_ml_accounts', sa.Integer(), server_default='5', nullable=True))
    
    # Recursos vendidos no plano
    op.add_column('subscriptions', sa.Column('storage_gb', sa.Integer(), server_default='5', nullable=True))
    op.add_column('subscriptions', sa.Column('ai_analysis_monthly', sa.Integer(), server_default='10', nullable=True))
    op.add_column('subscriptions', sa.Column('catalog_monitoring_slots', sa.Integer(), server_default='5', nullable=True))
    op.add_column('subscriptions', sa.Column('product_mining_slots', sa.Integer(), server_default='10', nullable=True))
    op.add_column('subscriptions', sa.Column('product_monitoring_slots', sa.Integer(), server_default='20', nullable=True))
    
    op.add_column('subscriptions', sa.Column('trial_days', sa.Integer(), server_default='0', nullable=True))
    
    # Permitir que company_id seja nulo (para templates de planos)
    op.alter_column('subscriptions', 'company_id', nullable=True)


def downgrade():
    # Remover colunas adicionadas
    op.drop_column('subscriptions', 'trial_days')
    op.drop_column('subscriptions', 'product_monitoring_slots')
    op.drop_column('subscriptions', 'product_mining_slots')
    op.drop_column('subscriptions', 'catalog_monitoring_slots')
    op.drop_column('subscriptions', 'ai_analysis_monthly')
    op.drop_column('subscriptions', 'storage_gb')
    op.drop_column('subscriptions', 'max_ml_accounts')
    op.drop_column('subscriptions', 'max_users')
    op.drop_column('subscriptions', 'billing_cycle')
    op.drop_column('subscriptions', 'description')
    
    # Restaurar company_id como NOT NULL
    op.alter_column('subscriptions', 'company_id', nullable=False)

