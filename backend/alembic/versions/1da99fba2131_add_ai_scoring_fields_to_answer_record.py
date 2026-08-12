"""add_ai_scoring_fields_to_answer_record

Revision ID: 1da99fba2131
Revises: f1e2d3c4b5a6
Create Date: 2026-08-05 13:08:40.614291

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1da99fba2131'
down_revision: Union[str, None] = 'f1e2d3c4b5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite 兼容：使用 batch mode 处理约束
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    if dialect == 'sqlite':
        # SQLite: 手动添加唯一约束（通过重建表）
        # 先添加 answer_record 字段
        op.add_column('answer_record', sa.Column('ai_score', sa.Float(), nullable=True))
        op.add_column('answer_record', sa.Column('ai_confidence', sa.Float(), nullable=True))
        op.add_column('answer_record', sa.Column('ai_reason', sa.Text(), nullable=True))
        op.add_column('answer_record', sa.Column('prompt_version', sa.String(length=20), nullable=True))
        op.add_column('answer_record', sa.Column('needs_review', sa.Boolean(), nullable=False, server_default=sa.false()))
        
        # SQLite: 使用 batch_alter_table 处理 ai_report 唯一约束
        with op.batch_alter_table('ai_report', schema=None) as batch_op:
            batch_op.create_unique_constraint('uq_ai_report_exam_record', ['exam_record_id'])
        
        # SQLite: 使用 batch_alter_table 处理 exam_record status 枚举
        with op.batch_alter_table('exam_record', schema=None) as batch_op:
            batch_op.alter_column('status',
                existing_type=sa.VARCHAR(length=16),
                type_=sa.Enum('not_started', 'in_progress', 'submitted', 'graded', name='record_status'),
                existing_nullable=False,
                existing_server_default=sa.text("'not_started'"))
        
        # SQLite: 删除 grading_record 唯一索引
        with op.batch_alter_table('grading_record', schema=None) as batch_op:
            batch_op.drop_index('ix_grading_record_exam_record_id')
    else:
        # MySQL/PostgreSQL: 标准操作
        op.create_unique_constraint('uq_ai_report_exam_record', 'ai_report', ['exam_record_id'])
        op.add_column('answer_record', sa.Column('ai_score', sa.Float(), nullable=True))
        op.add_column('answer_record', sa.Column('ai_confidence', sa.Float(), nullable=True))
        op.add_column('answer_record', sa.Column('ai_reason', sa.Text(), nullable=True))
        op.add_column('answer_record', sa.Column('prompt_version', sa.String(length=20), nullable=True))
        op.add_column('answer_record', sa.Column('needs_review', sa.Boolean(), nullable=False))
        op.alter_column('exam_record', 'status',
                   existing_type=sa.VARCHAR(length=16),
                   type_=sa.Enum('not_started', 'in_progress', 'submitted', 'graded', name='record_status'),
                   existing_nullable=False,
                   existing_server_default=sa.text("'not_started'"))
        op.drop_index('ix_grading_record_exam_record_id', table_name='grading_record')


def downgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    
    if dialect == 'sqlite':
        with op.batch_alter_table('grading_record', schema=None) as batch_op:
            batch_op.create_index('ix_grading_record_exam_record_id', ['exam_record_id'], unique=1)
        
        with op.batch_alter_table('exam_record', schema=None) as batch_op:
            batch_op.alter_column('status',
                existing_type=sa.Enum('not_started', 'in_progress', 'submitted', 'graded', name='record_status'),
                type_=sa.VARCHAR(length=16),
                existing_nullable=False,
                existing_server_default=sa.text("'not_started'"))
        
        op.drop_column('answer_record', 'needs_review')
        op.drop_column('answer_record', 'prompt_version')
        op.drop_column('answer_record', 'ai_reason')
        op.drop_column('answer_record', 'ai_confidence')
        op.drop_column('answer_record', 'ai_score')
        
        with op.batch_alter_table('ai_report', schema=None) as batch_op:
            batch_op.drop_constraint('uq_ai_report_exam_record', type_='unique')
    else:
        op.create_index('ix_grading_record_exam_record_id', 'grading_record', ['exam_record_id'], unique=1)
        op.alter_column('exam_record', 'status',
                   existing_type=sa.Enum('not_started', 'in_progress', 'submitted', 'graded', name='record_status'),
                   type_=sa.VARCHAR(length=16),
                   existing_nullable=False,
                   existing_server_default=sa.text("'not_started'"))
        op.drop_column('answer_record', 'needs_review')
        op.drop_column('answer_record', 'prompt_version')
        op.drop_column('answer_record', 'ai_reason')
        op.drop_column('answer_record', 'ai_confidence')
        op.drop_column('answer_record', 'ai_score')
        op.drop_constraint('uq_ai_report_exam_record', 'ai_report', type_='unique')
