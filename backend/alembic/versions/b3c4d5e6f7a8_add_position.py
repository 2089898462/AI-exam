"""add position field to exam

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-08-04 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'b3c4d5e6f7a8'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('exam') as batch_op:
        batch_op.add_column(sa.Column('position', sa.String(length=100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('exam') as batch_op:
        batch_op.drop_column('position')