"""S3.3.6 expand ai_report table

Revision ID: a1b2c3d4e5f7
Revises: 1da99fba2131
Create Date: 2026-08-05 22:00:00.000000

变更说明：
- ai_report 表新增字段：summary, skill_analysis, interview_suggestions,
  recommendation, model_used, prompt_version, status, updated_at
- 移除原 learning_suggestions 字段
"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f7'
down_revision = '1da99fba2131'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ai_report 表新增字段
    with op.batch_alter_table('ai_report', schema=None) as batch_op:
        batch_op.add_column(sa.Column('summary', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('skill_analysis', sa.JSON(), nullable=False, server_default='{}'))
        batch_op.add_column(sa.Column('interview_suggestions', sa.JSON(), nullable=False, server_default='[]'))
        batch_op.add_column(sa.Column('recommendation', sa.String(length=50), nullable=False, server_default='保留考虑'))
        batch_op.add_column(sa.Column('model_used', sa.String(length=50), nullable=False, server_default='qwen-plus'))
        batch_op.add_column(sa.Column('prompt_version', sa.String(length=20), nullable=False, server_default='1.0'))
        batch_op.add_column(sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('ai_report', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('status')
        batch_op.drop_column('prompt_version')
        batch_op.drop_column('model_used')
        batch_op.drop_column('recommendation')
        batch_op.drop_column('interview_suggestions')
        batch_op.drop_column('skill_analysis')
        batch_op.drop_column('summary')
