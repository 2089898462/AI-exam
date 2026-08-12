"""S3.3.1 add grading_record and question_score_rule tables

Revision ID: f1e2d3c4b5a6
Revises: e1f2a3b4c5d6
Create Date: 2026-08-05 18:00:00.000000

变更说明：
- 新增 grading_record 表：评分记录表，跟踪考试评分过程和结果
- 新增 question_score_rule 表：题目评分规则表，定义不同题型的评分策略
"""
from alembic import op
import sqlalchemy as sa


revision = 'f1e2d3c4b5a6'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # grading_record 表
    # ============================================================
    op.create_table(
        'grading_record',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('exam_record_id', sa.Integer(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('pending', 'grading', 'completed', 'failed', name='grading_status'),
            nullable=False,
            server_default='pending',
        ),
        sa.Column(
            'grading_type',
            sa.Enum('auto', 'ai', 'hybrid', name='grading_type'),
            nullable=False,
            server_default='auto',
        ),
        sa.Column('total_score', sa.Numeric(8, 2), nullable=True),
        sa.Column('auto_score', sa.Numeric(8, 2), nullable=True),
        sa.Column('ai_score', sa.Numeric(8, 2), nullable=True),
        sa.Column('passed', sa.Boolean(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['exam_record_id'], ['exam_record.id'],
            name='fk_grading_record_exam_record_id'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('exam_record_id', name='uq_grading_record_exam_record'),
    )
    op.create_index(
        op.f('ix_grading_record_exam_record_id'),
        'grading_record', ['exam_record_id'],
        unique=True,
    )

    # ============================================================
    # question_score_rule 表
    # ============================================================
    op.create_table(
        'question_score_rule',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('exam_id', sa.Integer(), nullable=False),
        sa.Column(
            'question_type',
            sa.Enum(
                'single_choice', 'multiple_choice', 'true_false', 'short_answer',
                name='rule_question_type'
            ),
            nullable=False,
        ),
        sa.Column(
            'score_method',
            sa.Enum('auto_compare', 'ai_score', 'manual', name='score_method'),
            nullable=False,
            server_default='auto_compare',
        ),
        sa.Column(
            'pass_score',
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text('0'),
        ),
        sa.Column(
            'weight',
            sa.Numeric(3, 2),
            nullable=False,
            server_default=sa.text('1.00'),
        ),
        sa.Column(
            'is_enabled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
        ),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['exam_id'], ['exam.id'],
            name='fk_score_rule_exam_id'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_question_score_rule_exam_id'),
        'question_score_rule', ['exam_id'],
    )


def downgrade() -> None:
    # ============================================================
    # 删除 question_score_rule 表
    # ============================================================
    op.drop_index(
        op.f('ix_question_score_rule_exam_id'),
        table_name='question_score_rule',
    )
    op.drop_table('question_score_rule')

    # ============================================================
    # 删除 grading_record 表
    # ============================================================
    op.drop_index(
        op.f('ix_grading_record_exam_record_id'),
        table_name='grading_record',
    )
    op.drop_table('grading_record')
