"""add_hr_review_fields

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d2
Create Date: 2026-08-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e7f8a9b0c1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add review_score and review_comment columns to grading_record table."""
    op.add_column(
        'grading_record',
        sa.Column(
            'review_score',
            sa.Numeric(precision=8, scale=2),
            nullable=True,
            comment='HR复核分数',
        )
    )
    op.add_column(
        'grading_record',
        sa.Column(
            'review_comment',
            sa.Text(),
            nullable=True,
            comment='HR复核备注',
        )
    )


def downgrade() -> None:
    """Remove review_score and review_comment columns from grading_record table."""
    op.drop_column('grading_record', 'review_comment')
    op.drop_column('grading_record', 'review_score')
