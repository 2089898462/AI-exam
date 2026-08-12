"""add_score_level_to_answer_record

Revision ID: e7f8a9b0c1d2
Revises: d4e5f6g7h8i9
Create Date: 2026-08-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, None] = '3a551392374b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add score_level column to answer_record table."""
    op.add_column(
        'answer_record',
        sa.Column(
            'score_level',
            sa.Enum('full_correct', 'partial_correct', 'incorrect', name='score_level'),
            nullable=True,
            comment='评分等级：完全正确/部分正确/错误',
        )
    )


def downgrade() -> None:
    """Remove score_level column from answer_record table."""
    op.drop_column('answer_record', 'score_level')
