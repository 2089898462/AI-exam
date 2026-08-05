"""add updated_at to exam_record and ai_report

Revision ID: d4e5f6g7h8i9
Revises: c1d2e3f4a5b6
Create Date: 2026-08-04 23:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd4e5f6g7h8i9'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    # exam_record 表
    exam_record_columns = {c['name'] for c in inspector.get_columns('exam_record')}
    if 'updated_at' not in exam_record_columns:
        op.add_column(
            'exam_record',
            sa.Column(
                'updated_at',
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
            ),
        )

    # ai_report 表
    ai_report_columns = {c['name'] for c in inspector.get_columns('ai_report')}
    if 'updated_at' not in ai_report_columns:
        op.add_column(
            'ai_report',
            sa.Column(
                'updated_at',
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
            ),
        )


def downgrade() -> None:
    connection = op.get_bind()

    # ai_report 表
    ai_report_columns = {c['name'] for c in sa.inspect(connection).get_columns('ai_report')}
    if 'updated_at' in ai_report_columns:
        op.drop_column('ai_report', 'updated_at')

    # exam_record 表
    exam_record_columns = {c['name'] for c in sa.inspect(connection).get_columns('exam_record')}
    if 'updated_at' in exam_record_columns:
        op.drop_column('exam_record', 'updated_at')
