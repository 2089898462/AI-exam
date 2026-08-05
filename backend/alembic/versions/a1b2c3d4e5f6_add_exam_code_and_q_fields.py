"""add exam_code and question fields

Revision ID: a1b2c3d4e5f6
Revises: db2a7edfcf67
Create Date: 2026-08-04 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "db2a7edfcf67"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("exam") as batch_op:
        batch_op.add_column(sa.Column("exam_code", sa.String(length=50), nullable=True))
        batch_op.create_unique_constraint("uq_exam_exam_code", ["exam_code"])

    with op.batch_alter_table("question") as batch_op:
        batch_op.add_column(sa.Column("question_no", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("category", sa.String(length=50), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("question") as batch_op:
        batch_op.drop_column("category")
        batch_op.drop_column("question_no")

    with op.batch_alter_table("exam") as batch_op:
        batch_op.drop_constraint("uq_exam_exam_code", type_="unique")
        batch_op.drop_column("exam_code")
