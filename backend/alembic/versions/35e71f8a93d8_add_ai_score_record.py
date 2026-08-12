"""add_ai_score_record

Revision ID: 35e71f8a93d8
Revises: d4c5e6f7a8b9
Create Date: 2026-08-06 11:16:57.051090

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '35e71f8a93d8'
down_revision: Union[str, None] = 'd4c5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_score_record',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('answer_record_id', sa.Integer(), nullable=False),
        sa.Column('ai_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('max_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('score_reason', sa.Text(), nullable=False),
        sa.Column('matched_points', sa.Text(), nullable=True),
        sa.Column('missing_points', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=True),
        sa.Column('prompt_version', sa.String(length=20), nullable=False),
        sa.Column(
            'review_status',
            sa.Enum('pending', 'ai_scored', 'hr_confirmed', 'completed', 'rejected', name='ai_score_review_status'),
            nullable=False,
        ),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('hr_remark', sa.Text(), nullable=True),
        sa.Column('confirmed_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['answer_record_id'], ['answer_record.id']),
        sa.ForeignKeyConstraint(['reviewed_by'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ai_score_record_answer_record_id'), 'ai_score_record', ['answer_record_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ai_score_record_answer_record_id'), table_name='ai_score_record')
    op.drop_table('ai_score_record')
