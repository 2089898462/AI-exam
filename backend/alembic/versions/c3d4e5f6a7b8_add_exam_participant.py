"""S4.3-A 新增 exam_participant 表

Revision ID: c3d4e5f6a7b8
Revises: b5c6d7e8f9a0
Create Date: 2026-08-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b5c6d7e8f9a0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建考试参与人员表
    op.create_table(
        'exam_participant',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('exam_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('candidate_name', sa.String(length=64), nullable=False),
        sa.Column('candidate_phone', sa.String(length=20), nullable=True),
        sa.Column('candidate_email', sa.String(length=128), nullable=True),
        sa.Column(
            'status',
            sa.Enum('assigned', 'not_started', 'in_progress', 'submitted', 'completed', name='participant_status'),
            nullable=False,
            server_default='assigned',
        ),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['exam_id'], ['exam.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('exam_id', 'candidate_phone', name='uq_exam_participant_phone'),
    )
    op.create_index(op.f('ix_exam_participant_exam_id'), 'exam_participant', ['exam_id'], unique=False)
    op.create_index(op.f('ix_exam_participant_user_id'), 'exam_participant', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_exam_participant_user_id'), table_name='exam_participant')
    op.drop_index(op.f('ix_exam_participant_exam_id'), table_name='exam_participant')
    op.drop_table('exam_participant')
