"""Add onboarding_completed column to usuarios table

Revision ID: 002
Revises: 001
Create Date: 2025-09-17 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Add onboarding_completed column to usuarios table
    op.add_column('usuarios', sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default='false'))


def downgrade():
    # Remove onboarding_completed column from usuarios table
    op.drop_column('usuarios', 'onboarding_completed')





